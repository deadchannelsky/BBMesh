"""
TradeWars Plugin for BBMesh - Classic space trading game adapted for async mesh
"""

import random
from typing import Dict, Any, Optional

from bbmesh.plugins.base import InteractivePlugin, PluginContext, PluginResponse
from .tradewars_storage import TradeWarsStorage
from .tradewars_universe import UniverseManager
from .tradewars_trade_calculator import TradeCalculator
from .tradewars_formatters import MessageFormatter


class TradeWarsPlugin(InteractivePlugin):
    """
    TradeWars - A space trading game for BBMesh

    MVP Features:
    - Player registration tied to node IDs
    - 100-sector universe with pathfinding
    - Port trading with dynamic prices
    - Cargo management
    - Persistent state across reboots
    """

    def __init__(self, name: str = "tradewars", config: Dict[str, Any] = None):
        if config is None:
            config = {"enabled": True, "description": "TradeWars space trading game"}
        super().__init__(name, config)

        # Initialize game components
        self.storage = TradeWarsStorage()
        self.universe = UniverseManager()
        self.trade_calc = TradeCalculator()
        self.formatter = MessageFormatter()

        # Initialize universe on first load
        self._ensure_universe_initialized()

    def _ensure_universe_initialized(self) -> None:
        """Initialize universe if not already done"""
        if self.storage.get_state("universe_initialized") != "true":
            self.logger.info("Initializing universe...")
            self.universe.generate_universe()
            self.universe.select_port_sectors()

            # Create sectors in database
            for sector_id in range(1, 101):
                connected = self.universe.get_connected_sectors(sector_id)

                # Determine if this sector has a port
                port_id = None
                if sector_id in self.universe.ports:
                    # Create port for this sector
                    port_name = self.universe.get_port_name(sector_id)
                    inventory = self.trade_calc.generate_port_inventory()
                    port_id = self.storage.create_port(
                        sector_id, port_name, 5000000, inventory
                    )

                self.storage.create_sector(sector_id, connected, port_id)

            self.storage.set_state("universe_initialized", "true")
            self.logger.info("Universe initialized with 100 sectors and 30 ports")

    def initialize(self) -> bool:
        """Initialize plugin"""
        if not super().initialize():
            return False

        # Verify database connectivity
        try:
            self._ensure_universe_initialized()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize TradeWars: {e}")
            return False

    # ===== Session Management =====

    def start_session(self, context: PluginContext) -> PluginResponse:
        """Start new game session or continue existing"""
        try:
            self.logger.info(f"[TRADEWARS START_SESSION] Node: {context.user_id}")
            node_id = context.user_id
            player = self.storage.get_player_by_node_id(node_id)

            if player is None:
                # New player - start registration
                self.logger.info(f"[TRADEWARS] New player, starting registration")
                return self._handle_registration_start(context)
            else:
                # Returning player - show main view
                return self._handle_sector_view(context, player["player_id"])

        except Exception as e:
            self.logger.error(f"Error in start_session: {e}")
            return PluginResponse(
                text=self.formatter.database_error(),
                continue_session=False,
                error=str(e)
            )

    def continue_session(self, context: PluginContext) -> PluginResponse:
        """Continue existing game session"""
        try:
            state = context.session_data.get(f"{self.name}_state", "SECTOR_VIEW")
            user_input = context.message.text.strip().upper()

            self.logger.info(f"[TRADEWARS CONTINUE_SESSION] START - State: {state}, Input: {user_input}")
            self.logger.info(f"[TRADEWARS CONTINUE_SESSION] session_data keys: {list(context.session_data.keys())}")
            self.logger.info(f"[TRADEWARS CONTINUE_SESSION] Full session_data: {context.session_data}")

            # During registration, we don't have a player_id yet
            if state == "REGISTRATION":
                # Handle registration flow (no player_id required)
                self.logger.info(f"[TRADEWARS CONTINUE_SESSION] Detected REGISTRATION state, calling _handle_registration_confirm")
                result = self._handle_registration_confirm(context, None, user_input)
                self.logger.info(f"[TRADEWARS CONTINUE_SESSION] _handle_registration_confirm returned: text={result.text[:50]}...")
                return result

            # For other states, player_id is required
            player_id = context.session_data.get(f"{self.name}_player_id")
            if not player_id:
                # Session lost - restart
                return self.start_session(context)

            # Route to appropriate handler based on state
            state_handlers = {
                "SECTOR_VIEW": self._handle_sector_view_input,
                "NAVIGATION": self._handle_navigation_input,
                "IN_PORT": self._handle_port_menu_input,
                "PORT_BUY": self._handle_port_buy_input,
                "PORT_SELL": self._handle_port_sell_input,
                "TRADE_QUANTITY": self._handle_trade_quantity_input,
                "VIEW_CARGO": self._handle_cargo_view_input,
                "VIEW_STATS": self._handle_stats_view_input,
            }

            handler = state_handlers.get(state, self._handle_sector_view)
            return handler(context, player_id, user_input)

        except Exception as e:
            self.logger.error(f"[TRADEWARS CONTINUE_SESSION] ERROR: {e}", exc_info=True)
            import traceback
            self.logger.error(f"[TRADEWARS CONTINUE_SESSION] Traceback: {traceback.format_exc()}")
            return PluginResponse(
                text=self.formatter.database_error(),
                continue_session=True,
                session_data=context.session_data,
                error=str(e)
            )

    # ===== Registration Flow =====

    def _handle_registration_start(self, context: PluginContext) -> PluginResponse:
        """Start player registration"""
        session_data = context.session_data.copy()
        session_data[f"{self.name}_active"] = True
        session_data[f"{self.name}_state"] = "REGISTRATION"

        self.logger.info(f"[TRADEWARS REGISTRATION_START] Returning session_data with active=True, state=REGISTRATION")
        self.logger.info(f"[TRADEWARS REGISTRATION_START] Session data: {session_data}")

        return PluginResponse(
            text=self.formatter.registration_prompt(),
            continue_session=True,
            session_data=session_data
        )

    def _handle_registration_confirm(self, context: PluginContext, player_id: int,
                                     user_input: str) -> PluginResponse:
        """Handle registration confirmation"""
        self.logger.info(f"[TRADEWARS REG_CONFIRM] Entered with input={user_input}")
        session_data = context.session_data.copy()
        self.logger.info(f"[TRADEWARS REG_CONFIRM] session_data keys: {list(session_data.keys())}")

        # First message - user provides name
        has_temp_name = f"{self.name}_temp_name" in session_data
        self.logger.info(f"[TRADEWARS REG_CONFIRM] has_temp_name={has_temp_name}")
        if not has_temp_name:
            # Validate name
            if len(user_input) < 1 or len(user_input) > 8:
                return PluginResponse(
                    text=self.formatter.name_invalid("Must be 1-8 chars"),
                    continue_session=True,
                    session_data=session_data
                )

            if not user_input.isalnum():
                return PluginResponse(
                    text=self.formatter.name_invalid("Alphanumeric only"),
                    continue_session=True,
                    session_data=session_data
                )

            # Check uniqueness
            player = self.storage.get_player_by_node_id(context.user_id)
            if player:
                return PluginResponse(
                    text="You're already registered!",
                    continue_session=False
                )

            # Store temp name and ask for confirmation
            session_data[f"{self.name}_temp_name"] = user_input
            return PluginResponse(
                text=self.formatter.registration_confirm(user_input),
                continue_session=True,
                session_data=session_data
            )

        # Second message - confirmation Y/N
        temp_name = session_data[f"{self.name}_temp_name"]

        if user_input in ["Y", "YES"]:
            # Create player and ship
            player_id = self.storage.create_player(context.user_id, temp_name)
            starting_sector = self.universe.get_starting_sector()
            self.storage.create_ship(player_id, starting_sector)

            self.logger.info(f"Created player {temp_name} at sector {starting_sector}")

            # Prepare session for main game
            session_data[f"{self.name}_player_id"] = player_id
            session_data[f"{self.name}_state"] = "SECTOR_VIEW"
            del session_data[f"{self.name}_temp_name"]

            # Get player and show sector view
            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)

            return PluginResponse(
                text=self.formatter.welcome_message(
                    temp_name, ship["current_sector"],
                    player["credits"], player["turns"]
                ),
                continue_session=True,
                session_data=session_data
            )

        elif user_input in ["N", "NO"]:
            # Try again
            del session_data[f"{self.name}_temp_name"]
            return PluginResponse(
                text="OK, new name?",
                continue_session=True,
                session_data=session_data
            )

        else:
            return PluginResponse(
                text="Y or N?",
                continue_session=True,
                session_data=session_data
            )

    # ===== Sector View =====

    def _handle_sector_view(self, context: PluginContext, player_id: int) -> PluginResponse:
        """Show sector view (initial entry)"""
        try:
            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)

            if not player or not ship:
                return PluginResponse(text="Error loading game state", continue_session=False)

            sector = self.storage.get_sector(ship["current_sector"])
            has_port = sector.get("port_id") is not None

            session_data = context.session_data.copy()
            session_data[f"{self.name}_active"] = True
            session_data[f"{self.name}_player_id"] = player_id
            session_data[f"{self.name}_state"] = "SECTOR_VIEW"
            session_data[f"{self.name}_current_sector"] = ship["current_sector"]

            response_text = self.formatter.sector_view(
                ship["current_sector"],
                sector["connected_sectors"],
                has_port,
                1,  # number of ships (always 1 in MVP)
                player["turns"],
                player["credits"]
            )

            return PluginResponse(
                text=response_text,
                continue_session=True,
                session_data=session_data
            )

        except Exception as e:
            self.logger.error(f"Error in sector_view: {e}")
            return PluginResponse(text=self.formatter.database_error(), continue_session=False, error=str(e))

    def _handle_sector_view_input(self, context: PluginContext, player_id: int,
                                 user_input: str) -> PluginResponse:
        """Handle commands in SECTOR_VIEW state"""
        session_data = context.session_data.copy()

        # SCAN/R command - re-display sector view
        if user_input in ["R", "SCAN"]:
            return self._handle_sector_view(context, player_id)

        if user_input == "M":
            # Show navigation menu
            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)
            sector = self.storage.get_sector(ship["current_sector"])

            session_data[f"{self.name}_state"] = "NAVIGATION"
            return PluginResponse(
                text=self.formatter.navigation_menu(
                    ship["current_sector"], sector["connected_sectors"]
                ),
                continue_session=True,
                session_data=session_data
            )

        elif user_input.startswith("M") and user_input[1:].isdigit():
            # Quick warp M### format
            dest_sector = int(user_input[1:])
            return self._execute_warp(context, player_id, dest_sector, session_data)

        elif user_input == "P":
            # Enter port
            ship = self.storage.get_ship_by_player_id(player_id)
            sector = self.storage.get_sector(ship["current_sector"])

            if sector.get("port_id") is None:
                return PluginResponse(
                    text="No port in this sector",
                    continue_session=True,
                    session_data=session_data
                )

            port = self.storage.get_port_by_id(sector["port_id"])
            session_data[f"{self.name}_state"] = "IN_PORT"
            session_data[f"{self.name}_port_id"] = port["port_id"]

            player = self.storage.get_player_by_id(player_id)
            return PluginResponse(
                text=self.formatter.port_menu(
                    ship["current_sector"], player["credits"], port["credits"]
                ),
                continue_session=True,
                session_data=session_data
            )

        elif user_input == "C":
            # View cargo
            ship = self.storage.get_ship_by_player_id(player_id)
            cargo_used = self.storage.get_cargo_used(ship["cargo"])

            session_data[f"{self.name}_state"] = "VIEW_CARGO"
            return PluginResponse(
                text=self.formatter.cargo_view(ship["cargo"], cargo_used, ship["cargo_holds"]),
                continue_session=True,
                session_data=session_data
            )

        elif user_input == "S":
            # View stats
            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)

            session_data[f"{self.name}_state"] = "VIEW_STATS"
            return PluginResponse(
                text=self.formatter.stats_view(
                    player["player_name"], player["credits"], player["turns"],
                    player["score"], player["total_warps"], player["total_trades"],
                    ship["current_sector"]
                ),
                continue_session=True,
                session_data=session_data
            )

        elif user_input == "H":
            # Help
            return PluginResponse(
                text=self.formatter.help_text(),
                continue_session=True,
                session_data=session_data
            )

        else:
            return PluginResponse(
                text="Unknown command. H=help",
                continue_session=True,
                session_data=session_data
            )

    # ===== Navigation =====

    def _handle_navigation_input(self, context: PluginContext, player_id: int,
                                user_input: str) -> PluginResponse:
        """Handle navigation input"""
        session_data = context.session_data.copy()

        if user_input == "0":
            # Cancel navigation
            session_data[f"{self.name}_state"] = "SECTOR_VIEW"
            return self._handle_sector_view(context, player_id)

        if not user_input.isdigit():
            return PluginResponse(
                text="Enter sector number",
                continue_session=True,
                session_data=session_data
            )

        return self._execute_warp(context, player_id, int(user_input), session_data)

    def _execute_warp(self, context: PluginContext, player_id: int,
                     dest_sector: int, session_data: Dict) -> PluginResponse:
        """Execute warp to destination sector"""
        try:
            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)
            current_sector = ship["current_sector"]

            # Validate destination
            if dest_sector < 1 or dest_sector > 100:
                return PluginResponse(
                    text=self.formatter.error_message("Invalid sector"),
                    continue_session=True,
                    session_data=session_data
                )

            # Find path
            path = self.universe.find_path(current_sector, dest_sector)
            if not path:
                return PluginResponse(
                    text=self.formatter.error_message("Unreachable sector"),
                    continue_session=True,
                    session_data=session_data
                )

            turns_needed = len(path) - 1
            if player["turns"] < turns_needed:
                return PluginResponse(
                    text=self.formatter.not_enough_turns(turns_needed, player["turns"]),
                    continue_session=True,
                    session_data=session_data
                )

            # Execute warp
            self.storage.update_ship_location(ship["ship_id"], dest_sector)
            new_turns = player["turns"] - turns_needed
            new_warps = player["total_warps"] + 1

            self.storage.update_player_stats(
                player_id, turns=new_turns, total_warps=new_warps
            )

            # Return to sector view with full display
            session_data[f"{self.name}_state"] = "SECTOR_VIEW"
            session_data[f"{self.name}_current_sector"] = dest_sector
            return self._handle_sector_view(context, player_id)

        except Exception as e:
            self.logger.error(f"Error in execute_warp: {e}")
            return PluginResponse(
                text=self.formatter.database_error(),
                continue_session=True,
                session_data=session_data,
                error=str(e)
            )

    # ===== Port Operations =====

    def _handle_port_menu_input(self, context: PluginContext, player_id: int,
                               user_input: str) -> PluginResponse:
        """Handle port main menu"""
        session_data = context.session_data.copy()
        port_id = session_data.get(f"{self.name}_port_id")

        if user_input == "0":
            # Exit port
            session_data[f"{self.name}_state"] = "SECTOR_VIEW"
            return self._handle_sector_view(context, player_id)

        elif user_input == "1":
            # Buy menu
            port = self.storage.get_port_by_id(port_id)
            session_data[f"{self.name}_state"] = "PORT_BUY"
            return PluginResponse(
                text=self.formatter.buy_menu(port["inventory"]),
                continue_session=True,
                session_data=session_data
            )

        elif user_input == "2":
            # Sell menu
            port = self.storage.get_port_by_id(port_id)
            ship = self.storage.get_ship_by_player_id(player_id)
            session_data[f"{self.name}_state"] = "PORT_SELL"
            return PluginResponse(
                text=self.formatter.sell_menu(port["inventory"], ship["cargo"]),
                continue_session=True,
                session_data=session_data
            )

        elif user_input == "3":
            # List menu
            port = self.storage.get_port_by_id(port_id)
            return PluginResponse(
                text=self.formatter.port_list(port["inventory"]),
                continue_session=True,
                session_data=session_data
            )

        else:
            return PluginResponse(
                text="Enter 1-3 or 0 to exit",
                continue_session=True,
                session_data=session_data
            )

    def _handle_port_buy_input(self, context: PluginContext, player_id: int,
                              user_input: str) -> PluginResponse:
        """Handle port buy menu selection"""
        session_data = context.session_data.copy()
        port_id = session_data.get(f"{self.name}_port_id")

        if user_input == "0":
            # Back to port menu
            port = self.storage.get_port_by_id(port_id)
            player = self.storage.get_player_by_id(player_id)
            session_data[f"{self.name}_state"] = "IN_PORT"
            return PluginResponse(
                text=self.formatter.port_menu(
                    self.storage.get_ship_by_player_id(player_id)["current_sector"],
                    player["credits"], port["credits"]
                ),
                continue_session=True,
                session_data=session_data
            )

        if not user_input.isdigit() or int(user_input) < 1 or int(user_input) > 5:
            return PluginResponse(
                text="Enter 1-5 or 0 to back",
                continue_session=True,
                session_data=session_data
            )

        # Select commodity
        commodities = list(self.trade_calc.COMMODITIES)
        selected_idx = int(user_input) - 1

        if selected_idx >= len(commodities):
            return PluginResponse(
                text="Invalid commodity",
                continue_session=True,
                session_data=session_data
            )

        commodity = commodities[selected_idx]
        port = self.storage.get_port_by_id(port_id)
        player = self.storage.get_player_by_id(player_id)
        ship = self.storage.get_ship_by_player_id(player_id)

        # Check if can buy
        cargo_used = self.storage.get_cargo_used(ship["cargo"])
        can_buy, reason = self.trade_calc.can_buy_from_port(
            commodity, 1, player["credits"], cargo_used, ship["cargo_holds"],
            port["inventory"]
        )

        if not can_buy:
            return PluginResponse(
                text=self.formatter.trade_error(reason),
                continue_session=True,
                session_data=session_data
            )

        # Calculate max units
        item = port["inventory"][commodity]
        max_units = min(
            item["quantity"],
            ship["cargo_holds"] - cargo_used,
            int(player["credits"] / item["price"])
        )

        session_data[f"{self.name}_state"] = "TRADE_QUANTITY"
        session_data[f"{self.name}_trade_commodity"] = commodity
        session_data[f"{self.name}_trade_is_buying"] = True

        return PluginResponse(
            text=self.formatter.trade_quantity_prompt(
                commodity, max_units, item["price"], player["credits"]
            ),
            continue_session=True,
            session_data=session_data
        )

    def _handle_port_sell_input(self, context: PluginContext, player_id: int,
                               user_input: str) -> PluginResponse:
        """Handle port sell menu selection"""
        session_data = context.session_data.copy()
        port_id = session_data.get(f"{self.name}_port_id")

        if user_input == "0":
            # Back to port menu
            port = self.storage.get_port_by_id(port_id)
            player = self.storage.get_player_by_id(player_id)
            session_data[f"{self.name}_state"] = "IN_PORT"
            return PluginResponse(
                text=self.formatter.port_menu(
                    self.storage.get_ship_by_player_id(player_id)["current_sector"],
                    player["credits"], port["credits"]
                ),
                continue_session=True,
                session_data=session_data
            )

        if not user_input.isdigit() or int(user_input) < 1 or int(user_input) > 5:
            return PluginResponse(
                text="Enter 1-5 or 0 to back",
                continue_session=True,
                session_data=session_data
            )

        # Select commodity
        commodities = list(self.trade_calc.COMMODITIES)
        selected_idx = int(user_input) - 1

        if selected_idx >= len(commodities):
            return PluginResponse(
                text="Invalid commodity",
                continue_session=True,
                session_data=session_data
            )

        commodity = commodities[selected_idx]
        port = self.storage.get_port_by_id(port_id)
        player = self.storage.get_player_by_id(player_id)
        ship = self.storage.get_ship_by_player_id(player_id)

        # Check if can sell
        can_sell, reason = self.trade_calc.can_sell_to_port(
            commodity, 1, ship["cargo"], port["inventory"], port["credits"]
        )

        if not can_sell:
            return PluginResponse(
                text=self.formatter.trade_error(reason),
                continue_session=True,
                session_data=session_data
            )

        # Calculate max units
        item = port["inventory"][commodity]
        max_units = min(
            ship["cargo"][commodity],
            int(port["credits"] / item["price"])
        )

        session_data[f"{self.name}_state"] = "TRADE_QUANTITY"
        session_data[f"{self.name}_trade_commodity"] = commodity
        session_data[f"{self.name}_trade_is_buying"] = False

        return PluginResponse(
            text=self.formatter.trade_quantity_prompt(
                commodity, max_units, item["price"], player["credits"]
            ),
            continue_session=True,
            session_data=session_data
        )

    def _handle_trade_quantity_input(self, context: PluginContext, player_id: int,
                                    user_input: str) -> PluginResponse:
        """Handle trade quantity input"""
        session_data = context.session_data.copy()

        if user_input == "0":
            # Cancel trade
            session_data[f"{self.name}_state"] = "IN_PORT"
            port_id = session_data.get(f"{self.name}_port_id")
            port = self.storage.get_port_by_id(port_id)
            player = self.storage.get_player_by_id(player_id)
            return PluginResponse(
                text=self.formatter.port_menu(
                    self.storage.get_ship_by_player_id(player_id)["current_sector"],
                    player["credits"], port["credits"]
                ),
                continue_session=True,
                session_data=session_data
            )

        if not user_input.isdigit():
            return PluginResponse(
                text=self.formatter.trade_invalid_quantity(),
                continue_session=True,
                session_data=session_data
            )

        quantity = int(user_input)
        if quantity < 1:
            return PluginResponse(
                text=self.formatter.trade_invalid_quantity(),
                continue_session=True,
                session_data=session_data
            )

        # Execute trade
        return self._execute_trade(context, player_id, quantity, session_data)

    def _execute_trade(self, context: PluginContext, player_id: int,
                      quantity: int, session_data: Dict) -> PluginResponse:
        """Execute buy/sell transaction"""
        try:
            port_id = session_data.get(f"{self.name}_port_id")
            commodity = session_data.get(f"{self.name}_trade_commodity")
            is_buying = session_data.get(f"{self.name}_trade_is_buying")

            player = self.storage.get_player_by_id(player_id)
            ship = self.storage.get_ship_by_player_id(player_id)
            port = self.storage.get_port_by_id(port_id)

            item = port["inventory"][commodity]
            price = item["price"]

            if is_buying:
                # Buying from port
                cost = self.trade_calc.execute_purchase(quantity, price)
                new_credits = player["credits"] - cost
                new_cargo = ship["cargo"].copy()
                new_cargo[commodity] += quantity

                # Update storage
                self.storage.update_player_stats(
                    player_id, credits=new_credits,
                    total_trades=player["total_trades"] + 1
                )
                self.storage.update_ship_cargo(ship["ship_id"], new_cargo)

                # Update port
                new_inventory = self.trade_calc.update_port_inventory_after_buy(
                    commodity, quantity, cost, port["inventory"]
                )
                self.storage.update_port_inventory(port_id, new_inventory)
                self.storage.update_port_credits(port_id, port["credits"] + cost)

                cargo_used = self.storage.get_cargo_used(new_cargo)
                response_text = self.formatter.trade_executed(
                    commodity, quantity, cost, new_credits, cargo_used, ship["cargo_holds"]
                )

            else:
                # Selling to port
                revenue = self.trade_calc.execute_sale(quantity, price)
                new_credits = player["credits"] + revenue
                new_cargo = ship["cargo"].copy()
                new_cargo[commodity] -= quantity

                # Update storage
                self.storage.update_player_stats(
                    player_id, credits=new_credits,
                    total_trades=player["total_trades"] + 1
                )
                self.storage.update_ship_cargo(ship["ship_id"], new_cargo)

                # Update port
                new_inventory = self.trade_calc.update_port_inventory_after_sell(
                    commodity, quantity, revenue, port["inventory"]
                )
                self.storage.update_port_inventory(port_id, new_inventory)
                self.storage.update_port_credits(port_id, port["credits"] - revenue)

                cargo_used = self.storage.get_cargo_used(new_cargo)
                response_text = self.formatter.trade_sold(
                    commodity, quantity, revenue, new_credits, cargo_used
                )

            # Return to port menu
            session_data[f"{self.name}_state"] = "IN_PORT"
            updated_port = self.storage.get_port_by_id(port_id)
            updated_player = self.storage.get_player_by_id(player_id)

            return PluginResponse(
                text=response_text + "\nPress any key for menu",
                continue_session=True,
                session_data=session_data
            )

        except Exception as e:
            self.logger.error(f"Error in execute_trade: {e}")
            return PluginResponse(
                text=self.formatter.database_error(),
                continue_session=True,
                session_data=session_data,
                error=str(e)
            )

    # ===== View Commands =====

    def _handle_cargo_view_input(self, context: PluginContext, player_id: int,
                                user_input: str) -> PluginResponse:
        """Return from cargo view"""
        session_data = context.session_data.copy()
        session_data[f"{self.name}_state"] = "SECTOR_VIEW"
        return self._handle_sector_view(context, player_id)

    def _handle_stats_view_input(self, context: PluginContext, player_id: int,
                                user_input: str) -> PluginResponse:
        """Return from stats view"""
        session_data = context.session_data.copy()
        session_data[f"{self.name}_state"] = "SECTOR_VIEW"
        return self._handle_sector_view(context, player_id)

    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.storage:
            self.storage.close()
        super().cleanup()
