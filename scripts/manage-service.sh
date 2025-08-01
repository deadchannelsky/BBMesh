#!/bin/bash

# BBMesh service management utility script
# Provides easy service management commands

set -e

SERVICE_NAME="bbmesh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_status() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

# Check if service exists
check_service_exists() {
    if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        log_error "BBMesh service is not installed."
        echo "Use 'sudo bbmesh install-service' to install it first."
        exit 1
    fi
}

# Show usage information
show_usage() {
    echo "BBMesh Service Management Utility"
    echo "================================="
    echo
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  start        Start the BBMesh service"
    echo "  stop         Stop the BBMesh service"
    echo "  restart      Restart the BBMesh service"
    echo "  status       Show service status"
    echo "  enable       Enable service to start on boot"
    echo "  disable      Disable service auto-start"
    echo "  logs         Show recent service logs"
    echo "  logs-follow  Follow service logs in real-time"
    echo "  health       Run health check"
    echo "  backup       Create backup manually"
    echo "  help         Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start     # Start the service"
    echo "  $0 logs      # Show recent logs"
    echo "  $0 status    # Check service status"
}

# Service management functions
service_start() {
    log_info "Starting BBMesh service..."
    sudo systemctl start "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "✓ Service started successfully"
    else
        log_error "✗ Service failed to start"
        log_info "Check logs with: $0 logs"
        exit 1
    fi
}

service_stop() {
    log_info "Stopping BBMesh service..."
    sudo systemctl stop "$SERVICE_NAME"
    log_info "✓ Service stopped"
}

service_restart() {
    log_info "Restarting BBMesh service..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "✓ Service restarted successfully"
    else
        log_error "✗ Service failed to restart"
        log_info "Check logs with: $0 logs"
        exit 1
    fi
}

service_status() {
    log_status "BBMesh Service Status"
    echo "===================="
    
    # Get basic status
    is_active=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
    is_enabled=$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null || echo "disabled")
    
    echo "Active: $is_active"
    echo "Enabled: $is_enabled"
    echo
    
    # Show systemctl status
    echo "Detailed Status:"
    echo "---------------"
    systemctl status "$SERVICE_NAME" --no-pager --lines=5
    
    # Show process info if active
    if [[ "$is_active" == "active" ]]; then
        echo
        echo "Process Information:"
        echo "-------------------"
        ps aux | grep -E "(PID|bbmesh)" | grep -v grep
    fi
}

service_enable() {
    log_info "Enabling BBMesh service for auto-start..."
    sudo systemctl enable "$SERVICE_NAME"
    log_info "✓ Service enabled for auto-start"
}

service_disable() {
    log_info "Disabling BBMesh service auto-start..."
    sudo systemctl disable "$SERVICE_NAME"
    log_info "✓ Service auto-start disabled"
}

show_logs() {
    log_status "Recent BBMesh service logs"
    echo "=========================="
    journalctl -u "$SERVICE_NAME" --no-pager --lines=50
}

follow_logs() {
    log_status "Following BBMesh service logs (Ctrl+C to exit)"
    echo "=============================================="
    journalctl -u "$SERVICE_NAME" -f
}

run_health_check() {
    log_status "Running BBMesh health check"
    echo "==========================="
    
    # Try to run bbmesh health-check command
    if command -v bbmesh &> /dev/null; then
        bbmesh health-check
    else
        # Fallback basic health check
        log_warn "BBMesh CLI not in PATH, running basic health check"
        
        # Check service status
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_info "✓ Service is running"
        else
            log_error "✗ Service is not running"
        fi
        
        # Check recent errors in logs
        if journalctl -u "$SERVICE_NAME" --since "1 hour ago" --no-pager | grep -i error > /dev/null; then
            log_warn "⚠ Recent errors found in logs"
        else
            log_info "✓ No recent errors in logs"
        fi
        
        # Check disk space
        available=$(df /var/lib/bbmesh 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
        if [[ "$available" -gt 1048576 ]]; then  # > 1GB
            log_info "✓ Sufficient disk space"
        else
            log_warn "⚠ Low disk space"
        fi
    fi
}

create_backup() {
    log_info "Creating manual backup..."
    
    backup_script="/opt/bbmesh/scripts/backup.sh"
    if [[ -f "$backup_script" ]]; then
        sudo -u bbmesh "$backup_script"
        log_info "✓ Backup completed"
    else
        log_error "Backup script not found at $backup_script"
        exit 1
    fi
}

# Main script logic
main() {
    case "$1" in
        start)
            check_service_exists
            service_start
            ;;
        stop)
            check_service_exists
            service_stop
            ;;
        restart)
            check_service_exists
            service_restart
            ;;
        status)
            check_service_exists
            service_status
            ;;
        enable)
            check_service_exists
            service_enable
            ;;
        disable)
            check_service_exists
            service_disable
            ;;
        logs)
            check_service_exists
            show_logs
            ;;
        logs-follow)
            check_service_exists
            follow_logs
            ;;
        health)
            check_service_exists
            run_health_check
            ;;
        backup)
            check_service_exists
            create_backup
            ;;
        help|--help|-h)
            show_usage
            ;;
        "")
            log_error "No command specified"
            echo
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"