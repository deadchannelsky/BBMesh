#!/usr/bin/env python3
"""
BBMesh Bulletin Board System Plugin Installer

This script installs the bulletin board plugin into an existing BBMesh installation.
It updates configuration files and sets up the plugin for use.
"""

import os
import sys
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any


class BulletinPluginInstaller:
    """Handles installation of the bulletin board plugin into BBMesh"""
    
    def __init__(self, bbmesh_root: str = None):
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
        
        # Plugin paths
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
                print(f"❌ Missing required file: {file_path}")
                return False
        
        print("✅ BBMesh installation validated")
        return True
    
    def backup_config_files(self) -> None:
        """Create backups of configuration files before modification"""
        config_files = ["plugins.yaml", "menus.yaml"]
        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for config_file in config_files:
            source = self.config_dir / config_file
            backup = backup_dir / f"{config_file}.backup_{timestamp}"
            
            if source.exists():
                shutil.copy2(source, backup)
                print(f"📄 Backed up {config_file} to {backup.name}")
    
    def install_plugin_files(self) -> None:
        """Copy plugin files to BBMesh plugins directory"""
        # Copy main plugin file to BBMesh plugins directory
        source_plugin = self.plugin_dir / "bulletin_plugin.py"
        dest_plugin = self.plugins_dir / "bulletin_board.py"
        
        if source_plugin.exists():
            shutil.copy2(source_plugin, dest_plugin)
            print(f"📦 Installed plugin file: {dest_plugin.name}")
        else:
            raise FileNotFoundError(f"Plugin file not found: {source_plugin}")
        
        # Create data directory for bulletin storage
        bulletin_data_dir = self.data_dir / "bulletin_system"
        bulletin_data_dir.mkdir(exist_ok=True)
        print(f"📁 Created data directory: {bulletin_data_dir}")
    
    def update_plugins_config(self) -> None:
        """Update plugins.yaml with bulletin system configuration"""
        plugins_file = self.config_dir / "plugins.yaml"
        
        # Load existing configuration
        with open(plugins_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Add bulletin system plugin configuration
        bulletin_config = {
            'enabled': True,
            'description': 'Community bulletin board system for mesh networks',
            'timeout': 60,
            'database_path': 'data/bulletin_system/bulletins.db',
            'max_bulletins_per_user': 50,
            'max_bulletin_length': 500,
            'categories': [
                {'name': 'General', 'description': 'General community discussions', 'max_bulletins': 200},
                {'name': 'Announcements', 'description': 'Official announcements and news', 'max_bulletins': 100},
                {'name': 'Emergency', 'description': 'Emergency communications and alerts', 'max_bulletins': 50},
                {'name': 'Community', 'description': 'Community events and activities', 'max_bulletins': 150},
                {'name': 'Technical', 'description': 'Technical discussions and support', 'max_bulletins': 100}
            ],
            'admin_users': [],
            'moderator_users': [],
            'auto_expire_days': 30,
            'allow_anonymous': True,
            'require_approval': False,
            'bulletins_per_page': 10,
            'max_search_results': 50,
            'show_bulletin_ids': True,
            'show_timestamps': True,
            'show_author_info': True,
            'max_posts_per_hour': 5,
            'max_posts_per_day': 20
        }
        
        # Add to plugins configuration
        if 'plugins' not in config:
            config['plugins'] = {}
        
        config['plugins']['bulletin_system'] = bulletin_config
        
        # Write updated configuration
        with open(plugins_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print("✅ Updated plugins.yaml with bulletin system configuration")
    
    def update_menus_config(self) -> None:
        """Update menus.yaml with bulletin system menu entries"""
        menus_file = self.config_dir / "menus.yaml"
        
        # Load existing configuration
        with open(menus_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Add bulletin board entry to main menu
        if 'menus' not in config:
            config['menus'] = {}
        
        if 'main' not in config['menus']:
            config['menus']['main'] = {'title': 'BBMesh Main Menu', 'options': {}}
        
        # Find next available slot in main menu
        main_options = config['menus']['main'].get('options', {})
        next_slot = max([int(k) for k in main_options.keys() if str(k).isdigit()] + [0]) + 1
        
        # Add bulletin board entry
        main_options[str(next_slot)] = {
            'title': 'Bulletin Board',
            'action': 'run_plugin',
            'plugin': 'bulletin_system',
            'description': 'Community bulletin board system'
        }
        
        config['menus']['main']['options'] = main_options
        
        # Add bulletin management to utilities menu if it exists
        if 'utilities' in config['menus']:
            util_options = config['menus']['utilities'].get('options', {})
            next_util_slot = max([int(k) for k in util_options.keys() if str(k).isdigit()] + [0]) + 1
            
            util_options[str(next_util_slot)] = {
                'title': 'Bulletin Management',
                'action': 'run_plugin',
                'plugin': 'bulletin_admin', 
                'description': 'Manage bulletin board system'
            }
            
            config['menus']['utilities']['options'] = util_options
        
        # Write updated configuration
        with open(menus_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print("✅ Updated menus.yaml with bulletin system menu entries")
    
    def update_bbmesh_config(self) -> None:
        """Update main BBMesh configuration to include bulletin plugin"""
        bbmesh_config_file = self.config_dir / "bbmesh.yaml"
        
        with open(bbmesh_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Add bulletin_system to enabled plugins if not already there
        if 'plugins' in config and 'enabled_plugins' in config['plugins']:
            enabled_plugins = config['plugins']['enabled_plugins']
            if 'bulletin_system' not in enabled_plugins:
                enabled_plugins.append('bulletin_system')
                
                with open(bbmesh_config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                print("✅ Added bulletin_system to enabled plugins in bbmesh.yaml")
    
    def register_plugin(self) -> None:
        """Register plugin in BBMesh builtin plugins registry"""
        builtin_file = self.plugins_dir / "builtin.py"
        
        # Read the current builtin.py file
        with open(builtin_file, 'r') as f:
            content = f.read()
        
        # Check if bulletin plugin import already exists
        if 'from .bulletin_board import BulletinBoardPlugin' not in content:
            # Add import after existing imports
            import_line = "from .bulletin_board import BulletinBoardPlugin\n"
            
            # Find the last import line
            lines = content.split('\n')
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith('from .') or line.startswith('import '):
                    import_index = i
            
            # Insert the import
            lines.insert(import_index + 1, import_line.rstrip())
            
            # Add to BUILTIN_PLUGINS registry
            registry_line = '    "bulletin_system": BulletinBoardPlugin,'
            
            # Find BUILTIN_PLUGINS dictionary
            for i, line in enumerate(lines):
                if 'BUILTIN_PLUGINS = {' in line:
                    # Find the closing brace
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() == '}':
                            lines.insert(j, registry_line)
                            break
                    break
            
            # Write updated file
            with open(builtin_file, 'w') as f:
                f.write('\n'.join(lines))
            
            print("✅ Registered plugin in BBMesh builtin plugins registry")
    
    def install(self) -> None:
        """Perform complete installation of bulletin board plugin"""
        print("🚀 Installing BBMesh Bulletin Board System Plugin...")
        print("=" * 60)
        
        try:
            # Validate BBMesh installation
            if not self.validate_bbmesh_installation():
                raise RuntimeError("Invalid BBMesh installation")
            
            # Create backups
            print("\n📄 Creating configuration backups...")
            self.backup_config_files()
            
            # Install plugin files
            print("\n📦 Installing plugin files...")
            self.install_plugin_files()
            
            # Update configurations
            print("\n⚙️ Updating configurations...")
            self.update_plugins_config()
            self.update_menus_config()
            self.update_bbmesh_config()
            
            # Register plugin
            print("\n🔧 Registering plugin...")
            self.register_plugin()
            
            print("\n✅ Installation completed successfully!")
            print("\n" + "=" * 60)
            print("📋 Bulletin Board System Plugin Installation Summary:")
            print("   • Plugin files installed to BBMesh plugins directory")
            print("   • Configuration files updated with bulletin system settings")  
            print("   • Menu entries added for bulletin board access")
            print("   • Plugin registered in BBMesh plugin system")
            print("\n🔄 Please restart BBMesh to activate the bulletin board system.")
            print("📖 Access via main menu: 'Bulletin Board' option")
            
        except Exception as e:
            print(f"\n❌ Installation failed: {e}")
            print("🔄 Please check the error and try again.")
            print("📄 Configuration backups are available in config/backups/")
            sys.exit(1)
    
    def uninstall(self) -> None:
        """Remove bulletin board plugin from BBMesh"""
        print("🗑️ Uninstalling BBMesh Bulletin Board System Plugin...")
        
        # Remove plugin file
        plugin_file = self.plugins_dir / "bulletin_board.py"
        if plugin_file.exists():
            plugin_file.unlink()
            print("🗑️ Removed plugin file")
        
        # Note: We don't automatically remove config entries to avoid breaking
        # existing configurations. User should manually clean up if desired.
        print("⚠️ Configuration entries left intact for safety.")
        print("   Manually remove 'bulletin_system' from config files if desired.")
        print("✅ Uninstallation completed")


def main():
    """Main installation script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BBMesh Bulletin Board Plugin Installer')
    parser.add_argument('--bbmesh-root', help='Path to BBMesh installation root')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall the plugin')
    parser.add_argument('--dev', action='store_true', help='Development installation')
    
    args = parser.parse_args()
    
    try:
        installer = BulletinPluginInstaller(args.bbmesh_root)
        
        if args.uninstall:
            installer.uninstall()
        else:
            installer.install()
            
            if args.dev:
                print("\n🔧 Development mode: Plugin installed for testing")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()