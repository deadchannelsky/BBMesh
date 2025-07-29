# BBMesh Examples

This directory contains example plugins, configurations, and use cases for BBMesh.

## Contents

### Plugin Examples
- **[simple_plugins.py](simple_plugins.py)** - Basic SimpleResponsePlugin examples
- **[interactive_plugins.py](interactive_plugins.py)** - Interactive plugin examples with session management
- **[advanced_plugins.py](advanced_plugins.py)** - Advanced plugins with external API integration
- **[utility_plugins.py](utility_plugins.py)** - Utility plugins for common tasks

### Configuration Examples
- **[minimal_config.yaml](minimal_config.yaml)** - Minimal configuration for basic operation
- **[development_config.yaml](development_config.yaml)** - Development environment settings
- **[production_config.yaml](production_config.yaml)** - Production deployment configuration
- **[pi_zero_config.yaml](pi_zero_config.yaml)** - Resource-constrained system configuration

### Menu Examples
- **[custom_menus.yaml](custom_menus.yaml)** - Custom menu structures and navigation
- **[game_focused_menus.yaml](game_focused_menus.yaml)** - Game-focused BBS setup
- **[utility_menus.yaml](utility_menus.yaml)** - Utility-focused menu organization

### Use Case Examples
- **[ham_radio_setup/](ham_radio_setup/)** - Ham radio emergency communications setup
- **[community_bbs/](community_bbs/)** - Community bulletin board configuration
- **[educational_setup/](educational_setup/)** - Educational/classroom deployment

## Running Examples

### Plugin Examples
```bash
# Test plugin examples
python docs/examples/test_plugins.py

# Install example plugins
cp docs/examples/simple_plugins.py src/bbmesh/plugins/examples.py
```

### Configuration Examples
```bash
# Use example configuration
cp docs/examples/development_config.yaml config/bbmesh.yaml

# Test configuration
bbmesh init-config --output config/test.yaml
python test_bbmesh.py
```

## Contributing Examples

To contribute your own examples:

1. Create example files following the existing patterns
2. Include comprehensive comments and documentation
3. Test examples thoroughly
4. Submit pull request with clear description

## Example Categories

### Beginner Examples
- Simple response plugins
- Basic configuration changes
- Menu customization

### Intermediate Examples
- Interactive plugins with session state
- External API integration
- Custom menu structures

### Advanced Examples
- Complex multi-step interactions
- Database integration
- Performance optimization

## Getting Help

If you need help with any examples:

1. Check the comments in the example files
2. Review the main documentation
3. Search existing GitHub issues
4. Create a new issue with your question

Each example includes:
- Clear documentation and comments
- Configuration requirements
- Testing instructions
- Common troubleshooting tips