#!/usr/bin/env python3
"""
BBMesh TradeWars Plugin Installer

This script installs the TradeWars space trading game plugin into an existing BBMesh installation.
It updates configuration files and registers the plugin with BBMesh.
"""

import os
import sys
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any


class TradeWarsPluginInstaller:
    """Handles installation of the TradeWars plugin into BBMesh"""

    def __init__(self, bbmesh_root: str = None):
        """Initialize installer with optional BBMesh root path"""
        # Auto-detect BBMesh root or use provided path
        if bbmesh_root:
            self.bbmesh_root = Path(bbmesh_root)
        else:
            # Try to find BBMesh root by looking for characteristic files
            current = Path.cwd()
            while current != current.parent:
                if (current / "src" / "bbmesh").exists() and (current / "config" / "bbmesh.yaml").exists():
                    self.bbmesh_root = current
                    break
                current = current.parent
            else:
                raise RuntimeError("Could not find BBMesh root directory. Please specify path.")

        # Define paths
        self.config_dir = self.bbmesh_root / "config"
        self.plugins_dir = self.bbmesh_root / "src" / "bbmesh" / "plugins"
        self.data_dir = self.bbmesh_root / "data"

        # Plugin source directory
        self.plugin_dir = Path(__file__).parent

        print(f"BBMesh root: {self.bbmesh_root}")
        print(f"Plugin directory: {self.plugin_dir}")

    def validate_bbmesh_installation(self) -> bool:
        """Validate that this is a proper BBMesh installation"""
        required_files = [
            self.config_dir / "bbmesh.yaml",
            self.config_dir / "plugins.yaml",
            self.config_dir / "menus.yaml",
            self.plugins_dir / "builtin.py",
            self.plugins_dir / "base.py"
        ]

        for file_path in required_files:
            if not file_path.exists():
                print(f"Missing required file: {file_path}")
                return False

        print("BBMesh installation validated")
        return True

    def backup_config_files(self) -> None:
        """Create backups of configuration files before modification"""
        config_files = ["bbmesh.yaml", "plugins.yaml", "menus.yaml"]
        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for config_file in config_files:
            source = self.config_dir / config_file
            backup = backup_dir / f"{config_file}.backup_{timestamp}"

            if source.exists():
                shutil.copy2(source, backup)
                print(f"Backed up {config_file}")

    def install_plugin_files(self) -> None:
        """Copy plugin files to BBMesh plugins directory"""
        # Copy main plugin file to BBMesh plugins directory
        source_plugin = self.plugin_dir / "tradewars_plugin.py"
        dest_plugin = self.plugins_dir / "tradewars_plugin.py"

        if source_plugin.exists():
            shutil.copy2(source_plugin, dest_plugin)
            print(f"Installed plugin file: {dest_plugin.name}")
        else:
            raise FileNotFoundError(f"Plugin file not found: {source_plugin}")

        # Copy supporting modules
        modules = ["storage.py", "universe.py", "trade_calculator.py", "formatters.py"]
        for module in modules:
            source = self.plugin_dir / module
            dest = self.plugins_dir / f"tradewars_{module}"

            if source.exists():
                shutil.copy2(source, dest)
                print(f"Installed module: {dest.name}")

        # Create data directory for game state
        self.data_dir.mkdir(exist_ok=True)
        tradewars_data_dir = self.data_dir / "tradewars"
        tradewars_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created data directory: {tradewars_data_dir}")

    def update_plugins_config(self) -> None:
        """Update plugins.yaml with TradeWars configuration"""
        plugins_file = self.config_dir / "plugins.yaml"

        # Load existing configuration
        with open(plugins_file, 'r') as f:
            config = yaml.safe_load(f)

        # Add TradeWars plugin configuration
        tradewars_config = {
            'enabled': True,
            'description': 'TradeWars - Classic space trading game for mesh networks',
            'timeout': 120,
            'database_path': 'data/tradewars/tradewars.db',
            'universe_seed': None,
            'starting_credits': 10000,
            'starting_turns': 1000,
            'max_cargo_holds': 20,
            'total_sectors': 100,
            'total_ports': 30
        }

        # Add to plugins configuration
        if 'plugins' not in config:
            config['plugins'] = {}

        config['plugins']['tradewars'] = tradewars_config

        # Write updated configuration
        with open(plugins_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print("Updated plugins.yaml with TradeWars configuration")

    def update_menus_config(self) -> None:
        """Update menus.yaml with TradeWars menu entries"""
        menus_file = self.config_dir / "menus.yaml"

        # Load existing configuration
        with open(menus_file, 'r') as f:
            config = yaml.safe_load(f)

        # Add TradeWars entry to main menu
        if 'menus' not in config:
            config['menus'] = {}

        if 'main' not in config['menus']:
            config['menus']['main'] = {'title': 'BBMesh Main Menu', 'options': {}}

        main_options = config['menus']['main'].get('options', {})

        # Check if tradewars plugin entry already exists in main menu
        tradewars_exists = any(
            item.get('plugin') == 'tradewars'
            for item in main_options.values()
        )

        if not tradewars_exists:
            # Find next available slot in main menu
            next_slot = max([int(k) for k in main_options.keys() if str(k).isdigit()] + [0]) + 1

            # Add TradeWars entry
            main_options[str(next_slot)] = {
                'title': 'TradeWars',
                'action': 'run_plugin',
                'plugin': 'tradewars',
                'description': 'Space trading game'
            }

            config['menus']['main']['options'] = main_options
            print("Added TradeWars to main menu")
        else:
            print("TradeWars entry already exists in main menu")

        # Write updated configuration
        with open(menus_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print("Menu configuration updated")

    def update_bbmesh_config(self) -> None:
        """Update main BBMesh configuration to include tradewars in enabled plugins"""
        bbmesh_config_file = self.config_dir / "bbmesh.yaml"

        with open(bbmesh_config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Add tradewars to enabled plugins if not already there
        if 'plugins' not in config:
            config['plugins'] = {}

        if 'enabled_plugins' not in config['plugins']:
            config['plugins']['enabled_plugins'] = []

        enabled_plugins = config['plugins']['enabled_plugins']

        if 'tradewars' not in enabled_plugins:
            enabled_plugins.append('tradewars')

            with open(bbmesh_config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            print("Added tradewars to enabled plugins in bbmesh.yaml")
        else:
            print("TradeWars already in enabled plugins")

    def register_plugin(self) -> None:
        """Register plugin in BBMesh builtin plugins registry"""
        builtin_file = self.plugins_dir / "builtin.py"

        with open(builtin_file, 'r') as f:
            lines = f.readlines()

        # Check if import already exists
        import_exists = any('from .tradewars_plugin import TradeWarsPlugin' in line for line in lines)
        registry_exists = any('"tradewars": TradeWarsPlugin' in line for line in lines)

        if import_exists and registry_exists:
            print("Plugin already registered in builtin.py")
            return

        # Add import if missing
        if not import_exists:
            # Find last import line
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('from .') or line.strip().startswith('import '):
                    last_import_idx = i

            import_line = "from .tradewars_plugin import TradeWarsPlugin\n"
            lines.insert(last_import_idx + 1, import_line)
            print("Added TradeWarsPlugin import")

        # Add registry entry if missing
        if not registry_exists:
            # Find BUILTIN_PLUGINS dict closing brace
            for i, line in enumerate(lines):
                if 'BUILTIN_PLUGINS = {' in line:
                    # Find closing brace
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() == '}':
                            registry_line = '    "tradewars": TradeWarsPlugin,\n'
                            lines.insert(j, registry_line)
                            print("Added TradeWarsPlugin to BUILTIN_PLUGINS registry")
                            break
                    break

        # Write updated file
        with open(builtin_file, 'w') as f:
            f.writelines(lines)

    def install(self) -> None:
        """Perform complete installation of TradeWars plugin"""
        print("Installing BBMesh TradeWars Plugin...")
        print("=" * 60)

        try:
            # Validate BBMesh installation
            if not self.validate_bbmesh_installation():
                raise RuntimeError("Invalid BBMesh installation")

            # Create backups
            print("\nCreating configuration backups...")
            self.backup_config_files()

            # Install plugin files
            print("\nInstalling plugin files...")
            self.install_plugin_files()

            # Update configurations
            print("\nUpdating configurations...")
            self.update_plugins_config()
            self.update_menus_config()
            self.update_bbmesh_config()

            # Register plugin
            print("\nRegistering plugin...")
            self.register_plugin()

            print("\n" + "=" * 60)
            print("Installation completed successfully!")
            print("\nTradeWars Plugin Installation Summary:")
            print("  • Plugin files installed to BBMesh plugins directory")
            print("  • Configuration updated with TradeWars settings")
            print("  • Menu entries added for TradeWars access")
            print("  • Plugin registered in BBMesh plugin system")
            print("\nPlease restart BBMesh to activate TradeWars.")
            print("Access via main menu: 'TradeWars' option")

        except Exception as e:
            print(f"\nInstallation failed: {e}")
            print("Configuration backups are available in config/backups/")
            sys.exit(1)

    def uninstall(self) -> None:
        """Remove TradeWars plugin from BBMesh"""
        print("Uninstalling BBMesh TradeWars Plugin...")

        # Remove plugin files
        files_to_remove = [
            self.plugins_dir / "tradewars_plugin.py",
            self.plugins_dir / "tradewars_storage.py",
            self.plugins_dir / "tradewars_universe.py",
            self.plugins_dir / "tradewars_trade_calculator.py",
            self.plugins_dir / "tradewars_formatters.py",
        ]

        for plugin_file in files_to_remove:
            if plugin_file.exists():
                plugin_file.unlink()
                print(f"Removed {plugin_file.name}")

        print("Configuration entries left intact for safety.")
        print("Manually remove 'tradewars' from config files if desired.")
        print("Uninstallation completed")


def main():
    """Main installation script"""
    import argparse

    parser = argparse.ArgumentParser(description='BBMesh TradeWars Plugin Installer')
    parser.add_argument('--bbmesh-root', help='Path to BBMesh installation root')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall the plugin')

    args = parser.parse_args()

    try:
        installer = TradeWarsPluginInstaller(args.bbmesh_root)

        if args.uninstall:
            installer.uninstall()
        else:
            installer.install()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
