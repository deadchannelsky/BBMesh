# BBMesh Configuration Guide

This guide covers all configuration options for BBMesh, including setup examples and troubleshooting tips.

## Configuration Files Overview

BBMesh uses three main YAML configuration files:

- **`config/bbmesh.yaml`** - Main system configuration
- **`config/menus.yaml`** - Menu structure and navigation
- **`config/plugins.yaml`** - Plugin settings and parameters

## Main Configuration (`config/bbmesh.yaml`)

### Meshtastic Configuration

```yaml
meshtastic:
  # Serial port settings for ESP32 connection
  serial:
    port: "/dev/ttyUSB0"  # Device path
    baudrate: 115200      # Communication speed
    timeout: 1.0          # Connection timeout in seconds
  
  # Node identification (auto-detected if null)
  node_id: null
  
  # Channels to monitor for incoming messages (0-7)
  monitored_channels: [0, 1, 2]
  
  # Channels where the BBS can respond
  response_channels: [0, 1, 2]
  
  # Only respond to direct messages (ignore broadcasts)
  direct_message_only: false
```

#### Serial Port Configuration

**Linux/Raspberry Pi:**
- USB devices: `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc.
- ACM devices: `/dev/ttyACM0`, `/dev/ttyACM1`, etc.
- Find your device: `ls /dev/tty*` or `dmesg | grep tty`

**macOS:**
- USB serial: `/dev/tty.usbserial-*`
- Find devices: `ls /dev/tty.*`

**Windows:**
- COM ports: `COM3`, `COM4`, etc.
- Check Device Manager for correct port

#### Channel Configuration

Meshtastic supports 8 channels (0-7):
- **Channel 0**: Primary channel (usually enabled by default)
- **Channels 1-7**: Secondary channels for specific purposes

**Configuration Tips:**
- `monitored_channels`: Channels BBMesh listens to
- `response_channels`: Channels BBMesh can send messages on
- Usually these should be the same channels
- Check your Meshtastic device channel settings

### Logging Configuration

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: "logs/bbmesh.log"
  max_file_size: "10MB"
  backup_count: 5
  console_output: true
```

#### Log Levels
- **DEBUG**: Verbose logging for development
- **INFO**: General information (recommended)
- **WARNING**: Important warnings
- **ERROR**: Error conditions
- **CRITICAL**: Critical system errors

#### File Rotation
- `max_file_size`: Maximum size before rotation (KB, MB, GB)
- `backup_count`: Number of backup files to keep
- Files are rotated as: `bbmesh.log`, `bbmesh.log.1`, `bbmesh.log.2`, etc.

### Server Configuration

```yaml
server:
  name: "BBMesh BBS"
  welcome_message: "Welcome to BBMesh BBS! Your gateway to the mesh network."
  motd_file: "config/motd.txt"
  max_message_length: 200
  session_timeout: 300
  rate_limit_messages: 10
  rate_limit_window: 60
  message_send_delay: 1.0
```

#### Server Settings Explained
- **name**: Display name for your BBS
- **welcome_message**: Greeting message for new users
- **motd_file**: Path to Message of the Day file (optional)
- **max_message_length**: Maximum characters per message (Meshtastic limit ~240)
- **session_timeout**: User session timeout in seconds
- **rate_limit_messages**: Max messages per user per window
- **rate_limit_window**: Rate limiting window in seconds
- **message_send_delay**: Minimum seconds between outgoing messages (prevents message loss/reordering)

#### Message Send Delay

The `message_send_delay` setting prevents rapid-fire message sending that can cause issues in mesh networks:

- **Purpose**: Ensures messages are sent with proper spacing to prevent ordering issues and message loss
- **Default**: 1.0 seconds (recommended for most deployments) 
- **Range**: 0.1 to 5.0 seconds
- **Tuning Guidelines**:
  - **Fast/reliable networks**: 0.5 seconds
  - **Standard mesh networks**: 1.0-1.5 seconds  
  - **Congested/slow networks**: 2.0-3.0 seconds
  - **Test environments**: 0.1 seconds (minimal delay)

**Note**: Lower values provide faster responses but may cause message delivery issues. Higher values ensure reliability but slow down interactions.

### Menu Configuration

```yaml
menu:
  menu_file: "config/menus.yaml"
  timeout: 300
  max_depth: 10
  prompt_suffix: " > "
```

### Plugin Configuration

```yaml
plugins:
  plugin_dir: "src/bbmesh/plugins"
  plugin_config_file: "config/plugins.yaml"
  enabled_plugins:
    - "welcome"
    - "help"
    - "time"
    - "ping"
  plugin_timeout: 30
```

### Database Configuration

```yaml
database:
  type: "sqlite"
  path: "data/bbmesh.db"
  backup_interval: 3600
```

## Menu Configuration (`config/menus.yaml`)

### Menu Structure

```yaml
menus:
  main:
    title: "BBMesh Main Menu"
    description: "Welcome to the BBMesh BBS system"
    options:
      1:
        title: "Help & Commands"
        action: "show_help"
        description: "Display available commands"
      2:
        title: "Games & Fun"
        action: "goto_menu"
        target: "games"
        description: "Access games and entertainment"
```

#### Menu Actions
- **show_help**: Display help information
- **show_status**: Show system status
- **show_time**: Display current time
- **show_mesh_info**: Show mesh network info
- **goto_menu**: Navigate to another menu
- **run_plugin**: Execute a plugin
- **show_message**: Display static message

#### Menu Settings

```yaml
settings:
  show_numbers: true
  show_descriptions: false
  max_options_per_page: 8
  timeout_seconds: 300
  back_commands: ["back", "b", ".."]
  home_commands: ["home", "main", "menu"]
  help_commands: ["help", "h", "?"]
```

## Plugin Configuration (`config/plugins.yaml`)

### Plugin Settings

```yaml
plugins:
  calculator:
    enabled: true
    description: "Basic calculator"
    allowed_operations: ["+", "-", "*", "/", "**", "%"]
    max_expression_length: 50
    timeout: 10
  
  number_guess:
    enabled: true
    description: "Number guessing game"
    min_number: 1
    max_number: 100
    max_attempts: 7
    timeout: 30
```

### Global Plugin Settings

```yaml
global:
  plugin_timeout: 30
  max_concurrent_sessions: 10
  error_message: "❌ Plugin error occurred. Please try again."
  timeout_message: "⏰ Plugin timed out. Please try again."
  disabled_message: "🚫 This feature is currently disabled."
```

## Environment-Specific Configurations

### Development Environment

```yaml
# config/bbmesh.yaml
meshtastic:
  serial:
    port: "/dev/ttyUSB0"

logging:
  level: "DEBUG"
  console_output: true

server:
  session_timeout: 600  # Longer timeout for testing
  rate_limit_messages: 100  # Relaxed rate limiting
```

### Production Environment

```yaml
# config/bbmesh.yaml
logging:
  level: "INFO"
  console_output: false
  file_path: "/var/log/bbmesh/bbmesh.log"

server:
  session_timeout: 300
  rate_limit_messages: 10
  rate_limit_window: 60

plugins:
  plugin_timeout: 30  # Strict timeouts
```

### Raspberry Pi Configuration

```yaml
# config/bbmesh.yaml
meshtastic:
  serial:
    port: "/dev/ttyACM0"  # Common for Pi
    timeout: 2.0  # Longer timeout for slower systems

logging:
  max_file_size: "5MB"  # Smaller logs for SD card
  backup_count: 3

server:
  max_message_length: 200  # Conservative limit
```

## Configuration Validation

BBMesh validates configuration on startup. Common validation errors:

### Serial Port Issues
```
Error: Serial port '/dev/ttyUSB0' not found
```
**Solution**: Check device connection and update port path

### Channel Configuration
```
Error: Channel 8 is invalid (must be 0-7)
```
**Solution**: Use channels 0-7 only

### File Path Issues
```
Error: Menu file 'config/menus.yaml' not found
```
**Solution**: Ensure file exists and path is correct

## Security Considerations

### File Permissions
```bash
# Secure configuration files
chmod 600 config/bbmesh.yaml
chmod 755 config/menus.yaml
chmod 755 config/plugins.yaml
```

### Serial Port Access
```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Rate Limiting
- Configure appropriate rate limits to prevent spam
- Monitor logs for suspicious activity
- Consider IP-based blocking for network interfaces

## Troubleshooting

### Common Configuration Issues

**Problem**: BBMesh won't start
```
Error: Failed to connect to Meshtastic node
```
**Solutions**:
1. Check serial port path
2. Verify device connection
3. Ensure Meshtastic firmware is installed
4. Check user permissions

**Problem**: No responses to messages
```
Messages received but no responses sent
```
**Solutions**:
1. Check monitored vs response channels
2. Verify direct_message_only setting
3. Check rate limiting configuration
4. Review plugin enable/disable status

**Problem**: Plugin timeouts
```
Plugin timed out during execution
```
**Solutions**:
1. Increase plugin_timeout value
2. Check system resources
3. Review plugin-specific timeouts
4. Enable debug logging

### Configuration Testing

Use the built-in test script to validate configuration:

```bash
python test_bbmesh.py
```

This will check:
- Configuration file loading
- Menu system validation
- Plugin initialization
- Mock message handling

### Debug Configuration

For troubleshooting, temporarily use this configuration:

```yaml
logging:
  level: "DEBUG"
  console_output: true

server:
  rate_limit_messages: 1000  # Disable rate limiting
  session_timeout: 3600      # Long timeout

plugins:
  plugin_timeout: 120        # Extended timeouts
```

## Performance Tuning

### Resource-Constrained Systems (Raspberry Pi Zero, etc.)

```yaml
server:
  max_message_length: 150    # Shorter messages
  session_timeout: 180       # Shorter sessions
  rate_limit_messages: 5     # Stricter rate limiting

plugins:
  plugin_timeout: 15         # Shorter timeouts
  max_concurrent_sessions: 3 # Fewer concurrent users

logging:
  level: "WARNING"           # Less logging
  max_file_size: "2MB"       # Smaller log files
```

### High-Performance Systems

```yaml
server:
  rate_limit_messages: 20    # Higher message limits
  session_timeout: 600       # Longer sessions

plugins:
  plugin_timeout: 60         # Longer timeouts
  max_concurrent_sessions: 20 # More concurrent users

logging:
  level: "INFO"
  max_file_size: "50MB"      # Larger log files
  backup_count: 10           # More backups
```

## Configuration Examples

See the `docs/examples/` directory for complete configuration examples for different use cases:

- `development.yaml` - Development environment
- `production.yaml` - Production deployment
- `minimal.yaml` - Minimal resource usage
- `full-featured.yaml` - All features enabled

## Configuration Updates

When updating BBMesh:

1. **Backup current configuration**:
   ```bash
   cp -r config/ config.backup/
   ```

2. **Check for new configuration options**:
   ```bash
   bbmesh init-config --output config/new-default.yaml
   diff config/bbmesh.yaml config/new-default.yaml
   ```

3. **Update configuration as needed**

4. **Validate new configuration**:
   ```bash
   python test_bbmesh.py
   ```

For questions about configuration, see the [troubleshooting guide](troubleshooting.md) or check the [GitHub issues](https://github.com/deadchannelsky/BBMesh/issues).