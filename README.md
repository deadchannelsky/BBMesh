# BBMesh - Meshtastic BBS System

📋 **[Release Planning & Roadmap](todo.md)** - Current development status and beta release plan

A bulletin board system (BBS) for Meshtastic mesh networks, inspired by the classic BBS systems of the early computing era. BBMesh provides an interactive, menu-driven interface accessible through Meshtastic radio nodes, bringing the nostalgic experience of dial-up BBSs to modern mesh networking.

## Features

- **Classic BBS Experience**: Hierarchical menu system with configurable options
- **Meshtastic Integration**: Direct serial connection to ESP32-based Meshtastic nodes
- **Plugin Architecture**: Extensible system for games, utilities, and custom scripts
- **Multi-Channel Support**: Monitor and respond to multiple Meshtastic channels
- **Configuration-Driven**: All settings managed through YAML configuration files
- **Interactive Sessions**: Stateful conversations with multiple users simultaneously

## Hardware Requirements

- **Raspberry Pi** (or similar Linux system) as the host
- **Heltec ESP32 V3** (or compatible Meshtastic node) connected via USB/Serial
- **LoRa Antenna** appropriate for your region's frequency band

## Quick Start

1. **Install BBMesh**:
   ```bash
   pip install -e .
   ```

2. **Generate default configuration**:
   ```bash
   bbmesh init-config
   ```

3. **Edit configuration** to match your setup:
   ```bash
   nano config/bbmesh.yaml
   ```

4. **Start the server**:
   ```bash
   bbmesh start
   ```

## Configuration

BBMesh uses YAML configuration files located in the `config/` directory:

- `bbmesh.yaml`: Main system configuration
- `menus.yaml`: Menu structure and navigation
- `plugins.yaml`: Plugin settings and parameters

See the [Configuration Guide](docs/configuration.md) for detailed setup instructions.

## Architecture

```
BBMesh/
├── src/bbmesh/
│   ├── core/        # Message handling, serial communication
│   ├── menus/       # Menu system and navigation
│   ├── plugins/     # Games, utilities, and extensions
│   └── utils/       # Logging, configuration, helpers
├── config/          # Configuration files
├── data/            # User data and message history
└── logs/            # System and access logs
```

## Plugin Development

BBMesh supports custom plugins for games, utilities, and integrations. See the [Plugin Development Guide](docs/plugins.md) for creating your own extensions.

## Development Workflow

### Git Branching Strategy

- **main**: Stable, production-ready code
- **develop**: Integration branch for ongoing development (default branch for new features)
- **feature/**: Individual feature development branches (branch from `develop`)
- **release/**: Release preparation branches (e.g., `release/0.2.0-beta.1`)
- **hotfix/**: Critical bug fixes for production

### Development Workflow

1. **New features**: Create feature branches from `develop`
   ```bash
   git checkout develop
   git checkout -b feature/new-feature-name
   ```

2. **Feature completion**: Merge back to `develop`
   ```bash
   git checkout develop
   git merge feature/new-feature-name
   ```

### Release Process

1. Create release branch from `develop`: `git checkout -b release/x.y.z-beta.n`
2. Update version in `pyproject.toml` and `CHANGELOG.md`
3. Test and finalize release candidate
4. Merge release branch to `main` and tag: `git tag vx.y.z-beta.n`
5. Merge release branch back to `develop` to sync changes

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for information on how to get started.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the classic BBS systems of the 1980s and 1990s
- Built on the excellent [Meshtastic](https://meshtastic.org/) mesh networking platform
- Thanks to the amateur radio and mesh networking communities