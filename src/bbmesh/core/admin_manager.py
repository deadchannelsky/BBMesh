"""
Admin node management and notification system for BBMesh

This module manages admin node registration (via YAML config or PSK) and
sends notifications to admin nodes when new mesh nodes are detected.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

from ..utils.logger import BBMeshLogger


class AdminManager:
    """
    Manages admin node registration and notifications
    
    Supports two registration methods:
    1. YAML configuration (permanent admins)
    2. PSK-based dynamic registration (temporary admins)
    """
    
    def __init__(self, db_path: str, config: Dict[str, Any], mesh_interface):
        """
        Initialize admin manager
        
        Args:
            db_path: Path to SQLite database file
            config: Node tracking configuration dictionary
            mesh_interface: MeshtasticInterface instance for sending messages
        """
        self.db_path = Path(db_path)
        self.config = config
        self.mesh_interface = mesh_interface
        self.logger = BBMeshLogger(__name__)
        self._lock = threading.Lock()
        
        # Extract configuration
        self.notification_format = config.get('notification_format', '🆕 {node_name} ({node_id})')
        self.admin_psk = config.get('admin_psk')
        self.psk_enabled = config.get('psk_enabled', True)
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.initialize_database()
        
        # Load YAML-configured admins
        yaml_admins = config.get('admin_nodes', [])
        if yaml_admins:
            self.load_config_admins(yaml_admins)
        
        self.logger.info(f"AdminManager initialized: {len(yaml_admins)} config admins, PSK={'enabled' if self.psk_enabled else 'disabled'}")
    
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
        """Create admin_nodes table if it doesn't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create admin_nodes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS admin_nodes (
                        node_id TEXT PRIMARY KEY,
                        node_name TEXT,
                        registration_method TEXT NOT NULL,
                        registered_at TIMESTAMP NOT NULL,
                        last_notification_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for active admins
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_active_admins 
                    ON admin_nodes(is_active)
                """)
                
                self.logger.info("Admin nodes database initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize admin database: {e}")
            raise
    
    def load_config_admins(self, admin_node_ids: List[str]) -> None:
        """
        Load admin nodes from YAML configuration
        
        Args:
            admin_node_ids: List of admin node IDs from config
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now()
                    
                    for node_id in admin_node_ids:
                        if not node_id:
                            continue
                        
                        # Check if already exists
                        cursor.execute(
                            "SELECT node_id FROM admin_nodes WHERE node_id = ?",
                            (node_id,)
                        )
                        
                        if cursor.fetchone() is None:
                            # Insert new config admin
                            cursor.execute("""
                                INSERT INTO admin_nodes 
                                (node_id, node_name, registration_method, registered_at, is_active)
                                VALUES (?, ?, 'config', ?, 1)
                            """, (node_id, 'Config Admin', now))
                            
                            self.logger.info(f"Registered config admin: {node_id}")
                        else:
                            # Update existing to ensure it's active and method is 'config'
                            cursor.execute("""
                                UPDATE admin_nodes 
                                SET registration_method = 'config',
                                    is_active = 1
                                WHERE node_id = ?
                            """, (node_id,))
                            
                            self.logger.debug(f"Updated config admin: {node_id}")
                    
        except Exception as e:
            self.logger.error(f"Error loading config admins: {e}")
    
    def register_admin_via_psk(self, node_id: str, node_name: str, provided_psk: str) -> bool:
        """
        Register admin node via PSK message
        
        Args:
            node_id: Node ID attempting to register
            node_name: Node's short name
            provided_psk: PSK provided by the node
            
        Returns:
            True if registration successful, False otherwise
        """
        if not self.psk_enabled:
            self.logger.warning(f"PSK registration disabled, rejected attempt from {node_id}")
            return False
        
        if not self.admin_psk:
            self.logger.error("Admin PSK not configured, cannot validate registration")
            return False
        
        # Validate PSK
        if provided_psk != self.admin_psk:
            self.logger.warning(f"Invalid PSK from {node_id} ({node_name})")
            return False
        
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now()
                    
                    # Check if already exists
                    cursor.execute(
                        "SELECT node_id, registration_method FROM admin_nodes WHERE node_id = ?",
                        (node_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        # Update existing admin
                        cursor.execute("""
                            UPDATE admin_nodes 
                            SET node_name = ?,
                                registration_method = 'psk',
                                registered_at = ?,
                                is_active = 1
                            WHERE node_id = ?
                        """, (node_name, now, node_id))
                        
                        self.logger.info(f"Re-registered admin via PSK: {node_name} ({node_id})")
                    else:
                        # Insert new PSK admin
                        cursor.execute("""
                            INSERT INTO admin_nodes 
                            (node_id, node_name, registration_method, registered_at, is_active)
                            VALUES (?, ?, 'psk', ?, 1)
                        """, (node_id, node_name, now))
                        
                        self.logger.info(f"Registered new admin via PSK: {node_name} ({node_id})")
                    
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error registering admin via PSK: {e}")
            return False
    
    def get_active_admins(self) -> List[Dict[str, Any]]:
        """
        Get list of active admin nodes
        
        Returns:
            List of dictionaries with admin information
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM admin_nodes 
                    WHERE is_active = 1
                    ORDER BY registered_at DESC
                """)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error getting active admins: {e}")
            return []
    
    def get_active_admin_ids(self) -> List[str]:
        """
        Get list of active admin node IDs
        
        Returns:
            List of node IDs
        """
        admins = self.get_active_admins()
        return [admin['node_id'] for admin in admins]
    
    def send_new_node_notification(self, node_id: str, node_name: str) -> None:
        """
        Send notification to all active admin nodes about a new node
        
        Args:
            node_id: New node's ID
            node_name: New node's name
        """
        try:
            # Get active admins
            admin_ids = self.get_active_admin_ids()
            
            if not admin_ids:
                self.logger.debug("No active admins to notify")
                return
            
            # Format notification message
            message = self.notification_format.format(
                node_name=node_name,
                node_id=node_id
            )
            
            # Send to each admin
            success_count = 0
            for admin_id in admin_ids:
                try:
                    # Send direct message to admin
                    success = self.mesh_interface.send_message(
                        text=message,
                        channel=0,  # Direct messages use channel 0
                        destination=admin_id
                    )
                    
                    if success:
                        success_count += 1
                        self.logger.debug(f"Sent new node notification to admin {admin_id}")
                        
                        # Update last notification time
                        self._update_last_notification(admin_id)
                    else:
                        self.logger.warning(f"Failed to send notification to admin {admin_id}")
                        
                except Exception as e:
                    self.logger.error(f"Error sending notification to admin {admin_id}: {e}")
            
            self.logger.info(
                f"Sent new node notification for {node_name} ({node_id}) "
                f"to {success_count}/{len(admin_ids)} admins"
            )
            
        except Exception as e:
            self.logger.error(f"Error in send_new_node_notification: {e}")
    
    def _update_last_notification(self, admin_id: str) -> None:
        """
        Update the last notification timestamp for an admin
        
        Args:
            admin_id: Admin node ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE admin_nodes 
                    SET last_notification_at = ?
                    WHERE node_id = ?
                """, (datetime.now(), admin_id))
                
        except Exception as e:
            self.logger.error(f"Error updating last notification time: {e}")
    
    def deactivate_admin(self, node_id: str) -> bool:
        """
        Deactivate an admin node (without deleting)
        
        Args:
            node_id: Admin node ID to deactivate
            
        Returns:
            True if deactivated, False if not found or error
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE admin_nodes 
                        SET is_active = 0
                        WHERE node_id = ?
                    """, (node_id,))
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"Deactivated admin: {node_id}")
                        return True
                    else:
                        self.logger.warning(f"Admin not found for deactivation: {node_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error deactivating admin {node_id}: {e}")
            return False
    
    def activate_admin(self, node_id: str) -> bool:
        """
        Activate an admin node
        
        Args:
            node_id: Admin node ID to activate
            
        Returns:
            True if activated, False if not found or error
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE admin_nodes 
                        SET is_active = 1
                        WHERE node_id = ?
                    """, (node_id,))
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"Activated admin: {node_id}")
                        return True
                    else:
                        self.logger.warning(f"Admin not found for activation: {node_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error activating admin {node_id}: {e}")
            return False
    
    def remove_admin(self, node_id: str) -> bool:
        """
        Remove an admin node from database
        
        Args:
            node_id: Admin node ID to remove
            
        Returns:
            True if removed, False if not found or error
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM admin_nodes 
                        WHERE node_id = ?
                    """, (node_id,))
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"Removed admin: {node_id}")
                        return True
                    else:
                        self.logger.warning(f"Admin not found for removal: {node_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error removing admin {node_id}: {e}")
            return False
    
    def get_admin_count(self) -> Dict[str, int]:
        """
        Get count of admin nodes by status
        
        Returns:
            Dictionary with counts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) as count FROM admin_nodes WHERE is_active = 1")
                active = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM admin_nodes WHERE is_active = 0")
                inactive = cursor.fetchone()['count']
                
                return {
                    'active': active,
                    'inactive': inactive,
                    'total': active + inactive
                }
                
        except Exception as e:
            self.logger.error(f"Error getting admin count: {e}")
            return {'active': 0, 'inactive': 0, 'total': 0}

# Made with Bob
