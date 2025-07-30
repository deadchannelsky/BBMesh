"""
Message handling and user session management for BBMesh
"""

import time
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from .config import Config
from .meshtastic_interface import MeshtasticInterface, MeshMessage
from ..utils.logger import BBMeshLogger


@dataclass
class UserSession:
    """Represents an active user session"""
    user_id: str
    user_name: str
    channel: int
    last_activity: datetime
    current_menu: str = "main"
    menu_history: List[str] = None
    context: Dict[str, any] = None
    message_count: int = 0
    
    def __post_init__(self):
        if self.menu_history is None:
            self.menu_history = []
        if self.context is None:
            self.context = {}


class RateLimiter:
    """Simple rate limiter for message handling"""
    
    def __init__(self, max_messages: int, window_seconds: int):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_times: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is allowed to send more messages"""
        now = time.time()
        user_times = self.message_times[user_id]
        
        # Remove old timestamps
        cutoff = now - self.window_seconds
        user_times[:] = [t for t in user_times if t > cutoff]
        
        # Check if under limit
        if len(user_times) < self.max_messages:
            user_times.append(now)
            return True
        
        return False


class MessageHandler:
    """
    Handles incoming messages and manages user sessions
    """
    
    def __init__(self, config: Config, mesh_interface: MeshtasticInterface):
        self.config = config
        self.mesh_interface = mesh_interface
        self.logger = BBMeshLogger(__name__)
        
        # User session management
        self.active_sessions: Dict[str, UserSession] = {}
        self.last_cleanup = time.time()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            config.server.rate_limit_messages,
            config.server.rate_limit_window
        )
        
        # Statistics
        self.stats = {
            "total_messages": 0,
            "direct_messages": 0,
            "broadcast_messages": 0,
            "rate_limited": 0,
            "session_timeouts": 0,
            "start_time": datetime.now()
        }
        
        # Command patterns
        self.help_patterns = [
            r"^help$", r"^h$", r"^\?$", r"^commands?$"
        ]
        self.menu_patterns = [
            r"^menu$", r"^main$", r"^bbs$", r"^start$"
        ]
        
    def initialize(self) -> None:
        """Initialize the message handler"""
        self.logger.info("Message handler initialized")
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("Message handler cleanup")
        self.active_sessions.clear()
    
    def handle_message(self, message: MeshMessage) -> None:
        """
        Handle an incoming Meshtastic message
        
        Args:
            message: Received message
        """
        try:
            self.stats["total_messages"] += 1
            
            if message.is_direct:
                self.stats["direct_messages"] += 1
            else:
                self.stats["broadcast_messages"] += 1
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(message.sender_id):
                self.stats["rate_limited"] += 1
                self.logger.warning(f"Rate limited user {message.sender_name} ({message.sender_id})")
                self._send_rate_limit_message(message)
                return
            
            # Clean up expired sessions periodically
            self._cleanup_expired_sessions()
            
            # Process the message
            self._process_message(message)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _process_message(self, message: MeshMessage) -> None:
        """
        Process a message and generate appropriate response
        
        Args:
            message: Message to process
        """
        # Get or create user session
        session = self._get_or_create_session(message)
        session.last_activity = datetime.now()
        session.message_count += 1
        
        # Clean and normalize message text
        text = message.text.strip().lower()
        
        # Handle different types of commands/messages
        if self._is_help_request(text):
            self._handle_help_request(message, session)
        elif self._is_menu_request(text):
            self._handle_menu_request(message, session)
        elif text in ["ping", "test"]:
            self._handle_ping(message, session)
        elif text in ["status", "info"]:
            self._handle_status(message, session)
        elif text in ["time", "date"]:
            self._handle_time(message, session)
        elif message.is_direct:
            # Direct message - could be menu navigation or general response
            self._handle_direct_message(message, session)
        else:
            # Broadcast message - only respond if specifically mentioned
            if self._is_mentioned(message.text):
                self._handle_mention(message, session)
    
    def _get_or_create_session(self, message: MeshMessage) -> UserSession:
        """
        Get existing session or create new one for user
        
        Args:
            message: Message from user
            
        Returns:
            User session
        """
        user_key = f"{message.sender_id}:{message.channel}"
        
        if user_key not in self.active_sessions:
            self.active_sessions[user_key] = UserSession(
                user_id=message.sender_id,
                user_name=message.sender_name,
                channel=message.channel,
                last_activity=datetime.now()
            )
            self.logger.info(f"Created new session for {message.sender_name} ({message.sender_id})")
        
        return self.active_sessions[user_key]
    
    def _is_help_request(self, text: str) -> bool:
        """Check if message is a help request"""
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in self.help_patterns)
    
    def _is_menu_request(self, text: str) -> bool:
        """Check if message is a menu request"""
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in self.menu_patterns)
    
    def _is_mentioned(self, text: str) -> bool:
        """Check if the BBS is mentioned in the message"""
        mention_patterns = [
            r"\bbbs\b", r"\bbbmesh\b", r"\bmesh.*bbs\b"
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in mention_patterns)
    
    def _handle_help_request(self, message: MeshMessage, session: UserSession) -> None:
        """Handle help/command requests"""
        help_text = (
            f"📻 {self.config.server.name} Commands:\\n"
            f"MENU - Main menu\\n"
            f"HELP - This help\\n"
            f"PING - Test response\\n"
            f"STATUS - System info\\n"
            f"TIME - Current time"
        )
        self._send_response(message, session, help_text)
    
    def _handle_menu_request(self, message: MeshMessage, session: UserSession) -> None:
        """Handle main menu requests"""
        menu_text = (
            f"🏠 {self.config.server.name} Main Menu:\\n"
            f"1. Help & Commands\\n"
            f"2. System Status\\n"
            f"3. Time & Date\\n"
            f"4. Mesh Info\\n"
            f"Send number or name"
        )
        session.current_menu = "main"
        self._send_response(message, session, menu_text)
    
    def _handle_ping(self, message: MeshMessage, session: UserSession) -> None:
        """Handle ping requests"""
        response = f"🏓 Pong! BBMesh is alive. Signal: {message.snr:.1f}dB SNR, {message.rssi}dBm RSSI"
        self._send_response(message, session, response)
    
    def _handle_status(self, message: MeshMessage, session: UserSession) -> None:
        """Handle status requests"""
        mesh_info = self.mesh_interface.get_mesh_info()
        uptime = datetime.now() - self.stats["start_time"]
        
        status_text = (
            f"📊 System Status:\\n"
            f"Uptime: {uptime.days}d {uptime.seconds//3600}h\\n"
            f"Messages: {self.stats['total_messages']}\\n"
            f"Sessions: {len(self.active_sessions)}\\n"
            f"Mesh Nodes: {mesh_info.get('node_count', 0)}"
        )
        self._send_response(message, session, status_text)
    
    def _handle_time(self, message: MeshMessage, session: UserSession) -> None:
        """Handle time requests"""
        now = datetime.now()
        time_text = f"🕒 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        self._send_response(message, session, time_text)
    
    def _handle_direct_message(self, message: MeshMessage, session: UserSession) -> None:
        """Handle direct messages"""
        text = message.text.strip().lower()
        
        # Check for menu navigation numbers
        if text.isdigit():
            menu_num = int(text)
            if session.current_menu == "main":
                if menu_num == 1:
                    self._handle_help_request(message, session)
                elif menu_num == 2:
                    self._handle_status(message, session)
                elif menu_num == 3:
                    self._handle_time(message, session)
                elif menu_num == 4:
                    self._handle_mesh_info(message, session)
                else:
                    self._send_response(message, session, "❌ Invalid option. Send MENU for options.")
                return
        
        # Default response for unrecognized direct messages
        welcome_response = (
            f"👋 Welcome to {self.config.server.name}!\\n"
            f"{self.config.server.welcome_message}\\n"
            f"Send HELP for commands or MENU for main menu."
        )
        self._send_response(message, session, welcome_response)
    
    def _handle_mention(self, message: MeshMessage, session: UserSession) -> None:
        """Handle broadcast messages that mention the BBS"""
        response = f"👋 Hi {message.sender_name}! Send me a direct message for the {self.config.server.name} menu."
        self._send_response(message, session, response)
    
    def _handle_mesh_info(self, message: MeshMessage, session: UserSession) -> None:
        """Handle mesh network info requests"""
        mesh_info = self.mesh_interface.get_mesh_info()
        
        info_text = (
            f"🌐 Mesh Network Info:\\n"
            f"Local Node: {mesh_info.get('local_node_id', 'Unknown')}\\n"
            f"Connected Nodes: {mesh_info.get('node_count', 0)}\\n"
            f"Channels: {len(mesh_info.get('monitored_channels', []))}\\n"
            f"Status: {'Connected' if mesh_info.get('connected') else 'Disconnected'}"
        )
        self._send_response(message, session, info_text)
    
    def _send_response(self, message: MeshMessage, session: UserSession, 
                      response_text: str) -> None:
        """
        Send a response message
        
        Args:
            message: Original message
            session: User session
            response_text: Text to send
        """
        try:
            # Determine destination and channel based on message type
            if message.is_direct:
                # For direct messages, always respond back as direct message to sender
                destination = message.sender_id
                channel = 0  # Direct messages use channel 0
            else:
                # For broadcast messages, respond on the same channel
                destination = None  # Broadcast response
                channel = message.channel
            
            # Check if channel is allowed for responses
            if channel not in self.config.meshtastic.response_channels:
                self.logger.warning(f"Channel {channel} not in response channels")
                return
            
            # Send the message
            success = self.mesh_interface.send_message(
                text=response_text,
                channel=channel,
                destination=destination
            )
            
            if success:
                self.logger.log_message(
                    "TX", session.user_name, channel, 
                    response_text, self.mesh_interface.local_node_id
                )
            else:
                self.logger.error(f"Failed to send response to {session.user_name}")
                
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    def _send_rate_limit_message(self, message: MeshMessage) -> None:
        """Send rate limit notification"""
        if message.is_direct:
            rate_limit_text = "⚠️ Too many messages. Please wait before sending more."
            self.mesh_interface.send_message(
                text=rate_limit_text,
                channel=message.channel,
                destination=message.sender_id
            )
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired user sessions"""
        now = time.time()
        
        # Only cleanup every 60 seconds
        if now - self.last_cleanup < 60:
            return
        
        self.last_cleanup = now
        timeout_seconds = self.config.server.session_timeout
        cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)
        
        expired_sessions = [
            key for key, session in self.active_sessions.items()
            if session.last_activity < cutoff_time
        ]
        
        for key in expired_sessions:
            session = self.active_sessions.pop(key)
            self.stats["session_timeouts"] += 1
            self.logger.info(f"Expired session for {session.user_name} ({session.user_id})")
    
    def process_pending_tasks(self) -> None:
        """Process any pending background tasks"""
        # This method can be extended for future background processing
        pass
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get message handler statistics
        
        Returns:
            Statistics dictionary
        """
        return {
            **self.stats,
            "active_sessions": len(self.active_sessions),
            "session_users": [
                {
                    "user_name": session.user_name,
                    "user_id": session.user_id,
                    "channel": session.channel,
                    "last_activity": session.last_activity.isoformat(),
                    "message_count": session.message_count
                }
                for session in self.active_sessions.values()
            ]
        }