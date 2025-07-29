"""
BBMesh - A Meshtastic BBS System

A bulletin board system (BBS) for Meshtastic mesh networks, inspired by the
classic BBS systems of the early computing era. Provides an interactive,
menu-driven interface accessible through Meshtastic radio nodes.
"""

__version__ = "0.1.0"
__author__ = "BBMesh Team"
__email__ = "contact@bbmesh.dev"

from .core.server import BBMeshServer
from .core.config import Config

__all__ = ["BBMeshServer", "Config"]