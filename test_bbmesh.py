#!/usr/bin/env python3
"""
Test script for BBMesh system - runs without actual Meshtastic hardware
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bbmesh.core.config import Config
from bbmesh.core.meshtastic_interface import MeshMessage
from bbmesh.core.message_handler import MessageHandler
from bbmesh.menus.menu_system import MenuSystem
from bbmesh.plugins.builtin import BUILTIN_PLUGINS
from bbmesh.plugins.base import PluginContext
from bbmesh.utils.logger import setup_logging, BBMeshLogger


class MockMeshtasticInterface:
    """Mock Meshtastic interface for testing"""
    
    def __init__(self):
        self.local_node_id = "test_node_123"
        self.connected = True
        self.sent_messages = []
    
    def send_message(self, text, channel=0, destination=None):
        """Mock send message"""
        self.sent_messages.append({
            "text": text,
            "channel": channel,
            "destination": destination,
            "timestamp": datetime.now()
        })
        print(f"[MOCK TX] CH{channel} -> {destination or 'BROADCAST'}: {text}")
        return True
    
    def get_mesh_info(self):
        """Mock mesh info"""
        return {
            "connected": True,
            "local_node_id": self.local_node_id,
            "node_count": 5,
            "channel_count": 8,
            "monitored_channels": [0, 1, 2],
            "response_channels": [0, 1, 2]
        }


def create_test_message(sender_id="test_user", sender_name="TestUser", 
                       text="help", channel=0, is_direct=True):
    """Create a test message"""
    return MeshMessage(
        sender_id=sender_id,
        sender_name=sender_name,
        channel=channel,
        text=text,
        timestamp=datetime.now(),
        is_direct=is_direct,
        hop_limit=3,
        snr=5.2,
        rssi=-85
    )


def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing configuration system...")
    
    config = Config.load(Path("config/bbmesh.yaml"))
    print(f"✓ Loaded config: {config.server.name}")
    print(f"✓ Serial port: {config.meshtastic.serial.port}")
    print(f"✓ Monitored channels: {config.meshtastic.monitored_channels}")
    print()


def test_menu_system():
    """Test menu system"""
    print("📋 Testing menu system...")
    
    config = Config.load(Path("config/bbmesh.yaml"))
    menu_system = MenuSystem(config.menu)
    
    # Test menu loading
    menus = menu_system.get_available_menus()
    print(f"✓ Loaded {len(menus)} menus: {', '.join(menus)}")
    
    # Test menu display
    main_menu_text = menu_system.get_menu_display("main")
    print(f"✓ Main menu display ({len(main_menu_text)} chars)")
    
    # Test menu navigation
    result = menu_system.process_menu_input("main", "1")
    print(f"✓ Menu input '1' -> action: {result.get('action')}")
    
    # Test validation
    errors = menu_system.validate_menu_structure()
    print(f"✓ Menu validation: {len(errors)} errors")
    
    print()


def test_plugins():
    """Test plugin system"""
    print("🔌 Testing plugin system...")
    
    config = Config.load(Path("config/bbmesh.yaml"))
    
    # Test plugin loading
    print(f"✓ Available plugins: {', '.join(BUILTIN_PLUGINS.keys())}")
    
    # Test help plugin
    help_plugin = BUILTIN_PLUGINS["help"]("help", {"enabled": True})
    help_plugin.initialize()
    
    test_message = create_test_message(text="help")
    context = PluginContext(
        user_id="test_user",
        user_name="TestUser", 
        channel=0,
        session_data={},
        message=test_message,
        plugin_config={}
    )
    
    response = help_plugin.execute(context)
    print(f"✓ Help plugin response: {response.text[:50]}...")
    
    # Test calculator plugin
    calc_plugin = BUILTIN_PLUGINS["calculator"]("calculator", {"enabled": True})
    calc_plugin.initialize()
    
    calc_message = create_test_message(text="2 + 2")
    calc_context = PluginContext(
        user_id="test_user",
        user_name="TestUser",
        channel=0,
        session_data={},
        message=calc_message,
        plugin_config={}
    )
    
    calc_response = calc_plugin.execute(calc_context)
    print(f"✓ Calculator plugin response: {calc_response.text}")
    
    print()


def test_message_handler():
    """Test message handling"""
    print("💬 Testing message handler...")
    
    config = Config.load(Path("config/bbmesh.yaml"))
    mock_interface = MockMeshtasticInterface()
    handler = MessageHandler(config, mock_interface)
    handler.initialize()
    
    # Test help message
    help_msg = create_test_message(text="help")
    handler.handle_message(help_msg)
    print(f"✓ Processed help message")
    
    # Test menu message
    menu_msg = create_test_message(text="menu")
    handler.handle_message(menu_msg)
    print(f"✓ Processed menu message")
    
    # Test ping message
    ping_msg = create_test_message(text="ping")
    handler.handle_message(ping_msg)
    print(f"✓ Processed ping message")
    
    # Check statistics
    stats = handler.get_statistics()
    print(f"✓ Handler stats: {stats['total_messages']} messages, {stats['active_sessions']} sessions")
    
    # Show sent messages
    print(f"✓ Mock interface sent {len(mock_interface.sent_messages)} responses")
    
    handler.cleanup()
    print()


def test_interactive_plugin():
    """Test interactive plugin (number guessing game)"""
    print("🎲 Testing interactive plugin...")
    
    game_plugin = BUILTIN_PLUGINS["number_guess"]("number_guess", {
        "enabled": True,
        "min_number": 1,
        "max_number": 10,
        "max_attempts": 3
    })
    game_plugin.initialize()
    
    # Start game
    start_message = create_test_message(text="guess")
    context = PluginContext(
        user_id="test_user",
        user_name="TestUser",
        channel=0,
        session_data={},
        message=start_message,
        plugin_config={}
    )
    
    response = game_plugin.execute(context)
    print(f"✓ Game start: {response.text[:50]}...")
    print(f"✓ Continue session: {response.continue_session}")
    
    # Make a guess
    if response.continue_session:
        guess_message = create_test_message(text="5")
        guess_context = PluginContext(
            user_id="test_user",
            user_name="TestUser",
            channel=0,
            session_data=response.session_data,
            message=guess_message,
            plugin_config={}
        )
        
        guess_response = game_plugin.execute(guess_context)
        print(f"✓ Guess response: {guess_response.text[:50]}...")
    
    print()


def main():
    """Run all tests"""
    print("🚀 BBMesh System Test")
    print("=" * 50)
    
    # Setup logging for testing
    from bbmesh.core.config import LoggingConfig
    log_config = LoggingConfig(level="INFO", console_output=True, file_path="")
    setup_logging(log_config, debug=False)
    
    try:
        test_configuration()
        test_menu_system()
        test_plugins()
        test_message_handler()
        test_interactive_plugin()
        
        print("✅ All tests completed successfully!")
        print("\nTo start the actual BBMesh server:")
        print("1. Connect your Heltec ESP32 V3 via USB")
        print("2. Update the serial port in config/bbmesh.yaml")
        print("3. Run: bbmesh start")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()