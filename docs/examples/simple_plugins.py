"""
Simple Plugin Examples for BBMesh

This file contains examples of simple response plugins that demonstrate
basic plugin development patterns and common use cases.
"""

import random
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List

from bbmesh.plugins.base import SimpleResponsePlugin, PluginContext


class EchoPlugin(SimpleResponsePlugin):
    """
    Simple echo plugin that repeats the user's message.
    
    Configuration:
        prefix: Text to add before echoed message
        max_length: Maximum message length to echo
    """
    
    def generate_response(self, context: PluginContext) -> str:
        prefix = self.config.get("prefix", "Echo:")
        max_length = self.config.get("max_length", 100)
        
        # Get the user's message, removing the trigger word
        message = context.message.text.strip()
        
        # Remove common trigger words
        for trigger in ["echo", "repeat", "say"]:
            if message.lower().startswith(trigger):
                message = message[len(trigger):].strip()
                break
        
        # Truncate if too long
        if len(message) > max_length:
            message = message[:max_length] + "..."
        
        return f"{prefix} {message}" if message else f"{prefix} (no message to echo)"


class QuotePlugin(SimpleResponsePlugin):
    """
    Daily quote plugin that returns inspirational quotes.
    
    Configuration:
        quotes: List of quotes to choose from
        daily: If true, same quote for entire day
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # Default quotes if none configured
        self.quotes = config.get("quotes", [
            "The mesh network connects us all. - Anonymous",
            "In radio we trust, in mesh we connect. - BBMesh User",
            "Every message matters in the mesh. - Ham Radio Wisdom",
            "73 from the mesh! - Radio Amateur",
            "Redundancy is reliability in communications. - Emergency Preparedness"
        ])
    
    def generate_response(self, context: PluginContext) -> str:
        daily = self.config.get("daily", True)
        
        if daily:
            # Same quote for the entire day
            today = datetime.now().date()
            random.seed(today.toordinal())
        
        quote = random.choice(self.quotes)
        return f"💭 Quote of the day:\n{quote}"


class Base64Plugin(SimpleResponsePlugin):
    """
    Base64 encoder/decoder plugin.
    
    Usage:
        "encode hello" -> encodes "hello" to base64
        "decode aGVsbG8=" -> decodes base64 to text
    """
    
    def generate_response(self, context: PluginContext) -> str:
        text = context.message.text.strip().lower()
        
        try:
            if text.startswith("encode "):
                # Encode to base64
                message = context.message.text[7:].strip()  # Remove "encode "
                if not message:
                    return "❌ No text to encode. Usage: encode <text>"
                
                encoded = base64.b64encode(message.encode('utf-8')).decode('ascii')
                return f"🔐 Encoded: {encoded}"
            
            elif text.startswith("decode "):
                # Decode from base64
                b64_text = context.message.text[7:].strip()  # Remove "decode "
                if not b64_text:
                    return "❌ No base64 to decode. Usage: decode <base64>"
                
                decoded = base64.b64decode(b64_text).decode('utf-8')
                return f"🔓 Decoded: {decoded}"
            
            else:
                return ("🔐 Base64 Tool\n"
                       "encode <text> - Encode text\n"
                       "decode <base64> - Decode base64")
        
        except Exception as e:
            return f"❌ Error: {str(e)[:50]}"


class HashPlugin(SimpleResponsePlugin):
    """
    Hash generator plugin for common hash algorithms.
    
    Usage:
        "md5 hello" -> MD5 hash of "hello"
        "sha1 hello" -> SHA1 hash of "hello"
        "sha256 hello" -> SHA256 hash of "hello"
    """
    
    def generate_response(self, context: PluginContext) -> str:
        text = context.message.text.strip().lower()
        
        # Parse command and text
        parts = context.message.text.strip().split(' ', 2)
        if len(parts) < 2:
            return ("🔐 Hash Tool\n"
                   "md5 <text> - MD5 hash\n"
                   "sha1 <text> - SHA1 hash\n"
                   "sha256 <text> - SHA256 hash")
        
        hash_type = parts[0].lower()
        message = parts[1] if len(parts) > 1 else ""
        
        if not message:
            return f"❌ No text to hash. Usage: {hash_type} <text>"
        
        try:
            if hash_type == "md5":
                hash_obj = hashlib.md5(message.encode('utf-8'))
            elif hash_type == "sha1":
                hash_obj = hashlib.sha1(message.encode('utf-8'))
            elif hash_type == "sha256":
                hash_obj = hashlib.sha256(message.encode('utf-8'))
            else:
                return "❌ Unsupported hash type. Use: md5, sha1, sha256"
            
            hex_hash = hash_obj.hexdigest()
            return f"🔐 {hash_type.upper()}: {hex_hash}"
        
        except Exception as e:
            return f"❌ Hash error: {str(e)[:50]}"


class DicePlugin(SimpleResponsePlugin):
    """
    Dice rolling plugin for games and random decisions.
    
    Usage:
        "roll" or "dice" -> Roll single d6
        "roll 2d6" -> Roll 2 six-sided dice
        "roll d20" -> Roll 20-sided die
        "roll 3d8" -> Roll 3 eight-sided dice
    """
    
    def generate_response(self, context: PluginContext) -> str:
        text = context.message.text.strip().lower()
        
        # Remove trigger words
        for trigger in ["roll", "dice"]:
            if text.startswith(trigger):
                text = text[len(trigger):].strip()
                break
        
        # Default to single d6 if no dice specified
        if not text:
            text = "1d6"
        
        try:
            # Parse dice notation (e.g., "2d6", "d20", "3d8")
            if 'd' not in text:
                return "❌ Invalid dice format. Use: XdY (e.g., 2d6, d20)"
            
            parts = text.split('d')
            if len(parts) != 2:
                return "❌ Invalid dice format. Use: XdY (e.g., 2d6, d20)"
            
            # Number of dice (default 1 if not specified)
            num_dice = int(parts[0]) if parts[0] else 1
            sides = int(parts[1])
            
            # Validation
            if num_dice < 1 or num_dice > 10:
                return "❌ Number of dice must be 1-10"
            
            if sides < 2 or sides > 100:
                return "❌ Die sides must be 2-100"
            
            # Roll the dice
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Format result
            if num_dice == 1:
                return f"🎲 Rolled d{sides}: {total}"
            else:
                rolls_str = ", ".join(map(str, rolls))
                return f"🎲 Rolled {num_dice}d{sides}: [{rolls_str}] = {total}"
        
        except ValueError:
            return "❌ Invalid dice format. Use: XdY (e.g., 2d6, d20)"
        except Exception as e:
            return f"❌ Dice error: {str(e)[:50]}"


class CountdownPlugin(SimpleResponsePlugin):
    """
    Countdown timer plugin that shows time until specified dates.
    
    Usage:
        "countdown new year" -> Days until new year
        "countdown christmas" -> Days until Christmas
        Custom dates can be configured in plugin settings
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # Get current year for calculating dates
        current_year = datetime.now().year
        
        # Default countdown targets
        self.targets = config.get("targets", {
            "new year": f"{current_year + 1}-01-01",
            "christmas": f"{current_year}-12-25",
            "halloween": f"{current_year}-10-31",
            "independence day": f"{current_year}-07-04",
        })
    
    def generate_response(self, context: PluginContext) -> str:
        text = context.message.text.strip().lower()
        
        # Remove trigger word
        if text.startswith("countdown"):
            text = text[9:].strip()
        
        if not text:
            targets_list = ", ".join(self.targets.keys())
            return f"⏰ Countdown targets:\n{targets_list}"
        
        # Find matching target
        target_date = None
        target_name = None
        
        for name, date_str in self.targets.items():
            if text in name.lower():
                try:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d")
                    target_name = name.title()
                    break
                except ValueError:
                    continue
        
        if not target_date:
            return f"❌ Unknown countdown target: {text}"
        
        # Calculate time difference
        now = datetime.now()
        diff = target_date - now
        
        if diff.days < 0:
            # Date has passed, calculate for next year
            next_year_date = target_date.replace(year=target_date.year + 1)
            diff = next_year_date - now
            target_name += f" ({next_year_date.year})"
        
        # Format countdown
        if diff.days == 0:
            hours = diff.seconds // 3600
            return f"⏰ {target_name} is today! ({hours} hours)"
        elif diff.days == 1:
            return f"⏰ {target_name} is tomorrow!"
        else:
            return f"⏰ {target_name}: {diff.days} days"


class FlipCoinPlugin(SimpleResponsePlugin):
    """
    Simple coin flip plugin for binary decisions.
    
    Usage:
        "flip" or "coin" -> Flip a coin
        "flip 5" -> Flip 5 coins
    """
    
    def generate_response(self, context: PluginContext) -> str:
        text = context.message.text.strip().lower()
        
        # Remove trigger words and get number of flips
        for trigger in ["flip", "coin"]:
            if text.startswith(trigger):
                text = text[len(trigger):].strip()
                break
        
        # Parse number of flips
        try:
            num_flips = int(text) if text and text.isdigit() else 1
            
            if num_flips < 1 or num_flips > 20:
                return "❌ Number of flips must be 1-20"
            
            # Flip coins
            results = []
            heads_count = 0
            
            for _ in range(num_flips):
                result = random.choice(["Heads", "Tails"])
                results.append(result)
                if result == "Heads":
                    heads_count += 1
            
            # Format result
            if num_flips == 1:
                emoji = "🪙" if results[0] == "Heads" else "🔴"
                return f"{emoji} {results[0]}!"
            else:
                results_str = ", ".join(results)
                return f"🪙 {num_flips} flips: {results_str}\nHeads: {heads_count}, Tails: {num_flips - heads_count}"
        
        except ValueError:
            return "❌ Invalid number of flips"


# Plugin registry for examples
EXAMPLE_PLUGINS = {
    "echo": EchoPlugin,
    "quote": QuotePlugin,
    "base64": Base64Plugin,
    "hash": HashPlugin,
    "dice": DicePlugin,
    "countdown": CountdownPlugin,
    "flip": FlipCoinPlugin,
}


# Example configuration for these plugins
EXAMPLE_CONFIG = {
    "echo": {
        "enabled": True,
        "description": "Echo user messages",
        "prefix": "📢 Echo:",
        "max_length": 100,
        "timeout": 5
    },
    "quote": {
        "enabled": True,
        "description": "Daily inspirational quotes",
        "daily": True,
        "timeout": 5
    },
    "base64": {
        "enabled": True,
        "description": "Base64 encoder/decoder",
        "timeout": 10
    },
    "hash": {
        "enabled": True,
        "description": "Hash generator (MD5, SHA1, SHA256)",
        "timeout": 10
    },
    "dice": {
        "enabled": True,
        "description": "Dice rolling for games",
        "timeout": 5
    },
    "countdown": {
        "enabled": True,
        "description": "Countdown to special dates",
        "targets": {
            "new year": "2025-01-01",
            "christmas": "2024-12-25",
            "field day": "2024-06-22"
        },
        "timeout": 5
    },
    "flip": {
        "enabled": True,
        "description": "Coin flipping for decisions",
        "timeout": 5
    }
}


if __name__ == "__main__":
    """Test the example plugins."""
    from datetime import datetime
    
    # Mock objects for testing
    class MockMessage:
        def __init__(self, text):
            self.sender_id = "test_user"
            self.sender_name = "TestUser"
            self.channel = 0
            self.text = text
            self.timestamp = datetime.now()
            self.is_direct = True
            self.hop_limit = 3
            self.snr = 5.2
            self.rssi = -85
    
    class MockContext:
        def __init__(self, text):
            self.user_id = "test_user"
            self.user_name = "TestUser"
            self.channel = 0
            self.session_data = {}
            self.message = MockMessage(text)
            self.plugin_config = {}
    
    # Test each plugin
    test_cases = [
        ("echo", "echo Hello World!"),
        ("quote", "quote"),
        ("base64", "encode Hello"),
        ("hash", "md5 test"),
        ("dice", "roll 2d6"),
        ("countdown", "countdown new year"),
        ("flip", "flip 3")
    ]
    
    print("Testing example plugins:")
    print("=" * 50)
    
    for plugin_name, test_input in test_cases:
        plugin_class = EXAMPLE_PLUGINS[plugin_name]
        config = EXAMPLE_CONFIG[plugin_name]
        
        plugin = plugin_class(plugin_name, config)
        plugin.initialize()
        
        context = MockContext(test_input)
        response = plugin.execute(context)
        
        print(f"\n{plugin_name.upper()} Plugin:")
        print(f"Input: {test_input}")
        print(f"Output: {response.text}")
    
    print("\n" + "=" * 50)
    print("All example plugins tested successfully!")