"""
Built-in plugins for BBMesh
"""

import math
import random
import re
from datetime import datetime
from typing import Dict, Any

from .base import SimpleResponsePlugin, InteractivePlugin, PluginContext, PluginResponse
from .bulletin_board import BulletinBoardPlugin


class WelcomePlugin(SimpleResponsePlugin):
    """Welcome message plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        return (
            f"👋 Welcome to BBMesh, {context.user_name}!\n"
            f"Your gateway to the mesh network.\n"
            f"Send HELP for commands or MENU for options."
        )


class HelpPlugin(SimpleResponsePlugin):
    """Help and command reference plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        return (
            f"📻 BBMesh Commands:\n"
            f"MENU - Main menu\n"
            f"HELP - This help\n"
            f"PING - Test response\n"
            f"STATUS - System info\n"
            f"TIME - Current time\n"
            f"GAMES - Fun activities\n"
            f"UTILS - Useful tools"
        )


class TimePlugin(SimpleResponsePlugin):
    """Date and time plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        timezone = self.config.get("timezone", "UTC")
        time_format = self.config.get("format", "%Y-%m-%d %H:%M:%S")
        
        now = datetime.now()
        formatted_time = now.strftime(time_format)
        
        return f"🕒 Current time: {formatted_time}"


class PingPlugin(SimpleResponsePlugin):
    """Network ping/connectivity test plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        include_signal = self.config.get("include_signal_info", True)
        
        if include_signal and hasattr(context.message, 'snr'):
            return (
                f"🏓 Pong! BBMesh is alive.\n"
                f"Signal: {context.message.snr:.1f}dB SNR, "
                f"{context.message.rssi}dBm RSSI"
            )
        else:
            return "🏓 Pong! BBMesh is alive and responding."


class CalculatorPlugin(SimpleResponsePlugin):
    """Basic calculator plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        # Extract calculation from message
        text = context.message.text.strip()
        
        # Remove common prefixes
        prefixes = ["calc ", "calculate ", "=", "math "]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        # Safety check - only allow basic math operations
        allowed_chars = set("0123456789+-*/.() ")
        allowed_ops = self.config.get("allowed_operations", ["+", "-", "*", "/", "**", "%"])
        max_length = self.config.get("max_expression_length", 50)
        
        if len(text) > max_length:
            return f"❌ Expression too long (max {max_length} characters)"
        
        # Check for forbidden characters
        if not all(c in allowed_chars for c in text):
            return "❌ Invalid characters in expression"
        
        try:
            # Evaluate the expression safely
            result = eval(text, {"__builtins__": {}}, {})
            
            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 6)
            
            return f"🧮 {text} = {result}"
            
        except ZeroDivisionError:
            return "❌ Division by zero"
        except Exception as e:
            return f"❌ Invalid expression: {str(e)[:50]}"


class NumberGuessPlugin(InteractivePlugin):
    """Number guessing game plugin"""
    
    def start_session(self, context: PluginContext) -> PluginResponse:
        min_num = self.config.get("min_number", 1)
        max_num = self.config.get("max_number", 100)
        max_attempts = self.config.get("max_attempts", 7)
        
        target_number = random.randint(min_num, max_num)
        
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_target": target_number,
            f"{self.name}_attempts": 0,
            f"{self.name}_max_attempts": max_attempts,
            f"{self.name}_min": min_num,
            f"{self.name}_max": max_num
        }
        
        response_text = (
            f"🎲 Number Guessing Game!\n"
            f"I'm thinking of a number between {min_num} and {max_num}.\n"
            f"You have {max_attempts} attempts. What's your guess?"
        )
        
        return PluginResponse(
            text=response_text,
            continue_session=True,
            session_data=session_data
        )
    
    def continue_session(self, context: PluginContext) -> PluginResponse:
        target = context.session_data.get(f"{self.name}_target")
        attempts = context.session_data.get(f"{self.name}_attempts", 0)
        max_attempts = context.session_data.get(f"{self.name}_max_attempts", 7)
        min_num = context.session_data.get(f"{self.name}_min", 1)
        max_num = context.session_data.get(f"{self.name}_max", 100)
        
        # Parse user's guess
        text = context.message.text.strip()
        
        try:
            guess = int(text)
        except ValueError:
            return PluginResponse(
                text=f"❌ Please enter a number between {min_num} and {max_num}",
                continue_session=True,
                session_data=context.session_data
            )
        
        attempts += 1
        context.session_data[f"{self.name}_attempts"] = attempts
        
        # Check the guess
        if guess == target:
            # Correct guess!
            context.session_data[f"{self.name}_active"] = False
            return PluginResponse(
                text=f"🎉 Correct! The number was {target}.\nYou got it in {attempts} attempts!",
                continue_session=False
            )
        
        elif attempts >= max_attempts:
            # Out of attempts
            context.session_data[f"{self.name}_active"] = False
            return PluginResponse(
                text=f"💀 Game over! The number was {target}.\nBetter luck next time!",
                continue_session=False
            )
        
        else:
            # Give hint and continue
            if guess < target:
                hint = "📈 Too low!"
            else:
                hint = "📉 Too high!"
            
            remaining = max_attempts - attempts
            response_text = f"{hint} {remaining} attempts left. Try again:"
            
            return PluginResponse(
                text=response_text,
                continue_session=True,
                session_data=context.session_data
            )


class NodeLookupPlugin(SimpleResponsePlugin):
    """Node information lookup plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        # This would typically interface with the mesh network
        # For now, return basic info about the sender
        show_signal = self.config.get("show_signal_info", True)
        
        info_parts = [
            f"📡 Node Info: {context.user_name}",
            f"ID: {context.user_id}",
            f"Channel: {context.channel}"
        ]
        
        if show_signal and hasattr(context.message, 'snr'):
            info_parts.extend([
                f"SNR: {context.message.snr:.1f}dB",
                f"RSSI: {context.message.rssi}dBm"
            ])
        
        return "\n".join(info_parts)


# Plugin registry - maps plugin names to classes
BUILTIN_PLUGINS = {
    "welcome": WelcomePlugin,
    "help": HelpPlugin,
    "time": TimePlugin,
    "ping": PingPlugin,
    "calculator": CalculatorPlugin,
    "number_guess": NumberGuessPlugin,
    "node_lookup": NodeLookupPlugin,
    "bulletin_system": BulletinBoardPlugin,
}