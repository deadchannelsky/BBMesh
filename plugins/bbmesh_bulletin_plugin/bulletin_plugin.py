"""
BBMesh Bulletin Board System Plugin

A feature-rich bulletin board system for mesh network communities.
Provides posting, reading, searching, and management of community bulletins.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Import BBMesh plugin framework
from .base import InteractivePlugin, PluginContext, PluginResponse
from ..utils.logger import BBMeshLogger


@dataclass
class Bulletin:
    """Represents a bulletin post"""
    id: int
    author_id: str
    author_name: str
    category: str
    subject: str
    content: str
    timestamp: datetime
    expires_at: Optional[datetime] = None
    reply_to_id: Optional[int] = None


class BulletinStorage:
    """
    Database storage for bulletin board system
    Handles all bulletin CRUD operations and database management
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = BBMeshLogger("bulletin.storage")
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Ensure database exists and has correct schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bulletins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT,
                    reply_to_id INTEGER,
                    FOREIGN KEY (reply_to_id) REFERENCES bulletins (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    max_bulletins INTEGER DEFAULT 100
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    last_post TEXT,
                    posts_today INTEGER DEFAULT 0,
                    posts_this_hour INTEGER DEFAULT 0,
                    last_activity TEXT NOT NULL
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bulletins_category ON bulletins(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bulletins_timestamp ON bulletins(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bulletins_author ON bulletins(author_id)")
            
            conn.commit()
    
    def post_bulletin(self, author_id: str, author_name: str, category: str, 
                     subject: str, content: str, reply_to_id: Optional[int] = None) -> int:
        """Post a new bulletin and return its ID"""
        expires_at = datetime.now() + timedelta(days=30)  # Auto-expire in 30 days
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO bulletins (author_id, author_name, category, subject, content, 
                                     timestamp, expires_at, reply_to_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (author_id, author_name, category, subject, content, 
                  datetime.now().isoformat(), expires_at.isoformat(), reply_to_id))
            
            bulletin_id = cursor.lastrowid
            
            # Update user activity
            self._update_user_activity(conn, author_id, author_name)
            
            conn.commit()
            return bulletin_id
    
    def get_bulletins(self, category: Optional[str] = None, limit: int = 10, 
                     offset: int = 0) -> List[Bulletin]:
        """Get bulletins, optionally filtered by category"""
        with sqlite3.connect(self.db_path) as conn:
            if category:
                cursor = conn.execute("""
                    SELECT id, author_id, author_name, category, subject, content, 
                           timestamp, expires_at, reply_to_id
                    FROM bulletins 
                    WHERE category = ? AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (category, datetime.now().isoformat(), limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT id, author_id, author_name, category, subject, content,
                           timestamp, expires_at, reply_to_id
                    FROM bulletins
                    WHERE expires_at IS NULL OR expires_at > ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (datetime.now().isoformat(), limit, offset))
            
            bulletins = []
            for row in cursor.fetchall():
                bulletins.append(Bulletin(
                    id=row[0],
                    author_id=row[1],
                    author_name=row[2],
                    category=row[3],
                    subject=row[4],
                    content=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    reply_to_id=row[8]
                ))
            
            return bulletins
    
    def get_bulletin_by_id(self, bulletin_id: int) -> Optional[Bulletin]:
        """Get a specific bulletin by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, author_id, author_name, category, subject, content,
                       timestamp, expires_at, reply_to_id
                FROM bulletins
                WHERE id = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (bulletin_id, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                return Bulletin(
                    id=row[0],
                    author_id=row[1],
                    author_name=row[2],
                    category=row[3],
                    subject=row[4],
                    content=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    reply_to_id=row[8]
                )
            return None
    
    def search_bulletins(self, query: str, limit: int = 20) -> List[Bulletin]:
        """Search bulletins by content, subject, or author"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, author_id, author_name, category, subject, content,
                       timestamp, expires_at, reply_to_id
                FROM bulletins
                WHERE (subject LIKE ? OR content LIKE ? OR author_name LIKE ?)
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", 
                  datetime.now().isoformat(), limit))
            
            bulletins = []
            for row in cursor.fetchall():
                bulletins.append(Bulletin(
                    id=row[0],
                    author_id=row[1],
                    author_name=row[2],
                    category=row[3],
                    subject=row[4],
                    content=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    reply_to_id=row[8]
                ))
            
            return bulletins
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all available categories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, description, 
                       (SELECT COUNT(*) FROM bulletins 
                        WHERE category = categories.name 
                          AND (expires_at IS NULL OR expires_at > ?)) as count
                FROM categories
                ORDER BY name
            """, (datetime.now().isoformat(),))
            
            return [{"name": row[0], "description": row[1], "count": row[2]} 
                   for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bulletin board statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total bulletins
            total_cursor = conn.execute("""
                SELECT COUNT(*) FROM bulletins 
                WHERE expires_at IS NULL OR expires_at > ?
            """, (datetime.now().isoformat(),))
            total_bulletins = total_cursor.fetchone()[0]
            
            # Recent bulletins (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_cursor = conn.execute("""
                SELECT COUNT(*) FROM bulletins 
                WHERE timestamp > ? AND (expires_at IS NULL OR expires_at > ?)
            """, (week_ago, datetime.now().isoformat()))
            recent_bulletins = recent_cursor.fetchone()[0]
            
            # Active users (posted in last 30 days)
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            users_cursor = conn.execute("""
                SELECT COUNT(DISTINCT author_id) FROM bulletins 
                WHERE timestamp > ?
            """, (month_ago,))
            active_users = users_cursor.fetchone()[0]
            
            # Categories with counts
            categories_cursor = conn.execute("""
                SELECT category, COUNT(*) as count FROM bulletins
                WHERE expires_at IS NULL OR expires_at > ?
                GROUP BY category
                ORDER BY count DESC
            """, (datetime.now().isoformat(),))
            categories = {row[0]: row[1] for row in categories_cursor.fetchall()}
            
            return {
                "total_bulletins": total_bulletins,
                "recent_bulletins": recent_bulletins,
                "active_users": active_users,
                "categories": categories
            }
    
    def _update_user_activity(self, conn: sqlite3.Connection, user_id: str, user_name: str) -> None:
        """Update user activity tracking"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        
        # Check existing activity
        cursor = conn.execute("""
            SELECT posts_today, posts_this_hour, last_activity 
            FROM user_activity WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            posts_today = row[0] if row[2] >= today_start.isoformat() else 0
            posts_this_hour = row[1] if row[2] >= hour_start.isoformat() else 0
            
            conn.execute("""
                UPDATE user_activity 
                SET user_name = ?, last_post = ?, posts_today = ?, 
                    posts_this_hour = ?, last_activity = ?
                WHERE user_id = ?
            """, (user_name, now.isoformat(), posts_today + 1, 
                  posts_this_hour + 1, now.isoformat(), user_id))
        else:
            conn.execute("""
                INSERT INTO user_activity 
                (user_id, user_name, last_post, posts_today, posts_this_hour, last_activity)
                VALUES (?, ?, ?, 1, 1, ?)
            """, (user_id, user_name, now.isoformat(), now.isoformat()))


class BulletinBoardPlugin(InteractivePlugin):
    """
    BBMesh Bulletin Board System Plugin
    
    Provides a full-featured bulletin board system for mesh network communities.
    Supports posting, reading, searching, and managing community bulletins.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # Plugin configuration
        self.db_path = config.get("database_path", "data/bulletin_system.db")
        self.categories = config.get("categories", [
            {"name": "General", "description": "General discussions"},
            {"name": "Announcements", "description": "Official announcements"},
            {"name": "Emergency", "description": "Emergency communications"},
            {"name": "Community", "description": "Community events"}
        ])
        self.admin_users = set(config.get("admin_users", []))
        self.bulletins_per_page = config.get("bulletins_per_page", 10)
        self.max_bulletin_length = config.get("max_bulletin_length", 500)
        
        # Initialize storage
        self.storage = BulletinStorage(self.db_path)
        
        # Initialize categories in database
        self._initialize_categories()
    
    def _initialize_categories(self) -> None:
        """Initialize default categories in database"""
        with sqlite3.connect(self.db_path) as conn:
            for category in self.categories:
                conn.execute("""
                    INSERT OR IGNORE INTO categories (name, description, created_at)
                    VALUES (?, ?, ?)
                """, (category["name"], category["description"], datetime.now().isoformat()))
            conn.commit()
    
    def start_session(self, context: PluginContext) -> PluginResponse:
        """Start a new bulletin board session"""
        # Show welcome message and main bulletin menu
        welcome_text = (
            "Bulletin Board\n\n"
            "1. Post\n"
            "2. Read\n"
            "3. Browse\n"
            "4. Search\n"
            "5. Stats\n"
            "9. Help\n"
            "0. Exit\n\n"
            "Choice:"
        )
        
        session_data = {
            f"{self.name}_active": True,
            f"{self.name}_state": "main_menu",
            f"{self.name}_page": 0
        }
        
        return PluginResponse(
            text=welcome_text,
            continue_session=True,
            session_data=session_data
        )
    
    def continue_session(self, context: PluginContext) -> PluginResponse:
        """Continue an existing bulletin board session"""
        state = context.session_data.get(f"{self.name}_state", "main_menu")
        user_input = context.message.text.strip()
        
        try:
            if state == "main_menu":
                return self._handle_main_menu(context, user_input)
            elif state == "posting_category":
                return self._handle_posting_category(context, user_input)
            elif state == "posting_subject":
                return self._handle_posting_subject(context, user_input)
            elif state == "posting_content":
                return self._handle_posting_content(context, user_input)
            elif state == "reading_bulletins":
                return self._handle_reading_bulletins(context, user_input)
            elif state == "browsing_categories":
                return self._handle_browsing_categories(context, user_input)
            elif state == "searching":
                return self._handle_searching(context, user_input)
            else:
                # Unknown state, return to main menu
                return self.start_session(context)
                
        except Exception as e:
            self.logger.error(f"Error in bulletin session: {e}")
            return PluginResponse(
                text="❌ An error occurred. Returning to main menu.",
                continue_session=True,
                session_data={f"{self.name}_active": True, f"{self.name}_state": "main_menu"}
            )
    
    def _handle_main_menu(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle main menu selection"""
        # Accept both numeric and abbreviated commands
        user_input = user_input.upper()
        
        if user_input == "1" or user_input == "P":
            # Start posting process
            categories = self.storage.get_categories()
            if not categories:
                categories = [{"name": cat["name"], "description": cat["description"]} 
                             for cat in self.categories]
            
            category_text = "Post Bulletin\n\nCategory:\n\n"
            for i, cat in enumerate(categories, 1):
                category_text += f"{i}. {cat['name']}\n"
            category_text += "\nNumber:"
            
            context.session_data[f"{self.name}_state"] = "posting_category"
            context.session_data[f"{self.name}_categories"] = categories
            
            return PluginResponse(
                text=category_text,
                continue_session=True,
                session_data=context.session_data
            )
        
        elif user_input == "2" or user_input == "R":
            # Read recent bulletins
            return self._show_recent_bulletins(context)
        
        elif user_input == "3" or user_input == "B":
            # Browse by category
            return self._show_categories(context)
        
        elif user_input == "4" or user_input == "S":
            # Search bulletins
            context.session_data[f"{self.name}_state"] = "searching"
            return PluginResponse(
                text="Search\n\nTerm:",
                continue_session=True,
                session_data=context.session_data
            )
        
        elif user_input == "5":
            # Show statistics
            return self._show_statistics(context)
        
        elif user_input == "9" or user_input == "H":
            # Show help
            return self._show_help(context)
        
        elif user_input == "0":
            # Exit
            return PluginResponse(
                text="Thanks! 73!",
                continue_session=False
            )
        
        else:
            return PluginResponse(
                text="Invalid. Enter 1-5, 9, or 0.",
                continue_session=True,
                session_data=context.session_data
            )
    
    def _handle_posting_category(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle category selection for posting"""
        categories = context.session_data.get(f"{self.name}_categories", [])
        
        try:
            choice = int(user_input) - 1
            if 0 <= choice < len(categories):
                selected_category = categories[choice]["name"]
                context.session_data[f"{self.name}_selected_category"] = selected_category
                context.session_data[f"{self.name}_state"] = "posting_subject"
                
                return PluginResponse(
                    text=f"To: {selected_category}\n\nSubject:",
                    continue_session=True,
                    session_data=context.session_data
                )
            else:
                return PluginResponse(
                    text="Invalid number:",
                    continue_session=True,
                    session_data=context.session_data
                )
        except ValueError:
            return PluginResponse(
                text="Enter valid number:",
                continue_session=True,
                session_data=context.session_data
            )
    
    def _handle_posting_subject(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle subject entry for posting"""
        if len(user_input.strip()) < 3:
            return PluginResponse(
                text="Subject too short (min 3 chars):",
                continue_session=True,
                session_data=context.session_data
            )
        
        if len(user_input) > 100:
            return PluginResponse(
                text="Subject too long (max 100 chars):",
                continue_session=True,
                session_data=context.session_data
            )
        
        context.session_data[f"{self.name}_subject"] = user_input.strip()
        context.session_data[f"{self.name}_state"] = "posting_content"
        
        return PluginResponse(
            text=f"Subject: {user_input.strip()}\n\nContent:",
            continue_session=True,
            session_data=context.session_data
        )
    
    def _handle_posting_content(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle content entry and post the bulletin"""
        if len(user_input.strip()) < 10:
            return PluginResponse(
                text="Content too short (min 10 chars):",
                continue_session=True,
                session_data=context.session_data
            )
        
        if len(user_input) > self.max_bulletin_length:
            return PluginResponse(
                text=f"Content too long (max {self.max_bulletin_length} chars):",
                continue_session=True,
                session_data=context.session_data
            )
        
        # Post the bulletin
        category = context.session_data[f"{self.name}_selected_category"]
        subject = context.session_data[f"{self.name}_subject"]
        content = user_input.strip()
        
        try:
            bulletin_id = self.storage.post_bulletin(
                author_id=context.user_id,
                author_name=context.user_name,
                category=category,
                subject=subject,
                content=content
            )
            
            success_text = (
                f"Posted! ID #{bulletin_id}\n"
                f"Category: {category}\n"
                f"Subject: {subject}"
            )
            
            # Return to main menu
            success_text += f"\n\n{self._get_abbreviated_menu()}"
            return PluginResponse(
                text=success_text,
                continue_session=True,
                session_data={
                    f"{self.name}_active": True,
                    f"{self.name}_state": "main_menu",
                    f"{self.name}_page": 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error posting bulletin: {e}")
            return PluginResponse(
                text=f"Error posting. Try later.\n\n{self._get_abbreviated_menu()}",
                continue_session=True,
                session_data={
                    f"{self.name}_active": True,
                    f"{self.name}_state": "main_menu",
                    f"{self.name}_page": 0
                }
            )
    
    def _show_recent_bulletins(self, context: PluginContext) -> PluginResponse:
        """Show recent bulletins"""
        bulletins = self.storage.get_bulletins(limit=self.bulletins_per_page)
        
        if not bulletins:
            return PluginResponse(
                text=f"No bulletins found.\n\n{self._get_abbreviated_menu()}",
                continue_session=True,
                session_data=context.session_data
            )
        
        text = "Recent\n\n"
        for bulletin in bulletins:
            text += f"#{bulletin.id} {bulletin.subject}\n"
            text += f"{bulletin.author_name} {bulletin.timestamp.strftime('%m/%d %H:%M')}\n"
            text += f"{bulletin.content[:80]}{'...' if len(bulletin.content) > 80 else ''}\n\n"
        
        text += f"Enter bulletin # to read, or {self._get_reading_menu()}"
        
        # Set session state to reading_bulletins and store bulletin list
        context.session_data[f"{self.name}_state"] = "reading_bulletins"
        context.session_data[f"{self.name}_bulletin_list"] = [b.id for b in bulletins]
        
        return PluginResponse(
            text=text,
            continue_session=True,
            session_data=context.session_data
        )
    
    def _show_categories(self, context: PluginContext) -> PluginResponse:
        """Show bulletin categories"""
        categories = self.storage.get_categories()
        
        if not categories:
            return PluginResponse(
                text=f"No categories.\n\n{self._get_abbreviated_menu()}",
                continue_session=True
            )
        
        text = "Categories\n\n"
        for cat in categories:
            text += f"{cat['name']} ({cat['count']})\n"
        
        text += f"\n{self._get_abbreviated_menu()}"
        
        return PluginResponse(
            text=text,
            continue_session=True
        )
    
    def _show_statistics(self, context: PluginContext) -> PluginResponse:
        """Show bulletin board statistics"""
        stats = self.storage.get_stats()
        
        text = (
            f"Stats\n\n"
            f"Total: {stats['total_bulletins']}\n"
            f"Recent: {stats['recent_bulletins']}\n"
            f"Users: {stats['active_users']}\n\n"
        )
        
        for category, count in stats['categories'].items():
            text += f"   {category}: {count} bulletins\n"
        
        text += f"\n{self._get_abbreviated_menu()}"
        
        return PluginResponse(
            text=text,
            continue_session=True
        )
    
    def _get_abbreviated_menu(self) -> str:
        """Get inline abbreviated menu for post-function display"""
        return "R)ead, P)ost, B)rowse, S)earch, H)elp, 0)Exit:"
    
    def _get_reading_menu(self) -> str:
        """Get inline menu for bulletin reading context"""
        return "# to read, R)efresh, M)ain menu, 0)Exit:"
    
    def _show_help(self, context: PluginContext) -> PluginResponse:
        """Show help information"""
        text = (
            "Help\n\n"
            "Functions:\n"
            "• Post bulletins\n"
            "• Read bulletins\n"
            "• Search topics\n"
            "• Browse categories\n\n"
            "Tips: Keep subjects clear, choose appropriate categories, be respectful.\n\n"
            "Happy meshing!\n\n"
        )
        
        text += self._get_abbreviated_menu()
        
        return PluginResponse(
            text=text,
            continue_session=True
        )
    
    def _show_full_bulletin(self, context: PluginContext, bulletin_id: int) -> PluginResponse:
        """Display a full bulletin by ID"""
        bulletin = self.storage.get_bulletin_by_id(bulletin_id)
        
        if not bulletin:
            return PluginResponse(
                text=f"Bulletin #{bulletin_id} not found.\n\n{self._get_reading_menu()}",
                continue_session=True,
                session_data=context.session_data
            )
        
        text = (
            f"Bulletin #{bulletin.id}\n"
            f"From: {bulletin.author_name}\n"
            f"Date: {bulletin.timestamp.strftime('%m/%d/%Y %H:%M')}\n"
            f"Category: {bulletin.category}\n"
            f"Subject: {bulletin.subject}\n\n"
            f"{bulletin.content}\n\n"
            f"{self._get_reading_menu()}"
        )
        
        return PluginResponse(
            text=text,
            continue_session=True,
            session_data=context.session_data
        )
    
    def _handle_reading_bulletins(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle bulletin reading menu input"""
        user_input = user_input.strip().upper()
        
        # Handle menu commands
        if user_input == "R":
            # Refresh bulletin list
            return self._show_recent_bulletins(context)
        
        elif user_input == "M":
            # Return to main menu
            context.session_data[f"{self.name}_state"] = "main_menu"
            welcome_text = (
                "Bulletin Board\n\n"
                "1. Post\n"
                "2. Read\n"
                "3. Browse\n"
                "4. Search\n"
                "5. Stats\n"
                "9. Help\n"
                "0. Exit\n\n"
                "Choice:"
            )
            return PluginResponse(
                text=welcome_text,
                continue_session=True,
                session_data=context.session_data
            )
        
        elif user_input == "0":
            # Exit plugin
            return PluginResponse(
                text="Thanks! 73!",
                continue_session=False
            )
        
        # Check if input is a bulletin ID number
        try:
            bulletin_id = int(user_input)
            bulletin_list = context.session_data.get(f"{self.name}_bulletin_list", [])
            
            if bulletin_id in bulletin_list:
                return self._show_full_bulletin(context, bulletin_id)
            else:
                return PluginResponse(
                    text=f"Bulletin #{bulletin_id} not in current list.\n\n{self._get_reading_menu()}",
                    continue_session=True,
                    session_data=context.session_data
                )
        
        except ValueError:
            # Invalid input
            return PluginResponse(
                text=f"Invalid selection '{user_input}'. {self._get_reading_menu()}",
                continue_session=True,
                session_data=context.session_data
            )
    
    def _handle_searching(self, context: PluginContext, user_input: str) -> PluginResponse:
        """Handle bulletin search"""
        if len(user_input.strip()) < 2:
            return PluginResponse(
                text="Term too short (min 2 chars):",
                continue_session=True,
                session_data=context.session_data
            )
        
        bulletins = self.storage.search_bulletins(user_input.strip())
        
        if not bulletins:
            return PluginResponse(
                text=f"No results for '{user_input.strip()}'\n\n{self._get_abbreviated_menu()}",
                continue_session=True
            )
        
        text = f"Results '{user_input.strip()}'\n\n"
        for bulletin in bulletins[:10]:  # Limit to 10 results
            text += f"#{bulletin.id} {bulletin.subject}\n"
            text += f"{bulletin.author_name} {bulletin.timestamp.strftime('%m/%d')}\n"
            text += f"{bulletin.content[:60]}{'...' if len(bulletin.content) > 60 else ''}\n\n"
        
        if len(bulletins) > 10:
            text += f"+{len(bulletins) - 10} more\n\n"
        else:
            text += "\n"
        
        text += self._get_abbreviated_menu()
        
        return PluginResponse(
            text=text,
            continue_session=True
        )
    
    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        try:
            # Check database path is writable
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Validate categories
            if not isinstance(self.categories, list) or not self.categories:
                self.logger.error("Invalid categories configuration")
                return False
            
            # Test database connection
            self.storage._ensure_database()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False