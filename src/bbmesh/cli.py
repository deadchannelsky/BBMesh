"""
Command line interface for BBMesh
"""

import click
import sys
import os
import subprocess
from pathlib import Path

from .core.server import BBMeshServer
from .core.config import Config
from .utils.logger import setup_logging
from .utils.connection_test import ConnectionTester


@click.group()
@click.version_option()
def main():
    """BBMesh - A Meshtastic BBS System"""
    pass


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/bbmesh.yaml",
    help="Configuration file path",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug logging",
)
def start(config: Path, debug: bool):
    """Start the BBMesh server"""
    try:
        # Load configuration
        cfg = Config.load(config)
        
        # Setup logging
        setup_logging(cfg.logging, debug)
        
        # Create and start server
        server = BBMeshServer(cfg)
        click.echo("Starting BBMesh server...")
        server.start()
        
    except KeyboardInterrupt:
        click.echo("\nShutting down BBMesh server...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="config/bbmesh.yaml",
    help="Output configuration file path",
)
def init_config(output: Path):
    """Generate a default configuration file"""
    try:
        config = Config.create_default()
        config.save(output)
        click.echo(f"Default configuration saved to {output}")
    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        sys.exit(1)


@main.command("test-connection")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/bbmesh.yaml",
    help="Configuration file path",
)
@click.option(
    "--port",
    "-p",
    help="Specific port to test (overrides config setting)"
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=15.0,
    help="Connection timeout in seconds"
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output"
)
def test_connection(config: Path, port: str, timeout: float, debug: bool):
    """Run comprehensive Meshtastic connection diagnostics"""
    try:
        # Load config if available
        cfg = None
        if config.exists():
            try:
                cfg = Config.load(config)
                click.echo(f"Loaded configuration from {config}")
            except Exception as e:
                click.echo(f"Warning: Could not load config: {e}")
                cfg = Config.create_default()
        else:
            click.echo(f"Config file {config} not found, using defaults")
            cfg = Config.create_default()
        
        # Override port if specified
        if port:
            cfg.meshtastic.serial.port = port
            click.echo(f"Using port override: {port}")
        
        # Setup basic logging for the test
        if debug:
            cfg.logging.level = "DEBUG"
        setup_logging(cfg.logging, debug)
        
        # Run diagnostic
        click.echo("Running Meshtastic connection diagnostic...")
        click.echo("=" * 50)
        
        tester = ConnectionTester(cfg)
        results = tester.run_full_diagnostic()
        tester.print_diagnostic_report(results)
        
        # Exit with appropriate code
        if results.get("connection_test", {}).get("connection_successful", False):
            click.echo("\n✓ Connection test PASSED")
            sys.exit(0)
        else:
            click.echo("\n✗ Connection test FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\nDiagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running diagnostic: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command("nodeid")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/bbmesh.yaml",
    help="Configuration file path",
)
@click.option(
    "--port",
    "-p",
    help="Specific port to test (overrides config setting)"
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=10.0,
    help="Connection timeout in seconds"
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output"
)
def nodeid(config: Path, port: str, timeout: float, debug: bool):
    """Get the connected Meshtastic radio's node ID"""
    try:
        # Load configuration file or use defaults
        cfg = None
        if config.exists():
            try:
                cfg = Config.load(config)
            except Exception as e:
                if debug:
                    click.echo(f"Warning: Could not load config: {e}")
                cfg = Config.create_default()
        else:
            if debug:
                click.echo(f"Config file {config} not found, using defaults")
            cfg = Config.create_default()
        
        # Override port from command line if specified
        if port:
            cfg.meshtastic.serial.port = port
        
        # Configure logging based on debug flag
        if debug:
            cfg.logging.level = "DEBUG"
        setup_logging(cfg.logging, debug)
        
        # Connect to Meshtastic device and retrieve node ID
        tester = ConnectionTester(cfg)
        node_id = tester.get_node_id_only(timeout)
        
        if node_id:
            click.echo(node_id)
            sys.exit(0)
        else:
            if debug:
                click.echo("Failed to retrieve node ID", err=True)
            sys.exit(1)
            
    except KeyboardInterrupt:
        if debug:
            click.echo("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        if debug:
            click.echo(f"Error getting node ID: {e}", err=True)
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command("install-service")
@click.option(
    "--user",
    default="bbmesh",
    help="Service user name (default: bbmesh)"
)
@click.option(
    "--install-dir",
    default="/opt/bbmesh",
    help="Installation directory (default: /opt/bbmesh)"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force installation even if service already exists"
)
def install_service(user: str, install_dir: str, force: bool):
    """Install BBMesh as a systemd service"""
    try:
        # Check if running as root
        if os.geteuid() != 0:
            click.echo("Error: This command must be run as root (use sudo)", err=True)
            sys.exit(1)
        
        # Get the project directory (where this script is located)
        script_dir = Path(__file__).parent.parent.parent
        install_script = script_dir / "scripts" / "install-service.sh"
        
        if not install_script.exists():
            click.echo(f"Error: Installation script not found at {install_script}", err=True)
            sys.exit(1)
        
        # Check if service already exists
        result = subprocess.run(
            ["systemctl", "is-enabled", "bbmesh"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and not force:
            click.echo("BBMesh service is already installed.")
            click.echo("Use --force to reinstall or 'bbmesh uninstall-service' to remove first.")
            sys.exit(0)
        
        # Run the installation script
        click.echo("Installing BBMesh as systemd service...")
        click.echo(f"Installation script: {install_script}")
        
        result = subprocess.run([str(install_script)], check=False)
        
        if result.returncode == 0:
            click.echo("✓ BBMesh service installed successfully!")
        else:
            click.echo("✗ Service installation failed", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error installing service: {e}", err=True)
        sys.exit(1)


@main.command("uninstall-service")
@click.option(
    "--keep-data",
    is_flag=True,
    help="Keep user data and logs (only remove service)"
)
@click.confirmation_option(
    prompt="Are you sure you want to uninstall the BBMesh service?"
)
def uninstall_service(keep_data: bool):
    """Uninstall BBMesh systemd service"""
    try:
        # Check if running as root
        if os.geteuid() != 0:
            click.echo("Error: This command must be run as root (use sudo)", err=True)
            sys.exit(1)
        
        service_name = "bbmesh"
        service_user = "bbmesh"
        install_dir = "/opt/bbmesh"
        log_dir = "/var/log/bbmesh"
        data_dir = "/var/lib/bbmesh"
        
        # Stop and disable service
        click.echo("Stopping and disabling service...")
        subprocess.run(["systemctl", "stop", service_name], check=False)
        subprocess.run(["systemctl", "disable", service_name], check=False)
        
        # Remove service file
        service_file = f"/etc/systemd/system/{service_name}.service"
        if os.path.exists(service_file):
            os.remove(service_file)
            click.echo(f"Removed service file: {service_file}")
        
        # Remove logrotate configuration
        logrotate_file = f"/etc/logrotate.d/{service_name}"
        if os.path.exists(logrotate_file):
            os.remove(logrotate_file)
            click.echo(f"Removed logrotate config: {logrotate_file}")
        
        # Remove cron jobs
        try:
            subprocess.run(["crontab", "-r", "-u", service_user], check=False)
            click.echo("Removed cron jobs")
        except Exception:
            pass
        
        # Remove installation directory
        if os.path.exists(install_dir):
            import shutil
            shutil.rmtree(install_dir)
            click.echo(f"Removed installation directory: {install_dir}")
        
        if not keep_data:
            # Remove data and logs
            if os.path.exists(data_dir):
                import shutil
                shutil.rmtree(data_dir)
                click.echo(f"Removed data directory: {data_dir}")
            
            if os.path.exists(log_dir):
                import shutil
                shutil.rmtree(log_dir)
                click.echo(f"Removed log directory: {log_dir}")
            
            # Remove user
            try:
                subprocess.run(["userdel", "-r", service_user], check=False)
                click.echo(f"Removed user: {service_user}")
            except Exception:
                pass
        else:
            click.echo(f"Kept data in: {data_dir}")
            click.echo(f"Kept logs in: {log_dir}")
            click.echo(f"Kept user: {service_user}")
        
        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        
        click.echo("✓ BBMesh service uninstalled successfully!")
        
    except Exception as e:
        click.echo(f"Error uninstalling service: {e}", err=True)
        sys.exit(1)


@main.command("service-status")
def service_status():
    """Check BBMesh service status and health"""
    try:
        service_name = "bbmesh"
        
        # Check if service exists
        result = subprocess.run(
            ["systemctl", "list-unit-files", service_name + ".service"],
            capture_output=True,
            text=True
        )
        
        if service_name not in result.stdout:
            click.echo("BBMesh service is not installed.")
            click.echo("Use 'bbmesh install-service' to install it.")
            sys.exit(1)
        
        # Get service status
        result = subprocess.run(
            ["systemctl", "status", service_name],
            capture_output=True,
            text=True
        )
        
        # Get service state
        is_active = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        is_enabled = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        # Display status
        click.echo("BBMesh Service Status")
        click.echo("=" * 50)
        click.echo(f"Active: {is_active}")
        click.echo(f"Enabled: {is_enabled}")
        click.echo()
        
        # Show recent logs
        click.echo("Recent logs:")
        click.echo("-" * 20)
        log_result = subprocess.run(
            ["journalctl", "-u", service_name, "--lines=10", "--no-pager"],
            capture_output=True,
            text=True
        )
        
        if log_result.returncode == 0:
            click.echo(log_result.stdout)
        else:
            click.echo("Could not retrieve logs")
        
        # Check process info if active
        if is_active == "active":
            click.echo("Process information:")
            click.echo("-" * 20)
            ps_result = subprocess.run(
                ["ps", "aux", "-p", "$(pgrep -f bbmesh)"],
                shell=True,
                capture_output=True,
                text=True
            )
            if ps_result.returncode == 0:
                lines = ps_result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    click.echo(lines[0])  # Header
                    click.echo(lines[1])  # Process info
        
        # Service management commands
        click.echo()
        click.echo("Service management commands:")
        click.echo("  sudo systemctl start bbmesh      # Start service")
        click.echo("  sudo systemctl stop bbmesh       # Stop service")
        click.echo("  sudo systemctl restart bbmesh    # Restart service")
        click.echo("  journalctl -u bbmesh -f          # Follow logs")
        
    except Exception as e:
        click.echo(f"Error checking service status: {e}", err=True)
        sys.exit(1)


@main.command("health-check")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/bbmesh.yaml",
    help="Configuration file path",
)
def health_check(config: Path):
    """Perform health check on BBMesh system"""
    try:
        click.echo("BBMesh Health Check")
        click.echo("=" * 50)
        
        health_status = True
        
        # Check configuration
        click.echo("1. Configuration Check...")
        try:
            cfg = Config.load(config)
            click.echo("   ✓ Configuration file valid")
        except Exception as e:
            click.echo(f"   ✗ Configuration error: {e}")
            health_status = False
        
        # Check serial port access
        click.echo("2. Serial Port Check...")
        try:
            if hasattr(cfg, 'meshtastic') and hasattr(cfg.meshtastic, 'serial'):
                port = cfg.meshtastic.serial.port
                if os.path.exists(port):
                    # Check if we can access the port
                    if os.access(port, os.R_OK | os.W_OK):
                        click.echo(f"   ✓ Serial port {port} accessible")
                    else:
                        click.echo(f"   ✗ Serial port {port} not accessible (check permissions)")
                        health_status = False
                else:
                    click.echo(f"   ✗ Serial port {port} does not exist")
                    health_status = False
            else:
                click.echo("   ⚠ Serial port not configured")
        except Exception as e:
            click.echo(f"   ✗ Serial port check failed: {e}")
            health_status = False
        
        # Check disk space
        click.echo("3. Disk Space Check...")
        try:
            import shutil
            
            # Check current directory
            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)
            
            if free_gb > 1:
                click.echo(f"   ✓ Sufficient disk space ({free_gb}GB free)")
            else:
                click.echo(f"   ⚠ Low disk space ({free_gb}GB free)")
                
        except Exception as e:
            click.echo(f"   ✗ Disk space check failed: {e}")
        
        # Check Python environment
        click.echo("4. Python Environment Check...")
        try:
            import meshtastic
            click.echo("   ✓ Meshtastic library available")
        except ImportError:
            click.echo("   ✗ Meshtastic library not installed")
            health_status = False
        
        try:
            import yaml
            click.echo("   ✓ YAML library available")
        except ImportError:
            click.echo("   ✗ YAML library not installed")
            health_status = False
        
        # Overall status
        click.echo()
        if health_status:
            click.echo("✓ Overall health status: GOOD")
            sys.exit(0)
        else:
            click.echo("✗ Overall health status: ISSUES DETECTED")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error during health check: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()