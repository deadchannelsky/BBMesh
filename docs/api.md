# BBMesh API Reference

This document provides a comprehensive reference for the BBMesh Python API, covering all major classes, methods, and interfaces.

## Table of Contents

- [Core Classes](#core-classes)
- [Configuration](#configuration)
- [Meshtastic Interface](#meshtastic-interface)
- [Message Handling](#message-handling)
- [Plugin System](#plugin-system)
- [Menu System](#menu-system)
- [Logging](#logging)
- [Utilities](#utilities)

## Core Classes

### BBMeshServer

Main server class that orchestrates all BBMesh components.

```python
class BBMeshServer:
    def __init__(self, config: Config)
    def start(self) -> None
    def stop(self) -> None
    def get_server_info(self) -> Dict[str, any]
```

**Constructor Parameters:**
- `config`: BBMesh configuration object

**Methods:**

#### `start() -> None`
Starts the BBMesh server, including:
- Connecting to Meshtastic node
- Initializing message handler
- Starting the main event loop

**Raises:**
- `Exception`: If server startup fails

#### `stop() -> None`
Gracefully stops the server and cleans up resources.

#### `get_server_info() -> Dict[str, any]`
Returns server status information including:
- Server name and running status
- Mesh network information
- Handler statistics
- Configuration summary

## Configuration

### Config

Main configuration class containing all BBMesh settings.

```python
@dataclass
class Config:
    meshtastic: MeshtasticConfig
    logging: LoggingConfig
    server: ServerConfig
    menu: MenuConfig
    plugins: PluginConfig
    database: DatabaseConfig
    
    @classmethod
    def load(cls, config_path: Path) -> "Config"
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config"
    def to_dict(self) -> Dict[str, Any]
    def save(self, config_path: Path) -> None
    @classmethod
    def create_default(cls) -> "Config"
```

#### `Config.load(config_path: Path) -> Config`
Load configuration from YAML file.

**Parameters:**
- `config_path`: Path to configuration file

**Returns:**
- Configured Config object

**Raises:**
- `FileNotFoundError`: If config file doesn't exist
- `yaml.YAMLError`: If YAML parsing fails

### MeshtasticConfig

Meshtastic node connection settings.

```python
@dataclass
class MeshtasticConfig:
    serial: SerialConfig
    node_id: Optional[str] = None
    monitored_channels: List[int] = field(default_factory=lambda: [0])
    response_channels: List[int] = field(default_factory=lambda: [0])
    direct_message_only: bool = False
```

### SerialConfig

Serial port configuration for Meshtastic connection.

```python
@dataclass
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    timeout: float = 1.0
```

### LoggingConfig

Logging system configuration.

```python
@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/bbmesh.log"
    max_file_size: str = "10MB"
    backup_count: int = 5
    console_output: bool = True
```

## Meshtastic Interface

### MeshtasticInterface

Interface to Meshtastic node via serial connection.

```python
class MeshtasticInterface:
    def __init__(self, config: MeshtasticConfig)
    def connect(self) -> bool
    def disconnect(self) -> None
    def send_message(self, text: str, channel: int = 0, destination: Optional[str] = None) -> bool
    def add_message_callback(self, callback: Callable[[MeshMessage], None]) -> None
    def remove_message_callback(self, callback: Callable[[MeshMessage], None]) -> None
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]
    def get_channel_info(self, channel: int) -> Optional[Dict[str, Any]]
    def get_mesh_info(self) -> Dict[str, Any]
```

#### `connect() -> bool`
Connect to Meshtastic node.

**Returns:**
- `True` if connection successful, `False` otherwise

#### `send_message(text, channel=0, destination=None) -> bool`
Send message via Meshtastic.

**Parameters:**
- `text`: Message text (max ~200 characters)
- `channel`: Channel number (0-7)
- `destination`: Target node ID for direct messages

**Returns:**
- `True` if message sent successfully

#### `add_message_callback(callback) -> None`
Register callback for received messages.

**Parameters:**
- `callback`: Function taking MeshMessage parameter

### MeshMessage

Represents a received Meshtastic message.

```python
@dataclass
class MeshMessage:
    sender_id: str
    sender_name: str
    channel: int
    text: str
    timestamp: datetime
    is_direct: bool
    hop_limit: int
    snr: float
    rssi: int
    to_node: Optional[str] = None
```

**Properties:**
- `sender_id`: Sender's node ID
- `sender_name`: Sender's display name
- `channel`: Message channel (0-7)
- `text`: Message content
- `timestamp`: When message was received
- `is_direct`: True if direct message to this node
- `hop_limit`: Number of mesh hops remaining
- `snr`: Signal-to-noise ratio in dB
- `rssi`: Received signal strength in dBm
- `to_node`: Destination node ID (if specified)

## Message Handling

### MessageHandler

Processes incoming messages and manages user sessions.

```python
class MessageHandler:
    def __init__(self, config: Config, mesh_interface: MeshtasticInterface)
    def initialize(self) -> None
    def cleanup(self) -> None
    def handle_message(self, message: MeshMessage) -> None
    def process_pending_tasks(self) -> None
    def get_statistics(self) -> Dict[str, any]
```

#### `handle_message(message: MeshMessage) -> None`
Process an incoming message.

**Parameters:**
- `message`: Received Meshtastic message

**Processing:**
- Rate limiting check
- Session management
- Command parsing
- Response generation

#### `get_statistics() -> Dict[str, any]`
Get handler statistics including:
- Total messages processed
- Active sessions
- Rate limiting info
- Session timeouts

### UserSession

Represents an active user session.

```python
@dataclass
class UserSession:
    user_id: str
    user_name: str
    channel: int
    last_activity: datetime
    current_menu: str = "main"
    menu_history: List[str] = None
    context: Dict[str, any] = None
    message_count: int = 0
```

### RateLimiter

Implements rate limiting for message handling.

```python
class RateLimiter:
    def __init__(self, max_messages: int, window_seconds: int)
    def is_allowed(self, user_id: str) -> bool
```

#### `is_allowed(user_id: str) -> bool`
Check if user can send more messages.

**Parameters:**
- `user_id`: User identifier

**Returns:**
- `True` if message allowed, `False` if rate limited

## Plugin System

### BBMeshPlugin (Abstract Base)

Base class for all BBMesh plugins.

```python
class BBMeshPlugin(ABC):
    def __init__(self, name: str, config: Dict[str, Any])
    
    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResponse
    
    def is_enabled(self) -> bool
    def get_help_text(self) -> str
    def validate_config(self) -> bool
    def initialize(self) -> bool
    def cleanup(self) -> None
```

**Properties:**
- `name`: Plugin name
- `config`: Plugin configuration dictionary
- `logger`: Plugin-specific logger
- `enabled`: Whether plugin is enabled
- `timeout`: Plugin execution timeout
- `description`: Plugin description

#### `execute(context: PluginContext) -> PluginResponse`
Main plugin execution method (abstract).

**Parameters:**
- `context`: Plugin execution context

**Returns:**
- Plugin response object

### SimpleResponsePlugin

Base class for simple response plugins.

```python
class SimpleResponsePlugin(BBMeshPlugin):
    @abstractmethod
    def generate_response(self, context: PluginContext) -> str
```

#### `generate_response(context: PluginContext) -> str`
Generate response text (abstract).

**Returns:**
- Response text string

### InteractivePlugin

Base class for interactive plugins with session state.

```python
class InteractivePlugin(BBMeshPlugin):
    @abstractmethod
    def start_session(self, context: PluginContext) -> PluginResponse
    
    @abstractmethod
    def continue_session(self, context: PluginContext) -> PluginResponse
```

#### `start_session(context: PluginContext) -> PluginResponse`
Start new interactive session.

#### `continue_session(context: PluginContext) -> PluginResponse`
Continue existing interactive session.

### PluginContext

Context information passed to plugins.

```python
@dataclass
class PluginContext:
    user_id: str
    user_name: str
    channel: int
    session_data: Dict[str, Any]
    message: MeshMessage
    plugin_config: Dict[str, Any]
```

### PluginResponse

Response returned by plugins.

```python
@dataclass
class PluginResponse:
    text: str
    continue_session: bool = False
    session_data: Dict[str, Any] = None
    error: Optional[str] = None
```

**Properties:**
- `text`: Response text to send to user
- `continue_session`: Whether to maintain session state
- `session_data`: Updated session data dictionary
- `error`: Error message if plugin failed

## Menu System

### MenuSystem

Manages hierarchical menu navigation.

```python
class MenuSystem:
    def __init__(self, config: MenuConfig)
    def get_menu(self, name: str) -> Optional[Menu]
    def get_menu_display(self, menu_name: str) -> str
    def process_menu_input(self, menu_name: str, user_input: str) -> Dict[str, Any]
    def get_menu_path(self, menu_name: str) -> List[str]
    def validate_menu_structure(self) -> List[str]
    def get_available_menus(self) -> List[str]
    def get_menu_statistics(self) -> Dict[str, Any]
```

#### `get_menu_display(menu_name: str) -> str`
Get formatted display text for a menu.

**Parameters:**
- `menu_name`: Name of menu to display

**Returns:**
- Formatted menu text

#### `process_menu_input(menu_name: str, user_input: str) -> Dict[str, Any]`
Process user input for menu navigation.

**Parameters:**
- `menu_name`: Current menu name
- `user_input`: User's selection/input

**Returns:**
- Dictionary with action information:
  - `action`: Action type (goto_menu, run_plugin, show_message, etc.)
  - `target`: Target menu name (for goto_menu)
  - `plugin`: Plugin name (for run_plugin)
  - `message`: Message text (for show_message)

### Menu

Represents a single menu with items.

```python
class Menu:
    def __init__(self, name: str, title: str, description: str = "", parent: str = None)
    def add_item(self, key: str, item: MenuItem) -> None
    def get_item(self, key: str) -> Optional[MenuItem]
    def get_display_text(self, show_descriptions: bool = False) -> str
```

**Properties:**
- `name`: Menu identifier
- `title`: Display title
- `description`: Menu description
- `parent`: Parent menu name
- `items`: Dictionary of menu items

### MenuItem

Represents a single menu item.

```python
class MenuItem:
    def __init__(self, title: str, action: str, **kwargs)
```

**Properties:**
- `title`: Display title
- `action`: Action to perform when selected
- `description`: Item description
- `target`: Target menu (for goto_menu action)
- `plugin`: Plugin name (for run_plugin action)
- `enabled`: Whether item is enabled

## Logging

### BBMeshLogger

Specialized logger with BBMesh-specific functionality.

```python
class BBMeshLogger:
    def __init__(self, name: str)
    def log_message(self, direction: str, sender: str, channel: int, message: str, node_id: Optional[str] = None)
    def log_menu_action(self, user: str, action: str, menu_path: str)
    def log_plugin_action(self, user: str, plugin: str, action: str, result: Optional[str] = None)
    def log_error(self, context: str, error: Exception, user: Optional[str] = None)
    def debug(self, message: str)
    def info(self, message: str)
    def warning(self, message: str)
    def error(self, message: str)
```

#### `log_message(direction, sender, channel, message, node_id=None)`
Log Meshtastic message with context.

**Parameters:**
- `direction`: "RX" or "TX"
- `sender`: Sender node ID or name
- `channel`: Channel number
- `message`: Message content
- `node_id`: Local node ID (optional)

### Logging Setup

```python
def setup_logging(config: LoggingConfig, debug: bool = False) -> None
def get_logger(name: str) -> logging.Logger
```

#### `setup_logging(config, debug=False)`
Configure logging system.

**Parameters:**
- `config`: Logging configuration
- `debug`: Enable debug mode (overrides config level)

## Utilities

### File Size Parsing

```python
def _parse_file_size(size_str: str) -> int
```

Parse file size strings like "10MB" into bytes.

**Parameters:**
- `size_str`: Size string with units (KB, MB, GB)

**Returns:**
- Size in bytes

## Error Handling

### Common Exceptions

BBMesh raises standard Python exceptions:

- `FileNotFoundError`: Configuration files not found
- `ConnectionError`: Meshtastic connection failures
- `TimeoutError`: Plugin or operation timeouts
- `ValueError`: Invalid configuration values
- `RuntimeError`: General runtime errors

### Plugin Exceptions

Plugins should handle exceptions gracefully:

```python
try:
    result = plugin.execute(context)
except Exception as e:
    logger.error(f"Plugin {plugin.name} failed: {e}")
    result = PluginResponse(
        text="❌ Plugin error occurred",
        error=str(e)
    )
```

## Usage Examples

### Basic Server Setup

```python
from pathlib import Path
from bbmesh.core.config import Config
from bbmesh.core.server import BBMeshServer

# Load configuration
config = Config.load(Path("config/bbmesh.yaml"))

# Create and start server
server = BBMeshServer(config)
server.start()
```

### Custom Plugin Development

```python
from bbmesh.plugins.base import SimpleResponsePlugin, PluginContext

class WeatherPlugin(SimpleResponsePlugin):
    def generate_response(self, context: PluginContext) -> str:
        location = context.message.text.replace("weather", "").strip()
        weather_data = self.get_weather(location)
        return f"🌤️ Weather in {location}: {weather_data}"
    
    def get_weather(self, location: str) -> str:
        # Implementation here
        return "Sunny, 22°C"
```

### Message Handler Customization

```python
from bbmesh.core.message_handler import MessageHandler

class CustomMessageHandler(MessageHandler):
    def _process_message(self, message):
        # Custom message processing logic
        if message.text.startswith("custom:"):
            return self._handle_custom_command(message)
        return super()._process_message(message)
```

## Testing

### Mock Objects

BBMesh provides mock objects for testing:

```python
class MockMeshtasticInterface:
    def __init__(self):
        self.sent_messages = []
    
    def send_message(self, text, channel=0, destination=None):
        self.sent_messages.append({
            "text": text,
            "channel": channel,
            "destination": destination
        })
        return True
```

### Test Utilities

```python
def create_test_message(sender_id="test", text="test") -> MeshMessage:
    return MeshMessage(
        sender_id=sender_id,
        sender_name="TestUser",
        channel=0,
        text=text,
        timestamp=datetime.now(),
        is_direct=True,
        hop_limit=3,
        snr=5.2,
        rssi=-85
    )
```

## Performance Considerations

### Memory Usage
- Session data is kept in memory
- Large plugin session data should be paginated
- Consider session cleanup intervals

### Response Times
- Plugin timeout defaults to 30 seconds
- Meshtastic message rate limits apply
- Network latency affects response times

### Concurrency
- BBMesh is single-threaded by design
- Plugin execution blocks message processing
- Use async patterns for I/O operations in plugins

## Version Compatibility

This API reference is for BBMesh v0.1.0. Future versions may include:

- Backward compatibility for configuration
- Plugin API stability
- Database schema migrations
- Deprecation warnings for removed features

For the most up-to-date API information, see the source code and inline documentation.