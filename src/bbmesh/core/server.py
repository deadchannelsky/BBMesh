"""
Main BBMesh server implementation
"""

import time
import signal
import sys
from typing import Dict, Optional
from pathlib import Path

from .config import Config
from .meshtastic_interface import MeshtasticInterface, MeshMessage
from .message_handler import MessageHandler
from ..utils.logger import BBMeshLogger


class BBMeshServer:
    """
    Main BBMesh BBS server
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = BBMeshLogger(__name__)
        self.running = False
        
        # Load MOTD content
        self.motd_content = self._load_motd()
        
        # Initialize components
        self.mesh_interface = MeshtasticInterface(config.meshtastic, config.server.message_send_delay)
        self.message_handler = MessageHandler(config, self.mesh_interface, self.motd_content)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self) -> None:
        """Start the BBMesh server"""
        try:
            self.logger.info(f"Starting {self.config.server.name}")
            
            # Log MOTD status
            if self.motd_content:
                self.logger.info(f"MOTD loaded: {len(self.motd_content)} characters")
            
            # Connect to Meshtastic node
            if not self.mesh_interface.connect():
                self.logger.error("Failed to connect to Meshtastic node")
                return
            
            # Register message callback
            self.mesh_interface.add_message_callback(self._on_message_received)
            
            # Initialize message handler
            self.message_handler.initialize()
            
            self.running = True
            self.logger.info("BBMesh server started successfully")
            
            # Main server loop
            self._run_server_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            self.stop()
    
    def stop(self) -> None:
        """Stop the BBMesh server"""
        if self.running:
            self.logger.info("Stopping BBMesh server...")
            self.running = False
            
            # Cleanup components
            if hasattr(self, 'message_handler'):
                self.message_handler.cleanup()
            
            if hasattr(self, 'mesh_interface'):
                self.mesh_interface.disconnect()
            
            self.logger.info("BBMesh server stopped")
    
    def _run_server_loop(self) -> None:
        """Main server event loop"""
        last_status_log = 0
        status_interval = 300  # Log status every 5 minutes
        
        try:
            while self.running:
                # Log periodic status
                current_time = time.time()
                if current_time - last_status_log > status_interval:
                    self._log_status()
                    last_status_log = current_time
                
                # Process any pending tasks
                self.message_handler.process_pending_tasks()
                
                # Sleep to prevent busy waiting
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in server loop: {e}")
        finally:
            self.stop()
    
    def _on_message_received(self, message: MeshMessage) -> None:
        """
        Handle received Meshtastic messages
        
        Args:
            message: Received message
        """
        try:
            # Let the message handler process the message
            self.message_handler.handle_message(message)
            
        except Exception as e:
            self.logger.error(f"Error handling message from {message.sender_id}: {e}")
    
    def _load_motd(self) -> Optional[str]:
        """
        Load message of the day from file
        
        Returns:
            MOTD content or None if not available
        """
        if not self.config.server.motd_file:
            return None
        
        try:
            motd_path = Path(self.config.server.motd_file)
            if motd_path.exists():
                return motd_path.read_text(encoding='utf-8').strip()
        except Exception as e:
            self.logger.warning(f"Failed to load MOTD: {e}")
        
        return None
    
    def _log_status(self) -> None:
        """Log server status information"""
        try:
            # Get mesh network info
            mesh_info = self.mesh_interface.get_mesh_info()
            
            # Get message handler stats
            handler_stats = self.message_handler.get_statistics()
            
            self.logger.info(
                f"Status - Connected: {mesh_info.get('connected', False)}, "
                f"Nodes: {mesh_info.get('node_count', 0)}, "
                f"Messages: {handler_stats.get('total_messages', 0)}, "
                f"Active Sessions: {handler_stats.get('active_sessions', 0)}"
            )
            
        except Exception as e:
            self.logger.warning(f"Error logging status: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle system signals for graceful shutdown
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_names = {2: 'SIGINT', 15: 'SIGTERM'}
        signal_name = signal_names.get(signum, f'Signal {signum}')
        
        self.logger.info(f"Received {signal_name}, shutting down...")
        self.running = False
    
    def get_server_info(self) -> Dict[str, any]:
        """
        Get server information for status/debugging
        
        Returns:
            Dictionary with server information
        """
        return {
            "name": self.config.server.name,
            "running": self.running,
            "mesh_info": self.mesh_interface.get_mesh_info(),
            "handler_stats": self.message_handler.get_statistics() if hasattr(self, 'message_handler') else {},
            "config": {
                "max_message_length": self.config.server.max_message_length,
                "session_timeout": self.config.server.session_timeout,
                "monitored_channels": self.config.meshtastic.monitored_channels,
                "response_channels": self.config.meshtastic.response_channels,
            }
        }