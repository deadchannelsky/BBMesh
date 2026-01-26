# New Node Notification - Quick Start Guide

## Overview
BBMesh can automatically notify admin nodes when new Meshtastic nodes connect to the mesh network. A node is considered "new" if it hasn't been seen in the last 30 days.

## Quick Setup

### 1. Enable Node Tracking in Configuration

Edit `config/bbmesh.yaml` and add:

```yaml
node_tracking:
  enabled: true
  new_node_threshold_days: 30
  notification_enabled: true
  notification_format: "🆕 {node_name} ({node_id})"
  
  # Method 1: Configure admin nodes directly
  admin_nodes:
    - "!a1b2c3d4"  # Replace with your admin node ID
  
  # Method 2: Enable PSK-based registration
  admin_psk: "your-secret-key-here"
  psk_enabled: true
```

### 2. Register as Admin Node

#### Option A: YAML Configuration (Recommended for permanent admins)
1. Add your node ID to `admin_nodes` list in config
2. Restart BBMesh: `sudo systemctl restart bbmesh`

#### Option B: PSK Registration (Dynamic registration)
1. From your admin node, send a direct message to BBMesh:
   ```
   ADMIN_REGISTER:your-secret-key-here
   ```
2. You'll receive confirmation: `✅ Admin registration successful`

### 3. Test the System

1. Have a new node send a message to BBMesh
2. Admin nodes should receive: `🆕 NodeName (!12345678)`

## Managing Nodes

### View All Tracked Nodes
```bash
bbmesh-nodes list
```

Output:
```
Node ID         Name                 First Seen           Last Seen            Messages  
------------------------------------------------------------------------------------------
!a1b2c3d4       TestNode1           2026-01-26 10:30     2026-01-26 15:45     42        
!e5f6g7h8       IoTDevice           2026-01-25 08:15     2026-01-26 14:20     18        
```

### Reset a Node (Mark as New)
```bash
bbmesh-nodes reset !a1b2c3d4
```

This will cause the node to trigger a "new node" notification on its next message.

### Clear Old Nodes
```bash
bbmesh-nodes clear --days 90
```

Removes nodes that haven't been seen in 90 days.

### List Admin Nodes
```bash
bbmesh-nodes admins
```

Output:
```
Node ID         Name                 Method     Registered          
----------------------------------------------------------------------
!a1b2c3d4       AdminNode1          config     2026-01-26 10:00    
!e5f6g7h8       AdminNode2          psk        2026-01-26 12:30    
```

## Use Cases

### IoT Exercise Monitoring
During live IoT exercises, admin nodes receive real-time notifications as participants connect their devices to the mesh network.

```
Participant connects → BBMesh detects new node → Admin receives notification
```

### Network Growth Tracking
Track when new nodes join your mesh network over time. Use the CLI to review connection history.

### Returning Node Detection
If a node hasn't been seen in 30+ days and reconnects, admins are notified (useful for detecting intermittent devices).

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable/disable node tracking |
| `new_node_threshold_days` | `30` | Days before node considered "new" again |
| `notification_enabled` | `true` | Send notifications to admins |
| `notification_format` | `"🆕 {node_name} ({node_id})"` | Message template |
| `admin_nodes` | `[]` | List of admin node IDs (YAML config) |
| `admin_psk` | `null` | Pre-shared key for dynamic registration |
| `psk_enabled` | `true` | Allow PSK-based admin registration |

## Security Notes

1. **Keep PSK Secret**: The admin PSK should be kept confidential
2. **Change Default PSK**: Always change from the example value
3. **Limit Admin Access**: Only register trusted nodes as admins
4. **Monitor Admin List**: Regularly review registered admins with `bbmesh-nodes admins`

## Troubleshooting

### Admin Not Receiving Notifications

1. **Check admin registration:**
   ```bash
   bbmesh-nodes admins
   ```
   Verify your node is listed and active.

2. **Check node tracking is enabled:**
   ```bash
   grep "node_tracking:" config/bbmesh.yaml
   ```

3. **Check BBMesh logs:**
   ```bash
   tail -f logs/bbmesh.log | grep -i "new node\|admin"
   ```

### Node Not Detected as New

1. **Check if node exists in database:**
   ```bash
   bbmesh-nodes list | grep "NodeID"
   ```

2. **Check last seen date** - if within 30 days, it won't trigger notification

3. **Reset the node** to force new notification:
   ```bash
   bbmesh-nodes reset !a1b2c3d4
   ```

### PSK Registration Failing

1. **Verify PSK is correct** in config file
2. **Check `psk_enabled` is `true`** in config
3. **Ensure message format** is exactly: `ADMIN_REGISTER:your-psk-here`
4. **Check logs** for registration attempts

## Database Location

Node tracking data is stored in: `data/bbmesh.db`

Tables:
- `mesh_nodes` - All tracked nodes
- `admin_nodes` - Registered admin nodes

You can inspect the database directly:
```bash
sqlite3 data/bbmesh.db "SELECT * FROM mesh_nodes ORDER BY last_seen_at DESC LIMIT 10;"
```

## Example Workflow

### Setting Up for an IoT Exercise

1. **Before the exercise:**
   ```bash
   # Clear old test data
   bbmesh-nodes clear --days 1
   
   # Register your admin node
   # Send from admin node: ADMIN_REGISTER:exercise-2026-key
   ```

2. **During the exercise:**
   - Participants connect their nodes
   - Admin receives notifications: `🆕 ParticipantNode (!12345678)`
   - Monitor in real-time: `tail -f logs/bbmesh.log | grep "🆕"`

3. **After the exercise:**
   ```bash
   # Review all participants
   bbmesh-nodes list
   
   # Export for records (if needed)
   sqlite3 data/bbmesh.db ".mode csv" ".output participants.csv" "SELECT * FROM mesh_nodes;"
   ```

## Advanced Configuration

### Custom Notification Format

You can customize the notification message:

```yaml
notification_format: "🆕 New: {node_name} | ID: {node_id} | Welcome!"
```

Available placeholders:
- `{node_name}` - Node's short name
- `{node_id}` - Node's Meshtastic ID

### Multiple Admin Nodes

Configure multiple admins to receive notifications:

```yaml
admin_nodes:
  - "!a1b2c3d4"  # Primary admin
  - "!e5f6g7h8"  # Secondary admin
  - "!i9j0k1l2"  # Backup admin
```

All listed admins will receive notifications for new nodes.

### Adjusting New Node Threshold

Change how long before a node is considered "new" again:

```yaml
new_node_threshold_days: 60  # 60 days instead of 30
```

Useful for:
- **Shorter (7-14 days)**: Frequent exercises, active networks
- **Longer (60-90 days)**: Stable networks, seasonal events

## Integration with Existing Features

The node tracking system integrates seamlessly with BBMesh:

- **No impact on BBS functionality** - All menu/plugin features work normally
- **Minimal overhead** - Database operations are fast and non-blocking
- **Backward compatible** - Existing installations work without changes
- **Optional feature** - Can be disabled entirely if not needed

## Support

For issues or questions:
1. Check BBMesh logs: `logs/bbmesh.log`
2. Review configuration: `config/bbmesh.yaml`
3. Test database: `bbmesh-nodes list`
4. See full documentation: `docs/new_node_notification_plan.md`