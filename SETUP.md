# BBMesh Setup Guide

This guide will help you set up and run your BBMesh BBS system.

## Prerequisites

### Hardware Required
- **Raspberry Pi** (or similar Linux system) as the host
- **Heltec ESP32 V3** (or compatible Meshtastic node)
- **LoRa Antenna** appropriate for your region
- **USB Cable** to connect ESP32 to Raspberry Pi

### Software Requirements
- Python 3.8 or higher
- pip package manager
- Git (for updates)

## Installation Steps

### 1. Hardware Setup
1. Flash your Heltec ESP32 V3 with Meshtastic firmware:
   - Visit https://flasher.meshtastic.org/
   - Connect ESP32 via USB and flash the firmware
   - Configure your node settings (region, channels, etc.)

2. Connect ESP32 to your Raspberry Pi via USB

### 2. Software Installation
1. Clone and install BBMesh:
   ```bash
   cd /home/pi
   git clone https://github.com/deadchannelsky/BBMesh.git
   cd BBMesh
   pip install -e .
   ```

2. Find your serial port:
   ```bash
   # List USB devices
   ls /dev/ttyUSB*
   # or for some systems
   ls /dev/ttyACM*
   ```

3. Update configuration:
   ```bash
   nano config/bbmesh.yaml
   ```
   
   Update the serial port to match your system:
   ```yaml
   meshtastic:
     serial:
       port: "/dev/ttyUSB0"  # Update this line
   ```

### 3. Test Installation
Run the test script to verify everything works:
```bash
python test_bbmesh.py
```

### 4. Start BBMesh
```bash
bbmesh start
```

## Configuration

### Main Configuration (`config/bbmesh.yaml`)
- **Serial settings**: Port, baud rate, timeout
- **Channels**: Which channels to monitor and respond to
- **Server settings**: Welcome message, rate limits, timeouts
- **Logging**: Log levels, file locations, rotation

### Menu System (`config/menus.yaml`)
- **Menu structure**: Hierarchical menu definitions
- **Menu items**: Actions, descriptions, navigation
- **Display settings**: Formatting options

### Plugins (`config/plugins.yaml`)
- **Plugin enable/disable**: Control which features are active
- **Plugin settings**: Configure individual plugin behavior
- **Timeouts**: Set execution limits for plugins

## Usage

### Available Commands
Users can interact with BBMesh by sending these commands to your node:

- **HELP** - Show available commands
- **MENU** - Display main menu
- **PING** - Test connectivity
- **STATUS** - System information
- **TIME** - Current date and time
- **GAMES** - Access games menu
- **UTILS** - Access utilities menu

### Menu Navigation
- Send **numbers** (1, 2, 3) to select menu options
- Send **BACK** to go to previous menu
- Send **MAIN** or **MENU** to return to main menu
- Send **HELP** for command reference

### Interactive Features
- **Number Guessing Game**: Multi-turn guessing game
- **Calculator**: Basic math operations
- **Node Lookup**: Information about mesh nodes
- **System Status**: Real-time system information

## Troubleshooting

### Common Issues

**"Failed to connect to Meshtastic node"**
- Check USB connection
- Verify serial port in config
- Ensure ESP32 has Meshtastic firmware
- Check permissions: `sudo usermod -a -G dialout $USER`

**"No response from BBS"**
- Verify node is connected to mesh
- Check monitored channels match your setup
- Ensure you're sending direct messages
- Check rate limiting settings

**"Plugin timeout errors"**
- Increase plugin timeout in config
- Check system resources
- Review plugin logs

### Logs
Check logs for detailed information:
```bash
tail -f logs/bbmesh.log
```

### Debug Mode
Run with debug logging:
```bash
bbmesh start --debug
```

## Customization

### Adding Custom Responses
Edit `src/bbmesh/core/message_handler.py` to add custom response patterns.

### Creating Custom Plugins
1. Create new plugin in `src/bbmesh/plugins/`
2. Extend `BBMeshPlugin` base class
3. Add plugin to configuration
4. Restart BBMesh

### Modifying Menus
Edit `config/menus.yaml` to add new menu items or reorganize structure.

## Security Considerations

- BBMesh runs with the privileges of the user account
- No external network connections by default
- Rate limiting prevents spam/abuse
- Plugin execution is sandboxed with timeouts
- All interactions are logged

## Performance Tips

- **Raspberry Pi 3B+** or better recommended for multiple concurrent users
- **SD Card Class 10** or better for logging performance
- **Monitor system resources** if running other services
- **Regular log rotation** to prevent disk space issues

## Updates

To update BBMesh:
```bash
cd BBMesh
git pull
pip install -e . --upgrade
```

## Support

For issues and feature requests:
- Check the logs first: `logs/bbmesh.log`
- Run test script: `python test_bbmesh.py`
- Review configuration files
- Submit issues on GitHub

## Legal

This software is provided as-is for amateur radio and educational use. Users are responsible for compliance with local regulations regarding radio operations.