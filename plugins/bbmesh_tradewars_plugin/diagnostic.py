#!/usr/bin/env python3
"""
TradeWars Plugin Diagnostic Tool

Run this on your Linux BBMesh system to diagnose installation issues.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_test(test_num, description, command_str, check_func=None):
    """Run a single diagnostic test"""
    print(f"\n[TEST {test_num}] {description}")
    print(f"Command: {command_str}")
    print("-" * 60)

    if check_func:
        result = check_func()
        return result
    return True


def test_1_plugin_files():
    """Check if plugin files are installed"""
    plugin_dir = Path("/home/jwtyler/BBMesh/src/bbmesh/plugins")
    files_to_check = [
        "tradewars_plugin.py",
        "tradewars_storage.py",
        "tradewars_universe.py",
        "tradewars_trade_calculator.py",
        "tradewars_formatters.py"
    ]

    found = []
    missing = []

    for filename in files_to_check:
        filepath = plugin_dir / filename
        if filepath.exists():
            found.append(filename)
            print(f"✓ {filename}")
        else:
            missing.append(filename)
            print(f"✗ {filename} MISSING")

    if missing:
        print(f"\n✗ Missing files: {', '.join(missing)}")
        return False
    else:
        print(f"\n✓ All plugin files found")
        return True


def test_2_builtin_import():
    """Check for TradeWarsPlugin import in builtin.py"""
    builtin_file = Path("/home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py")

    if not builtin_file.exists():
        print("✗ builtin.py not found")
        return False

    with open(builtin_file, 'r') as f:
        content = f.read()

    if 'from .tradewars_plugin import TradeWarsPlugin' in content:
        print("✓ Import statement found in builtin.py")
        # Show the line
        for i, line in enumerate(content.split('\n'), 1):
            if 'from .tradewars_plugin import' in line:
                print(f"  Line {i}: {line}")
        return True
    else:
        print("✗ Import statement NOT found in builtin.py")
        return False


def test_3_builtin_registry():
    """Check for tradewars in BUILTIN_PLUGINS registry"""
    builtin_file = Path("/home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py")

    if not builtin_file.exists():
        print("✗ builtin.py not found")
        return False

    with open(builtin_file, 'r') as f:
        content = f.read()

    if '"tradewars": TradeWarsPlugin' in content:
        print("✓ Registry entry found in BUILTIN_PLUGINS")
        # Show the line
        for i, line in enumerate(content.split('\n'), 1):
            if '"tradewars": TradeWarsPlugin' in line:
                print(f"  Line {i}: {line}")
        return True
    else:
        print("✗ Registry entry NOT found in BUILTIN_PLUGINS")
        return False


def test_4_direct_import():
    """Try to import the plugin directly"""
    try:
        sys.path.insert(0, '/home/jwtyler/BBMesh/src')
        from bbmesh.plugins.tradewars_plugin import TradeWarsPlugin
        print("✓ Direct Python import successful")
        print(f"  TradeWarsPlugin class: {TradeWarsPlugin}")
        return True
    except Exception as e:
        print(f"✗ Direct Python import FAILED")
        print(f"  Error: {type(e).__name__}: {e}")
        import traceback
        print("\n  Full traceback:")
        traceback.print_exc()
        return False


def test_5_builtin_plugins_dict():
    """Show the BUILTIN_PLUGINS dictionary"""
    builtin_file = Path("/home/jwtyler/BBMesh/src/bbmesh/plugins/builtin.py")

    if not builtin_file.exists():
        print("✗ builtin.py not found")
        return False

    with open(builtin_file, 'r') as f:
        lines = f.readlines()

    # Find BUILTIN_PLUGINS dictionary
    in_dict = False
    dict_lines = []

    for i, line in enumerate(lines):
        if 'BUILTIN_PLUGINS = {' in line:
            in_dict = True

        if in_dict:
            dict_lines.append((i + 1, line.rstrip()))
            if line.strip() == '}':
                break

    if dict_lines:
        print("Current BUILTIN_PLUGINS dictionary:")
        for line_num, line_text in dict_lines[:20]:  # Show first 20 lines
            print(f"  {line_num:3d}: {line_text}")

        # Check if tradewars is in there
        if any('tradewars' in line for _, line in dict_lines):
            print("\n✓ 'tradewars' entry found in BUILTIN_PLUGINS")
            return True
        else:
            print("\n✗ 'tradewars' entry NOT found in BUILTIN_PLUGINS")
            return False
    else:
        print("✗ Could not find BUILTIN_PLUGINS dictionary")
        return False


def main():
    """Run all diagnostic tests"""
    print("=" * 60)
    print("TradeWars Plugin Diagnostic Tool")
    print("=" * 60)

    results = []

    # Run all tests
    results.append(("Plugin Files", run_test(1, "Checking if plugin files are installed", "ls -la", test_1_plugin_files)))
    results.append(("Import Statement", run_test(2, "Checking builtin.py for TradeWarsPlugin import", "grep -n 'from .tradewars_plugin'", test_2_builtin_import)))
    results.append(("Registry Entry", run_test(3, "Checking builtin.py for BUILTIN_PLUGINS registry", "grep -n '\"tradewars\": TradeWarsPlugin'", test_3_builtin_registry)))
    results.append(("Direct Import", run_test(4, "Attempting direct Python import", "python3 -c 'from src.bbmesh.plugins.tradewars_plugin import TradeWarsPlugin'", test_4_direct_import)))
    results.append(("Dictionary", run_test(5, "Showing current BUILTIN_PLUGINS dictionary", "grep -A 15 'BUILTIN_PLUGINS'", test_5_builtin_plugins_dict)))

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✓ All tests passed! TradeWars plugin is properly installed.")
        return 0
    else:
        print("\n✗ Some tests failed. See details above.")
        print("\nNext steps:")
        print("1. Review the failed tests above")
        print("2. Run the installer again: python3 plugins/bbmesh_tradewars_plugin/install.py")
        print("3. Run this diagnostic again to verify")
        return 1


if __name__ == "__main__":
    sys.exit(main())
