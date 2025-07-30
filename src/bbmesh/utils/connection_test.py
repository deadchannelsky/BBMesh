"""
Connection test utility for Meshtastic devices

This module provides comprehensive diagnostic tools to test and troubleshoot
Meshtastic device connections.
"""

import os
import time
import glob
import stat
import grp
import subprocess
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

import serial
import serial.tools.list_ports
import meshtastic
import meshtastic.serial_interface

from .logger import BBMeshLogger
from ..core.config import Config, SerialConfig


class ConnectionTester:
    """
    Comprehensive Meshtastic connection testing utility
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.logger = BBMeshLogger(__name__)
        self.config = config or Config.create_default()
        
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """
        Run complete connection diagnostic
        
        Returns:
            Dictionary containing all diagnostic results
        """
        self.logger.info("Starting comprehensive Meshtastic connection diagnostic")
        
        results = {
            "system_info": self._get_system_info(),
            "available_ports": self._discover_serial_ports(),
            "permissions": self._check_permissions(),
            "port_conflicts": self._check_port_conflicts(),
            "system_services": self._check_system_services(),
            "lock_files": self._check_lock_files(),
            "port_tests": self._test_all_ports(),
            "connection_test": None
        }
        
        # Try connection with configured port
        if self.config.meshtastic.serial.port:
            results["connection_test"] = self._test_meshtastic_connection(
                self.config.meshtastic.serial.port
            )
        
        return results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information relevant to serial connections"""
        import platform
        
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "user": os.getenv("USER", "unknown"),
            "groups": []
        }
        
        try:
            # Get user groups
            import pwd
            user_groups = [g.gr_name for g in grp.getgrall() 
                          if info["user"] in g.gr_mem]
            primary_group = grp.getgrgid(pwd.getpwnam(info["user"]).pw_gid).gr_name
            if primary_group not in user_groups:
                user_groups.append(primary_group)
            info["groups"] = user_groups
        except Exception as e:
            self.logger.debug(f"Could not get group information: {e}")
        
        return info
    
    def _discover_serial_ports(self) -> List[Dict[str, Any]]:
        """
        Discover all available serial ports
        
        Returns:
            List of dictionaries containing port information
        """
        ports = []
        
        # Use pyserial's built-in discovery
        try:
            discovered_ports = serial.tools.list_ports.comports()
            for port in discovered_ports:
                port_info = {
                    "device": port.device,
                    "description": port.description or "Unknown",
                    "manufacturer": port.manufacturer or "Unknown",
                    "vid": port.vid,
                    "pid": port.pid,
                    "serial_number": port.serial_number,
                    "location": port.location,
                    "accessible": False,
                    "permissions": None
                }
                
                # Check accessibility
                try:
                    with serial.Serial(port.device, timeout=0.1) as ser:
                        port_info["accessible"] = True
                except Exception as e:
                    port_info["access_error"] = str(e)
                
                # Check permissions (Unix-like systems)
                try:
                    stat_info = os.stat(port.device)
                    port_info["permissions"] = oct(stat_info.st_mode)[-3:]
                    port_info["owner"] = stat_info.st_uid
                    port_info["group"] = stat_info.st_gid
                except Exception:
                    pass
                
                ports.append(port_info)
                
        except Exception as e:
            self.logger.error(f"Error discovering serial ports: {e}")
        
        # Also check common Meshtastic device paths manually
        common_paths = [
            "/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usbserial*", 
            "/dev/tty.SLAB_USBtoUART*", "/dev/tty.wchusbserial*"
        ]
        
        for pattern in common_paths:
            for device_path in glob.glob(pattern):
                # Skip if already found
                if any(p["device"] == device_path for p in ports):
                    continue
                    
                try:
                    stat_info = os.stat(device_path)
                    port_info = {
                        "device": device_path,
                        "description": "Manual discovery",
                        "manufacturer": "Unknown",
                        "accessible": False,
                        "permissions": oct(stat_info.st_mode)[-3:],
                        "owner": stat_info.st_uid,
                        "group": stat_info.st_gid
                    }
                    
                    # Test accessibility
                    try:
                        with serial.Serial(device_path, timeout=0.1) as ser:
                            port_info["accessible"] = True
                    except Exception as e:
                        port_info["access_error"] = str(e)
                    
                    ports.append(port_info)
                except Exception:
                    continue
        
        return ports
    
    def _check_permissions(self) -> Dict[str, Any]:
        """
        Check user permissions for serial port access
        
        Returns:
            Dictionary with permission information
        """
        perm_info = {
            "dialout_group": False,
            "uucp_group": False,
            "serial_group": False,
            "recommendations": []
        }
        
        try:
            user_groups = [g.gr_name for g in grp.getgrall() 
                          if os.getenv("USER", "") in g.gr_mem]
            
            # Add primary group
            import pwd
            primary_group = grp.getgrgid(
                pwd.getpwnam(os.getenv("USER", "")).pw_gid
            ).gr_name
            if primary_group not in user_groups:
                user_groups.append(primary_group)
            
            # Check for common serial access groups
            perm_info["dialout_group"] = "dialout" in user_groups
            perm_info["uucp_group"] = "uucp" in user_groups  
            perm_info["serial_group"] = "serial" in user_groups
            
            # Generate recommendations
            if not any([perm_info["dialout_group"], perm_info["uucp_group"], 
                       perm_info["serial_group"]]):
                perm_info["recommendations"].append(
                    "Add user to dialout group: sudo usermod -a -G dialout $USER"
                )
                perm_info["recommendations"].append(
                    "Then logout and login again, or run: newgrp dialout"
                )
                
        except Exception as e:
            self.logger.debug(f"Error checking permissions: {e}")
            perm_info["error"] = str(e)
        
        return perm_info
    
    def _check_port_conflicts(self) -> Dict[str, Any]:
        """
        Check for processes that might be using serial ports
        
        Returns:
            Dictionary with conflict information
        """
        conflicts = {
            "processes_using_ports": [],
            "recommendations": []
        }
        
        try:
            # Check all available serial ports for conflicts
            ports = self._discover_serial_ports()
            
            for port_info in ports:
                device = port_info["device"]
                processes = self._get_processes_using_port(device)
                
                if processes:
                    conflicts["processes_using_ports"].append({
                        "device": device,
                        "processes": processes
                    })
                    
                    # Add recommendations
                    for proc in processes:
                        if "getty" in proc.get("command", "").lower():
                            conflicts["recommendations"].append(
                                f"Disable serial console on {device}: "
                                f"sudo systemctl disable serial-getty@{device.split('/')[-1]}.service"
                            )
                        elif "modemmanager" in proc.get("command", "").lower():
                            conflicts["recommendations"].append(
                                "Disable ModemManager: sudo systemctl disable ModemManager"
                            )
                        else:
                            conflicts["recommendations"].append(
                                f"Kill process {proc.get('pid', 'unknown')} using {device}: "
                                f"sudo kill {proc.get('pid', 'unknown')}"
                            )
                            
        except Exception as e:
            conflicts["error"] = str(e)
            self.logger.debug(f"Error checking port conflicts: {e}")
        
        return conflicts
    
    def _get_processes_using_port(self, device: str) -> List[Dict[str, Any]]:
        """
        Get list of processes using a specific serial port
        
        Args:
            device: Serial device path (e.g., /dev/ttyUSB0)
            
        Returns:
            List of process information dictionaries
        """
        processes = []
        
        try:
            # Use lsof to find processes using the device
            result = subprocess.run(
                ["lsof", device],
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
            self.logger.debug(f"lsof timeout for {device}")
        except FileNotFoundError:
            # lsof not available, try fuser
            try:
                result = subprocess.run(
                    ["fuser", device],
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
            self.logger.debug(f"Error checking processes for {device}: {e}")
        
        return processes
    
    def _check_system_services(self) -> Dict[str, Any]:
        """
        Check for system services that might interfere with serial ports
        
        Returns:
            Dictionary with service status information
        """
        services_info = {
            "problematic_services": [],
            "recommendations": []
        }
        
        # Common services that can interfere with serial ports
        problematic_services = [
            "ModemManager",
            "serial-getty@ttyUSB0.service",
            "serial-getty@ttyACM0.service", 
            "getty@ttyUSB0.service",
            "getty@ttyACM0.service"
        ]
        
        try:
            for service in problematic_services:
                status = self._get_service_status(service)
                if status["active"]:
                    services_info["problematic_services"].append({
                        "service": service,
                        "status": status
                    })
                    
                    if "modemmanager" in service.lower():
                        services_info["recommendations"].append(
                            f"Disable {service}: sudo systemctl stop {service} && "
                            f"sudo systemctl disable {service}"
                        )
                    elif "getty" in service.lower():
                        services_info["recommendations"].append(
                            f"Disable serial console {service}: sudo systemctl stop {service} && "
                            f"sudo systemctl disable {service}"
                        )
                        
        except Exception as e:
            services_info["error"] = str(e)
            self.logger.debug(f"Error checking system services: {e}")
        
        return services_info
    
    def _get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Get systemd service status
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            Dictionary with service status information
        """
        status = {
            "active": False,
            "enabled": False,
            "status": "unknown"
        }
        
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            status["active"] = result.stdout.strip() == "active"
            
            # Check if service is enabled
            result = subprocess.run(
                ["systemctl", "is-enabled", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            status["enabled"] = result.stdout.strip() == "enabled"
            status["status"] = result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            status["status"] = "timeout"
        except FileNotFoundError:
            status["status"] = "systemctl_not_found"
        except Exception as e:
            status["status"] = f"error: {e}"
            self.logger.debug(f"Error checking service {service_name}: {e}")
        
        return status
    
    def _check_lock_files(self) -> Dict[str, Any]:
        """
        Check for stale lock files that might prevent port access
        
        Returns:
            Dictionary with lock file information
        """
        lock_info = {
            "lock_files_found": [],
            "recommendations": []
        }
        
        # Common lock file locations
        lock_dirs = ["/var/lock", "/tmp", "/var/run/lock"]
        
        try:
            for lock_dir in lock_dirs:
                if not os.path.exists(lock_dir):
                    continue
                    
                # Look for serial port lock files
                lock_patterns = [
                    "LCK..tty*",
                    "LCK..USB*", 
                    "LCK..ACM*",
                    "*.lock"
                ]
                
                for pattern in lock_patterns:
                    lock_files = glob.glob(os.path.join(lock_dir, pattern))
                    
                    for lock_file in lock_files:
                        try:
                            stat_info = os.stat(lock_file)
                            age = time.time() - stat_info.st_mtime
                            
                            lock_info["lock_files_found"].append({
                                "path": lock_file,
                                "age_seconds": age,
                                "size": stat_info.st_size,
                                "stale": age > 300  # Consider stale if older than 5 minutes
                            })
                            
                            if age > 300:  # Stale lock file
                                lock_info["recommendations"].append(
                                    f"Remove stale lock file: sudo rm {lock_file}"
                                )
                                
                        except Exception as e:
                            self.logger.debug(f"Error checking lock file {lock_file}: {e}")
                            
        except Exception as e:
            lock_info["error"] = str(e)
            self.logger.debug(f"Error checking lock files: {e}")
        
        return lock_info
    
    def _test_all_ports(self) -> List[Dict[str, Any]]:
        """
        Test basic serial communication on all discovered ports
        
        Returns:
            List of test results for each port
        """
        ports = self._discover_serial_ports()
        test_results = []
        
        for port_info in ports:
            if not port_info.get("accessible", False):
                continue
                
            device = port_info["device"]
            result = {
                "device": device,
                "basic_serial": False,
                "meshtastic_compatible": False,
                "error": None
            }
            
            # Test basic serial connectivity
            try:
                with serial.Serial(device, 115200, timeout=1.0) as ser:
                    result["basic_serial"] = True
                    
                    # Try to read some data (non-blocking)
                    ser.timeout = 0.1
                    data = ser.read(100)
                    if data:
                        result["received_data"] = len(data)
                        
            except Exception as e:
                result["error"] = f"Serial test failed: {e}"
            
            # Test Meshtastic compatibility (quick test)
            if result["basic_serial"]:
                try:
                    # Very short timeout for quick test
                    interface = meshtastic.serial_interface.SerialInterface(
                        devPath=device, debugOut=None
                    )
                    
                    # Wait briefly for any response
                    start_time = time.time()
                    timeout = 2.0  # Short timeout for discovery
                    
                    while not interface.myInfo and (time.time() - start_time) < timeout:
                        time.sleep(0.1)
                    
                    if interface.myInfo:
                        result["meshtastic_compatible"] = True
                        result["node_info"] = {
                            "num": interface.myInfo.get("num"),
                            "user": interface.myInfo.get("user", {})
                        }
                    
                    interface.close()
                    
                except Exception as e:
                    result["meshtastic_error"] = f"Meshtastic test failed: {e}"
            
            test_results.append(result)
            
        return test_results
    
    def _test_meshtastic_connection(self, port: str, 
                                   timeout: float = 15.0) -> Dict[str, Any]:
        """
        Perform detailed Meshtastic connection test with advanced error handling
        
        Args:
            port: Serial port path
            timeout: Connection timeout in seconds
            
        Returns:
            Detailed connection test results
        """
        result = {
            "port": port,
            "connection_successful": False,
            "steps": [],
            "node_info": None,
            "error": None,
            "error_type": None,
            "suggested_fixes": [],
            "timing": {}
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Check port accessibility
            step_start = time.time()
            result["steps"].append("Checking port accessibility")
            
            if not os.path.exists(port):
                result["error"] = f"Port {port} does not exist"
                return result
            
            try:
                with serial.Serial(port, 115200, timeout=0.1) as ser:
                    pass
            except Exception as e:
                result["error"] = f"Cannot access port {port}: {e}"
                return result
            
            result["timing"]["port_check"] = time.time() - step_start
            result["steps"].append("✓ Port accessible")
            
            # Step 2: Create Meshtastic interface
            step_start = time.time()
            result["steps"].append("Creating Meshtastic interface")
            
            interface = meshtastic.serial_interface.SerialInterface(
                devPath=port, debugOut=None
            )
            
            result["timing"]["interface_creation"] = time.time() - step_start
            result["steps"].append("✓ Interface created")
            
            # Step 3: Wait for node information with detailed progress
            step_start = time.time()
            result["steps"].append(f"Waiting for node info (timeout: {timeout}s)")
            
            poll_interval = 0.1
            polls = 0
            max_polls = int(timeout / poll_interval)
            
            while not interface.myInfo and polls < max_polls:
                time.sleep(poll_interval)
                polls += 1
                
                # Log progress every 2 seconds
                if polls % 20 == 0:
                    elapsed = polls * poll_interval
                    result["steps"].append(f"... still waiting ({elapsed:.1f}s elapsed)")
            
            result["timing"]["info_wait"] = time.time() - step_start
            
            if interface.myInfo:
                result["connection_successful"] = True
                result["node_info"] = dict(interface.myInfo)
                result["steps"].append("✓ Node information received")
                
                # Get additional information
                if hasattr(interface, 'nodes'):
                    result["mesh_nodes"] = len(interface.nodes)
                    
                if hasattr(interface, 'channels'):
                    result["channels"] = len(interface.channels)
                    
            else:
                result["error"] = f"Timeout waiting for node information after {timeout}s"
                result["steps"].append("✗ Timeout waiting for node info")
            
            # Clean up
            interface.close()
            
        except serial.SerialException as e:
            result["error"] = f"Serial connection failed: {e}"
            result["error_type"] = "serial_error"
            result["steps"].append(f"✗ Serial Exception: {e}")
            
            # Provide specific fixes for common serial errors
            error_msg = str(e).lower()
            if "permission denied" in error_msg:
                result["suggested_fixes"].extend([
                    "Add user to dialout group: sudo usermod -a -G dialout $USER",
                    "Logout and login again, or run: newgrp dialout",
                    "Check port permissions: ls -la " + port
                ])
            elif "resource temporarily unavailable" in error_msg or "could not exclusively lock port" in error_msg:
                result["suggested_fixes"].extend([
                    "Stop ModemManager: sudo systemctl stop ModemManager",
                    "Disable serial console: sudo systemctl disable serial-getty@" + os.path.basename(port) + ".service",
                    "Check for processes using port: lsof " + port,
                    "Remove stale lock files: sudo rm /var/lock/LCK.." + os.path.basename(port),
                    "Try unplugging and reconnecting the device"
                ])
            elif "device or resource busy" in error_msg:
                result["suggested_fixes"].extend([
                    "Close other applications using the serial port",
                    "Check for multiple instances: ps aux | grep meshtastic",
                    "Restart the system if necessary"
                ])
            elif "no such file or directory" in error_msg:
                result["suggested_fixes"].extend([
                    "Check if device is connected: ls -la /dev/tty*",
                    "Try different USB port",
                    "Check USB cable (must support data, not just power)",
                    "Install USB-to-serial drivers if needed"
                ])
                
        except ImportError as e:
            result["error"] = f"Missing dependency: {e}"
            result["error_type"] = "dependency_error"
            result["steps"].append(f"✗ Import Error: {e}")
            result["suggested_fixes"].extend([
                "Install meshtastic package: pip install meshtastic",
                "Update package: pip install --upgrade meshtastic",
                "Check Python environment is correct"
            ])
            
        except Exception as e:
            result["error"] = f"Connection test failed: {e}"
            result["error_type"] = "unknown_error"
            result["steps"].append(f"✗ Exception: {e}")
            
            # Generic troubleshooting steps
            result["suggested_fixes"].extend([
                "Try restarting the Meshtastic device",
                "Check device firmware is compatible",
                "Try using official Meshtastic CLI: meshtastic --info",
                "Check system logs: dmesg | tail -20"
            ])
        
        result["timing"]["total"] = time.time() - start_time
        return result
    
    def print_diagnostic_report(self, results: Dict[str, Any]) -> None:
        """
        Print formatted diagnostic report
        
        Args:
            results: Results from run_full_diagnostic()
        """
        print("\n" + "="*60)
        print("BBMesh Meshtastic Connection Diagnostic Report")
        print("="*60)
        
        # System Information
        sys_info = results["system_info"]
        print(f"\nSystem Information:")
        print(f"  Platform: {sys_info['platform']} {sys_info['platform_release']}")
        print(f"  Python: {sys_info['python_version']}")
        print(f"  User: {sys_info['user']}")
        print(f"  Groups: {', '.join(sys_info['groups'])}")
        
        # Permissions
        perms = results["permissions"]
        print(f"\nPermissions:")
        print(f"  Dialout group: {'✓' if perms['dialout_group'] else '✗'}")
        print(f"  UUCP group: {'✓' if perms['uucp_group'] else '✗'}")
        print(f"  Serial group: {'✓' if perms['serial_group'] else '✗'}")
        
        if perms.get("recommendations"):
            print(f"  Recommendations:")
            for rec in perms["recommendations"]:
                print(f"    • {rec}")
        
        # Available Ports
        ports = results["available_ports"]
        print(f"\nDiscovered Serial Ports ({len(ports)} found):")
        for port in ports:
            status = "✓" if port.get("accessible") else "✗"
            print(f"  {status} {port['device']}")
            print(f"      Description: {port.get('description', 'Unknown')}")
            print(f"      Manufacturer: {port.get('manufacturer', 'Unknown')}")
            if port.get("permissions"):
                print(f"      Permissions: {port['permissions']}")
            if port.get("access_error"):
                print(f"      Error: {port['access_error']}")
        
        # Port Conflicts
        conflicts = results.get("port_conflicts", {})
        if conflicts.get("processes_using_ports"):
            print(f"\nPort Conflicts Detected:")
            for conflict in conflicts["processes_using_ports"]:
                print(f"  {conflict['device']}:")
                for proc in conflict["processes"]:
                    print(f"    • {proc.get('command', 'Unknown')} (PID: {proc.get('pid', 'Unknown')})")
        
        # System Services
        services = results.get("system_services", {})
        if services.get("problematic_services"):
            print(f"\nProblematic System Services:")
            for service_info in services["problematic_services"]:
                service = service_info["service"]
                status = service_info["status"]
                print(f"  • {service} - Active: {status.get('active', False)}, Enabled: {status.get('enabled', False)}")
        
        # Lock Files
        locks = results.get("lock_files", {})
        if locks.get("lock_files_found"):
            print(f"\nSerial Port Lock Files:")
            for lock in locks["lock_files_found"]:
                age_min = lock["age_seconds"] / 60
                stale_status = " (STALE)" if lock["stale"] else ""
                print(f"  • {lock['path']} - Age: {age_min:.1f}min{stale_status}")
        
        # Recommendations
        all_recommendations = []
        for section in [conflicts, services, locks]:
            all_recommendations.extend(section.get("recommendations", []))
        
        if all_recommendations:
            print(f"\nRecommended Actions:")
            for i, rec in enumerate(all_recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Port Tests
        tests = results["port_tests"]
        if tests:
            print(f"\nPort Compatibility Tests:")
            for test in tests:
                device = test["device"]
                serial_ok = "✓" if test["basic_serial"] else "✗"
                mesh_ok = "✓" if test["meshtastic_compatible"] else "✗"
                print(f"  {device}:")
                print(f"    Serial: {serial_ok}  Meshtastic: {mesh_ok}")
                if test.get("node_info"):
                    node_num = test["node_info"].get("num", "Unknown")
                    print(f"    Node ID: {node_num}")
        
        # Connection Test
        conn_test = results["connection_test"]
        if conn_test:
            print(f"\nDetailed Connection Test:")
            print(f"  Port: {conn_test['port']}")
            print(f"  Result: {'✓ SUCCESS' if conn_test['connection_successful'] else '✗ FAILED'}")
            print(f"  Total time: {conn_test['timing'].get('total', 0):.2f}s")
            
            if conn_test.get("steps"):
                print(f"  Steps:")
                for step in conn_test["steps"]:
                    print(f"    {step}")
            
            if conn_test.get("node_info"):
                node_info = conn_test["node_info"]
                print(f"  Node Information:")
                print(f"    ID: {node_info.get('num', 'Unknown')}")
                if 'user' in node_info:
                    user = node_info['user']
                    print(f"    Name: {user.get('longName', 'Unknown')}")
                    print(f"    Short: {user.get('shortName', 'Unknown')}")
            
            if conn_test.get("error"):
                print(f"  Error: {conn_test['error']}")
                
                # Show suggested fixes for the specific error
                if conn_test.get("suggested_fixes"):
                    print(f"  Suggested Fixes:")
                    for fix in conn_test["suggested_fixes"]:
                        print(f"    • {fix}")
        
        print("\n" + "="*60)

    def get_node_id_only(self, timeout: float = 10.0) -> Optional[str]:
        """
        Get only the node ID from the connected Meshtastic device
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            Node ID as string if successful, None if failed
        """
        port = self.config.meshtastic.serial.port
        self.logger.debug(f"Attempting to get node ID from {port}")
        
        # Quick pre-connection check
        if not os.path.exists(port):
            self.logger.debug(f"Port {port} does not exist")
            return None
        
        try:
            # Create Meshtastic interface with minimal setup
            interface = meshtastic.serial_interface.SerialInterface(
                devPath=port, debugOut=None
            )
            
            # Wait for node information
            start_time = time.time()
            while not interface.myInfo and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            # Extract node ID if available (looking for user.id format like "!a0cbf888")
            if interface.myInfo:
                try:
                    # Try dictionary conversion first
                    node_info = dict(interface.myInfo)
                    user_info = node_info.get('user', {})
                    node_id = user_info.get('id')
                except (TypeError, AttributeError):
                    # Fall back to attribute access
                    user_info = getattr(interface.myInfo, 'user', None)
                    if user_info:
                        node_id = getattr(user_info, 'id', None)
                    else:
                        node_id = None
                
                if node_id is not None:
                    self.logger.debug(f"Successfully extracted node ID: {node_id}")
                    interface.close()
                    return node_id
                else:
                    self.logger.debug("Node info available but no user.id found")
            else:
                self.logger.debug(f"Timeout after {timeout}s waiting for node info")
            
            interface.close()
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting node ID: {e}")
            return None


def main():
    """CLI entry point for connection testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Meshtastic device connectivity"
    )
    parser.add_argument(
        "--config", "-c", 
        type=Path,
        default="config/bbmesh.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--port", "-p",
        help="Specific port to test (overrides config)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=15.0,
        help="Connection timeout in seconds"
    )
    
    args = parser.parse_args()
    
    # Load config if available
    config = None
    if args.config.exists():
        try:
            config = Config.load(args.config)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            config = Config.create_default()
    else:
        config = Config.create_default()
    
    # Override port if specified
    if args.port:
        config.meshtastic.serial.port = args.port
    
    # Run diagnostic
    tester = ConnectionTester(config)
    results = tester.run_full_diagnostic()
    tester.print_diagnostic_report(results)


if __name__ == "__main__":
    main()