"""
Hierarchical menu system for BBMesh
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml

from ..core.config import MenuConfig
from ..utils.logger import BBMeshLogger


class MenuItem:
    """Represents a single menu item"""
    
    def __init__(self, title: str, action: str, **kwargs):
        self.title = title
        self.action = action
        self.description = kwargs.get("description", "")
        self.target = kwargs.get("target", "")
        self.plugin = kwargs.get("plugin", "")
        self.enabled = kwargs.get("enabled", True)


class Menu:
    """Represents a menu with items"""
    
    def __init__(self, name: str, title: str, description: str = "", parent: str = None):
        self.name = name
        self.title = title
        self.description = description
        self.parent = parent
        self.items: Dict[str, MenuItem] = {}
    
    def add_item(self, key: str, item: MenuItem) -> None:
        """Add an item to the menu"""
        self.items[key] = item
    
    def get_item(self, key: str) -> Optional[MenuItem]:
        """Get a menu item by key"""
        return self.items.get(key)
    
    def get_display_text(self, show_descriptions: bool = False) -> str:
        """Generate display text for the menu"""
        lines = [f"{self.title}"]
        
        if self.description:
            lines.append(f"{self.description}")
        
        lines.append("")  # Empty line
        
        # Sort items by key for consistent display (numeric when possible, alphabetic fallback)
        def sort_key(item):
            """Custom sorting function that handles numeric menu keys properly"""
            key = item[0]
            try:
                # Try to convert to integer for proper numeric sorting
                return (0, int(key))
            except ValueError:
                # Fall back to string sorting for non-numeric keys
                return (1, key)
        
        sorted_items = sorted(self.items.items(), key=sort_key)
        
        for key, item in sorted_items:
            if not item.enabled:
                continue
                
            line = f"{key}. {item.title}"
            
            if show_descriptions and item.description:
                line += f" - {item.description}"
            
            lines.append(line)
        
        lines.append("")
        lines.append("Send option number or name")
        
        return "\n".join(lines)


class MenuSystem:
    """
    Hierarchical menu system manager
    """
    
    def __init__(self, config: MenuConfig):
        self.config = config
        self.logger = BBMeshLogger(__name__)
        self.menus: Dict[str, Menu] = {}
        self.settings: Dict[str, Any] = {}
        
        # Load menu configuration
        self._load_menu_config()
    
    def _load_menu_config(self) -> None:
        """Load menu configuration from YAML file"""
        try:
            menu_file = Path(self.config.menu_file)
            if not menu_file.exists():
                self.logger.warning(f"Menu file not found: {menu_file}")
                self._create_default_menus()
                return
            
            with open(menu_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Load settings
            self.settings = data.get("settings", {})
            
            # Load menus
            menus_data = data.get("menus", {})
            for menu_name, menu_data in menus_data.items():
                self._create_menu(menu_name, menu_data)
            
            self.logger.info(f"Loaded {len(self.menus)} menus from configuration")
            
        except Exception as e:
            self.logger.error(f"Error loading menu configuration: {e}")
            self._create_default_menus()
    
    def _create_menu(self, name: str, data: Dict[str, Any]) -> None:
        """Create a menu from configuration data"""
        menu = Menu(
            name=name,
            title=data.get("title", name.title()),
            description=data.get("description", ""),
            parent=data.get("parent")
        )
        
        # Add menu items
        options = data.get("options", {})
        for key, item_data in options.items():
            # Extract only the specific fields to avoid duplicate keyword arguments
            item = MenuItem(
                title=item_data.get("title", f"Option {key}"),
                action=item_data.get("action", "show_message"),
                description=item_data.get("description", ""),
                target=item_data.get("target", ""),
                plugin=item_data.get("plugin", ""),
                enabled=item_data.get("enabled", True)
            )
            menu.add_item(str(key), item)
        
        self.menus[name] = menu
    
    def _create_default_menus(self) -> None:
        """Create basic default menus if configuration is not available"""
        # Main menu
        main_menu = Menu("main", "BBMesh Main Menu", "Welcome to the BBMesh BBS")
        main_menu.add_item("1", MenuItem("Help & Commands", "show_help"))
        main_menu.add_item("2", MenuItem("System Status", "show_status"))
        main_menu.add_item("3", MenuItem("Time & Date", "show_time"))
        main_menu.add_item("4", MenuItem("Mesh Info", "show_mesh_info"))
        
        self.menus["main"] = main_menu
        
        self.logger.info("Created default menu system")
    
    def get_menu(self, name: str) -> Optional[Menu]:
        """Get a menu by name"""
        return self.menus.get(name)
    
    def get_menu_display(self, menu_name: str) -> str:
        """Get display text for a menu"""
        menu = self.get_menu(menu_name)
        if not menu:
            return f"Menu '{menu_name}' not found"
        
        show_descriptions = self.settings.get("show_descriptions", False)
        return menu.get_display_text(show_descriptions)
    
    def process_menu_input(self, menu_name: str, user_input: str) -> Dict[str, Any]:
        """
        Process user input for a menu
        
        Args:
            menu_name: Current menu name
            user_input: User's input/selection
            
        Returns:
            Dictionary with action information
        """
        menu = self.get_menu(menu_name)
        if not menu:
            return {
                "action": "error",
                "message": f"Menu '{menu_name}' not found"
            }
        
        # Normalize input
        input_key = user_input.strip().lower()
        
        # Check for special navigation commands
        back_commands = self.settings.get("back_commands", ["back", "b", ".."])
        home_commands = self.settings.get("home_commands", ["home", "main", "menu"])
        help_commands = self.settings.get("help_commands", ["help", "h", "?"])
        
        if input_key in back_commands:
            if menu.parent:
                return {
                    "action": "goto_menu",
                    "target": menu.parent
                }
            else:
                return {
                    "action": "show_message",
                    "message": "Already at top level menu"
                }
        
        elif input_key in home_commands:
            return {
                "action": "goto_menu",
                "target": "main"
            }
        
        elif input_key in help_commands:
            return {
                "action": "show_help"
            }
        
        # Look for menu item by number or partial name match
        selected_item = None
        
        # Try exact key match first
        if input_key in menu.items:
            selected_item = menu.items[input_key]
        else:
            # Try partial name matching
            for key, item in menu.items.items():
                if item.title.lower().startswith(input_key):
                    selected_item = item
                    break
        
        if not selected_item:
            return {
                "action": "show_current_menu",
                "message": "Please enter a valid option."
            }
        
        if not selected_item.enabled:
            return {
                "action": "show_current_menu",
                "message": "That option is currently disabled."
            }
        
        # Return the item's action
        result = {
            "action": selected_item.action,
            "title": selected_item.title
        }
        
        if selected_item.target:
            result["target"] = selected_item.target
        
        if selected_item.plugin:
            result["plugin"] = selected_item.plugin
        
        return result
    
    def get_menu_path(self, menu_name: str) -> List[str]:
        """
        Get the path from root to the specified menu
        
        Args:
            menu_name: Menu name
            
        Returns:
            List of menu names from root to target
        """
        path = []
        current = menu_name
        
        while current:
            menu = self.get_menu(current)
            if not menu:
                break
            
            path.insert(0, current)
            current = menu.parent
            
            # Prevent infinite loops
            if len(path) > 10:
                break
        
        return path
    
    def validate_menu_structure(self) -> List[str]:
        """
        Validate the menu structure for consistency
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check that all parent references exist
        for menu_name, menu in self.menus.items():
            if menu.parent and menu.parent not in self.menus:
                errors.append(f"Menu '{menu_name}' has invalid parent '{menu.parent}'")
        
        # Check for circular references
        for menu_name in self.menus:
            path = self.get_menu_path(menu_name)
            if len(set(path)) != len(path):
                errors.append(f"Circular reference detected in menu '{menu_name}'")
        
        # Check that goto_menu targets exist
        for menu_name, menu in self.menus.items():
            for key, item in menu.items.items():
                if item.action == "goto_menu" and item.target not in self.menus:
                    errors.append(f"Menu '{menu_name}' item '{key}' targets invalid menu '{item.target}'")
        
        return errors
    
    def get_available_menus(self) -> List[str]:
        """Get list of available menu names"""
        return list(self.menus.keys())
    
    def get_menu_statistics(self) -> Dict[str, Any]:
        """Get statistics about the menu system"""
        total_items = sum(len(menu.items) for menu in self.menus.values())
        enabled_items = sum(
            sum(1 for item in menu.items.values() if item.enabled)
            for menu in self.menus.values()
        )
        
        return {
            "total_menus": len(self.menus),
            "total_items": total_items,
            "enabled_items": enabled_items,
            "validation_errors": len(self.validate_menu_structure())
        }