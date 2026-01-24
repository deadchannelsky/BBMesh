# TradeWars Plugin for BBMesh

A classic space trading game adapted for async mesh networks. Buy low, sell high across 100 sectors with 30 dynamic ports. Navigate the galaxy, manage cargo, and track your trading profits on Meshtastic and other mesh networks.

## Features

**MVP (Phase 1) - Trading & Navigation**
- 100-sector procedurally generated universe
- 30 dynamic trading ports with supply/demand economics
- Player registration tied to mesh node IDs
- Full trading loop (buy/sell commodities)
- Cargo management (20-hold capacity)
- Navigation system with pathfinding
- Persistent state across BBMesh reboots
- 200-character message formatting optimized for mesh networks
- 5 commodities with realistic pricing mechanics

**Future Phases**
- Combat system (fighters, mines, torpedoes)
- Planetary colonization
- Asteroid mining
- Territory control and PvP
- Multiple ship classes
- Leaderboards and rankings

## Installation

### Prerequisites
- BBMesh installation (v0.1+)
- Python 3.8+
- PyYAML (for configuration)
- SQLite3 (included in Python standard library)

### Quick Install

1. Navigate to your BBMesh root directory:
```bash
cd /path/to/BBMesh
```

2. Run the installer:
```bash
python3 plugins/bbmesh_tradewars_plugin/install.py
```

3. Restart BBMesh

4. Access TradeWars from the main menu

### Manual Installation

If the installer fails:

1. Copy plugin files:
```bash
cp plugins/bbmesh_tradewars_plugin/*.py src/bbmesh/plugins/tradewars_*.py
```

2. Edit `config/plugins.yaml` and add:
```yaml
  tradewars:
    enabled: true
    description: TradeWars - Classic space trading game for mesh networks
    timeout: 120
    database_path: data/tradewars/tradewars.db
    starting_credits: 10000
    starting_turns: 1000
    max_cargo_holds: 20
```

3. Edit `config/menus.yaml` - add to main menu options:
```yaml
  '7':
    title: TradeWars
    action: run_plugin
    plugin: tradewars
    description: Space trading game
```

4. Edit `src/bbmesh/plugins/builtin.py` - add import:
```python
from .tradewars_plugin import TradeWarsPlugin
```

5. Register in BUILTIN_PLUGINS dict:
```python
    "tradewars": TradeWarsPlugin,
```

## Uninstallation

To remove TradeWars from your BBMesh installation:

```bash
python3 plugins/bbmesh_tradewars_plugin/install.py --uninstall
```

Then manually remove configuration entries from `plugins.yaml` and `menus.yaml` if desired.

## Gameplay Guide

### Starting Out

1. Send `TRADEWARS` to activate the plugin
2. Enter your 8-character call sign (alphanumeric only)
3. Confirm your call sign
4. You spawn in a random sector (1-10) with:
   - 10,000 credits
   - 1,000 turns
   - 20 cargo holds (empty)
   - 1 ship

### Main Commands

From the sector view:

| Command | Action |
|---------|--------|
| `M` | Show navigation menu (choose destination) |
| `M#` | Quick warp (e.g., `M47` to go to sector 47) |
| `P` | Enter port (if available in current sector) |
| `C` | View cargo |
| `S` | View stats |
| `H` | Help |
| `QUIT` | Exit game |

### Trading

1. Navigate to a port sector (`M` command)
2. Enter port (`P` command)
3. Choose action:
   - `1` = Buy commodities
   - `2` = Sell commodities
   - `3` = List port inventory
   - `0` = Exit port
4. Select commodity (1-5)
5. Enter quantity
6. Confirm - cargo updated, credits deducted/earned

### Example Trade

**Buying:**
```
Port-47 You:10K Port:5M
1)Buy 2)Sell 3)List 0)Exit
[Select: 1]

BUY FROM PORT:
1)Or:215cr 45K avail
2)Og:180cr 120K
3)Eq:3.8Kcr 7K
[Select: 1]

Buy Or@215cr
Holds:0/20 Cash:10K
Max:46 units
How many? [Enter: 30]

Bought 30 Or for 6,450cr
New balance: 3,550cr
Cargo: 30/20 holds
```

**Selling at another port:**
```
BUY: Ore at Port-47 for 215 cr = 6,450 total
SELL: Ore at Port-51 for 280 cr = 8,400 total
PROFIT: 1,950 credits (+30%)
```

## Abbreviations

Messages use abbreviations to fit the 200-character mesh network limit:

| Item | Abbreviation |
|------|--------------|
| Ore | Or |
| Organics | Og |
| Equipment | Eq |
| Armor | Ar |
| Batteries | Ba |
| Buying | B |
| Selling | S |
| Thousand | K (10K = 10,000) |
| Million | M (5M = 5,000,000) |
| Credits | Cr |
| Turns | T |

## Game Mechanics

### Turns System

- Each warp costs 1 turn per sector (Dijkstra pathfinding used)
- Start with 1,000 turns
- Once depleted, can't warp until regeneration
- Future: Turn regeneration over time (10/hour)

### Cargo Management

- 20 cargo holds total
- Each unit of commodity uses 1 hold
- Can't carry more than capacity allows
- Cargo persists across session

### Port Economics

- Dynamic pricing based on supply/demand
- 5 commodities with different base prices:
  - Ore: 250cr (bulk commodity)
  - Organics: 180cr (agricultural)
  - Equipment: 3,800cr (industrial)
  - Armor: 1,200cr (military)
  - Batteries: 11cr (electronics)
- Ports randomly buy or sell each commodity
- Prices fluctuate by ±30% based on quantities traded
- Port inventories regenerate every 4 hours

### Scoring

- Tracks total credits (net worth)
- Counts total trades executed
- Counts total warps/jumps
- Future: Leaderboards by sector

## Message Formatting

All messages are capped at 200 characters to fit within Meshtastic's message limits:

```
Sec47[→12,48,51]
Port:YES Ships:1
Turns:990 Cr:8.2K
H=help M=move P=port C=cargo
```

## Architecture

### Plugin Structure

```
bbmesh_tradewars_plugin/
├── tradewars_plugin.py      # Main plugin class & state machine
├── storage.py               # SQLite database layer
├── universe.py              # Sector generation & pathfinding
├── trade_calculator.py      # Economics engine
├── formatters.py            # Message formatting (200 char limit)
├── install.py               # Installation script
├── README.md                # This file
├── requirements.txt         # Dependencies
└── config/                  # Configuration templates (future)
```

### Database Schema

Uses SQLite with JSON for flexible data structures:

- **players** - User accounts linked to node IDs
- **ships** - Player ship state and cargo
- **sectors** - Universe map (100 sectors, connections)
- **ports** - Trading locations with inventory
- **game_state** - Game initialization flags

### State Machine

The plugin uses a state machine for gameplay:

```
REGISTRATION → SECTOR_VIEW ← ← ← ← ←
                    ↓                  ↓
        VIEW_CARGO, VIEW_STATS → NAVIGATION
                    ↓                  ↓
                IN_PORT → PORT_BUY → TRADE_QUANTITY
                    ↓
                PORT_SELL
```

## Testing

Manual testing on your BBMesh instance:

1. **Registration**: Send `TRADEWARS` with new node ID
2. **Navigation**: Warp 5+ sectors (`M` then select destination)
3. **Trading**: Buy commodities, check cargo (`C`), navigate to another port, sell
4. **Persistence**: Exit and re-enter, verify state restored
5. **Edge cases**: Try buying with insufficient funds, selling when empty, etc.

## Compatibility

- **BBMesh Core**: v0.1+
- **Python**: 3.8+
- **Network**: Any Meshtastic mesh or compatible system
- **Message Limit**: Optimized for 200-character limit

## Known Limitations (MVP Phase 1)

- No turn regeneration yet (future implementation)
- No real-time combat (async only)
- No planet colonization
- Single ship per player
- No corporation/team features
- No messaging system between players
- No market history or charts
- Limited to 100 sectors (by design for MVP)

## Future Enhancements

**Phase 2: Combat**
- Fighter deployment and combat
- Mine fields
- Torpedo systems
- Player-vs-player encounters

**Phase 3: Planets**
- Colonization and settlement
- Resource extraction
- Infrastructure building
- Tax systems

**Phase 4: Advanced**
- Multiple ship classes
- Ship upgrades and modifications
- Trading corporations
- Leaderboards and rankings
- Daily/weekly challenges
- Event system

## Troubleshooting

### Plugin won't load
- Verify Python 3.8+ installed
- Check BBMesh logs for import errors
- Ensure all plugin files copied correctly

### Database errors
- Delete `data/tradewars/tradewars.db` to reset
- Check disk space in data directory
- Verify SQLite3 available

### Message truncation issues
- Check 200-char limit compliance
- Review `formatters.py` for custom messages
- Report formatting bugs with examples

### Navigation failures
- Verify sectors 1-100 are valid
- Check universe generation in logs
- Pathfinding should work for any sector pair

## Contributing

Found a bug? Want to contribute features?
- Test extensively before reporting issues
- Include game state details in bug reports
- Suggest balance changes with rationale

## License

See parent BBMesh project license.

## Support

Questions or issues? Check:
1. This README
2. BBMesh documentation
3. Plugin logs in `~/.bbmesh/logs/`

Enjoy exploring the galaxy! Safe trading!
