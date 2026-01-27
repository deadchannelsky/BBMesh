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
    
    def __init__(self, config: MeshtasticConfig, message_send_delay: float = 1.0, max_message_length: int = 200):
        self.config = config
        self.message_send_delay = message_send_delay
        self.max_message_length = max_message_length
        self.logger = BBMeshLogger(__name__)
        self.interface: Optional[meshtastic.serial_interface.SerialInterface] = None
        self.node_info: Dict[str, Any] = {}
        self.local_node_id: Optional[str] = None
        self.connected = False
        self.message_callbacks: List[Callable[[MeshMessage], None]] = []
        self._stop_event = threading.Event()
        self._connection_lock = threading.Lock()  # Prevent concurrent connection attempts
        self._last_message_time: float = 0.0  # Track last message send time for delay enforcement

        # Health monitoring attributes
        self.last_received_message_time: Optional[datetime] = None  # Track when we last received a message
        self.message_timeout: int = 1800  # 30 minutes - warn if no messages received
        
    def connect(self, max_retries: int = 3) -> bool:
        """
        Connect to the Meshtastic node with enhanced diagnostics and retry logic
        
        Args:
            max_retries: Maximum number of connection attempts
            
        Returns:
            True if connection successful, False otherwise
        """
        # Prevent concurrent connection attempts
        with self._connection_lock:
            # Add stack trace to identify what's calling connect() during operation
            import traceback
            stack_trace = traceback.format_stack()
            self.logger.info(f"🔌 CONNECT() CALLED - Stack trace:")
            for line in stack_trace[-5:]:  # Show last 5 stack frames
                self.logger.info(f"🔌   {line.strip()}")
            
            # Check if already connected
            if self.connected and self.interface:
                self.logger.error("💥 SPURIOUS CONNECTION ATTEMPT - already connected!")
                self.logger.error("💥 This should NOT happen - investigating caller")
                return True
            
            if self.connected:
                self.logger.warning("Connection state inconsistent - marked connected but no interface")
                self.connected = False
            
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
            self.logger.info(f"=== ANALYZING myInfo STRUCTURE ===")
            self.logger.info(f"myInfo type: {type(interface.myInfo)}")
            self.logger.info(f"myInfo value: {interface.myInfo}")
            self.logger.info(f"myInfo is None: {interface.myInfo is None}")
            self.logger.info(f"myInfo is empty: {not bool(interface.myInfo) if interface.myInfo is not None else 'N/A'}")
            
            if interface.myInfo:
                # Enhanced debugging of myInfo structure
                self.logger.info(f"myInfo attributes: {dir(interface.myInfo)}")
                if hasattr(interface.myInfo, '__dict__'):
                    self.logger.info(f"myInfo.__dict__: {interface.myInfo.__dict__}")
                
                # Try to access every possible attribute that might contain node info
                potential_attrs = ['num', 'node_num', 'id', 'node_id', 'nodeNum', 'nodeId', 'my_node_num', 'local_node_num']
                for attr in potential_attrs:
                    if hasattr(interface.myInfo, attr):
                        attr_value = getattr(interface.myInfo, attr)
                        self.logger.info(f"myInfo.{attr}: {attr_value} (type: {type(attr_value)})")
                
                try:
                    # Try dictionary conversion first (works with older versions)
                    self.node_info = dict(interface.myInfo)
                    self.logger.info(f"✅ Successfully converted myInfo to dict: {self.node_info}")
                except (TypeError, AttributeError) as e:
                    self.logger.info(f"❌ Dict conversion failed: {e}")
                    # Fall back to attribute access for newer versions
                    self.node_info = {
                        'num': getattr(interface.myInfo, 'num', None),
                        'user': getattr(interface.myInfo, 'user', {})
                    }
                    self.logger.info(f"Attribute access result: {self.node_info}")
                    
                    # Try additional attribute names that might contain the node ID
                    for attr_name in ['node_num', 'id', 'node_id', 'nodeNum', 'nodeId']:
                        if hasattr(interface.myInfo, attr_name):
                            attr_value = getattr(interface.myInfo, attr_name)
                            self.logger.info(f"Found alternative node ID attribute '{attr_name}': {attr_value}")
                            if attr_value is not None and self.node_info.get('num') is None:
                                self.node_info['num'] = attr_value
                                self.logger.info(f"✅ Using {attr_name} as node ID: {attr_value}")
            else:
                self.logger.error("❌ myInfo is None or empty - this is the problem!")
                self.node_info = {'num': None, 'user': {}}
            
            # Store local node ID as string, extracting the proper user.id format (e.g., "!a0cbf888")
            user_info = self.node_info.get('user', {})
            user_id = user_info.get('id') if isinstance(user_info, dict) else getattr(user_info, 'id', None)
            
            if user_id is not None:
                self.local_node_id = user_id
                self.logger.info(f"✅ Successfully extracted local node ID from myInfo.user.id: {self.local_node_id}")
            else:
                self.logger.error("❌ User ID is None from myInfo.user.id - trying fallback methods")
                self.logger.info("=== STARTING FALLBACK NODE ID DETECTION ===")
                self.local_node_id = self._find_local_node_id_fallback(interface)
                
                if self.local_node_id is None:
                    # Try manual configuration as last resort
                    if self.config.node_id:
                        self.logger.info(f"🔧 Using manually configured node_id: {self.config.node_id}")
                        self.local_node_id = str(self.config.node_id)
                        # Ensure it has the ! prefix if it's not already there
                        if not self.local_node_id.startswith('!'):
                            self.local_node_id = f"!{self.local_node_id}"
                    else:
                        self.logger.error("💥 CRITICAL: Could not determine local node ID using any method!")
                        self.logger.error("💥 Direct message detection will not work correctly")
                        self.logger.error("💥 Try manually setting node_id in bbmesh.yaml (e.g., node_id: '!a0cbf888')")
                        self.logger.error("💥 Or wait for a direct message to auto-learn the node ID")
                else:
                    self.logger.info(f"✅ SUCCESS: Found local node ID using fallback method: {self.local_node_id}")
            
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
    
    def _find_local_node_id_fallback(self, interface) -> Optional[str]:
        """
        Try alternative methods to find the local node ID when myInfo fails
        
        Args:
            interface: Meshtastic interface object
            
        Returns:
            Local node ID as string, or None if not found
        """
        self.logger.info("🔍 === FALLBACK NODE ID DETECTION METHODS ===")
        self.logger.info(f"Interface type: {type(interface)}")
        self.logger.info(f"Interface attributes: {[attr for attr in dir(interface) if not attr.startswith('_')]}")
        
        try:
            # Method 1: Check if there's a myInfo property with user.id
            self.logger.info("🔍 Method 1: Checking interface.myInfo.user.id")
            if hasattr(interface, 'myInfo') and interface.myInfo:
                my_info = getattr(interface, 'myInfo')
                if hasattr(my_info, 'user'):
                    user = getattr(my_info, 'user')
                    if hasattr(user, 'id'):
                        user_id = getattr(user, 'id')
                        if user_id is not None:
                            self.logger.info(f"✅ Fallback method 1 SUCCESS: Found myInfo.user.id: {user_id}")
                            return user_id
                        else:
                            self.logger.info("❌ myInfo.user.id is None")
                    else:
                        self.logger.info("❌ myInfo.user has no id attribute")
                else:
                    self.logger.info("❌ myInfo has no user attribute")
            else:
                self.logger.info("❌ interface.myInfo not found or empty")
            
            # Method 2: Check if there's a localNode property with user.id
            if hasattr(interface, 'localNode'):
                local_node = getattr(interface, 'localNode')
                if local_node and hasattr(local_node, 'user'):
                    user = getattr(local_node, 'user')
                    if hasattr(user, 'id'):
                        user_id = getattr(user, 'id')
                        if user_id is not None:
                            self.logger.debug(f"Fallback method 2: Found localNode.user.id: {user_id}")
                            return user_id
            
            # Method 3: Look through nodes dictionary for the local node
            # The local node often has special properties or is marked differently
            if hasattr(interface, 'nodes') and interface.nodes:
                self.logger.debug(f"Fallback method 3: Searching through {len(interface.nodes)} nodes")
                
                for node_id, node_info in interface.nodes.items():
                    self.logger.debug(f"  Checking node {node_id}: {node_info}")
                    
                    # Look for indicators that this is the local node
                    if isinstance(node_info, dict):
                        # Check for 'isLocal' flag or similar
                        if node_info.get('isLocal') or node_info.get('is_local'):
                            self.logger.debug(f"Fallback method 3: Found local node by isLocal flag: {node_id}")
                            return str(node_id)
                        
                        # Check if this node has the same position/telemetry as we're receiving
                        # (This is more complex but could work in some cases)
                        user_info = node_info.get('user', {})
                        if user_info.get('isLicensed') == True or user_info.get('role') == 'ROUTER':
                            # These might indicate it's our node, but this is speculative
                            pass
            
            # Method 4: Try to extract from interface properties/methods
            interface_attrs = dir(interface)
            self.logger.debug(f"Interface attributes: {[attr for attr in interface_attrs if 'node' in attr.lower() or 'id' in attr.lower()]}")
            
            for attr_name in ['myNodeInfo', 'my_node_info', 'localNodeNum', 'local_node_num']:
                if hasattr(interface, attr_name):
                    attr_value = getattr(interface, attr_name)
                    self.logger.debug(f"Fallback method 4: Found {attr_name}: {attr_value}")
                    if attr_value and hasattr(attr_value, 'num'):
                        node_id = getattr(attr_value, 'num')
                        if node_id is not None:
                            self.logger.debug(f"Fallback method 4: Extracted node ID: {node_id}")
                            return str(node_id)
            
            self.logger.debug("All fallback methods failed to find local node ID")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in fallback node ID detection: {e}")
            return None
    
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

    def _check_connection_health(self) -> bool:
        """
        Verify connection is alive by checking interface state.
        Returns True if healthy, False if needs reconnection.
        """
        if not self.connected:
            return False

        if not self.interface:
            self.logger.warning("Interface object lost - reconnection needed")
            return False

        # Check if Meshtastic interface still has node info
        try:
            if not self.interface.myInfo:
                self.logger.warning("Lost node info - connection degraded")
                return False
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

        # Check if we're receiving messages (connection could be silently dead)
        if self._is_message_timeout():
            self.logger.warning("Message timeout detected - connection appears stalled")
            return False

        return True

    def _is_message_timeout(self) -> bool:
        """
        Check if we haven't received messages in too long
        Returns True if timeout exceeded, False otherwise
        """
        if self.last_received_message_time is None:
            return False  # No messages yet since startup

        time_since_last = (datetime.now() - self.last_received_message_time).total_seconds()

        # Warn if no messages for extended period
        # (But don't trigger on legitimate idle networks)
        if time_since_last > self.message_timeout:
            self.logger.warning(f"No messages received in {time_since_last:.0f}s")
            return True

        return False

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to Meshtastic device.
        Returns True if successful.
        """
        self.logger.info("Attempting reconnection...")

        # Disconnect cleanly
        try:
            self.disconnect()
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")

        # Wait briefly for serial port to settle
        time.sleep(2.0)

        # Reconnect
        success = self.connect(max_retries=3)

        if success:
            self.logger.info("Reconnection successful")
            # Reset last message time
            self.last_received_message_time = datetime.now()
        else:
            self.logger.error("Reconnection failed")

        return success

    def _cleanup_port_locks(self) -> None:
        """
        Clean up stale serial port lock files when disconnecting.
        This prevents "Device or resource busy" errors on subsequent restarts.
        """
        try:
            port = self.config.serial.port
            port_basename = os.path.basename(port)

            # Only proceed if configured to remove stale locks
            if not self.config.serial.remove_stale_locks:
                self.logger.debug("Stale lock cleanup disabled in configuration")
                return

            # Potential lock file locations (varies by system)
            lock_file_paths = [
                f"/var/lock/LCK..{port_basename}",
                f"/tmp/LCK..{port_basename}",
                f"/var/run/lock/LCK..{port_basename}"
            ]

            cleaned_any = False
            for lock_file in lock_file_paths:
                if os.path.exists(lock_file):
                    try:
                        self.logger.info(f"Removing stale lock file during disconnect: {lock_file}")
                        subprocess.run(["sudo", "rm", lock_file], check=True, timeout=5)
                        self.logger.info(f"✓ Removed lock file: {lock_file}")
                        cleaned_any = True
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"Could not remove lock file {lock_file}: {e}")
                    except Exception as e:
                        self.logger.debug(f"Error removing lock file {lock_file}: {e}")

            if cleaned_any:
                # Give the system a moment to fully release the port
                time.sleep(0.5)
                self.logger.info("Port locks cleaned up - device should be available for restart")

        except Exception as e:
            self.logger.warning(f"Error during port lock cleanup: {e}")

    def disconnect(self) -> None:
        """Disconnect from the Meshtastic node"""
        with self._connection_lock:
            if self.interface:
                try:
                    self.logger.info("Disconnecting from Meshtastic node...")
                    pub.unsubscribe(self._on_receive, "meshtastic.receive")
                    self.interface.close()
                    # Give the OS time to release the exclusive lock on the serial port
                    time.sleep(0.1)
                    self.connected = False
                    self.interface = None
                    self.logger.info("Successfully disconnected from Meshtastic node")
                except Exception as e:
                    self.logger.error(f"Error during disconnect: {e}")
                    # Force cleanup even if disconnect fails
                    self.connected = False
                    self.interface = None
                finally:
                    # Always clean up port locks to prevent restart failures
                    self._cleanup_port_locks()
            else:
                self.logger.debug("Disconnect called but no interface - already disconnected")
    
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
    
    def _split_message(self, text: str) -> List[str]:
        """
        Split a long message into multiple parts that fit within the configured limit.
        
        Args:
            text: The message text to split
            
        Returns:
            List of message parts, each within the configured length limit
        """
        if len(text) <= self.max_message_length:
            return [text]
        
        parts = []
        remaining = text
        part_num = 1
        
        # Reserve space for part indicators like " (1/N)"
        part_indicator_space = 8  # " (XX/XX)" takes up to 8 characters
        effective_limit = self.max_message_length - part_indicator_space
        
        # First pass: split text into parts without indicators
        temp_parts = []
        while remaining:
            if len(remaining) <= effective_limit:
                temp_parts.append(remaining)
                break
            
            # Find the best place to split (prefer word boundaries)
            split_point = effective_limit
            
            # Look for word boundary within last 50 characters
            word_boundary_start = max(0, effective_limit - 50)
            last_space = remaining.rfind(' ', word_boundary_start, effective_limit)
            
            if last_space > word_boundary_start:
                split_point = last_space
            
            # Split the message
            temp_parts.append(remaining[:split_point])
            remaining = remaining[split_point:]
            
            # Only remove leading space if we split at a space boundary
            if remaining.startswith(' '):
                remaining = remaining[1:]
        
        # Second pass: add part indicators
        total_parts = len(temp_parts)
        
        if total_parts == 1:
            # No splitting needed after all
            return temp_parts
        
        for i, part in enumerate(temp_parts, 1):
            indicator = f" ({i}/{total_parts})"
            # Ensure part + indicator doesn't exceed limit
            if len(part) + len(indicator) > self.max_message_length:
                # Trim the part to make room for indicator
                part = part[:self.max_message_length - len(indicator)]
            
            parts.append(part + indicator)
        
        return parts
    
    def _send_message_parts(self, parts: List[str], channel: int = 0, 
                           destination: Optional[str] = None) -> bool:
        """
        Send multiple message parts with proper delays between them.
        
        Args:
            parts: List of message parts to send
            channel: Channel number (0-7)
            destination: Destination node ID (None for broadcast)
            
        Returns:
            True if all parts sent successfully, False otherwise
        """
        if not parts:
            return True
        
        self.logger.info(f"📤 Sending {len(parts)} message parts")
        
        success_count = 0
        
        for i, part in enumerate(parts):
            try:
                # Send individual part using existing single message logic
                success = self._send_single_message(part, channel, destination)
                
                if success:
                    success_count += 1
                    self.logger.info(f"📤 Part {i+1}/{len(parts)} sent successfully")
                else:
                    self.logger.error(f"📤 Part {i+1}/{len(parts)} failed to send")
                    break  # Stop sending if any part fails

            except Exception as e:
                self.logger.error(f"📤 Error sending part {i+1}/{len(parts)}: {e}")
                break
        
        success = success_count == len(parts)
        
        if success:
            self.logger.info(f"✅ All {len(parts)} message parts sent successfully")
        else:
            self.logger.error(f"❌ Only {success_count}/{len(parts)} message parts sent successfully")
        
        return success
    
    def _send_single_message(self, text: str, channel: int = 0, 
                           destination: Optional[str] = None) -> bool:
        """
        Send a single message part (internal method).
        
        Args:
            text: Message text to send (should already be within length limits)
            channel: Channel number (0-7)
            destination: Destination node ID (None for broadcast)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.connected or not self.interface:
            self.logger.error("Cannot send message - not connected to Meshtastic node")
            return False
        
        try:
            # Enforce message send delay to prevent rapid-fire sending
            current_time = time.time()
            time_since_last = current_time - self._last_message_time
            
            if time_since_last < self.message_send_delay:
                delay_needed = self.message_send_delay - time_since_last
                self.logger.info(f"⏱️ Applying message send delay: {delay_needed:.2f}s")
                time.sleep(delay_needed)
            
            # Final length check (should not be needed, but safety first)
            if len(text) > self.max_message_length:
                self.logger.warning(f"📤 Message part still too long ({len(text)} chars), truncating")
                text = text[:self.max_message_length-3] + "..."
            
            # Send message using existing Meshtastic logic
            if destination:
                # Ensure destination is in proper format for Meshtastic
                if destination.isdigit():
                    # Convert numeric destination to !-prefixed format
                    numeric_dest = int(destination)
                    hex_dest = self.numeric_to_hex_id(numeric_dest)
                    meshtastic_destination = hex_dest
                elif destination.startswith('!'):
                    # Already in proper format
                    meshtastic_destination = destination
                else:
                    # Try to ensure proper format
                    meshtastic_destination = self.ensure_hex_id_format(destination)
                
                # Direct message to specific node
                self.interface.sendText(
                    text=text,
                    destinationId=meshtastic_destination,
                    channelIndex=channel
                )
                self.logger.log_message("TX", meshtastic_destination, channel, text, self.local_node_id)
            else:
                # Broadcast message
                self.interface.sendText(
                    text=text,
                    channelIndex=channel
                )
                self.logger.log_message("TX", "BROADCAST", channel, text, self.local_node_id)
            
            # Update last message time after successful send
            self._last_message_time = time.time()
            return True
            
        except Exception as e:
            self.logger.error(f"💥 Failed to send message part: {e}")
            return False
    
    def send_message(self, text: str, channel: int = 0, 
                    destination: Optional[str] = None) -> bool:
        """
        Send a message via Meshtastic, automatically splitting long messages into multiple parts.
        
        Args:
            text: Message text to send
            channel: Channel number (0-7)
            destination: Destination node ID (None for broadcast)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.connected or not self.interface:
            self.logger.error("Cannot send message - not connected to Meshtastic node")
            return False
        
        try:
            self.logger.info(f"📤 SENDING MESSAGE: length={len(text)} chars, channel={channel}, destination={destination}")
            self.logger.info(f"📤 Message preview: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            self.logger.info(f"📤 Max message length: {self.max_message_length} chars")
            
            # Split message if it's too long
            message_parts = self._split_message(text)
            
            if len(message_parts) == 1:
                self.logger.info(f"📤 Sending single message ({len(text)} chars)")
                return self._send_single_message(text, channel, destination)
            else:
                self.logger.info(f"📤 Splitting long message into {len(message_parts)} parts")
                return self._send_message_parts(message_parts, channel, destination)
            
        except Exception as e:
            self.logger.error(f"💥 CRITICAL: Failed to send message: {e}")
            import traceback
            self.logger.error(f"💥 Send message traceback: {traceback.format_exc()}")
            # Ensure this error doesn't corrupt connection state
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

            # Update last message timestamp - track that we're receiving TEXT messages
            # (Must be after TEXT_MESSAGE_APP check to avoid false positives from telemetry/position packets)
            self.last_received_message_time = datetime.now()
            
            # Extract message data
            from_id_numeric = str(packet.get('from', 'unknown'))
            to_id = packet.get('to')
            channel = packet.get('channel', 0)
            text = decoded.get('payload', b'').decode('utf-8', errors='ignore')
            hop_limit = packet.get('hopLimit', 0)
            
            # Convert sender ID to proper !-prefixed format for consistency
            if from_id_numeric != 'unknown':
                try:
                    from_id = self.ensure_hex_id_format(from_id_numeric)
                    self.logger.debug(f"🔄 ID CONVERSION: {from_id_numeric} → {from_id}")
                except Exception as e:
                    self.logger.debug(f"⚠️ Could not convert from_id {from_id_numeric}: {e}")
                    from_id = from_id_numeric
            else:
                from_id = from_id_numeric
            
            # Get signal quality information
            snr = packet.get('rxSnr', 0.0)
            rssi = packet.get('rxRssi', -999)
            
            # Learn local node ID from direct messages if we don't have it yet
            self.logger.debug(f"🔍 AUTO-LEARNING CHECK: local_node_id={self.local_node_id}, to_id={to_id}, BROADCAST_ADDR={BROADCAST_ADDR}")
            if self.local_node_id is None and to_id != BROADCAST_ADDR and str(to_id) != "^all":
                # If we receive a message with a specific to_id, that might be our local node ID
                try:
                    to_id_int = int(to_id) if to_id is not None else None
                    self.logger.info(f"🔍 Checking to_id_int: {to_id_int}")
                    if to_id_int and to_id_int != 4294967295 and to_id_int != -1:
                        self.logger.info(f"🎯 LEARNING NODE ID: Message addressed to {to_id_int} - this IS our local node ID!")
                        
                        # Set the local node ID (thread-safe update) - convert to proper !-prefixed format
                        with self._connection_lock:  # Ensure thread-safe update
                            old_local_node_id = self.local_node_id
                            # Convert numeric node ID to proper Meshtastic format (!hexvalue)
                            hex_node_id = f"!{to_id_int:08x}"
                            self.local_node_id = hex_node_id
                            self.node_info['num'] = to_id_int
                            # Also store the user info with proper ID
                            if 'user' not in self.node_info:
                                self.node_info['user'] = {}
                            self.node_info['user']['id'] = hex_node_id
                            
                            self.logger.info(f"✅ AUTO-LEARNED local node ID: {old_local_node_id} -> {self.local_node_id}")
                            self.logger.info(f"✅ Updated node_info: {self.node_info}")
                            
                            # This is critical - we now know our node ID and can process messages correctly
                            self.logger.info(f"🎉 DIRECT MESSAGE DETECTION NOW ENABLED!")
                    else:
                        self.logger.debug(f"to_id_int {to_id_int} is broadcast or invalid, not learning from it")
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Could not learn node ID from to_id {to_id}: {e}")
            else:
                if self.local_node_id is not None:
                    self.logger.debug(f"Already have local_node_id: {self.local_node_id}")
                else:
                    self.logger.debug(f"to_id {to_id} is broadcast, not learning from it")
            
            # Determine if this is a direct message
            # Handle case where local_node_id might be None
            is_direct = False
            
            # Debug logging for direct message detection
            self.logger.debug(f"DM Detection - to_id: {to_id} (type: {type(to_id)}), "
                            f"from_id: {from_id}, local_node_id: {self.local_node_id} (type: {type(self.local_node_id)}), "
                            f"BROADCAST_ADDR: {BROADCAST_ADDR} (type: {type(BROADCAST_ADDR)})")
            
            if self.local_node_id is not None:
                try:
                    # Extract numeric part from !-prefixed local node ID for comparison
                    if self.local_node_id.startswith('!'):
                        local_id_hex = self.local_node_id[1:]  # Remove the !
                        local_id_int = int(local_id_hex, 16)   # Convert hex to int
                    else:
                        # Fallback: try to parse as integer directly
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
                        self.logger.debug(f"DM Detection - Comparing: to_id_int={to_id_int} == local_id_int={local_id_int} (from {self.local_node_id}) -> is_direct={is_direct}")
                    
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
            self.logger.info(f"📞 CALLING MESSAGE CALLBACKS - {len(self.message_callbacks)} callbacks registered")
            for i, callback in enumerate(self.message_callbacks):
                try:
                    callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
                    self.logger.info(f"📞 Callback {i+1}/{len(self.message_callbacks)}: {callback_name}")
                    self.logger.info(f"📞 About to call callback with message: from={message.sender_id}, to={message.to_node}, text='{message.text}', is_direct={message.is_direct}")
                    
                    # Call the callback
                    callback(message)
                    
                    self.logger.info(f"✅ Callback {i+1} completed successfully")
                except Exception as e:
                    self.logger.error(f"💥 CRITICAL: Error in message callback {i+1} ({callback}): {e}")
                    import traceback
                    self.logger.error(f"💥 Callback traceback: {traceback.format_exc()}")
                    # Do not let callback exceptions affect interface state
                    continue
            
            self.logger.info(f"✅ All message callbacks completed")
                    
        except Exception as e:
            self.logger.error(f"CRITICAL: Error processing received message: {e}")
            import traceback
            self.logger.error(f"Message processing traceback: {traceback.format_exc()}")
            # Do not let message processing exceptions affect interface state
            self.logger.error("Message processing failed but interface remains connected")
    
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
    
    @staticmethod
    def numeric_to_hex_id(node_num: int) -> str:
        """
        Convert numeric node ID to Meshtastic !-prefixed hex format
        
        Args:
            node_num: Numeric node ID (e.g., 2697665316)
            
        Returns:
            Hex node ID with ! prefix (e.g., "!a0cbef24")
        """
        return f"!{node_num:08x}"
    
    @staticmethod
    def hex_id_to_numeric(hex_id: str) -> int:
        """
        Convert Meshtastic !-prefixed hex node ID to numeric format
        
        Args:
            hex_id: Hex node ID with ! prefix (e.g., "!a0cbef24")
            
        Returns:
            Numeric node ID (e.g., 2697665316)
        """
        if hex_id.startswith('!'):
            return int(hex_id[1:], 16)
        else:
            # If no ! prefix, try to parse as hex anyway
            return int(hex_id, 16)
    
    @staticmethod
    def ensure_hex_id_format(node_id: str) -> str:
        """
        Ensure node ID is in proper !-prefixed hex format
        
        Args:
            node_id: Node ID in any format (numeric string or hex)
            
        Returns:
            Node ID in !-prefixed hex format
        """
        if node_id.startswith('!'):
            return node_id
        
        try:
            # Try to parse as numeric and convert to hex
            numeric_id = int(node_id)
            return MeshtasticInterface.numeric_to_hex_id(numeric_id)
        except ValueError:
            # If it's already hex without !, add the prefix
            if all(c in '0123456789abcdefABCDEF' for c in node_id):
                return f"!{node_id.lower()}"
            else:
                # Return as-is if we can't parse it
                return node_id
    
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