"""
Command line interface for BBMesh
"""

import click
import sys
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


if __name__ == "__main__":
    main()