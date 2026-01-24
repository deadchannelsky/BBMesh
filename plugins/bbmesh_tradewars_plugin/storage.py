"""
TradeWars Plugin - Database Storage Layer
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


class TradeWarsStorage:
    """Database operations for TradeWars plugin"""

    def __init__(self, db_path: str = None):
        """Initialize storage with database path"""
        if db_path is None:
            # Use default location in BBMesh data directory
            home_dir = Path.home()
            data_dir = home_dir / ".bbmesh" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "tradewars.db")

        self.db_path = db_path
        self.conn = None
        self.init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def init_db(self) -> None:
        """Initialize database schema"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Create players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT UNIQUE NOT NULL,
                player_name TEXT UNIQUE NOT NULL,
                credits INTEGER NOT NULL DEFAULT 10000,
                turns INTEGER NOT NULL DEFAULT 1000,
                score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT NOT NULL,
                total_warps INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0
            )
        """)

        # Create ships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ships (
                ship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE NOT NULL,
                current_sector INTEGER NOT NULL,
                cargo_holds INTEGER NOT NULL DEFAULT 20,
                cargo TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        """)

        # Create sectors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sectors (
                sector_id INTEGER PRIMARY KEY,
                connected_sectors TEXT NOT NULL,
                port_id INTEGER,
                description TEXT,
                FOREIGN KEY (port_id) REFERENCES ports(port_id)
            )
        """)

        # Create ports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ports (
                port_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                credits INTEGER NOT NULL,
                inventory TEXT NOT NULL,
                last_regeneration TEXT NOT NULL,
                FOREIGN KEY (sector_id) REFERENCES sectors(sector_id)
            )
        """)

        # Create game_state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()

    # ===== Player Operations =====

    def player_exists(self, node_id: str) -> bool:
        """Check if player exists by node_id"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM players WHERE node_id = ?", (node_id,))
        return cursor.fetchone() is not None

    def create_player(self, node_id: str, player_name: str) -> int:
        """Create new player, return player_id"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO players
            (node_id, player_name, credits, turns, score, created_at, last_login)
            VALUES (?, ?, 10000, 1000, 0, ?, ?)
        """, (node_id, player_name, now, now))

        conn.commit()
        return cursor.lastrowid

    def get_player_by_node_id(self, node_id: str) -> Optional[Dict]:
        """Get player record by node_id"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_player_by_id(self, player_id: int) -> Optional[Dict]:
        """Get player record by player_id"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_player_stats(self, player_id: int, credits: int = None, turns: int = None,
                           score: int = None, total_warps: int = None, total_trades: int = None) -> None:
        """Update player statistics"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        updates = []
        params = []

        if credits is not None:
            updates.append("credits = ?")
            params.append(credits)
        if turns is not None:
            updates.append("turns = ?")
            params.append(turns)
        if score is not None:
            updates.append("score = ?")
            params.append(score)
        if total_warps is not None:
            updates.append("total_warps = ?")
            params.append(total_warps)
        if total_trades is not None:
            updates.append("total_trades = ?")
            params.append(total_trades)

        if updates:
            updates.append("last_login = ?")
            params.append(now)
            params.append(player_id)

            query = f"UPDATE players SET {', '.join(updates)} WHERE player_id = ?"
            cursor.execute(query, params)
            conn.commit()

    # ===== Ship Operations =====

    def create_ship(self, player_id: int, starting_sector: int) -> int:
        """Create ship for player, return ship_id"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Empty cargo
        cargo = json.dumps({
            "Ore": 0,
            "Organics": 0,
            "Equipment": 0,
            "Armor": 0,
            "Batteries": 0
        })

        cursor.execute("""
            INSERT INTO ships
            (player_id, current_sector, cargo_holds, cargo, created_at)
            VALUES (?, ?, 20, ?, ?)
        """, (player_id, starting_sector, cargo, now))

        conn.commit()
        return cursor.lastrowid

    def get_ship_by_player_id(self, player_id: int) -> Optional[Dict]:
        """Get ship for player"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ships WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        if row:
            ship = dict(row)
            ship['cargo'] = json.loads(ship['cargo'])
            return ship
        return None

    def update_ship_location(self, ship_id: int, sector_id: int) -> None:
        """Update ship location"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE ships SET current_sector = ? WHERE ship_id = ?",
                      (sector_id, ship_id))
        conn.commit()

    def update_ship_cargo(self, ship_id: int, cargo: Dict[str, int]) -> None:
        """Update ship cargo"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cargo_json = json.dumps(cargo)
        cursor.execute("UPDATE ships SET cargo = ? WHERE ship_id = ?",
                      (cargo_json, ship_id))
        conn.commit()

    def get_cargo_used(self, cargo: Dict[str, int]) -> int:
        """Calculate total cargo holds used"""
        return sum(cargo.values())

    # ===== Sector Operations =====

    def sector_exists(self, sector_id: int) -> bool:
        """Check if sector exists"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sectors WHERE sector_id = ?", (sector_id,))
        return cursor.fetchone() is not None

    def create_sector(self, sector_id: int, connected_sectors: List[int],
                     port_id: int = None, description: str = "") -> None:
        """Create sector"""
        conn = self._get_conn()
        cursor = conn.cursor()
        connected_json = json.dumps(connected_sectors)

        cursor.execute("""
            INSERT INTO sectors
            (sector_id, connected_sectors, port_id, description)
            VALUES (?, ?, ?, ?)
        """, (sector_id, connected_json, port_id, description))

        conn.commit()

    def get_sector(self, sector_id: int) -> Optional[Dict]:
        """Get sector"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sectors WHERE sector_id = ?", (sector_id,))
        row = cursor.fetchone()
        if row:
            sector = dict(row)
            sector['connected_sectors'] = json.loads(sector['connected_sectors'])
            return sector
        return None

    def get_all_sectors(self) -> List[Dict]:
        """Get all sectors"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sectors ORDER BY sector_id")
        rows = cursor.fetchall()
        sectors = []
        for row in rows:
            sector = dict(row)
            sector['connected_sectors'] = json.loads(sector['connected_sectors'])
            sectors.append(sector)
        return sectors

    # ===== Port Operations =====

    def create_port(self, sector_id: int, name: str, credits: int, inventory: Dict) -> int:
        """Create port"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        inventory_json = json.dumps(inventory)

        cursor.execute("""
            INSERT INTO ports
            (sector_id, name, credits, inventory, last_regeneration)
            VALUES (?, ?, ?, ?, ?)
        """, (sector_id, name, credits, inventory_json, now))

        conn.commit()
        return cursor.lastrowid

    def get_port_by_sector_id(self, sector_id: int) -> Optional[Dict]:
        """Get port in sector"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ports WHERE sector_id = ?", (sector_id,))
        row = cursor.fetchone()
        if row:
            port = dict(row)
            port['inventory'] = json.loads(port['inventory'])
            return port
        return None

    def get_port_by_id(self, port_id: int) -> Optional[Dict]:
        """Get port by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ports WHERE port_id = ?", (port_id,))
        row = cursor.fetchone()
        if row:
            port = dict(row)
            port['inventory'] = json.loads(port['inventory'])
            return port
        return None

    def update_port_inventory(self, port_id: int, inventory: Dict) -> None:
        """Update port inventory"""
        conn = self._get_conn()
        cursor = conn.cursor()
        inventory_json = json.dumps(inventory)
        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE ports SET inventory = ?, last_regeneration = ?
            WHERE port_id = ?
        """, (inventory_json, now, port_id))

        conn.commit()

    def update_port_credits(self, port_id: int, credits: int) -> None:
        """Update port buying power"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE ports SET credits = ? WHERE port_id = ?",
                      (credits, port_id))
        conn.commit()

    # ===== Game State =====

    def set_state(self, key: str, value: str) -> None:
        """Set game state value"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO game_state (key, value)
            VALUES (?, ?)
        """, (key, value))

        conn.commit()

    def get_state(self, key: str) -> Optional[str]:
        """Get game state value"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM game_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
