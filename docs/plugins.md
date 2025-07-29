# BBMesh Plugin Development Guide

This guide covers everything you need to know about developing plugins for BBMesh, from simple response plugins to complex interactive games.

## Table of Contents

- [Plugin Architecture Overview](#plugin-architecture-overview)
- [Plugin Types](#plugin-types)
- [Quick Start Tutorial](#quick-start-tutorial)
- [Plugin Base Classes](#plugin-base-classes)
- [Built-in Plugin Reference](#built-in-plugin-reference)
- [Advanced Plugin Development](#advanced-plugin-development)
- [Testing Plugins](#testing-plugins)
- [Publishing Plugins](#publishing-plugins)

## Plugin Architecture Overview

BBMesh plugins are Python classes that extend base plugin classes. They receive message context and return responses that can be simple text or complex interactive sessions.

### Key Concepts

- **Plugin Context**: Information about the user, message, and session
- **Plugin Response**: Text response with optional session state
- **Session Management**: Maintaining state across multiple interactions
- **Configuration**: Plugin-specific settings and parameters

### Plugin Lifecycle

1. **Initialization**: Plugin loaded and configured
2. **Execution**: Plugin receives message context
3. **Response**: Plugin returns text and session data
4. **Cleanup**: Plugin resources are cleaned up

## Plugin Types

### Simple Response Plugins
Return immediate text responses without maintaining state.

**Use Cases:**
- Information display (time, status, help)
- Calculations and utilities
- Quick lookups and references

### Interactive Plugins
Maintain session state for multi-turn conversations.

**Use Cases:**
- Games and puzzles
- Multi-step wizards
- Complex data entry

## Quick Start Tutorial

### Creating Your First Plugin

Let's create a simple "Hello World" plugin:

1. **Create the plugin file**: `src/bbmesh/plugins/hello.py`

```python
from .base import SimpleResponsePlugin, PluginContext

class HelloPlugin(SimpleResponsePlugin):
    """A simple hello world plugin."""
    
    def generate_response(self, context: PluginContext) -> str:
        """Generate a personalized greeting."""
        user_name = context.user_name
        return f"👋 Hello {user_name}! Welcome to BBMesh!"
```

2. **Register the plugin**: Add to `BUILTIN_PLUGINS` in `builtin.py`

```python
BUILTIN_PLUGINS = {
    # ... existing plugins
    "hello": HelloPlugin,
}
```

3. **Configure the plugin**: Add to `config/plugins.yaml`

```yaml
plugins:
  hello:
    enabled: true
    description: "Simple greeting plugin"
    timeout: 5
```

4. **Add to menu**: Update `config/menus.yaml`

```yaml
menus:
  main:
    options:
      # ... existing options
      5:
        title: "Say Hello"
        action: "run_plugin"
        plugin: "hello"
        description: "Get a friendly greeting"
```

### Testing Your Plugin

Run the test script to verify your plugin works:

```bash
python test_bbmesh.py
```

Or test manually:
```bash
python -c "
from src.bbmesh.plugins.hello import HelloPlugin
from src.bbmesh.plugins.base import PluginContext, MeshMessage
from datetime import datetime

plugin = HelloPlugin('hello', {'enabled': True})
plugin.initialize()

# Create test context
msg = MeshMessage('test_user', 'TestUser', 0, 'hello', datetime.now(), True, 3, 5.2, -85)
context = PluginContext('test_user', 'TestUser', 0, {}, msg, {})

response = plugin.execute(context)
print(response.text)
"
```

## Plugin Base Classes

### BBMeshPlugin (Abstract Base)

The foundation for all plugins:

```python
class BBMeshPlugin(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = BBMeshLogger(f"plugin.{name}")
        self.enabled = config.get("enabled", True)
        self.timeout = config.get("timeout", 30)
        self.description = config.get("description", "No description")
    
    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResponse:
        """Execute the plugin with given context."""
        pass
```

**Key Methods:**
- `execute()`: Main plugin logic (abstract)
- `is_enabled()`: Check if plugin is enabled
- `get_help_text()`: Return help text
- `validate_config()`: Validate plugin configuration
- `initialize()`: Setup plugin resources
- `cleanup()`: Clean up plugin resources

### SimpleResponsePlugin

For plugins that return immediate responses:

```python
class SimpleResponsePlugin(BBMeshPlugin):
    @abstractmethod
    def generate_response(self, context: PluginContext) -> str:
        """Generate response text."""
        pass
```

**Example:**
```python
class TimePlugin(SimpleResponsePlugin):
    def generate_response(self, context: PluginContext) -> str:
        now = datetime.now()
        return f"🕒 Current time: {now.strftime('%H:%M:%S')}"
```

### InteractivePlugin

For plugins that maintain session state:

```python
class InteractivePlugin(BBMeshPlugin):
    @abstractmethod
    def start_session(self, context: PluginContext) -> PluginResponse:
        """Start a new interactive session."""
        pass
    
    @abstractmethod
    def continue_session(self, context: PluginContext) -> PluginResponse:
        """Continue an existing session."""
        pass
```

**Example:**
```python
class QuizPlugin(InteractivePlugin):
    def start_session(self, context: PluginContext) -> PluginResponse:
        question = self.get_random_question()
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_question": question,
            f"{self.name}_attempts": 0
        }
        
        return PluginResponse(
            text=f"📚 Quiz Time!\n{question['text']}",
            continue_session=True,
            session_data=session_data
        )
    
    def continue_session(self, context: PluginContext) -> PluginResponse:
        question = context.session_data[f"{self.name}_question"]
        user_answer = context.message.text.strip().lower()
        
        if user_answer == question['answer'].lower():
            return PluginResponse(
                text="🎉 Correct! Well done!",
                continue_session=False
            )
        else:
            return PluginResponse(
                text="❌ Incorrect. Try again:",
                continue_session=True,
                session_data=context.session_data
            )
```

## Plugin Context and Response

### PluginContext

Information passed to plugins:

```python
@dataclass
class PluginContext:
    user_id: str              # Unique user identifier
    user_name: str            # Display name
    channel: int              # Meshtastic channel
    session_data: Dict        # Session state data
    message: MeshMessage      # Original message
    plugin_config: Dict       # Plugin configuration
```

### PluginResponse

Plugin return value:

```python
@dataclass
class PluginResponse:
    text: str                      # Response text to send
    continue_session: bool = False # Keep session active?
    session_data: Dict = None      # Updated session data
    error: Optional[str] = None    # Error message if any
```

### MeshMessage

Message information:

```python
@dataclass
class MeshMessage:
    sender_id: str        # Node ID of sender
    sender_name: str      # Display name
    channel: int          # Channel number
    text: str             # Message text
    timestamp: datetime   # When received
    is_direct: bool       # Direct message vs broadcast
    hop_limit: int        # Message hop count
    snr: float           # Signal to noise ratio
    rssi: int            # Signal strength
    to_node: Optional[str] # Destination node (if any)
```

## Built-in Plugin Reference

### WelcomePlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Welcome new users  
**Configuration**: None  
**Usage**: Automatic on first contact

### HelpPlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Display available commands  
**Configuration**: None  
**Usage**: User sends "help"

### TimePlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Display current time  
**Configuration**:
```yaml
time:
  timezone: "UTC"
  format: "%Y-%m-%d %H:%M:%S"
```

### PingPlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Connectivity test with signal info  
**Configuration**:
```yaml
ping:
  include_signal_info: true
```

### CalculatorPlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Basic arithmetic calculations  
**Configuration**:
```yaml
calculator:
  allowed_operations: ["+", "-", "*", "/", "**", "%"]
  max_expression_length: 50
```
**Usage**: Send math expressions like "2 + 2" or "calc 10 * 5"

### NumberGuessPlugin
**Type**: InteractivePlugin  
**Purpose**: Number guessing game  
**Configuration**:
```yaml
number_guess:
  min_number: 1
  max_number: 100
  max_attempts: 7
```
**Session Data**:
- `number_guess_active`: Game active flag
- `number_guess_target`: Target number
- `number_guess_attempts`: Current attempt count

### NodeLookupPlugin
**Type**: SimpleResponsePlugin  
**Purpose**: Display mesh node information  
**Configuration**:
```yaml
node_lookup:
  show_signal_info: true
  show_last_seen: true
```

## Advanced Plugin Development

### Configuration Validation

Override `validate_config()` to check plugin settings:

```python
class WeatherPlugin(SimpleResponsePlugin):
    def validate_config(self) -> bool:
        """Validate that API key is provided."""
        api_key = self.config.get("api_key")
        if not api_key:
            self.logger.error("Weather API key not configured")
            return False
        return True
```

### Error Handling

Always handle errors gracefully:

```python
def generate_response(self, context: PluginContext) -> str:
    try:
        # Plugin logic here
        result = self.perform_calculation(context.message.text)
        return f"Result: {result}"
    except ValueError as e:
        return f"❌ Invalid input: {e}"
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        return "❌ Plugin error occurred. Please try again."
```

### External API Integration

For plugins that call external APIs:

```python
import requests
from typing import Optional

class WeatherPlugin(SimpleResponsePlugin):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = config.get("api_key")
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def generate_response(self, context: PluginContext) -> str:
        location = self.extract_location(context.message.text)
        weather_data = self.get_weather(location)
        
        if weather_data:
            return self.format_weather(weather_data)
        else:
            return "❌ Unable to get weather information"
    
    def get_weather(self, location: str) -> Optional[Dict]:
        """Fetch weather data from API."""
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Weather API error: {e}")
            return None
```

### Session Data Management

For complex interactive plugins:

```python
class MultiStepWizardPlugin(InteractivePlugin):
    STEPS = ["name", "age", "location", "confirm"]
    
    def start_session(self, context: PluginContext) -> PluginResponse:
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_step": 0,
            f"{self.name}_data": {}
        }
        
        return PluginResponse(
            text="📝 Registration Wizard\nWhat's your name?",
            continue_session=True,
            session_data=session_data
        )
    
    def continue_session(self, context: PluginContext) -> PluginResponse:
        step_index = context.session_data[f"{self.name}_step"]
        user_data = context.session_data[f"{self.name}_data"]
        user_input = context.message.text.strip()
        
        # Process current step
        current_step = self.STEPS[step_index]
        user_data[current_step] = user_input
        
        # Move to next step
        step_index += 1
        
        if step_index >= len(self.STEPS):
            # Wizard complete
            return PluginResponse(
                text=f"✅ Registration complete!\nName: {user_data['name']}",
                continue_session=False
            )
        else:
            # Continue to next step
            next_step = self.STEPS[step_index]
            prompt = self.get_step_prompt(next_step)
            
            context.session_data[f"{self.name}_step"] = step_index
            
            return PluginResponse(
                text=prompt,
                continue_session=True,
                session_data=context.session_data
            )
```

### Resource Management

For plugins that use resources:

```python
class DatabasePlugin(SimpleResponsePlugin):
    def initialize(self) -> bool:
        """Initialize database connection."""
        try:
            self.db_path = self.config.get("database_path", "data/plugin.db")
            self.connection = sqlite3.connect(self.db_path)
            self.logger.info(f"Database connected: {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Close database connection."""
        if hasattr(self, 'connection'):
            self.connection.close()
            self.logger.info("Database connection closed")
```

## Testing Plugins

### Unit Testing

Create test files in `tests/plugins/`:

```python
# tests/plugins/test_calculator.py
import pytest
from datetime import datetime
from src.bbmesh.plugins.builtin import CalculatorPlugin
from src.bbmesh.plugins.base import PluginContext
from src.bbmesh.core.meshtastic_interface import MeshMessage

def create_test_context(text: str) -> PluginContext:
    """Helper to create test context."""
    message = MeshMessage(
        sender_id="test_user",
        sender_name="TestUser",
        channel=0,
        text=text,
        timestamp=datetime.now(),
        is_direct=True,
        hop_limit=3,
        snr=5.2,
        rssi=-85
    )
    
    return PluginContext(
        user_id="test_user",
        user_name="TestUser",
        channel=0,
        session_data={},
        message=message,
        plugin_config={}
    )

def test_calculator_basic_arithmetic():
    """Test basic arithmetic operations."""
    plugin = CalculatorPlugin("calc", {"enabled": True})
    plugin.initialize()
    
    test_cases = [
        ("2 + 2", "4"),
        ("10 - 3", "7"),
        ("5 * 6", "30"),
        ("15 / 3", "5"),
    ]
    
    for expression, expected in test_cases:
        context = create_test_context(expression)
        response = plugin.execute(context)
        
        assert expected in response.text
        assert response.error is None

def test_calculator_invalid_expression():
    """Test error handling for invalid expressions."""
    plugin = CalculatorPlugin("calc", {"enabled": True})
    plugin.initialize()
    
    context = create_test_context("invalid expression")
    response = plugin.execute(context)
    
    assert "❌" in response.text
    assert "Invalid" in response.text or "error" in response.text.lower()
```

### Integration Testing

Test plugins with the full system:

```python
# tests/test_plugin_integration.py
def test_plugin_in_message_handler():
    """Test plugin execution through message handler."""
    config = Config.load(Path("config/bbmesh.yaml"))
    mock_interface = MockMeshtasticInterface()
    handler = MessageHandler(config, mock_interface)
    handler.initialize()
    
    # Test plugin execution
    calc_message = create_test_message(text="2 + 2")
    handler.handle_message(calc_message)
    
    # Check response was sent
    assert len(mock_interface.sent_messages) > 0
    response_text = mock_interface.sent_messages[0]["text"]
    assert "4" in response_text
```

### Manual Testing

Test interactively with the system:

```bash
# Start BBMesh in debug mode
bbmesh start --debug

# Send test messages from another terminal or device
# Monitor logs for plugin execution
tail -f logs/bbmesh.log
```

## Plugin Security Best Practices

### Input Validation

Always validate user input:

```python
def generate_response(self, context: PluginContext) -> str:
    user_input = context.message.text.strip()
    
    # Length validation
    if len(user_input) > 100:
        return "❌ Input too long"
    
    # Content validation
    if not re.match(r'^[a-zA-Z0-9\s]+$', user_input):
        return "❌ Invalid characters"
    
    # Process validated input
    return self.process_input(user_input)
```

### Resource Limits

Prevent resource exhaustion:

```python
def execute(self, context: PluginContext) -> PluginResponse:
    # Set execution timeout
    start_time = time.time()
    timeout = self.config.get("timeout", 30)
    
    while self.processing:
        if time.time() - start_time > timeout:
            return PluginResponse(
                text="⏰ Plugin timed out",
                error="Timeout exceeded"
            )
        # Continue processing...
```

### Error Handling

Never expose internal details:

```python
def generate_response(self, context: PluginContext) -> str:
    try:
        return self.process_request(context)
    except ValueError as e:
        # User error - safe to show
        return f"❌ {str(e)}"
    except Exception as e:
        # System error - log but don't expose
        self.logger.error(f"Plugin error: {e}")
        return "❌ An error occurred. Please try again."
```

### Configuration Security

Validate configuration values:

```python
def validate_config(self) -> bool:
    """Validate plugin configuration."""
    # Check required fields
    if "api_key" not in self.config:
        return False
    
    # Validate URL format
    url = self.config.get("api_url", "")
    if url and not url.startswith(("http://", "https://")):
        return False
    
    # Check numeric ranges
    timeout = self.config.get("timeout", 30)
    if not (1 <= timeout <= 300):
        return False
    
    return True
```

## Publishing Plugins

### Creating Plugin Packages

Structure your plugin as a Python package:

```
my_bbmesh_plugin/
├── setup.py
├── README.md
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   └── config.yaml
└── tests/
    └── test_plugin.py
```

### Plugin Registration

Plugins can be loaded dynamically:

```python
# In your plugin package
from bbmesh.plugins.base import SimpleResponsePlugin

class MyCustomPlugin(SimpleResponsePlugin):
    """Custom plugin for BBMesh."""
    
    def generate_response(self, context):
        return "Hello from my custom plugin!"

# Plugin entry point
def get_plugin_class():
    return MyCustomPlugin
```

### Distribution

Consider these distribution methods:

1. **GitHub Repository**: Share source code
2. **PyPI Package**: `pip install bbmesh-my-plugin`
3. **Direct Installation**: Copy files to plugins directory

### Documentation

Include comprehensive documentation:

- **README.md**: Installation and usage
- **Configuration**: All config options
- **Examples**: Usage examples
- **API**: Plugin interface documentation

## Plugin Development Checklist

Before publishing your plugin:

- [ ] Plugin follows naming conventions
- [ ] Configuration is validated
- [ ] Error handling is comprehensive
- [ ] Input validation is implemented
- [ ] Logging is appropriate (not excessive)
- [ ] Documentation is complete
- [ ] Tests are written and passing
- [ ] Security considerations addressed
- [ ] Performance is acceptable
- [ ] Memory usage is reasonable

## Getting Help

### Resources
- **Examples**: Check `src/bbmesh/plugins/builtin.py`
- **API Reference**: See `docs/api.md`
- **Community**: GitHub Discussions
- **Issues**: GitHub Issues for bugs

### Common Questions

**Q: How do I access mesh network information in my plugin?**
A: Use `context.message` for signal info, and access the mesh interface through the handler if needed.

**Q: Can plugins communicate with each other?**
A: Not directly. Use session data or external storage for coordination.

**Q: How do I handle plugin dependencies?**
A: Validate dependencies in `validate_config()` and provide clear error messages.

**Q: What's the maximum plugin execution time?**
A: Configurable, default 30 seconds. Keep plugins responsive.

### Plugin Ideas

**Simple Plugins:**
- Weather information
- Unit converter
- QR code generator
- Morse code translator
- Base64 encoder/decoder

**Interactive Plugins:**
- Adventure games
- Trivia contests
- Survey/polling system
- Multi-user chat rooms
- Turn-based games

**Utility Plugins:**
- File transfer
- Message forwarding
- Network diagnostics
- System monitoring
- Database queries

Happy plugin development! The BBMesh community looks forward to seeing your creative contributions.