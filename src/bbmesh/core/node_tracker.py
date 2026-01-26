"""
Node tracking and new node detection for BBMesh

This module manages tracking of Meshtastic nodes that interact with the BBMesh system,
detecting when nodes are "new" (not seen in the configured threshold period).
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

from ..utils.logger import BBMeshLogger


class NodeTracker:
    """
    Manages node tracking and new node detection
    
    Tracks all nodes that message the BBMesh system, storing first-seen and last-seen
    timestamps. Determines if a node is "new" based on configurable threshold.
    """
    
    def __init__(self, db_path: str, threshold_days: int = 30):
        """
        Initialize node tracker
        
        Args:
            db_path: Path to SQLite database file
            threshold_days: Days before node is considered "new" again
        """
        self.db_path = Path(db_path)
        self.threshold_days = threshold_days
        self.logger = BBMeshLogger(__name__)
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.initialize_database()
        
        self.logger.info(f"NodeTracker initialized: db={db_path}, threshold={threshold_days} days")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def initialize_database(self) -> None:
        """Create mesh_nodes table if it doesn't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create mesh_nodes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mesh_nodes (
                        node_id TEXT PRIMARY KEY,
                        node_name TEXT,
                        first_seen_at TIMESTAMP NOT NULL,
                        last_seen_at TIMESTAMP NOT NULL,
                        message_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for efficient queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_seen 
                    ON mesh_nodes(last_seen_at)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_node_name 
                    ON mesh_nodes(node_name)
                """)
                
                self.logger.info("Node tracking database initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def record_node_activity(self, node_id: str, node_name: str) -> bool:
        """
        Record node activity and determine if node is "new"
        
        A node is considered "new" if:
        - It doesn't exist in the database, OR
        - It hasn't been seen in threshold_days or more
        
        Args:
            node_id: Meshtastic node ID (e.g., "!a1b2c3d4")
            node_name: Node's short name
            
        Returns:
            True if node is new (should trigger notification), False otherwise
        """
        if not node_id or not node_name:
            self.logger.warning(f"Invalid node data: id={node_id}, name={node_name}")
            return False
        
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now()
                    
                    # Check if node exists
                    cursor.execute(
                        "SELECT last_seen_at FROM mesh_nodes WHERE node_id = ?",
                        (node_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result is None:
                        # New node - insert into database
                        cursor.execute("""
                            INSERT INTO mesh_nodes 
                            (node_id, node_name, first_seen_at, last_seen_at, message_count)
                            VALUES (?, ?, ?, ?, 1)
                        """, (node_id, node_name, now, now))
                        
                        self.logger.info(f"New node tracked: {node_name} ({node_id})")
                        return True
                    
                    else:
                        # Existing node - check if it's been too long
                        last_seen = datetime.fromisoformat(result['last_seen_at'])
                        days_since_seen = (now - last_seen).days
                        
                        is_new = days_since_seen >= self.threshold_days
                        
                        # Update node record
                        cursor.execute("""
                            UPDATE mesh_nodes 
                            SET node_name = ?,
                                last_seen_at = ?,
                                message_count = message_count + 1,
                                updated_at = ?
                            WHERE node_id = ?
                        """, (node_name, now, now, node_id))
                        
                        if is_new:
                            self.logger.info(
                                f"Returning node (after {days_since_seen} days): "
                                f"{node_name} ({node_id})"
                            )
                        else:
                            self.logger.debug(
                                f"Known node activity: {node_name} ({node_id}), "
                                f"last seen {days_since_seen} days ago"
                            )
                        
                        return is_new
                        
        except Exception as e:
            self.logger.error(f"Error recording node activity for {node_id}: {e}")
            return False
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored information about a node
        
        Args:
            node_id: Meshtastic node ID
            
        Returns:
            Dictionary with node information, or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM mesh_nodes WHERE node_id = ?",
                    (node_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting node info for {node_id}: {e}")
            return None
    
    def get_all_nodes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get list of all tracked nodes
        
        Args:
            limit: Maximum number of nodes to return (None for all)
            
        Returns:
            List of dictionaries with node information
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM mesh_nodes ORDER BY last_seen_at DESC"
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error getting all nodes: {e}")
            return []
    
    def get_node_count(self) -> int:
        """
        Get total number of tracked nodes
        
        Returns:
            Number of nodes in database
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM mesh_nodes")
                result = cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            self.logger.error(f"Error getting node count: {e}")
            return 0
    
    def reset_node(self, node_id: str) -> bool:
        """
        Reset a node's tracking (mark as if not seen, will be "new" on next message)
        
        Args:
            node_id: Meshtastic node ID
            
        Returns:
            True if node was reset, False if not found or error
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Set last_seen_at to a date beyond threshold
                    old_date = datetime.now() - timedelta(days=self.threshold_days + 1)
                    
                    cursor.execute("""
                        UPDATE mesh_nodes 
                        SET last_seen_at = ?,
                            updated_at = ?
                        WHERE node_id = ?
                    """, (old_date, datetime.now(), node_id))
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"Reset node tracking: {node_id}")
                        return True
                    else:
                        self.logger.warning(f"Node not found for reset: {node_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error resetting node {node_id}: {e}")
            return False
    
    def clear_old_nodes(self, days: int) -> int:
        """
        Remove nodes not seen in specified number of days
        
        Args:
            days: Remove nodes not seen in this many days
            
        Returns:
            Number of nodes removed
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cutoff_date = datetime.now() - timedelta(days=days)
                    
                    cursor.execute("""
                        DELETE FROM mesh_nodes 
                        WHERE last_seen_at < ?
                    """, (cutoff_date,))
                    
                    count = cursor.rowcount
                    self.logger.info(f"Cleared {count} nodes not seen in {days} days")
                    return count
                    
        except Exception as e:
            self.logger.error(f"Error clearing old nodes: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked nodes
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total nodes
                cursor.execute("SELECT COUNT(*) as count FROM mesh_nodes")
                total = cursor.fetchone()['count']
                
                # Active nodes (seen in last threshold_days)
                cutoff = datetime.now() - timedelta(days=self.threshold_days)
                cursor.execute(
                    "SELECT COUNT(*) as count FROM mesh_nodes WHERE last_seen_at >= ?",
                    (cutoff,)
                )
                active = cursor.fetchone()['count']
                
                # Total messages
                cursor.execute("SELECT SUM(message_count) as total FROM mesh_nodes")
                messages = cursor.fetchone()['total'] or 0
                
                return {
                    'total_nodes': total,
                    'active_nodes': active,
                    'inactive_nodes': total - active,
                    'total_messages': messages,
                    'threshold_days': self.threshold_days
                }
                
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {
                'total_nodes': 0,
                'active_nodes': 0,
                'inactive_nodes': 0,
                'total_messages': 0,
                'threshold_days': self.threshold_days
            }

# Made with Bob
