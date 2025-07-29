"""
Logging utilities for BBMesh
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from ..core.config import LoggingConfig


def setup_logging(config: LoggingConfig, debug: bool = False) -> None:
    """
    Setup logging configuration for BBMesh
    
    Args:
        config: Logging configuration
        debug: Enable debug mode (overrides config level)
    """
    # Set log level
    level = logging.DEBUG if debug else getattr(logging, config.level.upper())
    
    # Create formatter
    formatter = logging.Formatter(config.format)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.file_path:
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max file size
        max_bytes = _parse_file_size(config.max_file_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('meshtastic').setLevel(logging.WARNING)
    logging.getLogger('serial').setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def _parse_file_size(size_str: str) -> int:
    """
    Parse file size string into bytes
    
    Args:
        size_str: Size string like "10MB", "1GB", etc.
        
    Returns:
        Size in bytes
    """
    size_str = size_str.upper().strip()
    
    # Extract number and unit
    if size_str.endswith('KB'):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith('MB'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('GB'):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    elif size_str.endswith('B'):
        return int(float(size_str[:-1]))
    else:
        # Assume bytes if no unit
        return int(float(size_str))


class BBMeshLogger:
    """
    Specialized logger for BBMesh with additional context
    """
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def log_message(self, direction: str, sender: str, channel: int, 
                   message: str, node_id: Optional[str] = None) -> None:
        """
        Log a Meshtastic message with context
        
        Args:
            direction: "RX" or "TX"
            sender: Sender node ID or name
            channel: Channel number
            message: Message content
            node_id: Local node ID
        """
        node_info = f" [{node_id}]" if node_id else ""
        self.logger.info(
            f"{direction}{node_info} CH{channel} {sender}: {message[:100]}"
            + ("..." if len(message) > 100 else "")
        )
    
    def log_menu_action(self, user: str, action: str, menu_path: str) -> None:
        """
        Log menu navigation
        
        Args:
            user: User identifier
            action: Action taken
            menu_path: Current menu path
        """
        self.logger.info(f"MENU {user}: {action} -> {menu_path}")
    
    def log_plugin_action(self, user: str, plugin: str, action: str, 
                         result: Optional[str] = None) -> None:
        """
        Log plugin execution
        
        Args:
            user: User identifier
            plugin: Plugin name
            action: Action performed
            result: Result or error message
        """
        result_info = f" -> {result}" if result else ""
        self.logger.info(f"PLUGIN {user}: {plugin}.{action}{result_info}")
    
    def log_error(self, context: str, error: Exception, user: Optional[str] = None) -> None:
        """
        Log errors with context
        
        Args:
            context: Error context
            error: Exception that occurred
            user: User identifier if applicable
        """
        user_info = f" [{user}]" if user else ""
        self.logger.error(f"ERROR{user_info} {context}: {error}")
    
    def debug(self, message: str) -> None:
        """Debug logging"""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Info logging"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Warning logging"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Error logging"""
        self.logger.error(message)