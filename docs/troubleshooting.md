# BBMesh Troubleshooting Guide

This guide covers common issues, diagnostic procedures, and solutions for BBMesh deployment and operation.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Connection Issues](#connection-issues)
- [Message Handling Problems](#message-handling-problems)
- [Plugin Issues](#plugin-issues)
- [Performance Problems](#performance-problems)
- [Configuration Errors](#configuration-errors)
- [Hardware-Specific Issues](#hardware-specific-issues)
- [Log Analysis](#log-analysis)
- [Advanced Debugging](#advanced-debugging)

## Quick Diagnostics

### System Health Check

Run these commands to quickly assess system status:

```bash
# Test BBMesh configuration
python test_bbmesh.py

# Check BBMesh status
bbmesh --version
bbmesh start --debug

# Check system resources
df -h                    # Disk space
free -h                  # Memory usage
ps aux | grep bbmesh     # BBMesh processes
```

### Log Quick Check

```bash
# Recent errors
tail -50 logs/bbmesh.log | grep ERROR

# Connection status
grep "Connect" logs/bbmesh.log | tail -10

# Recent activity
tail -20 logs/bbmesh.log
```

## Connection Issues

### "Failed to connect to Meshtastic node"

**Symptoms:**
- BBMesh fails to start
- Error: "Failed to connect to Meshtastic node"
- No response from BBS

**Diagnosis:**
```bash
# Check if device is detected
ls -la /dev/ttyUSB* /dev/ttyACM*

# Check device permissions
ls -la /dev/ttyUSB0

# Test serial connection
python -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('Serial connection successful')
ser.close()
"
```

**Solutions:**

1. **Check Physical Connection**
   ```bash
   # Unplug and reconnect USB cable
   # Check cable quality
   dmesg | tail -10  # Look for USB device messages
   ```

2. **Fix Permissions**
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Logout and login again
   
   # Or temporarily fix permissions
   sudo chmod 666 /dev/ttyUSB0
   ```

3. **Verify Serial Port**
   ```bash
   # Find correct port
   dmesg | grep tty
   ls /dev/tty* | grep -E "(USB|ACM)"
   
   # Update config with correct port
   nano config/bbmesh.yaml
   ```

4. **Check Meshtastic Firmware**
   ```bash
   # Test with Meshtastic CLI
   pip install meshtastic
   meshtastic --port /dev/ttyUSB0 --info
   ```

### "Device busy" or "Permission denied"

**Symptoms:**
- Serial port permission errors
- Device already in use

**Solutions:**
```bash
# Kill conflicting processes
sudo fuser -k /dev/ttyUSB0

# Check what's using the port
sudo lsof /dev/ttyUSB0

# Fix permissions permanently
sudo usermod -a -G dialout $USER
```

### Intermittent Connection Drops

**Symptoms:**
- Connection works initially then fails
- Periodic reconnection attempts

**Diagnosis:**
```bash
# Check USB power management
cat /sys/bus/usb/devices/*/power/autosuspend_delay_ms

# Monitor USB messages
sudo dmesg -w | grep -i usb
```

**Solutions:**
```bash
# Disable USB auto-suspend
echo -1 | sudo tee /sys/bus/usb/devices/*/power/autosuspend_delay_ms

# Increase timeout in config
nano config/bbmesh.yaml
# Set timeout: 3.0 under serial section
```

## Message Handling Problems

### "No response from BBS"

**Symptoms:**
- Messages sent to BBS but no reply
- BBS appears to receive messages but doesn't respond

**Diagnosis:**
```bash
# Check message reception
grep "RX" logs/bbmesh.log | tail -10

# Check channel configuration
grep "channel" config/bbmesh.yaml

# Verify rate limiting
grep "Rate limited" logs/bbmesh.log
```

**Solutions:**

1. **Check Channel Configuration**
   ```yaml
   # config/bbmesh.yaml
   meshtastic:
     monitored_channels: [0, 1, 2]  # Channels to listen on
     response_channels: [0, 1, 2]   # Channels to respond on
   ```

2. **Verify Message Types**
   ```yaml
   # Allow both direct and broadcast messages
   meshtastic:
     direct_message_only: false
   ```

3. **Check Rate Limiting**
   ```yaml
   # Temporarily disable rate limiting
   server:
     rate_limit_messages: 1000
     rate_limit_window: 60
   ```

### "Plugin timeout" or "Plugin error"

**Symptoms:**
- Plugin commands time out
- Error messages from plugins

**Diagnosis:**
```bash
# Check plugin logs
grep "plugin" logs/bbmesh.log | tail -20

# Test plugin individually
python -c "
from src.bbmesh.plugins.builtin import CalculatorPlugin
plugin = CalculatorPlugin('calc', {'enabled': True})
print(plugin.get_help_text())
"
```

**Solutions:**
```yaml
# Increase plugin timeout
plugins:
  plugin_timeout: 60  # Increase from default 30
```

## Plugin Issues

### Plugin Won't Load

**Symptoms:**
- Plugin not responding
- "Plugin not found" errors

**Diagnosis:**
```bash
# Check plugin is enabled
grep -A5 "enabled_plugins" config/bbmesh.yaml

# Verify plugin file exists
ls src/bbmesh/plugins/

# Test plugin import
python -c "
from src.bbmesh.plugins.builtin import BUILTIN_PLUGINS
print(list(BUILTIN_PLUGINS.keys()))
"
```

**Solutions:**
1. Enable plugin in configuration
2. Check plugin file permissions
3. Verify plugin class is registered

### Interactive Plugin Session Issues

**Symptoms:**
- Interactive plugins don't maintain state
- Sessions end unexpectedly

**Diagnosis:**
```bash
# Check session timeout
grep "session_timeout" config/bbmesh.yaml

# Look for session cleanup logs
grep "session" logs/bbmesh.log | tail -10
```

**Solutions:**
```yaml
# Increase session timeout
server:
  session_timeout: 600  # 10 minutes

# Check plugin session data handling
menu:
  timeout: 600
```

## Performance Problems

### High Memory Usage

**Symptoms:**
- BBMesh using excessive memory
- System becomes sluggish

**Diagnosis:**
```bash
# Check BBMesh memory usage
ps aux | grep bbmesh

# Monitor memory over time
watch 'ps aux | grep bbmesh'

# Check for memory leaks
valgrind python -c "import bbmesh; ..."
```

**Solutions:**
```yaml
# Reduce session timeout
server:
  session_timeout: 180  # 3 minutes

# Limit concurrent sessions
plugins:
  max_concurrent_sessions: 5

# Reduce log file size
logging:
  max_file_size: "5MB"
  backup_count: 3
```

### Slow Response Times

**Symptoms:**
- Long delays before responses
- Timeouts on simple commands

**Diagnosis:**
```bash
# Check system load
top
htop

# Monitor I/O
iotop

# Check plugin execution times
grep "Plugin.*took" logs/bbmesh.log
```

**Solutions:**
```yaml
# Reduce plugin timeouts
plugins:
  plugin_timeout: 15

# Optimize logging
logging:
  level: "WARNING"  # Reduce log verbosity

# Use faster storage
database:
  path: "/tmp/bbmesh.db"  # Use RAM disk (temporary)
```

## Configuration Errors

### YAML Parsing Errors

**Symptoms:**
- "Error loading configuration"
- YAML syntax errors

**Diagnosis:**
```bash
# Validate YAML syntax
python -c "
import yaml
with open('config/bbmesh.yaml', 'r') as f:
    yaml.safe_load(f)
print('YAML is valid')
"

# Check for common issues
grep -n ":" config/bbmesh.yaml | grep -E "(  :|:$)"
```

**Solutions:**
```bash
# Check indentation (use spaces, not tabs)
sed 's/\t/    /g' config/bbmesh.yaml > config/bbmesh_fixed.yaml

# Validate quotes
grep -n '"' config/bbmesh.yaml
```

### Invalid Configuration Values

**Symptoms:**
- "Invalid channel" errors
- Configuration validation failures

**Common Issues:**
```yaml
# Fix channel ranges (0-7 only)
meshtastic:
  monitored_channels: [0, 1, 2]  # Not [8, 9, 10]

# Fix timeout values
server:
  session_timeout: 300  # Not -1 or 0

# Fix file paths
logging:
  file_path: "logs/bbmesh.log"  # Not "../../../etc/passwd"
```

## Hardware-Specific Issues

### Raspberry Pi Issues

**Common Problems:**
- Power supply insufficient
- SD card corruption
- USB port limitations

**Solutions:**
```bash
# Check power supply
vcgencmd get_throttled
# 0x0 = OK, anything else indicates power issues

# Check SD card health
sudo fsck /dev/mmcblk0p2

# Use powered USB hub for Meshtastic device
# Check USB current
lsusb -v | grep -A1 "MaxPower"
```

### ESP32 Specific Issues

**Symptoms:**
- Frequent disconnections
- Boot loops
- Flash corruption

**Solutions:**
```bash
# Check ESP32 health
esptool.py --port /dev/ttyUSB0 flash_id

# Re-flash Meshtastic firmware if needed
# Use different USB cable
# Check power supply to ESP32
```

### USB-C Connection Issues

**Symptoms:**
- Device not detected
- Intermittent connections

**Solutions:**
```bash
# Try different USB-C orientation
# Use USB-A to USB-C cable instead of USB-C to USB-C
# Check for USB-C PD negotiation issues
```

## Log Analysis

### Understanding Log Messages

**Connection Logs:**
```
INFO - Connecting to Meshtastic node on /dev/ttyUSB0
INFO - Connected to node 123456789
```

**Message Logs:**
```
INFO - RX [123456789] CH0 TestUser: hello
INFO - TX [987654321] CH0 TestUser: Welcome to BBMesh!
```

**Error Patterns:**
```bash
# Find all errors
grep "ERROR" logs/bbmesh.log

# Connection issues
grep -E "(Failed|timeout|connection)" logs/bbmesh.log

# Plugin issues  
grep -E "(plugin.*error|timeout.*plugin)" logs/bbmesh.log

# Rate limiting
grep "Rate limited" logs/bbmesh.log
```

### Log Rotation Issues

**Symptoms:**
- Log files growing too large
- Disk space full

**Solutions:**
```yaml
# Configure log rotation
logging:
  max_file_size: "10MB"
  backup_count: 5

# Manual cleanup
find logs/ -name "*.log.*" -mtime +7 -delete
```

## Advanced Debugging

### Debug Mode

Enable comprehensive debugging:

```bash
# Start with debug logging
bbmesh start --debug

# Or set in config
logging:
  level: "DEBUG"
```

### Python Debugging

```bash
# Run with Python debugger
python -m pdb src/bbmesh/cli.py start

# Add debug prints to code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Network Analysis

```bash
# Monitor serial traffic (if using network connection)
sudo tcpdump -i any port 4403

# Check Meshtastic network status
meshtastic --port /dev/ttyUSB0 --nodes
```

### Memory Debugging

```bash
# Profile memory usage
python -m memory_profiler test_bbmesh.py

# Check for memory leaks
valgrind --tool=memcheck python test_bbmesh.py
```

## Getting More Help

### Information to Gather

When reporting issues, include:

1. **System Information:**
   ```bash
   uname -a
   python --version
   pip list | grep -E "(meshtastic|bbmesh)"
   ```

2. **Configuration:**
   ```bash
   # Sanitized configuration (remove sensitive data)
   cat config/bbmesh.yaml
   ```

3. **Logs:**
   ```bash
   # Recent logs with error context
   tail -100 logs/bbmesh.log
   ```

4. **Hardware:**
   - Meshtastic device model
   - Host system specs
   - Connection method

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community help
- **Documentation**: Check docs/ directory first
- **Test Script**: Run `python test_bbmesh.py` for basic validation

### Creating Minimal Reproduction

For complex issues:

1. Use minimal configuration
2. Enable debug logging
3. Document exact steps to reproduce
4. Include complete error messages

### Emergency Recovery

If BBMesh won't start:

```bash
# Reset to default configuration
cp config/bbmesh.yaml config/bbmesh.yaml.backup
bbmesh init-config

# Clear all data
rm -rf data/ logs/
mkdir data logs

# Verify hardware connection
python -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('Hardware OK')
ser.close()
"
```

Remember: Most issues are configuration-related and can be resolved by carefully reviewing the configuration files and logs.