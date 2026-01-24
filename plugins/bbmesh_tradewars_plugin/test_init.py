#!/usr/bin/env python3
"""
TradeWars Plugin Initialization Test

This script attempts to instantiate and initialize the TradeWarsPlugin
to identify the actual error causing "Plugin 'tradewars' not available."
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, '/home/jwtyler/BBMesh/src')

print("=" * 60)
print("TradeWars Plugin Initialization Test")
print("=" * 60)
print()

# Test 1: Import the plugin
print("[TEST 1] Importing TradeWarsPlugin...")
try:
    from bbmesh.plugins.tradewars_plugin import TradeWarsPlugin
    print("✓ Import successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# Test 2: Check data directory
print("[TEST 2] Checking data directory...")
data_dir = Path("/home/jwtyler/BBMesh/data/tradewars")
if data_dir.exists():
    print(f"✓ Data directory exists: {data_dir}")
else:
    print(f"✗ Data directory does NOT exist: {data_dir}")
    print("  Creating it now...")
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {data_dir}")
    except Exception as e:
        print(f"✗ Failed to create: {e}")

print()

# Test 3: Instantiate the plugin
print("[TEST 3] Instantiating TradeWarsPlugin...")
config = {
    "enabled": True,
    "description": "TradeWars space trading game",
    "timeout": 120,
    "database_path": "/home/jwtyler/BBMesh/data/tradewars/tradewars.db"
}

try:
    plugin = TradeWarsPlugin(name="tradewars", config=config)
    print(f"✓ Plugin instantiated: {plugin}")
    print(f"  Name: {plugin.name}")
    print(f"  Description: {plugin.description}")
except Exception as e:
    print(f"✗ Instantiation failed: {e}")
    print()
    print("FULL TRACEBACK:")
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Initialize the plugin
print("[TEST 4] Initializing TradeWarsPlugin...")
try:
    result = plugin.initialize()
    if result:
        print(f"✓ Plugin initialized successfully")
    else:
        print(f"✗ Plugin.initialize() returned False")
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    print()
    print("FULL TRACEBACK:")
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: Check plugin status
print("[TEST 5] Checking plugin status...")
try:
    enabled = plugin.is_enabled()
    print(f"✓ Plugin enabled: {enabled}")
    print(f"✓ Plugin timeout: {plugin.timeout}")
    print(f"✓ Storage connected: {plugin.storage is not None}")
    print(f"✓ Universe initialized: {plugin.storage.get_state('universe_initialized')}")
except Exception as e:
    print(f"✗ Status check failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✓ ALL TESTS PASSED")
print("=" * 60)
print()
print("The plugin can be instantiated and initialized successfully.")
print("If you're still seeing 'Plugin not available' in BBMesh,")
print("the issue may be with plugin discovery or configuration loading.")
