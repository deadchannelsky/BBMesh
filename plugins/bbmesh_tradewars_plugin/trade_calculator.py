"""
TradeWars Plugin - Trade Calculator and Economics Engine
"""

from typing import Dict, Tuple, Optional
import random


class TradeCalculator:
    """Handles trade calculations, pricing, and validation"""

    COMMODITIES = ["Ore", "Organics", "Equipment", "Armor", "Batteries"]

    # Base prices for commodities (in credits)
    BASE_PRICES = {
        "Ore": 250,
        "Organics": 180,
        "Equipment": 3800,
        "Armor": 1200,
        "Batteries": 11
    }

    # Price volatility (how much prices can change)
    PRICE_MODIFIERS = {
        "Ore": 1000,
        "Organics": 800,
        "Equipment": 5000,
        "Armor": 3000,
        "Batteries": 20
    }

    def __init__(self):
        pass

    def generate_port_inventory(self) -> Dict[str, Dict]:
        """
        Generate initial port inventory with prices and quantities

        Returns:
            Dictionary of commodity data
        """
        inventory = {}

        for commodity in self.COMMODITIES:
            # Randomly decide if port is buying or selling
            is_buying = random.choice([True, False])

            # Generate quantity (in units)
            if is_buying:
                quantity = random.randint(5000, 100000)
            else:
                quantity = random.randint(1000, 50000)

            # Generate price modifier (price variance)
            modifier = random.uniform(0.7, 1.3)
            base_price = self.BASE_PRICES[commodity]
            price = round(base_price * modifier, 1)

            inventory[commodity] = {
                "status": "Buying" if is_buying else "Selling",
                "quantity": quantity,
                "price": price,
                "base_price": base_price,
                "price_modifier": self.PRICE_MODIFIERS[commodity]
            }

        return inventory

    def calculate_price(self, commodity: str, quantity_change: int, current_inventory: Dict) -> float:
        """
        Calculate dynamic price based on supply/demand

        Args:
            commodity: Commodity name
            quantity_change: Positive for buying from port, negative for selling
            current_inventory: Current port inventory data

        Returns:
            Price per unit in credits
        """
        if commodity not in self.COMMODITIES:
            return 0

        current = current_inventory.get(commodity, {})
        base_price = current.get("base_price", self.BASE_PRICES[commodity])
        price_modifier = current.get("price_modifier", self.PRICE_MODIFIERS[commodity])

        # Current price
        current_price = current.get("price", base_price)

        # Price changes based on quantity being traded
        # Buying from port increases price, selling decreases it
        current_quantity = current.get("quantity", 10000)

        # Calculate new price based on quantity change
        # Formula: price_change = (quantity_change / price_modifier) * base_price
        if current_quantity > 0:
            demand_factor = quantity_change / price_modifier
            new_price = base_price + (demand_factor * base_price)
            new_price = max(base_price * 0.5, new_price)  # Floor at 50% of base
            new_price = min(base_price * 2.0, new_price)  # Ceiling at 200% of base
            return round(new_price, 1)

        return current_price

    def can_buy_from_port(self, commodity: str, quantity: int,
                         player_credits: int, player_cargo_used: int,
                         player_cargo_capacity: int,
                         port_inventory: Dict) -> Tuple[bool, str]:
        """
        Check if player can buy commodity from port

        Args:
            commodity: Commodity name
            quantity: Units to buy
            player_credits: Player's current credits
            player_cargo_used: Current cargo space used
            player_cargo_capacity: Total cargo capacity
            port_inventory: Port's inventory data

        Returns:
            Tuple of (can_buy, reason)
        """
        if commodity not in port_inventory:
            return False, "Commodity not available"

        item = port_inventory[commodity]

        if item["status"] != "Selling":
            return False, f"Port not selling {commodity}"

        if item["quantity"] < quantity:
            return False, f"Only {item['quantity']} available"

        # Check cargo space
        cargo_needed = player_cargo_used + quantity
        if cargo_needed > player_cargo_capacity:
            return False, f"Need {cargo_needed - player_cargo_capacity} more holds"

        # Check credits
        price = item["price"]
        cost = quantity * price
        if player_credits < cost:
            max_units = int(player_credits / price)
            return False, f"Only {max_units} units affordable"

        return True, ""

    def can_sell_to_port(self, commodity: str, quantity: int,
                        player_cargo: Dict,
                        port_inventory: Dict,
                        port_credits: int) -> Tuple[bool, str]:
        """
        Check if player can sell commodity to port

        Args:
            commodity: Commodity name
            quantity: Units to sell
            player_cargo: Player's cargo
            port_inventory: Port's inventory
            port_credits: Port's buying power

        Returns:
            Tuple of (can_sell, reason)
        """
        if commodity not in player_cargo:
            return False, "You don't have that commodity"

        if player_cargo[commodity] < quantity:
            have = player_cargo[commodity]
            return False, f"You only have {have} units"

        if commodity not in port_inventory:
            return False, "Port doesn't trade this"

        item = port_inventory[commodity]

        if item["status"] != "Buying":
            return False, f"Port not buying {commodity}"

        # Check port credits
        price = item["price"]
        revenue = quantity * price
        if port_credits < revenue:
            max_units = int(port_credits / price)
            return False, f"Port can only buy {max_units} units"

        return True, ""

    def execute_purchase(self, quantity: int, price: float) -> int:
        """
        Calculate cost of purchase

        Returns:
            Total cost in credits
        """
        return round(quantity * price)

    def execute_sale(self, quantity: int, price: float) -> int:
        """
        Calculate revenue of sale

        Returns:
            Total revenue in credits
        """
        return round(quantity * price)

    def update_port_inventory_after_buy(self, commodity: str, quantity: int,
                                       cost: int, port_inventory: Dict) -> Dict:
        """
        Update port inventory after player buys from port

        Returns:
            Updated port inventory
        """
        updated = {k: v.copy() for k, v in port_inventory.items()}

        if commodity in updated:
            item = updated[commodity]
            item["quantity"] -= quantity
            item["status"] = "Buying" if item["quantity"] < 50000 else "Selling"

        return updated

    def update_port_inventory_after_sell(self, commodity: str, quantity: int,
                                        revenue: int, port_inventory: Dict) -> Dict:
        """
        Update port inventory after player sells to port

        Returns:
            Updated port inventory
        """
        updated = {k: v.copy() for k, v in port_inventory.items()}

        if commodity in updated:
            item = updated[commodity]
            item["quantity"] += quantity
            item["status"] = "Buying" if item["quantity"] < 50000 else "Selling"

        return updated

    def should_regenerate_port(self, last_regeneration_iso: str) -> bool:
        """
        Check if port should regenerate inventory

        Returns:
            True if 4+ hours have passed since last regeneration
        """
        from datetime import datetime, timedelta

        last_regen = datetime.fromisoformat(last_regeneration_iso)
        now = datetime.now()
        hours_passed = (now - last_regen).total_seconds() / 3600

        return hours_passed >= 4

    def regenerate_port_inventory(self, current_inventory: Dict) -> Dict:
        """
        Slowly regenerate port inventory toward initial levels

        Returns:
            Updated inventory with regenerated quantities
        """
        regenerated = {k: v.copy() for k, v in current_inventory.items()}

        for commodity in self.COMMODITIES:
            if commodity in regenerated:
                item = regenerated[commodity]

                # Regenerate toward middle quantity (25000)
                target = 25000
                current = item["quantity"]

                if current < target:
                    # Add 10% of the difference
                    change = round((target - current) * 0.1)
                    item["quantity"] = min(current + change, target)
                elif current > target:
                    # Remove 10% of the difference
                    change = round((current - target) * 0.1)
                    item["quantity"] = max(current - change, target)

        return regenerated

    def calculate_profit(self, buy_commodity: str, buy_quantity: int, buy_price: float,
                        sell_price: float) -> Tuple[int, float]:
        """
        Calculate profit from a trade route

        Returns:
            Tuple of (profit_credits, profit_percentage)
        """
        buy_cost = self.execute_purchase(buy_quantity, buy_price)
        sell_revenue = self.execute_sale(buy_quantity, sell_price)
        profit = sell_revenue - buy_cost
        profit_pct = (profit / buy_cost * 100) if buy_cost > 0 else 0

        return profit, profit_pct
