# New Node Notification Feature - Implementation Plan

## Overview
This feature adds automatic notification to admin nodes when new Meshtastic nodes connect to the BBMesh system. Nodes are tracked in a database, and notifications are sent for nodes that haven't been seen in the last 30 days.

## Requirements Summary
1. Track all nodes that message the BBMesh connected node
2. Store first-seen and last-seen timestamps in a database
3. Send direct message notifications to registered admin nodes for new/returning nodes
4. Consider a node "new" if not seen in the last 30 days
5. Support both YAML config and PSK-based admin node registration
6. Provide CLI tool for database management

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Meshtastic Network                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Node A  │    │  Node B  │    │ Admin    │              │
│  │  (New)   │    │ (Known)  │    │ Node     │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
└───────┼───────────────┼───────────────┼──────────────────────┘
        │               │               │
        │  Message      │  Message      │  Receives
        │               │               │  Notifications
        └───────────────┴───────────────┘
                        │
                ┌───────▼────────┐
                │   BBMesh BBS   │
                │  (This System) │
                └───────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼────────┐ ┌───▼────────┐ ┌───▼──────────┐
│ MessageHandler │ │ NodeTracker│ │ AdminManager │
│                │ │            │ │              │
│ - Receives msg │ │ - Track    │ │ - Manage     │
│ - Extracts     │ │   nodes    │ │   admin list │
│   node info    │ │ - Check    │ │ - Send       │
│ - Calls        │ │   new/old  │ │   notifs     │
│   tracker      │ │ - Update   │ │              │
└────────────────┘ │   DB       │ └──────────────┘
                   └─────┬──────┘
                         │
                   ┌─────▼──────┐
                   │  SQLite DB │
                   │            │
                   │ - nodes    │
                   │ - admins   │
                   └────────────┘
```

### Database Schema

#### Table: `mesh_nodes`
Tracks all nodes that have interacted with the system.

```sql
CREATE TABLE mesh_nodes (
    node_id TEXT PRIMARY KEY,           -- Meshtastic node ID (e.g., "!a1b2c3d4")
    node_name TEXT,                     -- Short name of the node
    first_seen_at TIMESTAMP NOT NULL,   -- First time this node was seen
    last_seen_at TIMESTAMP NOT NULL,    -- Most recent interaction
    message_count INTEGER DEFAULT 1,    -- Total messages from this node
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_last_seen ON mesh_nodes(last_seen_at);
CREATE INDEX idx_node_name ON mesh_nodes(node_name);
```

#### Table: `admin_nodes`
Tracks registered admin nodes that receive notifications.

```sql
CREATE TABLE admin_nodes (
    node_id TEXT PRIMARY KEY,           -- Admin node ID
    node_name TEXT,                     -- Admin node name
    registration_method TEXT NOT NULL,  -- 'config' or 'psk'
    registered_at TIMESTAMP NOT NULL,
    last_notification_at TIMESTAMP,     -- Last time we sent a notification
    is_active BOOLEAN DEFAULT 1,        -- Can be disabled without deletion
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_active_admins ON admin_nodes(is_active);
```

### Configuration Schema

#### bbmesh.yaml additions

```yaml
# New section for node tracking and admin notifications
node_tracking:
  enabled: true                          # Enable/disable node tracking
  new_node_threshold_days: 30            # Days before node considered "new" again
  notification_enabled: true             # Enable/disable notifications
  notification_format: "🆕 {node_name} ({node_id})"  # Notification message template
  
  # Admin nodes configured via YAML (primary method)
  admin_nodes:
    - "!a1b2c3d4"  # Admin node ID 1
    - "!e5f6g7h8"  # Admin node ID 2
  
  # PSK for dynamic admin registration
  admin_psk: "your-secret-key-here"     # Pre-shared key for admin registration
  psk_enabled: true                      # Allow PSK-based registration
```

### Implementation Details

#### 1. NodeTracker Class (`src/bbmesh/core/node_tracker.py`)

```python
class NodeTracker:
    """
    Manages node tracking and new node detection
    """
    
    def __init__(self, db_path: str, threshold_days: int = 30):
        """Initialize node tracker with database connection"""
        
    def initialize_database(self) -> None:
        """Create tables if they don't exist"""
        
    def record_node_activity(self, node_id: str, node_name: str) -> bool:
        """
        Record node activity and determine if node is "new"
        
        Returns:
            True if node is new (not seen in threshold_days), False otherwise
        """
        
    def get_node_info(self, node_id: str) -> Optional[Dict]:
        """Get stored information about a node"""
        
    def get_all_nodes(self) -> List[Dict]:
        """Get list of all tracked nodes"""
        
    def reset_node(self, node_id: str) -> bool:
        """Reset a node's tracking (mark as new)"""
        
    def clear_old_nodes(self, days: int) -> int:
        """Remove nodes not seen in X days"""
```

#### 2. AdminManager Class (`src/bbmesh/core/admin_manager.py`)

```python
class AdminManager:
    """
    Manages admin node registration and notifications
    """
    
    def __init__(self, db_path: str, config: Dict, mesh_interface):
        """Initialize admin manager"""
        
    def initialize_database(self) -> None:
        """Create admin_nodes table"""
        
    def load_config_admins(self, admin_node_ids: List[str]) -> None:
        """Load admin nodes from YAML config"""
        
    def register_admin_via_psk(self, node_id: str, node_name: str, psk: str) -> bool:
        """
        Register admin node via PSK message
        
        Message format: "ADMIN_REGISTER:<psk>"
        """
        
    def get_active_admins(self) -> List[str]:
        """Get list of active admin node IDs"""
        
    def send_new_node_notification(self, node_id: str, node_name: str) -> None:
        """Send notification to all active admin nodes"""
        
    def deactivate_admin(self, node_id: str) -> bool:
        """Deactivate an admin node"""
```

#### 3. Integration Points

##### MessageHandler Integration (`src/bbmesh/core/message_handler.py`)

```python
class MessageHandler:
    def __init__(self, ...):
        # Add new components
        self.node_tracker = NodeTracker(
            db_path=config.database.path,
            threshold_days=config.node_tracking.new_node_threshold_days
        )
        self.admin_manager = AdminManager(
            db_path=config.database.path,
            config=config.node_tracking,
            mesh_interface=mesh_interface
        )
        
    def _process_message(self, message: MeshMessage) -> None:
        """Process incoming message"""
        
        # Check for admin registration command FIRST
        if message.text.strip().startswith("ADMIN_REGISTER:"):
            self._handle_admin_registration(message)
            return
            
        # Track node activity
        if self.config.node_tracking.enabled:
            is_new = self.node_tracker.record_node_activity(
                message.sender_id,
                message.sender_name
            )
            
            # Send notification if new node
            if is_new and self.config.node_tracking.notification_enabled:
                self.admin_manager.send_new_node_notification(
                    message.sender_id,
                    message.sender_name
                )
        
        # Continue with normal message processing...
        
    def _handle_admin_registration(self, message: MeshMessage) -> None:
        """Handle admin registration via PSK"""
        if not self.config.node_tracking.psk_enabled:
            return
            
        # Extract PSK from message
        parts = message.text.strip().split(":", 1)
        if len(parts) != 2:
            return
            
        provided_psk = parts[1]
        
        # Attempt registration
        success = self.admin_manager.register_admin_via_psk(
            message.sender_id,
            message.sender_name,
            provided_psk
        )
        
        if success:
            response = "✅ Admin registration successful"
        else:
            response = "❌ Admin registration failed"
            
        self._send_response(message, session, response)
```

#### 4. CLI Tool (`src/bbmesh/cli_nodes.py`)

```python
#!/usr/bin/env python3
"""
BBMesh Node Management CLI Tool
"""

import click
from pathlib import Path
from bbmesh.core.node_tracker import NodeTracker
from bbmesh.core.admin_manager import AdminManager

@click.group()
@click.option('--db', default='data/bbmesh.db', help='Database path')
@click.pass_context
def cli(ctx, db):
    """BBMesh Node Management Tool"""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db

@cli.command()
@click.pass_context
def list(ctx):
    """List all tracked nodes"""
    tracker = NodeTracker(ctx.obj['db_path'])
    nodes = tracker.get_all_nodes()
    
    click.echo(f"\n{'Node ID':<15} {'Name':<20} {'First Seen':<20} {'Last Seen':<20} {'Messages':<10}")
    click.echo("-" * 90)
    for node in nodes:
        click.echo(f"{node['node_id']:<15} {node['node_name']:<20} "
                  f"{node['first_seen_at']:<20} {node['last_seen_at']:<20} "
                  f"{node['message_count']:<10}")

@cli.command()
@click.argument('node_id')
@click.pass_context
def reset(ctx, node_id):
    """Reset a node's tracking (mark as new)"""
    tracker = NodeTracker(ctx.obj['db_path'])
    if tracker.reset_node(node_id):
        click.echo(f"✅ Reset node {node_id}")
    else:
        click.echo(f"❌ Node {node_id} not found")

@cli.command()
@click.option('--days', default=90, help='Remove nodes not seen in X days')
@click.confirmation_option(prompt='Are you sure you want to clear old nodes?')
@click.pass_context
def clear(ctx, days):
    """Clear nodes not seen in X days"""
    tracker = NodeTracker(ctx.obj['db_path'])
    count = tracker.clear_old_nodes(days)
    click.echo(f"✅ Removed {count} nodes not seen in {days} days")

@cli.command()
@click.pass_context
def admins(ctx):
    """List registered admin nodes"""
    manager = AdminManager(ctx.obj['db_path'], {}, None)
    admins = manager.get_active_admins()
    
    click.echo(f"\n{'Node ID':<15} {'Name':<20} {'Method':<10} {'Registered':<20}")
    click.echo("-" * 70)
    for admin in admins:
        click.echo(f"{admin['node_id']:<15} {admin['node_name']:<20} "
                  f"{admin['registration_method']:<10} {admin['registered_at']:<20}")

if __name__ == '__main__':
    cli()
```

### Configuration Class Updates

#### config.py additions

```python
@dataclass
class NodeTrackingConfig:
    """Node tracking and admin notification configuration"""
    enabled: bool = True
    new_node_threshold_days: int = 30
    notification_enabled: bool = True
    notification_format: str = "🆕 {node_name} ({node_id})"
    admin_nodes: List[str] = field(default_factory=list)
    admin_psk: Optional[str] = None
    psk_enabled: bool = True

@dataclass
class Config:
    # ... existing fields ...
    node_tracking: NodeTrackingConfig = field(default_factory=NodeTrackingConfig)
```

## Implementation Sequence

### Phase 1: Database Foundation
1. Create `node_tracker.py` with NodeTracker class
2. Implement database schema and initialization
3. Add basic CRUD operations for nodes
4. Write unit tests for NodeTracker

### Phase 2: Admin Management
1. Create `admin_manager.py` with AdminManager class
2. Implement admin node registration (config-based)
3. Implement PSK-based registration
4. Add notification sending logic
5. Write unit tests for AdminManager

### Phase 3: Integration
1. Update Config classes with NodeTrackingConfig
2. Integrate NodeTracker into MessageHandler
3. Integrate AdminManager into MessageHandler
4. Add admin registration command handling
5. Test message flow end-to-end

### Phase 4: CLI Tool
1. Create `cli_nodes.py` with Click commands
2. Implement list, reset, clear, admins commands
3. Add to pyproject.toml as console script
4. Test CLI operations

### Phase 5: Documentation & Testing
1. Update configuration.md with new settings
2. Create user guide for admin registration
3. Add integration tests
4. Test with real Meshtastic hardware

## Testing Strategy

### Unit Tests
- NodeTracker: database operations, new node detection
- AdminManager: registration, notification sending
- Config: schema validation

### Integration Tests
- Message flow with node tracking
- Admin registration via PSK
- Notification delivery
- CLI tool operations

### Manual Testing Checklist
- [ ] New node sends first message → admin receives notification
- [ ] Known node (< 30 days) sends message → no notification
- [ ] Old node (> 30 days) sends message → admin receives notification
- [ ] Admin registers via PSK → confirmation received
- [ ] Admin registers via config → loads on startup
- [ ] CLI list shows all nodes correctly
- [ ] CLI reset marks node as new
- [ ] CLI clear removes old nodes
- [ ] Multiple admins receive notifications

## Security Considerations

1. **PSK Storage**: Store admin PSK securely in config, never log it
2. **Rate Limiting**: Prevent spam of admin registration attempts
3. **Validation**: Validate node IDs before database operations
4. **SQL Injection**: Use parameterized queries throughout
5. **Access Control**: Only allow admin operations from authorized nodes

## Performance Considerations

1. **Database Indexing**: Index on last_seen_at for efficient queries
2. **Batch Operations**: Consider batching notifications if many new nodes
3. **Caching**: Cache admin list to avoid repeated DB queries
4. **Async Operations**: Consider async notification sending to avoid blocking

## Migration Path

For existing BBMesh installations:

1. Database will auto-create tables on first run
2. Existing nodes will be "new" until they send a message
3. Config file needs manual update to add node_tracking section
4. No breaking changes to existing functionality

## Future Enhancements

1. Web dashboard for node visualization
2. Node statistics and analytics
3. Configurable notification throttling
4. Node grouping/tagging
5. Export node data to CSV
6. Admin notification preferences (which events to receive)