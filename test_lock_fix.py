#!/usr/bin/env python3
"""
Test script for the enhanced serial port lock detection and resolution
"""

import sys
import os
sys.path.insert(0, 'src')

from bbmesh.core.config import Config, SerialConfig, MeshtasticConfig
from bbmesh.core.meshtastic_interface import MeshtasticInterface
from bbmesh.utils.logger import BBMeshLogger

def test_exclusive_lock_detection():
    """Test the enhanced exclusive lock detection"""
    
    # Create a test configuration
    serial_config = SerialConfig(
        port="/dev/ttyUSB0",
        auto_resolve_conflicts=True,
        stop_modemmanager=True,
        stop_getty_services=True,
        remove_stale_locks=True
    )
    
    meshtastic_config = MeshtasticConfig(serial=serial_config)
    
    # Test the enhanced interface
    interface = MeshtasticInterface(meshtastic_config)
    
    print("Testing enhanced exclusive lock detection...")
    print("=" * 50)
    
    # Test exclusive lock directly
    print("1. Testing exclusive lock availability...")
    lock_available = interface._test_exclusive_lock("/dev/ttyUSB0")
    print(f"   Exclusive lock available: {lock_available}")
    
    if not lock_available:
        print("\n2. Identifying lock holders...")
        holders = interface._identify_lock_holders("/dev/ttyUSB0")
        if holders:
            for holder in holders:
                print(f"   Process: {holder.get('command', 'unknown')} (PID: {holder.get('pid', 'unknown')})")
        else:
            print("   No lock holders identified")
    
    print("\n3. Attempting full connection test...")
    success = interface._pre_connection_checks("/dev/ttyUSB0")
    print(f"   Pre-connection checks passed: {success}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_exclusive_lock_detection()