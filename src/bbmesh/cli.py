"""
Command line interface for BBMesh
"""

import click
import sys
from pathlib import Path

from .core.server import BBMeshServer
from .core.config import Config
from .utils.logger import setup_logging


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


if __name__ == "__main__":
    main()