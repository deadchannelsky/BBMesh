"""
Base plugin system for BBMesh
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.meshtastic_interface import MeshMessage
from ..utils.logger import BBMeshLogger


@dataclass
class PluginContext:
    """Context information passed to plugins"""
    user_id: str
    user_name: str
    channel: int
    session_data: Dict[str, Any]
    message: MeshMessage
    plugin_config: Dict[str, Any]


@dataclass
class PluginResponse:
    """Response from a plugin"""
    text: str
    continue_session: bool = False
    session_data: Dict[str, Any] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.session_data is None:
            self.session_data = {}


class BBMeshPlugin(ABC):
    """
    Base class for all BBMesh plugins
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = BBMeshLogger(f"plugin.{name}")
        self.enabled = config.get("enabled", True)
        self.timeout = config.get("timeout", 30)
        self.description = config.get("description", "No description")
    
    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResponse:
        """
        Execute the plugin with given context
        
        Args:
            context: Plugin execution context
            
        Returns:
            Plugin response
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self.enabled
    
    def get_help_text(self) -> str:
        """Get help text for this plugin"""
        return f"{self.name}: {self.description}"
    
    def validate_config(self) -> bool:
        """
        Validate plugin configuration
        
        Returns:
            True if configuration is valid
        """
        return True
    
    def initialize(self) -> bool:
        """
        Initialize the plugin
        
        Returns:
            True if initialization successful
        """
        if not self.validate_config():
            self.logger.error(f"Invalid configuration for plugin {self.name}")
            return False
        
        self.logger.info(f"Initialized plugin: {self.name}")
        return True
    
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        self.logger.info(f"Cleaning up plugin: {self.name}")


class SimpleResponsePlugin(BBMeshPlugin):
    """
    Base class for simple response plugins that return static or generated text
    """
    
    @abstractmethod
    def generate_response(self, context: PluginContext) -> str:
        """
        Generate response text
        
        Args:
            context: Plugin context
            
        Returns:
            Response text
        """
        pass
    
    def execute(self, context: PluginContext) -> PluginResponse:
        """Execute simple response plugin"""
        try:
            response_text = self.generate_response(context)
            return PluginResponse(text=response_text)
        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}")
            return PluginResponse(
                text="❌ Plugin error occurred",
                error=str(e)
            )


class InteractivePlugin(BBMeshPlugin):
    """
    Base class for interactive plugins that maintain session state
    """
    
    @abstractmethod
    def start_session(self, context: PluginContext) -> PluginResponse:
        """
        Start a new interactive session
        
        Args:
            context: Plugin context
            
        Returns:
            Initial response
        """
        pass
    
    @abstractmethod
    def continue_session(self, context: PluginContext) -> PluginResponse:
        """
        Continue an existing interactive session
        
        Args:
            context: Plugin context with session data
            
        Returns:
            Response to continue or end session
        """
        pass
    
    def execute(self, context: PluginContext) -> PluginResponse:
        """Execute interactive plugin"""
        try:
            # Check for universal exit commands first
            user_input = context.message.text.strip().lower()
            exit_commands = ["exit", "quit", "menu", "bbs", "main"]

            # Debug logging
            active_key = f"{self.name}_active"
            is_active = context.session_data.get(active_key)
            self.logger.info(f"[{self.name.upper()} EXECUTE] session_data keys: {list(context.session_data.keys())}")
            self.logger.info(f"[{self.name.upper()} EXECUTE] {active_key}={is_active}, user_input={user_input}")

            if user_input in exit_commands and context.session_data.get(f"{self.name}_active"):
                # User wants to exit plugin and return to main BBS
                self.logger.debug(f"Plugin {self.name} received exit command: {user_input}")
                return PluginResponse(
                    text="📋 Returning to BBMesh main menu. Send MENU to see options.",
                    continue_session=False,
                    session_data={}  # Clear plugin session data
                )

            # Check if this is a new session or continuation
            if not context.session_data.get(f"{self.name}_active"):
                self.logger.info(f"[{self.name.upper()} EXECUTE] Not active, calling start_session()")
                return self.start_session(context)
            else:
                self.logger.info(f"[{self.name.upper()} EXECUTE] Active, calling continue_session()")
                return self.continue_session(context)
        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}")
            return PluginResponse(
                text="❌ Plugin error occurred",
                error=str(e)
            )