"""
Built-in plugins for BBMesh
"""

import math
import random
import re
from datetime import datetime
from typing import Dict, Any

from .base import SimpleResponsePlugin, InteractivePlugin, PluginContext, PluginResponse
from .askai import AskAIPlugin


class WelcomePlugin(SimpleResponsePlugin):
    """Welcome message plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        return (
            f"Welcome to BBMesh, {context.user_name}!\n"
            f"Your gateway to the mesh network.\n"
            f"Send HELP for commands or MENU for options."
        )


class HelpPlugin(SimpleResponsePlugin):
    """Help and command reference plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        return (
            f"BBMesh Commands:\n"
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
        
        return f"Current time: {formatted_time}"


class PingPlugin(SimpleResponsePlugin):
    """Network ping/connectivity test plugin"""
    
    def generate_response(self, context: PluginContext) -> str:
        include_signal = self.config.get("include_signal_info", True)
        
        if include_signal and hasattr(context.message, 'snr'):
            return (
                f"Pong! BBMesh is alive.\n"
                f"Signal: {context.message.snr:.1f}dB SNR, "
                f"{context.message.rssi}dBm RSSI"
            )
        else:
            return "Pong! BBMesh is alive and responding."


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
            return f"Expression too long (max {max_length} characters)"
        
        # Check for forbidden characters
        if not all(c in allowed_chars for c in text):
            return "Invalid characters in expression"
        
        try:
            # Evaluate the expression safely
            result = eval(text, {"__builtins__": {}}, {})
            
            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 6)
            
            return f"{text} = {result}"
            
        except ZeroDivisionError:
            return "Division by zero"
        except Exception as e:
            return f"Invalid expression: {str(e)[:50]}"


class NumberGuessPlugin(InteractivePlugin):
    """Number guessing game - escalating difficulty"""

    def _get_difficulty_range(self, level: int) -> tuple:
        """Get min/max for difficulty level (1-indexed)"""
        ranges = {
            1: (1, 5),
            2: (1, 7),
            3: (1, 10),
            4: (1, 15),
            5: (1, 20),
        }
        return ranges.get(level, (1, 20))

    def start_session(self, context: PluginContext) -> PluginResponse:
        """Start a new game at level 1"""
        min_num, max_num = self._get_difficulty_range(1)
        target_number = random.randint(min_num, max_num)

        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_target": target_number,
            f"{self.name}_attempts": 0,
            f"{self.name}_level": 1,
            f"{self.name}_min": min_num,
            f"{self.name}_max": max_num
        }

        response_text = (
            f"Guess My Number!\n\n"
            f"Level 1: I'm thinking of a number 1-5\n"
            f"You have 3 tries. What's your guess?"
        )

        return PluginResponse(
            text=response_text,
            continue_session=True,
            session_data=session_data
        )

    def continue_session(self, context: PluginContext) -> PluginResponse:
        target = context.session_data.get(f"{self.name}_target")
        attempts = context.session_data.get(f"{self.name}_attempts", 0)
        level = context.session_data.get(f"{self.name}_level", 1)
        min_num = context.session_data.get(f"{self.name}_min", 1)
        max_num = context.session_data.get(f"{self.name}_max", 5)

        # Parse user's guess
        text = context.message.text.strip()

        try:
            guess = int(text)
        except ValueError:
            return PluginResponse(
                text=f"Enter a number between {min_num}-{max_num}:",
                continue_session=True,
                session_data=context.session_data
            )

        attempts += 1
        context.session_data[f"{self.name}_attempts"] = attempts

        # Check the guess
        if guess == target:
            # Correct! Move to next level or end game
            if level < 5:
                # Go to next level
                next_level = level + 1
                next_min, next_max = self._get_difficulty_range(next_level)
                next_target = random.randint(next_min, next_max)

                context.session_data[f"{self.name}_target"] = next_target
                context.session_data[f"{self.name}_attempts"] = 0
                context.session_data[f"{self.name}_level"] = next_level
                context.session_data[f"{self.name}_min"] = next_min
                context.session_data[f"{self.name}_max"] = next_max

                response_text = (
                    f"Correct! You got it in {attempts} tries!\n\n"
                    f"Level {next_level}: Now guess between {next_min}-{next_max}"
                )

                return PluginResponse(
                    text=response_text,
                    continue_session=True,
                    session_data=context.session_data
                )
            else:
                # Max level reached
                context.session_data[f"{self.name}_active"] = False
                return PluginResponse(
                    text=f"Correct! You beat all 5 levels!\nYou're a Number Master! 🏆",
                    continue_session=False
                )

        elif attempts >= 3:
            # Out of attempts - back to main menu
            context.session_data[f"{self.name}_active"] = False
            return PluginResponse(
                text=f"Nope! The number was {target}.\nBack to the main menu with you!",
                continue_session=False
            )

        else:
            # Give hint and continue
            if guess < target:
                hint = "Too low!"
            else:
                hint = "Too high!"

            remaining = 3 - attempts
            response_text = f"{hint} {remaining} tries left:"

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
            f"Node Info: {context.user_name}",
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
    "askai": AskAIPlugin,
}