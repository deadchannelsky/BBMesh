#!/bin/bash

# TradeWars Plugin Diagnostic Script
# Run this on your Linux BBMesh system to diagnose installation issues

echo "========================================"
echo "TradeWars Plugin Diagnostic Test"
echo "========================================"
echo ""

# Test 1: Check if plugin files are installed
echo "[TEST 1] Checking if plugin files are installed..."
echo "Command: ls -la /home/jwtyler/BBMesh/src/bbmesh/plugins/tradewars*"
ls -la /home/jwtyler/BBMesh/src/bbmesh/plugins/tradewars* 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Plugin files found"
else
    echo "✗ Plugin files NOT found - installation failed"
fi
echo ""

# Test 2: Check builtin.py for TradeWarsPlugin import
echo "[TEST 2] Checking builtin.py for TradeWarsPlugin import..."
echo "Command: grep -n 'from .tradewars_plugin import' /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py"
grep -n "from .tradewars_plugin import" /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py
if [ $? -eq 0 ]; then
    echo "✓ Import statement found"
else
    echo "✗ Import statement NOT found in builtin.py"
fi
echo ""

# Test 3: Check builtin.py for BUILTIN_PLUGINS registry entry
echo "[TEST 3] Checking builtin.py for BUILTIN_PLUGINS registry..."
echo "Command: grep -n '\"tradewars\": TradeWarsPlugin' /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py"
grep -n '"tradewars": TradeWarsPlugin' /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py
if [ $? -eq 0 ]; then
    echo "✓ Registry entry found"
else
    echo "✗ Registry entry NOT found in builtin.py"
fi
echo ""

# Test 4: Try to import the plugin directly
echo "[TEST 4] Attempting direct Python import..."
echo "Command: cd /home/jwtyler/BBMesh && python3 -c \"from src.bbmesh.plugins.tradewars_plugin import TradeWarsPlugin; print('✓ Import successful')\""
cd /home/jwtyler/BBMesh
python3 -c "from src.bbmesh.plugins.tradewars_plugin import TradeWarsPlugin; print('✓ Import successful')" 2>&1
if [ $? -ne 0 ]; then
    echo "✗ Import failed - see error above"
fi
echo ""

# Test 5: Show the actual BUILTIN_PLUGINS dictionary
echo "[TEST 5] Showing current BUILTIN_PLUGINS dictionary..."
echo "Command: grep -A 15 'BUILTIN_PLUGINS = {' /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py | head -20"
grep -A 15 'BUILTIN_PLUGINS = {' /home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py | head -20
echo ""

echo "========================================"
echo "Diagnostic Complete"
echo "========================================"
