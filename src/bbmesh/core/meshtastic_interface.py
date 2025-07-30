"""
Meshtastic interface for BBMesh
"""

import time
import threading
import os
import fcntl
import subprocess
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

import meshtastic
import meshtastic.serial_interface
from meshtastic import BROADCAST_ADDR
from pubsub import pub
import serial

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
        
    def connect(self, max_retries: int = 3) -> bool:
        """
        Connect to the Meshtastic node with enhanced diagnostics and retry logic
        
        Args:
            max_retries: Maximum number of connection attempts
            
        Returns:
            True if connection successful, False otherwise
        """
        port = self.config.serial.port
        self.logger.info(f"Starting connection to Meshtastic node on {port}")
        
        # Pre-connection diagnostics
        if not self._pre_connection_checks(port):
            return False
        
        # Progressive timeouts for each retry
        timeouts = [5, 10, 15]  # seconds
        retry_delays = [1, 2, 3]  # seconds between retries
        
        for attempt in range(max_retries):
            timeout = timeouts[min(attempt, len(timeouts) - 1)]
            
            self.logger.info(f"Connection attempt {attempt + 1}/{max_retries} (timeout: {timeout}s)")
            
            if self._attempt_connection(port, timeout, attempt + 1):
                self.logger.info(f"Successfully connected on attempt {attempt + 1}")
                return True
            
            # Wait before next retry (except on last attempt)
            if attempt < max_retries - 1:
                delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                self.logger.info(f"Waiting {delay}s before retry...")
                time.sleep(delay)
        
        self.logger.error(f"Failed to connect after {max_retries} attempts")
        return False
    
    def _pre_connection_checks(self, port: str) -> bool:
        """
        Perform pre-connection diagnostic checks including exclusive lock testing
        
        Args:
            port: Serial port path
            
        Returns:
            True if checks pass, False otherwise
        """
        self.logger.debug("Running pre-connection diagnostic checks")
        
        # Check if port exists
        if not os.path.exists(port):
            self.logger.error(f"Serial port {port} does not exist")
            self.logger.info("Available ports might include: /dev/ttyUSB*, /dev/ttyACM*, /dev/tty.usbserial*")
            return False
        
        self.logger.debug(f"✓ Port {port} exists")
        
        # Check basic port accessibility
        try:
            with serial.Serial(port, self.config.serial.baudrate, timeout=0.1) as ser:
                self.logger.debug(f"✓ Port {port} is accessible for basic operations")
        except serial.SerialException as e:
            self.logger.error(f"Cannot access port {port}: {e}")
            
            # Provide helpful error context
            if "Permission denied" in str(e):
                self.logger.error("Permission denied - user may need to be added to dialout group")
                self.logger.info("Try: sudo usermod -a -G dialout $USER && newgrp dialout")
            elif "Device or resource busy" in str(e):
                self.logger.error("Port is busy - another process may be using it")
                self.logger.info("Check if another BBMesh instance or Meshtastic client is running")
            
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error accessing port {port}: {e}")
            return False
        
        # Test exclusive lock availability (critical for Meshtastic library)
        if not self._test_exclusive_lock(port):
            return False
        
        return True
    
    def _test_exclusive_lock(self, port: str) -> bool:
        """
        Test if exclusive lock can be obtained on the serial port
        
        Args:
            port: Serial port path
            
        Returns:
            True if exclusive lock is available, False otherwise
        """
        self.logger.debug("Testing exclusive lock availability")
        
        try:
            # Open port with exclusive access (same as Meshtastic library does)
            ser = serial.Serial()
            ser.port = port
            ser.baudrate = self.config.serial.baudrate
            ser.timeout = 0.1
            ser.exclusive = True  # This is the key parameter
            
            ser.open()
            self.logger.debug(f"✓ Exclusive lock available on {port}")
            ser.close()
            return True
            
        except serial.SerialException as e:
            error_msg = str(e).lower()
            if "resource temporarily unavailable" in error_msg or "could not exclusively lock port" in error_msg:
                self.logger.error(f"✗ Exclusive lock not available on {port}: {e}")
                
                # Identify what is holding the lock
                lock_holders = self._identify_lock_holders(port)
                if lock_holders:
                    self.logger.error(f"Processes using {port}:")
                    for holder in lock_holders:
                        self.logger.error(f"  • {holder['command']} (PID: {holder['pid']}) - User: {holder.get('user', 'unknown')}")
                    
                    # Try to resolve conflicts if possible
                    if self._should_resolve_conflicts():
                        self.logger.info("Attempting to resolve port conflicts...")
                        if self._resolve_port_conflicts(port, lock_holders):
                            self.logger.info("Port conflicts resolved, retesting exclusive lock...")
                            return self._test_exclusive_lock(port)  # Retry once
                else:
                    self.logger.error("Could not identify process holding the exclusive lock")
                    self.logger.info("Manual steps to try:")
                    self.logger.info(f"  • Check for processes: lsof {port}")
                    self.logger.info(f"  • Remove stale locks: sudo rm /var/lock/LCK..{os.path.basename(port)}")
                    self.logger.info("  • Stop ModemManager: sudo systemctl stop ModemManager")
                
                return False
            else:
                # Other serial errors
                self.logger.error(f"Serial error during exclusive lock test: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error testing exclusive lock: {e}")
            return False
    
    def _identify_lock_holders(self, port: str) -> List[Dict[str, str]]:
        """
        Identify processes that are using the serial port
        
        Args:
            port: Serial port path
            
        Returns:
            List of dictionaries with process information
        """
        processes = []
        
        try:
            # Use lsof to find processes using the device
            result = subprocess.run(
                ["lsof", port],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        processes.append({
                            "command": parts[0],
                            "pid": parts[1],
                            "user": parts[2] if len(parts) > 2 else "unknown",
                            "full_line": line
                        })
            
        except subprocess.TimeoutExpired:
            self.logger.debug(f"lsof timeout for {port}")
        except FileNotFoundError:
            # lsof not available, try fuser
            try:
                result = subprocess.run(
                    ["fuser", port],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    pids = result.stdout.strip().split()
                    for pid in pids:
                        if pid.isdigit():
                            processes.append({
                                "pid": pid,
                                "command": f"PID {pid}",
                                "user": "unknown"
                            })
                            
            except Exception as e:
                self.logger.debug(f"Error using fuser: {e}")
        except Exception as e:
            self.logger.debug(f"Error identifying lock holders for {port}: {e}")
        
        return processes
    
    def _should_resolve_conflicts(self) -> bool:
        """
        Determine if automatic conflict resolution should be attempted
        
        Returns:
            True if conflicts should be resolved automatically
        """
        return self.config.serial.auto_resolve_conflicts
    
    def _resolve_port_conflicts(self, port: str, lock_holders: List[Dict[str, str]]) -> bool:
        """
        Attempt to resolve port conflicts by stopping interfering processes
        
        Args:
            port: Serial port path
            lock_holders: List of processes using the port
            
        Returns:
            True if conflicts were resolved, False otherwise
        """
        resolved_any = False
        port_basename = os.path.basename(port)
        
        for holder in lock_holders:
            command = holder.get("command", "").lower()
            pid = holder.get("pid", "")
            
            try:
                # Handle ModemManager
                if "modemmanager" in command and self.config.serial.stop_modemmanager:
                    self.logger.info(f"Stopping ModemManager service (PID: {pid})")
                    result = subprocess.run(
                        ["sudo", "systemctl", "stop", "ModemManager"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        self.logger.info("✓ ModemManager stopped")
                        resolved_any = True
                    else:
                        self.logger.warning(f"Failed to stop ModemManager: {result.stderr}")
                
                # Handle getty services
                elif "getty" in command and self.config.serial.stop_getty_services:
                    service_name = f"serial-getty@{port_basename}.service"
                    self.logger.info(f"Disabling serial console service: {service_name}")
                    result = subprocess.run(
                        ["sudo", "systemctl", "stop", service_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        self.logger.info(f"✓ {service_name} stopped")
                        resolved_any = True
                    else:
                        self.logger.debug(f"Could not stop {service_name}: {result.stderr}")
                
                # Handle other BBMesh instances
                elif "bbmesh" in command or "python" in command:
                    if pid and pid.isdigit():
                        # Check if this is our own process
                        our_pid = str(os.getpid())
                        if pid != our_pid:
                            self.logger.info(f"Found another BBMesh/Python process using {port} (PID: {pid})")
                            self.logger.warning("Another BBMesh instance may be running - manual intervention required")
                            # Don't automatically kill other BBMesh instances for safety
                
                # Handle other processes with caution
                else:
                    if pid and pid.isdigit():
                        self.logger.info(f"Found process {command} using {port} (PID: {pid})")
                        self.logger.info("Manual intervention may be required to stop this process")
                        
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout while trying to resolve conflict with {command}")
            except Exception as e:
                self.logger.debug(f"Error resolving conflict with {command}: {e}")
        
        # Clean up stale lock files
        if self.config.serial.remove_stale_locks:
            lock_file_paths = [
                f"/var/lock/LCK..{port_basename}",
                f"/tmp/LCK..{port_basename}",
                f"/var/run/lock/LCK..{port_basename}"
            ]
            
            for lock_file in lock_file_paths:
                if os.path.exists(lock_file):
                    try:
                        self.logger.info(f"Removing stale lock file: {lock_file}")
                        subprocess.run(["sudo", "rm", lock_file], check=True, timeout=5)
                        self.logger.info(f"✓ Removed {lock_file}")
                        resolved_any = True
                    except Exception as e:
                        self.logger.debug(f"Could not remove lock file {lock_file}: {e}")
        
        if resolved_any:
            # Give the system a moment to release the port
            time.sleep(1)
        
        return resolved_any
    
    def _attempt_connection(self, port: str, timeout: float, attempt_num: int) -> bool:
        """
        Attempt a single connection to the Meshtastic device
        
        Args:
            port: Serial port path
            timeout: Connection timeout in seconds
            attempt_num: Current attempt number for logging
            
        Returns:
            True if connection successful, False otherwise
        """
        interface = None
        start_time = time.time()
        
        try:
            # Step 1: Create serial interface
            self.logger.debug(f"Attempt {attempt_num}: Creating serial interface")
            step_start = time.time()
            
            interface = meshtastic.serial_interface.SerialInterface(
                devPath=port,
                debugOut=None  # Disable debug output to reduce noise
            )
            
            interface_time = time.time() - step_start
            self.logger.debug(f"Attempt {attempt_num}: Interface created in {interface_time:.2f}s")
            
            # Step 2: Wait for node information with detailed progress
            self.logger.debug(f"Attempt {attempt_num}: Waiting for node info (timeout: {timeout}s)")
            info_start = time.time()
            
            poll_interval = 0.1
            last_log_time = info_start
            log_interval = 2.0  # Log progress every 2 seconds
            
            while not interface.myInfo and (time.time() - info_start) < timeout:
                time.sleep(poll_interval)
                
                # Log progress periodically
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    elapsed = current_time - info_start
                    self.logger.debug(f"Attempt {attempt_num}: Still waiting for node info ({elapsed:.1f}s elapsed)")
                    last_log_time = current_time
            
            info_time = time.time() - info_start
            
            # Step 3: Check if we got node information
            if not interface.myInfo:
                self.logger.warning(f"Attempt {attempt_num}: Timeout after {info_time:.2f}s waiting for node info")
                
                # Log interface state for debugging
                self.logger.debug(f"Attempt {attempt_num}: Interface state - nodes: {hasattr(interface, 'nodes')}, "
                                f"channels: {hasattr(interface, 'channels')}")
                
                # Try to get any available information
                if hasattr(interface, 'nodes') and interface.nodes:
                    self.logger.debug(f"Attempt {attempt_num}: Found {len(interface.nodes)} nodes in mesh")
                
                interface.close()
                return False
            
            # Step 4: Process successful connection
            self.logger.debug(f"Attempt {attempt_num}: Received node info in {info_time:.2f}s")
            
            # Store node information - handle different myInfo object types across Meshtastic versions
            # myInfo can be a dict-like object, an object with attributes, or a protobuf message
            if interface.myInfo:
                try:
                    # Try dictionary conversion first (works with older versions)
                    self.node_info = dict(interface.myInfo)
                except (TypeError, AttributeError):
                    # Fall back to attribute access for newer versions
                    self.node_info = {
                        'num': getattr(interface.myInfo, 'num', None),
                        'user': getattr(interface.myInfo, 'user', {})
                    }
            else:
                self.node_info = {'num': None, 'user': {}}
            
            # Store local node ID as string, handling None values properly
            node_num = self.node_info.get('num')
            if node_num is not None:
                self.local_node_id = str(node_num)
            else:
                self.local_node_id = None
                self.logger.warning("Node number is None - direct message detection may not work correctly")
            
            # Log node details
            user_info = self.node_info.get('user', {})
            node_name = user_info.get('longName', 'Unknown')
            short_name = user_info.get('shortName', 'Unknown')
            
            self.logger.info(f"Connected to node {self.local_node_id} ({node_name}/{short_name})")
            
            # Subscribe to message reception
            pub.subscribe(self._on_receive, "meshtastic.receive")
            
            # Store interface and mark as connected
            self.interface = interface
            self.connected = True
            
            total_time = time.time() - start_time
            self.logger.info(f"Connection established in {total_time:.2f}s")
            
            # Log additional mesh information if available
            self._log_mesh_status()
            
            # Validate configuration for direct message only mode
            self._validate_direct_message_config()
            
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"Attempt {attempt_num}: Serial communication error: {e}")
            
            # Provide context for common serial errors
            if "Permission denied" in str(e):
                self.logger.error("Serial permission error - check user permissions")
            elif "No such file or directory" in str(e):
                self.logger.error("Serial port not found - device may be disconnected")
            elif "Device or resource busy" in str(e):
                self.logger.error("Serial port busy - close other applications using the port")
                
        except ImportError as e:
            self.logger.error(f"Attempt {attempt_num}: Missing dependency: {e}")
            self.logger.error("Make sure 'meshtastic' Python package is installed")
            
        except Exception as e:
            self.logger.error(f"Attempt {attempt_num}: Unexpected error: {type(e).__name__}: {e}")
            
            # Log additional context for debugging
            self.logger.debug(f"Attempt {attempt_num}: Error occurred after {time.time() - start_time:.2f}s")
            
        finally:
            # Clean up interface if connection failed
            if interface and not self.connected:
                try:
                    interface.close()
                except Exception as e:
                    self.logger.debug(f"Error closing interface: {e}")
        
        return False
    
    def _log_mesh_status(self) -> None:
        """Log current mesh network status information"""
        try:
            if not self.interface:
                return
            
            # Log node count
            if hasattr(self.interface, 'nodes') and self.interface.nodes:
                node_count = len(self.interface.nodes)
                self.logger.info(f"Mesh network has {node_count} known nodes")
                
                # Log some node details in debug mode
                for node_id, node_info in list(self.interface.nodes.items())[:5]:  # First 5 nodes
                    user = node_info.get('user', {})
                    name = user.get('shortName', user.get('longName', 'Unknown'))
                    self.logger.debug(f"  Node {node_id}: {name}")
                
                if node_count > 5:
                    self.logger.debug(f"  ... and {node_count - 5} more nodes")
            
            # Log channel information
            if hasattr(self.interface, 'channels') and self.interface.channels:
                channel_count = len(self.interface.channels)
                self.logger.info(f"Device has {channel_count} configured channels")
                
        except Exception as e:
            self.logger.debug(f"Error logging mesh status: {e}")
    
    def _validate_direct_message_config(self) -> None:
        """Validate configuration for direct message functionality"""
        try:
            if self.config.direct_message_only:
                if self.local_node_id is None:
                    self.logger.error("CONFIGURATION ERROR: direct_message_only=true but local_node_id is None!")
                    self.logger.error("Direct messages cannot be detected. Consider setting direct_message_only=false")
                else:
                    self.logger.info(f"Direct message only mode enabled - Local node ID: {self.local_node_id}")
                    self.logger.info("Will ONLY process direct messages sent to this node")
                    
                # Log BROADCAST_ADDR for debugging
                self.logger.debug(f"BROADCAST_ADDR constant value: {BROADCAST_ADDR} (type: {type(BROADCAST_ADDR)})")
            else:
                self.logger.info(f"Processing both direct messages and broadcasts on channels: {self.config.monitored_channels}")
                
        except Exception as e:
            self.logger.error(f"Error validating direct message configuration: {e}")
    
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
            # Handle case where local_node_id might be None
            is_direct = False
            
            # Debug logging for direct message detection
            self.logger.debug(f"DM Detection - to_id: {to_id} (type: {type(to_id)}), "
                            f"from_id: {from_id}, local_node_id: {self.local_node_id} (type: {type(self.local_node_id)}), "
                            f"BROADCAST_ADDR: {BROADCAST_ADDR} (type: {type(BROADCAST_ADDR)})")
            
            if self.local_node_id is not None:
                try:
                    # Handle both string and integer node IDs
                    local_id_int = int(self.local_node_id)
                    to_id_int = int(to_id) if to_id is not None else None
                    
                    # Check for broadcast addresses - handle multiple formats
                    is_broadcast = (
                        to_id == BROADCAST_ADDR or  # String format "^all"
                        to_id_int == 4294967295 or  # Standard broadcast address
                        to_id_int == -1 or          # Signed broadcast address
                        to_id == "^all"             # Explicit string check
                    )
                    
                    if is_broadcast:
                        is_direct = False
                        self.logger.debug(f"DM Detection - Message is broadcast (to_id={to_id}, to_id_int={to_id_int})")
                    else:
                        is_direct = to_id_int == local_id_int
                        self.logger.debug(f"DM Detection - Comparing: to_id_int={to_id_int} == local_id_int={local_id_int} -> is_direct={is_direct}")
                    
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Error comparing node IDs for direct message detection: {e}")
                    self.logger.debug(f"Failed conversion - to_id: {to_id}, local_node_id: {self.local_node_id}")
                    is_direct = False
            else:
                self.logger.debug("DM Detection - local_node_id is None, cannot detect direct messages")
                is_direct = False
            
            # Get sender name
            sender_name = self._get_node_name(from_id)
            
            # Filter messages based on configuration
            should_process = self._should_process_message(channel, is_direct)
            self.logger.debug(f"Message filtering - channel: {channel}, is_direct: {is_direct}, "
                            f"direct_message_only: {self.config.direct_message_only}, "
                            f"monitored_channels: {self.config.monitored_channels}, "
                            f"should_process: {should_process}")
            
            if not should_process:
                self.logger.debug(f"Message REJECTED - From: {sender_name}({from_id}), "
                                f"Channel: {channel}, Direct: {is_direct}, Text: '{text}'")
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
        # Always process direct messages
        if is_direct:
            self.logger.debug(f"Processing direct message (is_direct=True)")
            return True
            
        # If direct message only mode, ignore broadcasts
        if self.config.direct_message_only:
            self.logger.debug(f"Rejecting broadcast message - direct_message_only mode enabled")
            return False
            
        # Check if channel is monitored
        is_monitored = channel in self.config.monitored_channels
        if is_monitored:
            self.logger.debug(f"Processing broadcast message on monitored channel {channel}")
        else:
            self.logger.debug(f"Rejecting message on unmonitored channel {channel}")
        
        return is_monitored
    
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