# New Node Notification Feature - Executive Summary

## Feature Overview

Automatically notify designated admin nodes when new Meshtastic devices connect to the BBMesh system. This feature is designed to support live IoT exercises by providing real-time awareness of network participants.

## Key Capabilities

1. **Automatic Node Tracking**: All nodes that message BBMesh are tracked in a SQLite database
2. **Smart "New" Detection**: Nodes not seen in 30 days are considered "new" (configurable)
3. **Dual Admin Registration**: Support both YAML config and dynamic PSK-based registration
4. **Minimal Notifications**: Simple format `🆕 NodeName (!12345678)` to conserve bandwidth
5. **CLI Management Tool**: Command-line interface for viewing and managing tracked nodes

## Architecture Summary

```
Incoming Message → MessageHandler → NodeTracker (check if new)
                                         ↓
                                    Is New? → AdminManager → Send DM to Admins
                                         ↓
                                    Update Database
```

**Components:**
- `NodeTracker`: Manages node database and new/old detection
- `AdminManager`: Handles admin registration and notification delivery
- `CLI Tool`: Provides database management commands
- `Database`: SQLite with two tables (mesh_nodes, admin_nodes)

## Implementation Phases

### Phase 1: Database Foundation (2-3 hours)
- Create NodeTracker class
- Implement database schema
- Add CRUD operations
- Unit tests

### Phase 2: Admin Management (2-3 hours)
- Create AdminManager class
- Implement YAML-based admin loading
- Implement PSK registration
- Notification sending logic
- Unit tests

### Phase 3: Integration (2-3 hours)
- Update Config classes
- Integrate into MessageHandler
- Add admin registration command handling
- Integration tests

### Phase 4: CLI Tool (1-2 hours)
- Create Click-based CLI
- Implement list, reset, clear, admins commands
- Add to pyproject.toml

### Phase 5: Documentation & Testing (1-2 hours)
- Update configuration docs
- Create user guides
- Manual testing with hardware

**Total Estimated Time: 8-13 hours**

## File Changes Required

### New Files (5)
1. `src/bbmesh/core/node_tracker.py` - Node tracking logic (~200 lines)
2. `src/bbmesh/core/admin_manager.py` - Admin management (~250 lines)
3. `src/bbmesh/cli_nodes.py` - CLI tool (~150 lines)
4. `tests/test_node_tracker.py` - Unit tests (~200 lines)
5. `tests/test_admin_manager.py` - Unit tests (~200 lines)

### Modified Files (4)
1. `src/bbmesh/core/config.py` - Add NodeTrackingConfig class (~50 lines added)
2. `src/bbmesh/core/message_handler.py` - Integration (~100 lines added)
3. `config/bbmesh.yaml.example` - Add node_tracking section (~15 lines)
4. `pyproject.toml` - Add CLI script entry (~3 lines)

### Documentation Files (3)
1. `docs/new_node_notification_plan.md` - Detailed implementation plan (485 lines) ✅
2. `docs/new_node_notification_quickstart.md` - User guide (253 lines) ✅
3. `docs/configuration.md` - Update with new config section (~50 lines added)

**Total New Code: ~1,000 lines**
**Total Modified Code: ~200 lines**

## Database Impact

### Storage Requirements
- **Per Node**: ~150 bytes (node_id, name, timestamps, counters)
- **100 Nodes**: ~15 KB
- **1,000 Nodes**: ~150 KB
- **10,000 Nodes**: ~1.5 MB

**Conclusion**: Minimal storage impact, even for large networks.

### Performance Impact
- **Node lookup**: O(1) with primary key index
- **New node check**: Single SELECT query (~1ms)
- **Notification send**: Existing mesh interface, no additional overhead
- **Database writes**: Async, non-blocking

**Conclusion**: Negligible performance impact on message processing.

## Configuration Example

```yaml
node_tracking:
  enabled: true
  new_node_threshold_days: 30
  notification_enabled: true
  notification_format: "🆕 {node_name} ({node_id})"
  admin_nodes:
    - "!a1b2c3d4"
  admin_psk: "exercise-2026-secret"
  psk_enabled: true
```

## Usage Examples

### For IoT Exercise Coordinators

**Before Exercise:**
```bash
# Clear test data
bbmesh-nodes clear --days 1

# Verify admin registration
bbmesh-nodes admins
```

**During Exercise:**
- Participants connect → Admins receive: `🆕 ParticipantNode (!12345678)`
- Monitor: `tail -f logs/bbmesh.log | grep "🆕"`

**After Exercise:**
```bash
# Review all participants
bbmesh-nodes list

# Export data
sqlite3 data/bbmesh.db ".mode csv" ".output report.csv" "SELECT * FROM mesh_nodes;"
```

### For Network Administrators

**Monitor Network Growth:**
```bash
# View all nodes
bbmesh-nodes list

# Check admin notifications
bbmesh-nodes admins
```

**Maintenance:**
```bash
# Clean up old nodes (90+ days)
bbmesh-nodes clear --days 90

# Reset specific node
bbmesh-nodes reset !a1b2c3d4
```

## Security Considerations

1. **PSK Protection**: Admin PSK stored in config file (file permissions critical)
2. **Rate Limiting**: Existing rate limiter prevents registration spam
3. **SQL Injection**: Parameterized queries throughout
4. **Access Control**: Only direct messages processed for admin registration
5. **Audit Trail**: All admin registrations logged

## Testing Strategy

### Unit Tests
- ✅ NodeTracker database operations
- ✅ AdminManager registration logic
- ✅ Config schema validation
- ✅ New node detection algorithm

### Integration Tests
- ✅ End-to-end message flow
- ✅ Admin notification delivery
- ✅ PSK registration workflow
- ✅ CLI tool operations

### Manual Testing
- ✅ Real Meshtastic hardware
- ✅ Multiple admin nodes
- ✅ 30-day threshold verification
- ✅ Database persistence

## Backward Compatibility

- ✅ **No breaking changes** to existing BBMesh functionality
- ✅ **Optional feature** - can be disabled via config
- ✅ **Graceful degradation** - works without admin nodes configured
- ✅ **Database auto-creation** - no manual migration needed
- ✅ **Existing configs work** - new section is optional

## Future Enhancements

### Short Term (Next Release)
1. Node statistics dashboard
2. Configurable notification throttling
3. Admin notification preferences

### Long Term (Future Releases)
1. Web-based node visualization
2. Node grouping/tagging
3. Advanced analytics and reporting
4. Integration with external monitoring systems

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Database corruption | Low | Medium | Regular backups, transaction safety |
| Notification spam | Low | Low | Rate limiting, threshold tuning |
| PSK compromise | Medium | Medium | Config file permissions, PSK rotation |
| Performance degradation | Very Low | Low | Indexed queries, async operations |
| Storage exhaustion | Very Low | Low | Automatic cleanup, configurable retention |

**Overall Risk Level: LOW**

## Success Criteria

1. ✅ Admin nodes receive notifications for new nodes
2. ✅ Nodes not seen in 30+ days trigger notifications
3. ✅ Both YAML and PSK registration methods work
4. ✅ CLI tool provides full database management
5. ✅ No impact on existing BBMesh functionality
6. ✅ Performance remains within acceptable limits
7. ✅ Documentation is clear and complete

## Deployment Checklist

- [ ] Code review completed
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Manual testing with hardware completed
- [ ] Documentation reviewed and approved
- [ ] Configuration examples updated
- [ ] Migration guide created (if needed)
- [ ] Security review completed
- [ ] Performance benchmarks acceptable
- [ ] Backward compatibility verified

## Approval & Next Steps

### For Review
This plan provides a comprehensive approach to implementing the new node notification feature. Key decisions made:

1. **Dual registration method** (YAML + PSK) for flexibility
2. **Minimal notification format** to conserve bandwidth
3. **CLI tool** for easy management
4. **30-day threshold** as default (configurable)
5. **SQLite database** for simplicity and reliability

### Questions for Stakeholders
1. Is the 30-day threshold appropriate for your use case?
2. Should we add any additional fields to track (e.g., signal strength, location)?
3. Are there any specific security requirements beyond what's planned?
4. Should notifications include any additional information?

### Ready to Implement
Once approved, implementation can begin following the phased approach outlined above. Estimated completion: 8-13 hours of development time.

---

**Status**: ✅ Planning Complete - Ready for Implementation
**Next Step**: Switch to Code mode to begin implementation