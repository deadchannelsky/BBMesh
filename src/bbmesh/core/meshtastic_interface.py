"""
Meshtastic interface for BBMesh
"""

import time
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

import meshtastic
import meshtastic.serial_interface
from meshtastic import BROADCAST_ADDR
from pubsub import pub

from .config import MeshtasticConfig
from ..utils.logger import BBMeshLogger


@dataclass
class MeshMessage:
    """Represents a received Meshtastic message"""
    sender_id: str
    sender_name: str
    channel: int
    text: str
    timestamp: datetime
    is_direct: bool
    hop_limit: int
    snr: float
    rssi: int
    to_node: Optional[str] = None


class MeshtasticInterface:
    """
    Interface to Meshtastic node via serial connection
    """
    
    def __init__(self, config: MeshtasticConfig):
        self.config = config
        self.logger = BBMeshLogger(__name__)
        self.interface: Optional[meshtastic.serial_interface.SerialInterface] = None
        self.node_info: Dict[str, Any] = {}
        self.local_node_id: Optional[str] = None
        self.connected = False
        self.message_callbacks: List[Callable[[MeshMessage], None]] = []
        self._stop_event = threading.Event()
        
    def connect(self) -> bool:
        """
        Connect to the Meshtastic node
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to Meshtastic node on {self.config.serial.port}")
            
            # Create serial interface
            self.interface = meshtastic.serial_interface.SerialInterface(
                devPath=self.config.serial.port,
                debugOut=None  # Disable debug output
            )
            
            # Wait for connection and node info
            timeout = 10  # seconds
            start_time = time.time()
            
            while not self.interface.myInfo and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.interface.myInfo:
                self.logger.error("Failed to get node information within timeout")
                return False
            
            # Store node information
            self.node_info = self.interface.myInfo
            self.local_node_id = str(self.node_info.get('num', 'unknown'))
            
            # Subscribe to message reception
            pub.subscribe(self._on_receive, "meshtastic.receive")
            
            self.connected = True
            self.logger.info(f"Connected to node {self.local_node_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Meshtastic node: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the Meshtastic node"""
        if self.interface:
            try:
                pub.unsubscribe(self._on_receive, "meshtastic.receive")
                self.interface.close()
                self.connected = False
                self.logger.info("Disconnected from Meshtastic node")
            except Exception as e:
                self.logger.error(f"Error disconnecting: {e}")
    
    def add_message_callback(self, callback: Callable[[MeshMessage], None]) -> None:
        """
        Add a callback function to be called when messages are received
        
        Args:
            callback: Function that takes a MeshMessage parameter
        """
        self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable[[MeshMessage], None]) -> None:
        """
        Remove a message callback
        
        Args:
            callback: Function to remove
        """
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    def send_message(self, text: str, channel: int = 0, 
                    destination: Optional[str] = None) -> bool:
        """
        Send a message via Meshtastic
        
        Args:
            text: Message text to send
            channel: Channel number (0-7)
            destination: Destination node ID (None for broadcast)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.connected or not self.interface:
            self.logger.error("Not connected to Meshtastic node")
            return False
        
        try:
            # Truncate message if too long
            max_length = 200  # Meshtastic text message limit
            if len(text) > max_length:
                text = text[:max_length-3] + "..."
            
            # Send message
            if destination:
                # Direct message to specific node
                self.interface.sendText(
                    text=text,
                    destinationId=destination,
                    channelIndex=channel
                )
                self.logger.log_message("TX", destination, channel, text, self.local_node_id)
            else:
                # Broadcast message
                self.interface.sendText(
                    text=text,
                    channelIndex=channel
                )
                self.logger.log_message("TX", "BROADCAST", channel, text, self.local_node_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific node
        
        Args:
            node_id: Node ID to look up
            
        Returns:
            Node information dictionary or None if not found
        """
        if not self.connected or not self.interface:
            return None
        
        try:
            nodes = self.interface.nodes
            return nodes.get(node_id)
        except Exception as e:
            self.logger.error(f"Failed to get node info for {node_id}: {e}")
            return None
    
    def get_channel_info(self, channel: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific channel
        
        Args:
            channel: Channel number
            
        Returns:
            Channel information dictionary or None if not found
        """
        if not self.connected or not self.interface:
            return None
        
        try:
            channels = getattr(self.interface, 'channels', [])
            if 0 <= channel < len(channels):
                return channels[channel]
            return None
        except Exception as e:
            self.logger.error(f"Failed to get channel info for {channel}: {e}")
            return None
    
    def _on_receive(self, packet: Dict[str, Any], interface=None) -> None:
        """
        Handle received Meshtastic packets
        
        Args:
            packet: Received packet data
            interface: Meshtastic interface (unused)
        """
        try:
            # Extract packet information
            decoded = packet.get('decoded', {})
            
            # Only process text messages
            if decoded.get('portnum') != 'TEXT_MESSAGE_APP':
                return
            
            # Extract message data
            from_id = str(packet.get('from', 'unknown'))
            to_id = packet.get('to')
            channel = packet.get('channel', 0)
            text = decoded.get('payload', b'').decode('utf-8', errors='ignore')
            hop_limit = packet.get('hopLimit', 0)
            
            # Get signal quality information
            snr = packet.get('rxSnr', 0.0)
            rssi = packet.get('rxRssi', -999)
            
            # Determine if this is a direct message
            is_direct = to_id != BROADCAST_ADDR and to_id == int(self.local_node_id)
            
            # Get sender name
            sender_name = self._get_node_name(from_id)
            
            # Filter messages based on configuration
            if not self._should_process_message(channel, is_direct):
                return
            
            # Create message object
            message = MeshMessage(
                sender_id=from_id,
                sender_name=sender_name,
                channel=channel,
                text=text,
                timestamp=datetime.now(),
                is_direct=is_direct,
                hop_limit=hop_limit,
                snr=snr,
                rssi=rssi,
                to_node=str(to_id) if to_id else None
            )
            
            # Log the message
            msg_type = "DIRECT" if is_direct else "BROADCAST"
            self.logger.log_message("RX", f"{sender_name}({from_id})", channel, 
                                  f"[{msg_type}] {text}", self.local_node_id)
            
            # Call message callbacks
            for callback in self.message_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    def _get_node_name(self, node_id: str) -> str:
        """
        Get the display name for a node
        
        Args:
            node_id: Node ID
            
        Returns:
            Node display name or ID if name not available
        """
        try:
            if self.interface and hasattr(self.interface, 'nodes'):
                node_info = self.interface.nodes.get(node_id, {})
                user_info = node_info.get('user', {})
                return user_info.get('shortName', user_info.get('longName', node_id))
        except Exception:
            pass
        return node_id
    
    def _should_process_message(self, channel: int, is_direct: bool) -> bool:
        """
        Determine if a message should be processed based on configuration
        
        Args:
            channel: Message channel
            is_direct: Whether message is direct to this node
            
        Returns:
            True if message should be processed
        """
        # Always process direct messages if not in direct-only mode
        if is_direct:
            return True
            
        # If direct message only mode, ignore broadcasts
        if self.config.direct_message_only:
            return False
            
        # Check if channel is monitored
        return channel in self.config.monitored_channels
    
    def get_mesh_info(self) -> Dict[str, Any]:
        """
        Get general mesh network information
        
        Returns:
            Dictionary with mesh network status
        """
        if not self.connected or not self.interface:
            return {"connected": False}
        
        try:
            nodes = getattr(self.interface, 'nodes', {})
            channels = getattr(self.interface, 'channels', [])
            
            return {
                "connected": True,
                "local_node_id": self.local_node_id,
                "node_count": len(nodes),
                "channel_count": len(channels),
                "monitored_channels": self.config.monitored_channels,
                "response_channels": self.config.response_channels,
            }
        except Exception as e:
            self.logger.error(f"Failed to get mesh info: {e}")
            return {"connected": False, "error": str(e)}