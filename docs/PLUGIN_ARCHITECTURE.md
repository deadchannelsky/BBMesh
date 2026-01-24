# BBMesh Plugin Architecture Guide

## Core Principles

### 1. **Closed Input Loop** (FOUNDATIONAL)

Once a user enters an interactive plugin session with `continue_session=True`, that plugin owns ALL subsequent input from that user until the plugin explicitly ends the session with `continue_session=False`.

**This is a hard requirement.** No other BBS commands or global handlers should intercept plugin input except for:
- System-critical errors (crashes, network failures)  
- Explicitly defined exit commands the plugin recognizes

**Why:** Interactive plugins (games, editors, forms) require uninterrupted control to maintain game state and user experience. Interrupting input stream breaks session continuity and confuses users.

### 2. **Session State Ownership**

The plugin maintains complete responsibility for:
- Session state machine (what "screen" the user is on)
- Session data persistence across messages
- All input validation and routing
- Session cleanup on exit

The BBMesh message handler is responsible for:
- Routing input to the active plugin
- Preserving session data between requests
- Cleanup after plugin exits

### 3. **Universal Exit Commands**

All interactive plugins must support:
- `QUIT` - Exit to main BBMesh menu
- `EXIT` - Exit to main BBMesh menu
- `MENU` - Return to main menu
- `0` - Context-dependent exit/back (may vary by plugin state)

These are intercepted by the base `InteractivePlugin.execute()` method.

## Plugin Types

### SimpleResponsePlugin
Returns a single response. No session state.

### InteractivePlugin
Maintains session state across multiple messages. Closed input loop until `continue_session=False`.

## Session Data Structure

Session data is stored per plugin per user in `session.context[f"plugin_{plugin_name}"]`.

**Required keys:**
- `{plugin_name}_active` (bool) - Must be True for plugin to receive input
- `{plugin_name}_state` (str) - Current state in state machine

## State Machine Pattern (Recommended)

Route input based on state:

```python
def continue_session(self, context: PluginContext) -> PluginResponse:
    state = context.session_data.get(f"{self.name}_state", "START")
    user_input = context.message.text.strip().upper()

    state_handlers = {
        "START": self._handle_start,
        "PLAYING": self._handle_playing,
    }

    handler = state_handlers.get(state, self._handle_start)
    return handler(context, user_input)
```

## Critical Best Practices

### 1. Always Include Session Data

```python
return PluginResponse(
    text="Game status",
    continue_session=True,
    session_data={
        "tradewars_active": True,
        "tradewars_state": "SECTOR_VIEW",
        "tradewars_player_id": 42
    }
)
```

### 2. Preserve Existing Session Data

```python
session_data = context.session_data.copy()
session_data[f"{self.name}_state"] = "NEW_STATE"
# ... more updates ...

return PluginResponse(
    text="Response",
    continue_session=True,
    session_data=session_data
)
```

### 3. Handle Missing Session Data

```python
def continue_session(self, context: PluginContext) -> PluginResponse:
    player_id = context.session_data.get(f"{self.name}_player_id")

    if not player_id:
        # Session lost - restart
        return self.start_session(context)
```

## Message Routing MUST

The message handler MUST:

1. Check for active plugin FIRST (before menu parsing)
2. If `{plugin_name}_active = True`, route ALL input to plugin
3. Do NOT parse global commands while plugin is active
4. Preserve session_data exactly between requests
5. Let plugin decide when session ends

---

For full documentation and examples, see this file.
