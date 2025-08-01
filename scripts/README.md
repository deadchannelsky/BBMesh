# BBMesh Service Deployment Scripts

This directory contains scripts and utilities for deploying BBMesh as a systemd service on Linux systems.

## Files

### Installation Scripts
- **`install-service.sh`** - Complete automated installation script for setting up BBMesh as a systemd service
- **`manage-service.sh`** - Service management utility (installed as `bbmesh-service` command)

## Quick Start

### 1. Install BBMesh as a Service

```bash
# Run the installation script as root
sudo ./scripts/install-service.sh
```

This will:
- Create a dedicated `bbmesh` user
- Install the application to `/opt/bbmesh`
- Configure systemd service with security hardening
- Set up log rotation and automated backups
- Start the service and enable auto-start on boot

### 2. Manage the Service

After installation, you can manage the service using either:

**Easy way (recommended):**
```bash
bbmesh-service start      # Start service
bbmesh-service stop       # Stop service
bbmesh-service restart    # Restart service
bbmesh-service status     # Check status
bbmesh-service logs       # Show recent logs
bbmesh-service health     # Run health check
```

**Traditional systemctl way:**
```bash
sudo systemctl start bbmesh
sudo systemctl stop bbmesh
sudo systemctl status bbmesh
journalctl -u bbmesh -f
```

### 3. CLI Service Commands

BBMesh CLI also provides service management commands:

```bash
# Install service (must be run as root)
sudo bbmesh install-service

# Check service status
bbmesh service-status

# Run health check
bbmesh health-check

# Uninstall service (with confirmation)
sudo bbmesh uninstall-service
```

## Installation Details

### System Requirements
- Linux system with systemd
- Python 3.8 or higher
- Root access for installation

### What Gets Installed
- **Application**: `/opt/bbmesh/` - Main application directory
- **Configuration**: `/opt/bbmesh/config/` - Configuration files
- **Logs**: `/var/log/bbmesh/` - Service logs
- **Data**: `/var/lib/bbmesh/` - Database and persistent data
- **Backups**: `/var/lib/bbmesh/backups/` - Automated backups
- **Service**: `/etc/systemd/system/bbmesh.service` - Systemd service file
- **Utility**: `/usr/local/bin/bbmesh-service` - Management utility

### Security Features
- Dedicated `bbmesh` user with minimal privileges
- Restricted file system access
- Resource limits (CPU, memory)
- Automatic log rotation
- No new privileges flag
- Protected system directories

### Automated Maintenance
- Daily database backups (2 AM)
- Monthly database optimization
- Automatic log rotation (30 days)
- Old backup cleanup (30 days)

## Configuration

### Service Configuration
The service uses absolute paths suitable for system deployment:
- Logs: `/var/log/bbmesh/bbmesh.log`
- Database: `/var/lib/bbmesh/bbmesh.db`
- Config: `/opt/bbmesh/config/bbmesh.yaml`

### Customizing Installation
You can customize the installation by modifying the variables at the top of `install-service.sh`:
```bash
SERVICE_NAME="bbmesh"
SERVICE_USER="bbmesh"
INSTALL_DIR="/opt/bbmesh"
LOG_DIR="/var/log/bbmesh"
DATA_DIR="/var/lib/bbmesh"
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
bbmesh-service status

# Check recent logs
bbmesh-service logs

# Run health check
bbmesh-service health

# Check system logs
journalctl -u bbmesh -f
```

### Permission Issues
```bash
# Check file ownership
ls -la /opt/bbmesh/config/
ls -la /var/log/bbmesh/
ls -la /var/lib/bbmesh/

# Fix ownership if needed
sudo chown -R bbmesh:bbmesh /opt/bbmesh /var/log/bbmesh /var/lib/bbmesh
```

### Serial Port Access
```bash
# Check if bbmesh user is in dialout group
groups bbmesh

# Add to dialout group if missing
sudo usermod -a -G dialout bbmesh

# Check serial port permissions
ls -la /dev/ttyUSB*
```

## Uninstallation

To completely remove BBMesh service:

```bash
# Uninstall everything
sudo bbmesh uninstall-service

# Or keep data and only remove service
sudo bbmesh uninstall-service --keep-data
```

## Backup and Recovery

### Manual Backup
```bash
bbmesh-service backup
```

### Restore from Backup
```bash
# Stop service
sudo systemctl stop bbmesh

# Restore from backup archive
cd /tmp
tar -xzf /var/lib/bbmesh/backups/bbmesh_backup_YYYYMMDD_HHMMSS.tar.gz

# Copy files back
sudo -u bbmesh cp -r config/* /opt/bbmesh/config/
sudo -u bbmesh cp bbmesh.db /var/lib/bbmesh/

# Start service
sudo systemctl start bbmesh
```

## Advanced Usage

### Multiple Instances
To run multiple BBMesh instances (e.g., for different serial ports):

1. Copy and modify the installation script
2. Change service name and directories
3. Update configuration for different serial ports
4. Install as separate service

### Custom Configuration
```bash
# Edit configuration
sudo -u bbmesh nano /opt/bbmesh/config/bbmesh.yaml

# Validate configuration
bbmesh health-check --config /opt/bbmesh/config/bbmesh.yaml

# Restart service to apply changes
bbmesh-service restart
```

### Monitoring Integration
The service is designed to work with standard Linux monitoring tools:
- **Systemd**: Built-in service monitoring
- **Journald**: Centralized logging
- **Logrotate**: Automatic log management
- **Cron**: Scheduled maintenance tasks

For external monitoring, you can:
- Monitor service status via `systemctl is-active bbmesh`
- Parse logs from `/var/log/bbmesh/bbmesh.log`
- Check process health via `bbmesh health-check`
- Monitor resource usage via standard system tools

## Support

For issues with service deployment:
1. Check the service status and logs
2. Run the health check command
3. Review the troubleshooting section
4. Submit issues on GitHub with service logs and configuration