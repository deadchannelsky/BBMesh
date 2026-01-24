"""
TradeWars Plugin - Message Formatting for 200 Character Limit
"""

from typing import Dict, List, Optional


class MessageFormatter:
    """Formats messages for 200 character mesh network limit"""

    MAX_LENGTH = 200

    # Abbreviations for saving space
    COMMODITY_SHORT = {
        "Ore": "Or",
        "Organics": "Og",
        "Equipment": "Eq",
        "Armor": "Ar",
        "Batteries": "Ba"
    }

    @staticmethod
    def format_credits(credits: int) -> str:
        """Format credits with abbreviations"""
        if credits >= 1000000:
            return f"{credits/1000000:.1f}M"
        elif credits >= 1000:
            return f"{credits/1000:.1f}K"
        else:
            return str(credits)

    @staticmethod
    def format_quantity(qty: int) -> str:
        """Format quantity with abbreviations"""
        if qty >= 1000:
            return f"{qty/1000:.1f}K"
        else:
            return str(qty)

    @staticmethod
    def truncate(text: str, max_len: int = 200) -> str:
        """Truncate text to max length"""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."

    @staticmethod
    def sector_view(sector_id: int, connected_sectors: List[int],
                   has_port: bool, player_ships: int,
                   turns: int, credits: int) -> str:
        """Format sector view message (main game screen)"""
        cred_fmt = MessageFormatter.format_credits(credits)
        connections = ",".join(map(str, connected_sectors[:3]))

        msg = (
            f"Sec{sector_id}[→{connections}]\n"
            f"Port:{'Y' if has_port else 'N'} Ships:{player_ships}\n"
            f"Turns:{turns} Cr:{cred_fmt}\n"
            f"H=help M=move P=port C=cargo"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def welcome_message(player_name: str, sector_id: int,
                       credits: int, turns: int) -> str:
        """Welcome message for new player"""
        cred_fmt = MessageFormatter.format_credits(credits)
        msg = f"Cmdr {player_name} reporting!\nSec:{sector_id} Cr:{cred_fmt} T:{turns}"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def registration_prompt() -> str:
        """Prompt for player name during registration"""
        msg = "Welcome to TradeWars!\nYour call sign? (8 chars max)"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def registration_confirm(name: str) -> str:
        """Confirmation prompt before creating player"""
        msg = f"Cmdr {name}, ready? Y/N"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def name_invalid(reason: str) -> str:
        """Invalid name message"""
        msg = f"Invalid: {reason}\nTry again:"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def navigation_menu(current_sector: int, connected: List[int]) -> str:
        """Navigation menu"""
        connected_str = ",".join(map(str, connected))
        msg = (
            f"Sector {current_sector}\n"
            f"Warp to? ({connected_str})\n"
            f"Or enter sector# (0=cancel)"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def navigation_invalid(valid_sectors: List[int]) -> str:
        """Invalid navigation target"""
        valid_str = ",".join(map(str, valid_sectors))
        msg = f"Invalid sector\nTry: {valid_str}"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def not_enough_turns(needed: int, have: int) -> str:
        """Not enough turns error"""
        msg = f"Need {needed} turns, have {have}"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def warped_success(sector_id: int, turns_left: int) -> str:
        """Successful warp message"""
        msg = f"Warped to Sector {sector_id}\nTurns:{turns_left}"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def port_menu(sector_id: int, player_credits: int, port_credits: int) -> str:
        """Port main menu"""
        p_cred = MessageFormatter.format_credits(player_credits)
        port_cred = MessageFormatter.format_credits(port_credits)
        msg = (
            f"Port-{sector_id} You:{p_cred} Port:{port_cred}\n"
            f"1)Buy 2)Sell 3)List 0)Exit"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def port_list(inventory: Dict, port_status: str = "") -> str:
        """List commodities at port"""
        msg = f"PORT ({port_status}):\n"
        lines = []

        for idx, (commodity, data) in enumerate(inventory.items(), 1):
            if idx > 5:
                break

            short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
            status = data["status"][0]  # B or S
            price = data["price"]
            qty = MessageFormatter.format_quantity(data["quantity"])

            # Format: "1)Or:215cr B 45K avail"
            line = f"{idx}){short}:{price:.0f}cr {status} {qty}"
            lines.append(line)

        msg += "\n".join(lines[:3])  # Fit in message
        msg += "\n0)Back"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def buy_menu(inventory: Dict) -> str:
        """Buy commodities menu"""
        msg = "BUY FROM PORT:\n"
        lines = []

        for idx, (commodity, data) in enumerate(inventory.items(), 1):
            if idx > 5:
                break

            if data["status"] == "Selling":
                short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
                price = data["price"]
                qty = MessageFormatter.format_quantity(data["quantity"])
                line = f"{idx}){short}:{price:.0f}cr {qty} avail"
                lines.append(line)

        msg += "\n".join(lines[:3])
        msg += "\n0)Back"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def sell_menu(inventory: Dict, cargo: Dict) -> str:
        """Sell commodities menu"""
        msg = "SELL TO PORT:\n"
        lines = []

        for idx, (commodity, data) in enumerate(inventory.items(), 1):
            if idx > 5:
                break

            if data["status"] == "Buying" and cargo.get(commodity, 0) > 0:
                short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
                price = data["price"]
                have = cargo[commodity]
                line = f"{idx}){short}:{price:.0f}cr (have:{have})"
                lines.append(line)

        msg += "\n".join(lines[:3])
        msg += "\n0)Back"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def trade_quantity_prompt(commodity: str, max_units: int, price: float,
                             player_credits: int) -> str:
        """Prompt for trade quantity"""
        short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
        cred_fmt = MessageFormatter.format_credits(player_credits)
        msg = (
            f"Buy {short}@{price:.0f}cr\n"
            f"Max:{max_units} Cr:{cred_fmt}\n"
            f"How many?"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def trade_invalid_quantity() -> str:
        """Invalid quantity error"""
        msg = "Invalid amount\nEnter number:"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def trade_executed(commodity: str, quantity: int, cost: int,
                      new_balance: int, cargo_used: int, cargo_max: int) -> str:
        """Trade executed confirmation"""
        short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
        new_bal = MessageFormatter.format_credits(new_balance)
        msg = (
            f"Bought {quantity} {short}\n"
            f"Cost: {cost}cr\n"
            f"Balance:{new_bal} Cargo:{cargo_used}/{cargo_max}"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def trade_sold(commodity: str, quantity: int, revenue: int,
                  new_balance: int, cargo_used: int) -> str:
        """Sale executed confirmation"""
        short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
        new_bal = MessageFormatter.format_credits(new_balance)
        msg = (
            f"Sold {quantity} {short}\n"
            f"Revenue: {revenue}cr\n"
            f"Balance:{new_bal} Cargo:{cargo_used}u"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def cargo_view(cargo: Dict, used: int, max: int) -> str:
        """Display player cargo"""
        msg = f"CARGO {used}/{max}:\n"
        lines = []

        for commodity, qty in cargo.items():
            if qty > 0:
                short = MessageFormatter.COMMODITY_SHORT.get(commodity, commodity)
                qty_fmt = MessageFormatter.format_quantity(qty)
                lines.append(f"{short}:{qty_fmt}")

        if not lines:
            msg += "Empty\nSend any key to return"
        else:
            msg += " ".join(lines[:5])
            msg += "\nAny key=back"

        return MessageFormatter.truncate(msg)

    @staticmethod
    def stats_view(player_name: str, credits: int, turns: int, score: int,
                  total_warps: int, total_trades: int, sector: int) -> str:
        """Display player statistics"""
        cred_fmt = MessageFormatter.format_credits(credits)
        msg = (
            f"{player_name} Stats:\n"
            f"Cr:{cred_fmt} T:{turns} Sc:{score}\n"
            f"Warps:{total_warps} Trades:{total_trades}\n"
            f"Loc:Sec{sector}"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def error_message(error: str) -> str:
        """Format error message"""
        msg = f"ERROR: {error}"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def trade_error(error: str) -> str:
        """Format trade error"""
        msg = f"Can't trade: {error}\n0=back"
        return MessageFormatter.truncate(msg)

    @staticmethod
    def help_text() -> str:
        """Display help text"""
        msg = (
            "TradeWars Help:\n"
            "M=move P=port C=cargo S=stats\n"
            "1-5=buy/sell Q=quit"
        )
        return MessageFormatter.truncate(msg)

    @staticmethod
    def database_error() -> str:
        """Database error message"""
        msg = "Database error. Try again later."
        return MessageFormatter.truncate(msg)

    @staticmethod
    def session_recovered(sector: int) -> str:
        """Session recovered message"""
        msg = f"Session restored. Sector {sector}. Continue?"
        return MessageFormatter.truncate(msg)
