# BBMesh Production Deployment Guide

This guide covers deploying BBMesh in production environments, including systemd services, monitoring, security hardening, and maintenance procedures.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [System Service Setup](#system-service-setup)
- [Security Hardening](#security-hardening)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Optimization](#performance-optimization)
- [High Availability](#high-availability)
- [Troubleshooting Production Issues](#troubleshooting-production-issues)

## Prerequisites

### System Requirements

**Minimum:**
- Linux system (Raspberry Pi 3B+ or equivalent)
- 512MB RAM
- 4GB storage
- Python 3.8+
- Meshtastic-compatible device

**Recommended:**
- Raspberry Pi 4B or dedicated server
- 2GB+ RAM
- 16GB+ storage (SSD preferred)
- UPS power backup
- Network connectivity for monitoring

### Network Requirements

- Serial connection to Meshtastic device
- Optional: Network access for monitoring/updates
- Firewall considerations for monitoring ports

## Installation

### System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git

# Create dedicated user
sudo useradd -r -m -s /bin/bash bbmesh
sudo usermod -a -G dialout bbmesh

# Create directory structure
sudo mkdir -p /opt/bbmesh
sudo mkdir -p /var/log/bbmesh
sudo mkdir -p /var/lib/bbmesh
sudo chown -R bbmesh:bbmesh /opt/bbmesh /var/log/bbmesh /var/lib/bbmesh
```

### Application Installation

```bash
# Switch to bbmesh user
sudo -u bbmesh -i

# Clone repository
cd /opt/bbmesh
git clone https://github.com/deadchannelsky/BBMesh.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install application
pip install -e .

# Generate production configuration
bbmesh init-config --output config/bbmesh.yaml
```

### Configuration

Create production configuration:

```bash
# Edit production config
sudo -u bbmesh nano /opt/bbmesh/config/bbmesh.yaml
```

Key production settings:

```yaml
meshtastic:
  serial:
    port: "/dev/ttyUSB0"
    timeout: 1.0
  monitored_channels: [0, 1]
  response_channels: [0, 1]
  direct_message_only: true

logging:
  level: "INFO"
  file_path: "/var/log/bbmesh/bbmesh.log"
  max_file_size: "20MB"
  backup_count: 10
  console_output: false

server:
  session_timeout: 300
  rate_limit_messages: 10
  rate_limit_window: 60

database:
  path: "/var/lib/bbmesh/bbmesh.db"
```

## System Service Setup

### Systemd Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/bbmesh.service
```

```ini
[Unit]
Description=BBMesh BBS Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=bbmesh
Group=bbmesh
WorkingDirectory=/opt/bbmesh
Environment=PATH=/opt/bbmesh/venv/bin
ExecStart=/opt/bbmesh/venv/bin/bbmesh start
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bbmesh

# Security settings
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=false
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/log/bbmesh /var/lib/bbmesh /opt/bbmesh/logs /opt/bbmesh/data

# Resource limits
LimitNOFILE=1024
LimitNPROC=512
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable bbmesh

# Start service
sudo systemctl start bbmesh

# Check status
sudo systemctl status bbmesh

# View logs
journalctl -u bbmesh -f
```

### Automatic Startup

Ensure service starts on boot:

```bash
# Enable service
sudo systemctl enable bbmesh

# Test boot sequence
sudo systemctl list-dependencies bbmesh

# Verify startup after reboot
sudo reboot
# After reboot:
sudo systemctl status bbmesh
```

## Security Hardening

### User and Permissions

```bash
# Verify user isolation
sudo -u bbmesh id

# Set proper file permissions
sudo chmod 644 /opt/bbmesh/config/*.yaml
sudo chmod 755 /opt/bbmesh/src/bbmesh/
sudo chmod 600 /var/log/bbmesh/*.log

# Restrict access to sensitive files
sudo chown root:bbmesh /opt/bbmesh/config/bbmesh.yaml
sudo chmod 640 /opt/bbmesh/config/bbmesh.yaml
```

### Firewall Configuration

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (if needed)
sudo ufw allow ssh

# Deny other incoming connections
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Optional: Allow monitoring port
sudo ufw allow 8080/tcp comment "BBMesh monitoring"
```

### Log Security

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/bbmesh
```

```
/var/log/bbmesh/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    postrotate
        /bin/systemctl reload bbmesh
    endscript
}
```

### System Hardening

```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon

# Configure automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Set up fail2ban (optional)
sudo apt install fail2ban
```

## Monitoring and Maintenance

### Health Monitoring Script

Create monitoring script:

```bash
sudo nano /opt/bbmesh/scripts/health_check.sh
```

```bash
#!/bin/bash

LOG_FILE="/var/log/bbmesh/health.log"
SERVICE_NAME="bbmesh"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check if service is running
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    log_message "ERROR: Service is not running"
    systemctl start "$SERVICE_NAME"
    log_message "INFO: Attempted to restart service"
    exit 1
fi

# Check log for recent errors
if tail -100 /var/log/bbmesh/bbmesh.log | grep -q "ERROR.*$(date +%Y-%m-%d)"; then
    log_message "WARNING: Recent errors found in log"
fi

# Check disk space
DISK_USAGE=$(df /var/lib/bbmesh | awk 'NR==2{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log_message "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -C python3 | grep bbmesh | awk '{print $4}')
if [ $(echo "$MEM_USAGE > 50" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
    log_message "WARNING: High memory usage: ${MEM_USAGE}%"
fi

log_message "INFO: Health check completed"
```

```bash
# Make executable
sudo chmod +x /opt/bbmesh/scripts/health_check.sh
sudo chown bbmesh:bbmesh /opt/bbmesh/scripts/health_check.sh
```

### Cron Jobs

Set up automated maintenance:

```bash
# Edit crontab for bbmesh user
sudo -u bbmesh crontab -e
```

```cron
# Health check every 5 minutes
*/5 * * * * /opt/bbmesh/scripts/health_check.sh

# Database backup daily at 2 AM
0 2 * * * cp /var/lib/bbmesh/bbmesh.db /var/lib/bbmesh/backups/bbmesh-$(date +\%Y\%m\%d).db

# Clean old backups (keep 7 days)
0 3 * * * find /var/lib/bbmesh/backups/ -name "bbmesh-*.db" -mtime +7 -delete

# Restart service weekly (optional)
0 4 * * 0 /bin/systemctl restart bbmesh
```

### Monitoring Dashboard

Optional web monitoring interface:

```bash
# Install monitoring dependencies
sudo -u bbmesh /opt/bbmesh/venv/bin/pip install flask

# Create simple monitoring script
sudo -u bbmesh nano /opt/bbmesh/scripts/monitor.py
```

```python
#!/usr/bin/env python3
"""Simple BBMesh monitoring dashboard."""

from flask import Flask, jsonify, render_template_string
import subprocess
import json
import os

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BBMesh Monitor</title>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>BBMesh Status</h1>
    <h2>Service Status: {{ status.service }}</h2>
    <h2>Last Update: {{ status.timestamp }}</h2>
    <h3>System Info:</h3>
    <ul>
        <li>Uptime: {{ status.uptime }}</li>
        <li>Memory: {{ status.memory }}</li>
        <li>CPU: {{ status.cpu }}</li>
    </ul>
    <h3>Recent Logs:</h3>
    <pre>{{ status.logs }}</pre>
</body>
</html>
"""

@app.route('/')
def dashboard():
    status = get_system_status()
    return render_template_string(TEMPLATE, status=status)

@app.route('/api/status')
def api_status():
    return jsonify(get_system_status())

def get_system_status():
    # Get service status
    try:
        result = subprocess.run(['systemctl', 'is-active', 'bbmesh'], 
                              capture_output=True, text=True)
        service_status = result.stdout.strip()
    except:
        service_status = "unknown"
    
    # Get recent logs
    try:
        result = subprocess.run(['tail', '-20', '/var/log/bbmesh/bbmesh.log'], 
                              capture_output=True, text=True)
        logs = result.stdout
    except:
        logs = "Unable to read logs"
    
    return {
        'service': service_status,
        'timestamp': subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
        'uptime': subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip(),
        'memory': subprocess.run(['free', '-h'], capture_output=True, text=True).stdout,
        'cpu': subprocess.run(['top', '-bn1'], capture_output=True, text=True).stdout.split('\n')[2],
        'logs': logs
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup directory
sudo -u bbmesh mkdir -p /var/lib/bbmesh/backups

# Backup script
sudo -u bbmesh nano /opt/bbmesh/scripts/backup.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/var/lib/bbmesh/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bbmesh_backup_${DATE}.tar.gz"

# Create compressed backup
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    -C /opt/bbmesh config/ \
    -C /var/lib/bbmesh bbmesh.db \
    -C /var/log/bbmesh bbmesh.log

# Keep only last 30 backups
ls -t "${BACKUP_DIR}"/bbmesh_backup_*.tar.gz | tail -n +31 | xargs rm -f

echo "Backup created: ${BACKUP_FILE}"
```

### Disaster Recovery

Recovery procedure:

```bash
# Stop service
sudo systemctl stop bbmesh

# Restore from backup
cd /tmp
tar -xzf /var/lib/bbmesh/backups/bbmesh_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore files
sudo -u bbmesh cp -r config/* /opt/bbmesh/config/
sudo -u bbmesh cp bbmesh.db /var/lib/bbmesh/

# Start service
sudo systemctl start bbmesh

# Verify restoration
sudo systemctl status bbmesh
```

## Performance Optimization

### Resource Monitoring

```bash
# Monitor BBMesh performance
sudo -u bbmesh /opt/bbmesh/venv/bin/python -c "
import psutil
import time

while True:
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
        if 'bbmesh' in proc.info['name']:
            print(f'PID: {proc.info[\"pid\"]}, Memory: {proc.info[\"memory_percent\"]:.1f}%, CPU: {proc.info[\"cpu_percent\"]:.1f}%')
    time.sleep(60)
"
```

### Database Optimization

```bash
# Vacuum SQLite database
sudo -u bbmesh sqlite3 /var/lib/bbmesh/bbmesh.db "VACUUM;"

# Add to monthly cron
sudo -u bbmesh crontab -e
# Add: 0 1 1 * * sqlite3 /var/lib/bbmesh/bbmesh.db "VACUUM;"
```

### Log Management

```bash
# Monitor log size
watch "du -sh /var/log/bbmesh/"

# Compress old logs
find /var/log/bbmesh/ -name "*.log.*" -not -name "*.gz" -exec gzip {} \;
```

## High Availability

### Multiple Node Setup

For critical deployments, consider multiple BBMesh instances:

```bash
# Second instance configuration
sudo cp -r /opt/bbmesh /opt/bbmesh2
sudo sed -i 's/ttyUSB0/ttyUSB1/g' /opt/bbmesh2/config/bbmesh.yaml
sudo sed -i 's/bbmesh.log/bbmesh2.log/g' /opt/bbmesh2/config/bbmesh.yaml

# Create second service
sudo cp /etc/systemd/system/bbmesh.service /etc/systemd/system/bbmesh2.service
sudo sed -i 's/bbmesh/bbmesh2/g' /etc/systemd/system/bbmesh2.service
```

### Load Balancing

For high traffic scenarios:

```yaml
# Distribute channels across instances
# Instance 1:
meshtastic:
  monitored_channels: [0, 2]
  response_channels: [0, 2]

# Instance 2:
meshtastic:
  monitored_channels: [1, 3]
  response_channels: [1, 3]
```

## Troubleshooting Production Issues

### Service Won't Start

```bash
# Check service status
sudo systemctl status bbmesh

# Check journal logs
journalctl -u bbmesh --since "1 hour ago"

# Check permissions
sudo -u bbmesh ls -la /opt/bbmesh/config/
```

### Performance Issues

```bash
# Check system resources
top -p $(pgrep -f bbmesh)
iotop -p $(pgrep -f bbmesh)

# Check disk I/O
iostat -x 1

# Profile application
sudo -u bbmesh /opt/bbmesh/venv/bin/python -m cProfile /opt/bbmesh/venv/bin/bbmesh start
```

### Memory Leaks

```bash
# Monitor memory usage
watch "ps aux | grep bbmesh"

# Generate memory profile
sudo -u bbmesh /opt/bbmesh/venv/bin/python -m memory_profiler /opt/bbmesh/venv/bin/bbmesh start
```

### Network Issues

```bash
# Check serial port
ls -la /dev/ttyUSB*
dmesg | tail -10

# Test serial connection
sudo -u bbmesh python3 -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('Connection OK')
ser.close()
"
```

## Production Checklist

Before deploying to production:

- [ ] System hardening completed
- [ ] Firewall configured
- [ ] Automated backups set up
- [ ] Monitoring in place
- [ ] Log rotation configured
- [ ] Service auto-start enabled
- [ ] Health checks implemented
- [ ] Documentation updated
- [ ] Recovery procedures tested
- [ ] Performance baselines established

## Updates and Maintenance

### Regular Updates

```bash
# Monthly update procedure
sudo systemctl stop bbmesh

# Backup current version
sudo -u bbmesh cp -r /opt/bbmesh /opt/bbmesh.backup.$(date +%Y%m%d)

# Update code
sudo -u bbmesh git pull
sudo -u bbmesh /opt/bbmesh/venv/bin/pip install -e . --upgrade

# Test configuration
sudo -u bbmesh /opt/bbmesh/venv/bin/python test_bbmesh.py

# Start service
sudo systemctl start bbmesh

# Verify operation
sudo systemctl status bbmesh
```

### Security Updates

```bash
# System security updates
sudo apt update && sudo apt upgrade -y

# Python package updates
sudo -u bbmesh /opt/bbmesh/venv/bin/pip list --outdated
sudo -u bbmesh /opt/bbmesh/venv/bin/pip install --upgrade $(pip list --outdated --format=freeze | cut -d= -f1)
```

This deployment guide ensures BBMesh runs reliably in production with proper monitoring, security, and maintenance procedures.