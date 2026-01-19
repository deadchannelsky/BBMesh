"""
AskAI Plugin - Query local Ollama instance for AI responses
"""

import requests
from typing import Dict, Any
from .base import InteractivePlugin, PluginContext, PluginResponse


class AskAIPlugin(InteractivePlugin):
    """Interactive plugin for querying local Ollama AI instance"""

    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        required_keys = ["ollama_endpoint", "model", "ollama_timeout", "max_question_length"]
        for key in required_keys:
            if key not in self.config:
                self.logger.error(f"Missing required config: {key}")
                return False
        return True

    def start_session(self, context: PluginContext) -> PluginResponse:
        """Start a new AskAI session"""
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_state": "menu",
        }

        response_text = self._display_menu()

        return PluginResponse(
            text=response_text,
            continue_session=True,
            session_data=session_data
        )

    def continue_session(self, context: PluginContext) -> PluginResponse:
        """Continue an existing AskAI session"""
        current_state = context.session_data.get(f"{self.name}_state", "menu")
        user_input = context.message.text.strip()

        if current_state == "menu":
            return self._handle_menu_selection(user_input, context)
        elif current_state == "waiting_question":
            return self._handle_question(user_input, context)
        else:
            # Unknown state, reset to menu
            context.session_data[f"{self.name}_state"] = "menu"
            return PluginResponse(
                text=self._display_menu(),
                continue_session=True,
                session_data=context.session_data
            )

    def _display_menu(self) -> str:
        """Display the plugin menu"""
        return (
            "AskAI - Local AI Assistant\n\n"
            "1. Ask AI\n"
            "2. Exit\n\n"
            "Enter choice:"
        )

    def _handle_menu_selection(self, choice: str, context: PluginContext) -> PluginResponse:
        """Handle user's menu selection"""
        choice = choice.strip().lower()

        if choice == "1":
            # Move to question input state
            context.session_data[f"{self.name}_state"] = "waiting_question"
            return PluginResponse(
                text="Enter your question (max 200 chars):",
                continue_session=True,
                session_data=context.session_data
            )
        elif choice == "2":
            # Exit plugin
            context.session_data[f"{self.name}_active"] = False
            return PluginResponse(
                text="📋 Returning to BBMesh main menu. Send MENU to see options.",
                continue_session=False
            )
        else:
            # Invalid choice
            return PluginResponse(
                text="Invalid choice. Enter 1 or 2:",
                continue_session=True,
                session_data=context.session_data
            )

    def _handle_question(self, question: str, context: PluginContext) -> PluginResponse:
        """Handle user's question input"""
        max_length = self.config.get("max_question_length", 200)

        # Check question length
        if len(question) > max_length:
            return PluginResponse(
                text=f"Question too long! Max {max_length} chars. Try again:",
                continue_session=True,
                session_data=context.session_data
            )

        # Query Ollama
        ai_response = self._query_ollama(question)

        # Return to menu state after processing
        context.session_data[f"{self.name}_state"] = "menu"

        # Format response with prefix
        response_prefix = self.config.get("response_prefix", "🤖 ")
        formatted_response = f"{response_prefix}{ai_response}"

        return PluginResponse(
            text=f"{formatted_response}\n\n{self._display_menu()}",
            continue_session=True,
            session_data=context.session_data
        )

    def _query_ollama(self, question: str) -> str:
        """Query local Ollama instance for AI response"""
        try:
            endpoint = self.config.get("ollama_endpoint")
            model = self.config.get("model", "llama2")
            timeout = self.config.get("ollama_timeout", 30)

            payload = {
                "model": model,
                "prompt": question,
                "stream": False
            }

            self.logger.debug(f"Querying Ollama with model: {model}")

            response = requests.post(
                endpoint,
                json=payload,
                timeout=timeout
            )

            # Handle HTTP errors
            response.raise_for_status()

            # Extract response from JSON
            response_data = response.json()
            ai_response = response_data.get("response", "No response from AI")

            # Clean up response (remove leading/trailing whitespace)
            ai_response = ai_response.strip()

            self.logger.info(f"Successfully queried Ollama")
            return ai_response

        except requests.exceptions.ConnectionError:
            error_msg = "❌ Cannot connect to Ollama. Is it running on port 11434?"
            self.logger.warning(error_msg)
            return error_msg
        except requests.exceptions.Timeout:
            error_msg = "⏰ AI response timed out. Try a simpler question."
            self.logger.warning(error_msg)
            return error_msg
        except requests.exceptions.HTTPError as e:
            error_msg = f"❌ AI error: {str(e)[:50]}"
            self.logger.error(f"HTTP Error: {e}")
            return error_msg
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)[:50]}"
            self.logger.error(f"Error querying Ollama: {e}")
            return error_msg
