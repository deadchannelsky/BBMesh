#!/bin/bash

# BBMesh systemd service installation script
# This script sets up BBMesh as a systemd service with proper security and configuration

set -e

# Configuration
SERVICE_NAME="bbmesh"
SERVICE_USER="bbmesh"
INSTALL_DIR="/opt/bbmesh"
LOG_DIR="/var/log/bbmesh"
DATA_DIR="/var/lib/bbmesh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check for systemd
    if ! command -v systemctl &> /dev/null; then
        log_error "systemctl not found. This system doesn't support systemd."
        exit 1
    fi
    
    # Check for Python 3.8+
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        log_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 not found. Please install python3-pip"
        exit 1
    fi
    
    log_info "System requirements satisfied"
}

# Create dedicated user for BBMesh service
create_service_user() {
    log_info "Creating service user '$SERVICE_USER'..."
    
    # Create user if it doesn't exist
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -m -s /bin/bash -c "BBMesh BBS Service" "$SERVICE_USER"
        log_info "Created user '$SERVICE_USER'"
    else
        log_info "User '$SERVICE_USER' already exists"
    fi
    
    # Add user to dialout group for serial port access
    usermod -a -G dialout "$SERVICE_USER"
    log_info "Added '$SERVICE_USER' to dialout group"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$DATA_DIR/backups"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$LOG_DIR" "$DATA_DIR"
    
    # Set permissions
    chmod 755 "$INSTALL_DIR" "$LOG_DIR" "$DATA_DIR"
    chmod 750 "$DATA_DIR/backups"
    
    log_info "Directory structure created"
}

# Install BBMesh application
install_application() {
    log_info "Installing BBMesh application..."
    
    # Copy application files
    cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    
    # Create virtual environment as service user
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv"
    
    # Install application in virtual environment
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    log_info "Application installed"
}

# Configure application for service deployment
configure_application() {
    log_info "Configuring application for service deployment..."
    
    # Update configuration file paths for service deployment
    CONFIG_FILE="$INSTALL_DIR/config/bbmesh.yaml"
    
    if [[ -f "$CONFIG_FILE" ]]; then
        # Update log file path to use system location
        sed -i "s|file_path:.*|file_path: $LOG_DIR/bbmesh.log|g" "$CONFIG_FILE"
        
        # Update database path to use system location
        sed -i "s|path:.*bbmesh\.db|path: $DATA_DIR/bbmesh.db|g" "$CONFIG_FILE"
        
        # Set ownership and permissions for config
        chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_FILE"
        chmod 640 "$CONFIG_FILE"
        
        log_info "Configuration updated for service deployment"
    else
        log_warn "Configuration file not found, creating default..."
        sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/bbmesh" init-config --output "$CONFIG_FILE"
        
        # Apply the same updates to the new config
        sed -i "s|file_path:.*|file_path: $LOG_DIR/bbmesh.log|g" "$CONFIG_FILE"
        sed -i "s|path:.*bbmesh\.db|path: $DATA_DIR/bbmesh.db|g" "$CONFIG_FILE"
        chmod 640 "$CONFIG_FILE"
    fi
}

# Create systemd service file
create_service_file() {
    log_info "Creating systemd service file..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=BBMesh BBS Server
Documentation=https://github.com/deadchannelsky/BBMesh
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/bbmesh start --config $INSTALL_DIR/config/bbmesh.yaml
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=false
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$LOG_DIR $DATA_DIR $INSTALL_DIR/logs $INSTALL_DIR/data

# Resource limits
LimitNOFILE=1024
LimitNPROC=512
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF
    
    log_info "Systemd service file created"
}

# Set up log rotation
setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        /bin/systemctl reload $SERVICE_NAME || true
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

# Create backup script
create_backup_script() {
    log_info "Creating backup script..."
    
    cat > "$INSTALL_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash

# BBMesh backup script
BACKUP_DIR="/var/lib/bbmesh/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bbmesh_backup_${DATE}.tar.gz"

# Create compressed backup
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    -C /opt/bbmesh config/ \
    -C /var/lib/bbmesh bbmesh.db \
    -C /var/log/bbmesh bbmesh.log 2>/dev/null || true

# Keep only last 30 backups
ls -t "${BACKUP_DIR}"/bbmesh_backup_*.tar.gz 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null || true

echo "Backup created: ${BACKUP_FILE}"
EOF
    
    chmod +x "$INSTALL_DIR/scripts/backup.sh"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/scripts/backup.sh"
    
    log_info "Backup script created"
}

# Install service management utility
install_management_utility() {
    log_info "Installing service management utility..."
    
    # Copy management script to system location
    cp "$SCRIPT_DIR/manage-service.sh" "/usr/local/bin/bbmesh-service"
    chmod +x "/usr/local/bin/bbmesh-service"
    
    log_info "Service management utility installed as 'bbmesh-service'"
}

# Set up cron jobs for maintenance
setup_cron_jobs() {
    log_info "Setting up maintenance cron jobs..."
    
    # Create cron file for bbmesh user
    cat > "/tmp/bbmesh-cron" << EOF
# BBMesh maintenance cron jobs

# Database backup daily at 2 AM
0 2 * * * $INSTALL_DIR/scripts/backup.sh

# Clean old backups (keep 30 days)
0 3 * * * find $DATA_DIR/backups/ -name "bbmesh_backup_*.tar.gz" -mtime +30 -delete 2>/dev/null || true

# Vacuum SQLite database monthly
0 1 1 * * sqlite3 $DATA_DIR/bbmesh.db "VACUUM;" 2>/dev/null || true
EOF
    
    # Install cron jobs for service user
    sudo -u "$SERVICE_USER" crontab "/tmp/bbmesh-cron"
    rm "/tmp/bbmesh-cron"
    
    log_info "Cron jobs configured"
}

# Enable and start service
enable_service() {
    log_info "Enabling and starting service..."
    
    # Reload systemd daemon
    systemctl daemon-reload
    
    # Enable service for auto-start
    systemctl enable "$SERVICE_NAME"
    
    # Start service
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Service started successfully"
    else
        log_error "Service failed to start. Check logs with: journalctl -u $SERVICE_NAME"
        return 1
    fi
}

# Display post-installation information
show_post_install_info() {
    log_info "Installation completed successfully!"
    echo
    echo "BBMesh has been installed as a systemd service. Here's what you can do:"
    echo
    echo "Service Management (Easy Way):"
    echo "  bbmesh-service start         # Start the service"
    echo "  bbmesh-service stop          # Stop the service"
    echo "  bbmesh-service restart       # Restart the service"
    echo "  bbmesh-service status        # Check service status"
    echo "  bbmesh-service logs          # Show recent logs"
    echo "  bbmesh-service health        # Run health check"
    echo
    echo "Service Management (systemctl):"
    echo "  sudo systemctl start $SERVICE_NAME      # Start the service"
    echo "  sudo systemctl stop $SERVICE_NAME       # Stop the service"
    echo "  sudo systemctl restart $SERVICE_NAME    # Restart the service"
    echo "  sudo systemctl status $SERVICE_NAME     # Check service status"
    echo "  sudo systemctl enable $SERVICE_NAME     # Enable auto-start (already done)"
    echo "  sudo systemctl disable $SERVICE_NAME    # Disable auto-start"
    echo
    echo "Monitoring:"
    echo "  journalctl -u $SERVICE_NAME -f          # Follow service logs"
    echo "  journalctl -u $SERVICE_NAME --since today # Today's logs"
    echo "  tail -f $LOG_DIR/bbmesh.log             # Follow application logs"
    echo
    echo "Configuration:"
    echo "  sudo -u $SERVICE_USER nano $INSTALL_DIR/config/bbmesh.yaml"
    echo "  sudo systemctl restart $SERVICE_NAME    # After config changes"
    echo
    echo "Files and Directories:"
    echo "  Application: $INSTALL_DIR"
    echo "  Configuration: $INSTALL_DIR/config/"
    echo "  Logs: $LOG_DIR/"
    echo "  Data: $DATA_DIR/"
    echo "  Backups: $DATA_DIR/backups/"
    echo
    echo "The service will automatically start on boot and restart if it crashes."
    echo "Backups are created daily at 2 AM and kept for 30 days."
}

# Main installation function
main() {
    log_info "Starting BBMesh service installation..."
    
    check_root
    check_requirements
    create_service_user
    create_directories
    install_application
    configure_application
    create_service_file
    setup_log_rotation
    create_backup_script
    install_management_utility
    setup_cron_jobs
    enable_service
    show_post_install_info
}

# Run main function
main "$@"