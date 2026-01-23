# BBMesh Plugin Architecture

## Design Principles

BBMesh uses a plugin-based architecture that cleanly separates core BBS infrastructure from user-facing features. This design enables extensibility and maintainability while preventing tight coupling.

### Core BBS Responsibilities (src/bbmesh/core/)

The core BBS should ONLY handle infrastructure:
- **Message transport**: Sending/receiving via Meshtastic interface
- **Session management**: Tracking user sessions, timeouts, rate limiting
- **Message routing**: Directing messages (direct, broadcast, mentions)
- **Menu system**: Displaying menus, navigating menu structure, processing menu input

**DO NOT implement in core:**
- User-facing features or commands
- Feature-specific response generation
- Command parsing (except HELP and MENU navigation)
- Business logic for games, utilities, or other features

### Plugin Responsibilities (src/bbmesh/plugins/)

Plugins handle ALL user-facing functionality:
- User-facing features and commands
- Response generation and formatting
- Feature state management (for interactive plugins)
- User interaction logic and flows
- Configuration management for the feature

## Current Plugin System

### Built-in Plugins

Built-in plugins are defined in `src/bbmesh/plugins/builtin.py`:

#### SimpleResponsePlugin-based (stateless):
- **WelcomePlugin** - Initial greeting message
- **HelpPlugin** - Command reference and help system
- **TimePlugin** - Date and time display
- **PingPlugin** - Connectivity test with signal info
- **StatusPlugin** - System status and basic information
- **CalculatorPlugin** - Basic arithmetic calculator
- **NodeLookupPlugin** - Mesh node information lookup

#### InteractivePlugin-based (stateful):
- **NumberGuessPlugin** - Number guessing game with escalating difficulty levels

#### External Plugins:
- **AskAIPlugin** - AI assistant powered by local Ollama (builtin.py)
- **bulletin_system** - Community bulletin board (separate plugin directory)

### Configuration

Each plugin requires configuration in two places:

1. **Enable in bbmesh.yaml** (enabled_plugins list):
```yaml
plugins:
  enabled_plugins:
    - welcome
    - help
    - time
    - ping
    - status
    - calculator
    - number_guess
    - node_lookup
    - askai
```

2. **Configure in plugins.yaml** (optional, plugin-specific settings):
```yaml
plugins:
  time:
    enabled: true
    description: Date and time display
    timezone: UTC
    format: '%Y-%m-%d %H:%M:%S %Z'
    timeout: 5
```

3. **Add menu entry in menus.yaml** (how users access the plugin):
```yaml
menus:
  main:
    options:
      1:
        title: Time & Date
        action: show_time  # or run_plugin + plugin: time
        description: Display current date and time
```

## Command Routing Architecture

### Direct Shortcuts (Core Navigation Only)

Only these commands bypass the menu system:
- `HELP` → Routes to HelpPlugin
- `MENU` → Displays main menu

All other commands must be accessed through the menu system.

### Menu System Flow

1. User sends direct message (no active plugin session)
2. MessageHandler receives message
3. Checks if active plugin session exists
   - If yes: route to active plugin
   - If no: parse as menu input
4. MenuSystem.process_menu_input() determines action
5. Handler processes action:
   - `show_help` → route to help plugin
   - `show_time` → route to time plugin
   - `show_status` → route to status plugin
   - `show_mesh_info` → route to node_lookup plugin
   - `goto_menu` → navigate to different menu
   - `run_plugin` → execute specified plugin

### Plugin Execution Flow

```
User Message
    ↓
MessageHandler._handle_direct_message()
    ↓
Check for active plugin session
    ├─ YES → _execute_plugin() [continue session]
    └─ NO ↓
        MenuSystem.process_menu_input()
        ↓
        _handle_menu_action()
        ↓
        Route action to plugin or navigate menu
        ↓
        Plugin.execute(context)
        ├─ SimpleResponsePlugin → generate_response()
        └─ InteractivePlugin → start_session() or continue_session()
        ↓
        Send response + update session
```

## Adding New Features

### Creating a Simple Response Plugin

For stateless features (one-time queries):

```python
class MyPlugin(SimpleResponsePlugin):
    """Description of what this plugin does"""

    def generate_response(self, context: PluginContext) -> str:
        # Access user info
        user = context.user_name
        user_id = context.user_id

        # Access configuration
        timeout = self.config.get("timeout", 30)

        # Generate response
        return "Your response here"
```

### Creating an Interactive Plugin

For stateful features (games, multi-step workflows):

```python
class MyInteractivePlugin(InteractivePlugin):
    """Description of multi-turn feature"""

    def start_session(self, context: PluginContext) -> PluginResponse:
        # Initialize game/workflow
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_step": 1,
            # ... other state
        }

        return PluginResponse(
            text="Initial prompt",
            continue_session=True,
            session_data=session_data
        )

    def continue_session(self, context: PluginContext) -> PluginResponse:
        # Process user input
        user_input = context.message.text.strip()

        # Determine if session continues or ends
        if is_game_over:
            return PluginResponse(
                text="Game over message",
                continue_session=False
            )
        else:
            return PluginResponse(
                text="Next prompt",
                continue_session=True,
                session_data=updated_session_data
            )
```

### Integration Checklist

1. **Create plugin class** in `src/bbmesh/plugins/builtin.py`
   - Inherit from `SimpleResponsePlugin` or `InteractivePlugin`
   - Implement required methods

2. **Register plugin** in `BUILTIN_PLUGINS` dict
   - Add entry: `"plugin_name": PluginClass`

3. **Add configuration** in `config/plugins.yaml`
   - Create section under `plugins:`
   - Include timeout and any feature-specific settings

4. **Enable plugin** in `config/bbmesh.yaml`
   - Add to `enabled_plugins` list

5. **Create menu entry** in `config/menus.yaml`
   - Add to appropriate menu section
   - Use `action: run_plugin` and `plugin: plugin_name`
   - Or use `action: show_*` if it's a core action

6. **Test thoroughly**
   - Verify plugin loads without errors
   - Test basic functionality
   - Test error cases

## Integrating External Plugins

External plugins are located in separate directories (e.g., `plugins/bbmesh_bulletin_plugin/`).

### Structure

```
plugins/
  bbmesh_bulletin_plugin/
    README.md
    requirements.txt
    install.sh
    bulletin_plugin.py
    config.yaml
```

### Integration Steps

1. **Install** via install script or manual setup
2. **Add configuration** to main `config/plugins.yaml`
   ```yaml
   bulletin_system:
     enabled: true
     description: Community bulletin board system
     database_path: data/bulletin_system/bulletins.db
     # ... other settings
   ```

3. **Enable** in `config/bbmesh.yaml` if needed
   - Can be omitted if handled differently

4. **Add menu entry** in `config/menus.yaml`

5. **Plugin code** inherits from base classes
   - Imports from `bbmesh.plugins.base`
   - Uses `PluginContext`, `PluginResponse` for compatibility

## Architecture Benefits

**Before this cleanup:**
- Duplicate code paths for same features
- Core had feature logic (bad separation)
- Phantom configs created confusion
- Multiple ways to trigger same feature

**After cleanup:**
- ✅ Single code path per feature (through plugins)
- ✅ Core is purely infrastructure (clean separation)
- ✅ Configuration matches implementation
- ✅ Consistent access via menu system
- ✅ Clear documentation for future development
- ✅ Ready for stable release

## Future Enhancements

### Planned Improvements

1. **Enhance StatusPlugin**
   - Add mesh network statistics
   - Include system uptime and session count
   - Show connected node information

2. **Plugin Hot-Reload**
   - Update plugins without restarting BBS
   - Reload configuration changes on demand

3. **Plugin Discovery**
   - Auto-detect plugins in plugins/ directory
   - Dynamic plugin loading

4. **Plugin Installation Tool**
   - `bbmesh plugin install <path>`
   - `bbmesh plugin remove <name>`

### Potential Missing Plugins (if needed)

These configurations exist in code history but are not implemented:
- word_game - Word association game
- trivia - Trivia question game
- unit_converter - Unit conversion utility
- weather - Weather information

If implementing these, follow the plugin integration checklist above.

## Troubleshooting

### Plugin Not Loading

1. **Check enabled_plugins list** in bbmesh.yaml
2. **Verify plugin configuration** in plugins.yaml (syntax errors)
3. **Check BUILTIN_PLUGINS registry** has plugin entry
4. **Review logs** for initialization errors

### Plugin Not Appearing in Menu

1. **Verify menu entry** in menus.yaml
2. **Check action is correct** (show_* or run_plugin)
3. **Verify plugin_name matches** registry name
4. **Test menu system** with existing plugins

### Session Data Not Persisting

1. **For InteractivePlugin**: return PluginResponse with session_data
2. **Verify session_data is not None**
3. **Check session data keys** follow naming convention
4. **Review continue_session logic** in plugin

## Summary

The BBMesh plugin system provides:
- Clear separation between core and features
- Extensible architecture for adding functionality
- Consistent user experience via menu system
- Documented patterns for plugin development
- Support for both simple and interactive plugins

All user-facing features should be implemented as plugins, never in the core message handler.
