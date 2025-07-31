# BBMesh Bulletin Board System Plugin

A feature-rich bulletin board system plugin for BBMesh that provides community messaging and information sharing capabilities within mesh networks.

## Overview

This plugin extends BBMesh with a classic bulletin board system, allowing users to:
- Post community bulletins and announcements
- Read and browse messages by category
- Search and organize community content
- Manage bulletin board administration

## Features

- **Interactive Bulletin Posting**: Multi-step posting process with categories and subjects
- **Bulletin Reading**: Browse and read community messages
- **Category Organization**: Organize bulletins by topics and categories
- **Search Functionality**: Find specific bulletins and content
- **Administrative Tools**: Manage bulletins, categories, and system settings
- **BBMesh Integration**: Seamlessly integrates with BBMesh menu system and conventions

## Installation

### Prerequisites
- BBMesh v0.2.0-beta.1 or later
- Python 3.8+
- Dependencies listed in requirements.txt

### Automatic Installation
```bash
cd plugins/bbmesh_bulletin_plugin
python install.py
```

### Manual Installation
1. Copy plugin files to BBMesh plugins directory
2. Add plugin configuration to BBMesh's `config/plugins.yaml`
3. Add menu entries to BBMesh's `config/menus.yaml`
4. Restart BBMesh service

## Plugin Architecture

This plugin follows BBMesh's plugin architecture patterns:
- Extends `InteractivePlugin` for multi-turn conversations
- Uses BBMesh's session management for state persistence
- Integrates with BBMesh's menu system and navigation
- Follows BBMesh's logging and error handling conventions

## Usage

Once installed, the bulletin system is accessible through the BBMesh main menu:
1. Connect to BBMesh BBS
2. Select "Bulletin Board" from main menu
3. Choose from available bulletin options:
   - Post New Bulletin
   - Read Bulletins
   - Search Bulletins
   - Manage System (admin)

## Development

This plugin can be developed independently while maintaining BBMesh integration:

```bash
# Clone plugin repository
git clone [plugin-repo-url]
cd bbmesh_bulletin_plugin

# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Install to BBMesh for testing
python install.py --dev
```

## Configuration

Plugin configuration is managed through BBMesh's standard configuration system:

```yaml
# In BBMesh's config/plugins.yaml
bulletin_system:
  enabled: true
  description: "Community bulletin board system"
  max_bulletins: 1000
  categories: ["General", "Announcements", "Emergency", "Community"]
  admin_users: ["admin_node_id"]
  timeout: 60
```

## Database Schema

The plugin uses SQLite for bulletin storage:
- `bulletins`: Bulletin messages and metadata
- `categories`: Bulletin categories and organization
- `users`: User activity and permissions

## License

This plugin follows the same license as BBMesh (MIT License).

## Contributing

Contributions welcome! Please follow BBMesh's plugin development guidelines and submit pull requests for review.