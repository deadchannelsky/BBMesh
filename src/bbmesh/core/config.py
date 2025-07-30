"""
Configuration management for BBMesh
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml


@dataclass
class SerialConfig:
    """Serial port configuration"""
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    timeout: float = 1.0
    auto_resolve_conflicts: bool = True
    stop_modemmanager: bool = True
    stop_getty_services: bool = True
    remove_stale_locks: bool = True


@dataclass
class MeshtasticConfig:
    """Meshtastic node configuration"""
    serial: SerialConfig = field(default_factory=SerialConfig)
    node_id: Optional[str] = None
    monitored_channels: List[int] = field(default_factory=lambda: [0])
    response_channels: List[int] = field(default_factory=lambda: [0])
    direct_message_only: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/bbmesh.log"
    max_file_size: str = "10MB"
    backup_count: int = 5
    console_output: bool = True


@dataclass
class ServerConfig:
    """Server configuration"""
    name: str = "BBMesh BBS"
    welcome_message: str = "Welcome to BBMesh BBS!"
    motd_file: Optional[str] = "config/motd.txt"
    max_message_length: int = 200
    session_timeout: int = 300  # seconds
    rate_limit_messages: int = 10
    rate_limit_window: int = 60  # seconds
    message_send_delay: float = 1.0  # seconds


@dataclass
class MenuConfig:
    """Menu system configuration"""
    menu_file: str = "config/menus.yaml"
    timeout: int = 300  # seconds
    max_depth: int = 10
    prompt_suffix: str = " > "


@dataclass
class PluginConfig:
    """Plugin system configuration"""
    plugin_dir: str = "src/bbmesh/plugins"
    plugin_config_file: str = "config/plugins.yaml"
    enabled_plugins: List[str] = field(default_factory=list)
    plugin_timeout: int = 30  # seconds


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "sqlite"
    path: str = "data/bbmesh.db"
    backup_interval: int = 3600  # seconds


@dataclass
class Config:
    """Main BBMesh configuration"""
    meshtastic: MeshtasticConfig = field(default_factory=MeshtasticConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    menu: MenuConfig = field(default_factory=MenuConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary"""
        config = cls()
        
        # Update configuration sections
        if "meshtastic" in data:
            meshtastic_data = data["meshtastic"]
            if "serial" in meshtastic_data:
                config.meshtastic.serial = SerialConfig(**meshtastic_data["serial"])
            for key, value in meshtastic_data.items():
                if key != "serial" and hasattr(config.meshtastic, key):
                    setattr(config.meshtastic, key, value)
        
        if "logging" in data:
            for key, value in data["logging"].items():
                if hasattr(config.logging, key):
                    setattr(config.logging, key, value)
        
        if "server" in data:
            for key, value in data["server"].items():
                if hasattr(config.server, key):
                    setattr(config.server, key, value)
        
        if "menu" in data:
            for key, value in data["menu"].items():
                if hasattr(config.menu, key):
                    setattr(config.menu, key, value)
        
        if "plugins" in data:
            for key, value in data["plugins"].items():
                if hasattr(config.plugins, key):
                    setattr(config.plugins, key, value)
        
        if "database" in data:
            for key, value in data["database"].items():
                if hasattr(config.database, key):
                    setattr(config.database, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary"""
        return {
            "meshtastic": {
                "serial": {
                    "port": self.meshtastic.serial.port,
                    "baudrate": self.meshtastic.serial.baudrate,
                    "timeout": self.meshtastic.serial.timeout,
                },
                "node_id": self.meshtastic.node_id,
                "monitored_channels": self.meshtastic.monitored_channels,
                "response_channels": self.meshtastic.response_channels,
                "direct_message_only": self.meshtastic.direct_message_only,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
            },
            "server": {
                "name": self.server.name,
                "welcome_message": self.server.welcome_message,
                "motd_file": self.server.motd_file,
                "max_message_length": self.server.max_message_length,
                "session_timeout": self.server.session_timeout,
                "rate_limit_messages": self.server.rate_limit_messages,
                "rate_limit_window": self.server.rate_limit_window,
                "message_send_delay": self.server.message_send_delay,
            },
            "menu": {
                "menu_file": self.menu.menu_file,
                "timeout": self.menu.timeout,
                "max_depth": self.menu.max_depth,
                "prompt_suffix": self.menu.prompt_suffix,
            },
            "plugins": {
                "plugin_dir": self.plugins.plugin_dir,
                "plugin_config_file": self.plugins.plugin_config_file,
                "enabled_plugins": self.plugins.enabled_plugins,
                "plugin_timeout": self.plugins.plugin_timeout,
            },
            "database": {
                "type": self.database.type,
                "path": self.database.path,
                "backup_interval": self.database.backup_interval,
            },
        }
    
    def save(self, config_path: Path) -> None:
        """Save configuration to YAML file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    @classmethod
    def create_default(cls) -> "Config":
        """Create a default configuration"""
        return cls()