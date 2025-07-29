# Contributing to BBMesh

Thank you for your interest in contributing to BBMesh! This document provides guidelines and information for contributors.

## Development Environment Setup

### Prerequisites
- Python 3.8 or higher
- Git
- A Meshtastic-compatible device for testing (optional)

### Setting Up Your Development Environment

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/BBMesh.git
   cd BBMesh
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run Tests**
   ```bash
   python test_bbmesh.py
   pytest tests/  # When unit tests are added
   ```

## Code Style Guidelines

### Python Code Standards
- **Black**: Code formatting (line length: 88 characters)
- **flake8**: Linting and style checking
- **mypy**: Type checking (encouraged)
- **pytest**: Testing framework

### Pre-commit Hooks
We recommend using pre-commit hooks to maintain code quality:

```bash
pip install pre-commit
pre-commit install
```

### Code Style Rules
1. **Imports**: Use absolute imports, group by standard library, third-party, local
2. **Docstrings**: Use Google-style docstrings for all public functions and classes
3. **Type Hints**: Add type hints to function signatures
4. **Comments**: Write clear, concise comments explaining "why", not "what"
5. **Variable Names**: Use descriptive names (avoid abbreviations)

### Example Code Style
```python
from typing import Optional, Dict, Any
from datetime import datetime

from .base import BBMeshPlugin


class ExamplePlugin(BBMeshPlugin):
    """
    Example plugin demonstrating proper code style.
    
    This plugin shows how to implement a basic BBMesh plugin
    following the project's coding standards.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.last_executed: Optional[datetime] = None
    
    def execute(self, context: PluginContext) -> PluginResponse:
        """
        Execute the plugin with the given context.
        
        Args:
            context: Plugin execution context containing user and message data
            
        Returns:
            Plugin response with text and session management info
        """
        self.last_executed = datetime.now()
        return PluginResponse(text="Hello from example plugin!")
```

## Testing Guidelines

### Running Tests
- **System Test**: `python test_bbmesh.py` - Tests without hardware
- **Unit Tests**: `pytest tests/` - Individual component tests
- **Integration Tests**: Test with actual Meshtastic hardware when possible

### Writing Tests
1. **Test Coverage**: Aim for >80% code coverage
2. **Test Types**: Unit tests for individual functions, integration tests for workflows
3. **Mock Objects**: Use mocks for external dependencies (serial, network)
4. **Test Naming**: Use descriptive test names that explain the scenario

### Test Example
```python
def test_calculator_plugin_basic_arithmetic():
    """Test that calculator plugin handles basic arithmetic correctly."""
    plugin = CalculatorPlugin("calc", {"enabled": True})
    context = create_test_context(message_text="2 + 2")
    
    response = plugin.execute(context)
    
    assert "2 + 2 = 4" in response.text
    assert response.error is None
```

## Pull Request Process

### Before Submitting
1. **Test Your Changes**: Run all tests and ensure they pass
2. **Update Documentation**: Update relevant docs if you change functionality
3. **Check Code Style**: Run black, flake8, and fix any issues
4. **Update CHANGELOG**: Add entry describing your changes

### Pull Request Guidelines
1. **Clear Title**: Summarize the change in the title
2. **Detailed Description**: Explain what changed and why
3. **Link Issues**: Reference related GitHub issues
4. **Screenshots**: Include screenshots for UI changes
5. **Breaking Changes**: Clearly mark any breaking changes

### PR Template
```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

## Issue Reporting

### Bug Reports
Include the following information:
- **BBMesh Version**: `bbmesh --version`
- **Python Version**: `python --version`
- **Operating System**: OS and version
- **Hardware**: Meshtastic device model
- **Configuration**: Relevant config sections (sanitized)
- **Log Output**: Error messages and relevant logs
- **Steps to Reproduce**: Clear reproduction steps

### Feature Requests
- **Use Case**: Describe the problem you're trying to solve
- **Proposed Solution**: Your idea for implementing the feature
- **Alternatives**: Other solutions you've considered
- **Additional Context**: Screenshots, examples, references

## Development Areas

### High Priority Contributions Needed
- **Plugin Development**: New games, utilities, integrations
- **Hardware Support**: Testing with different Meshtastic devices
- **Documentation**: Tutorials, examples, API documentation
- **Testing**: Unit tests, integration tests, hardware testing
- **Performance**: Optimization for resource-constrained devices

### Plugin Development
See [docs/plugins.md](docs/plugins.md) for detailed plugin development guide.

### Core Development
- **Message Handling**: Improvements to message processing
- **Menu System**: Enhanced navigation and display options
- **Configuration**: New configuration options and validation
- **Logging**: Better logging and monitoring capabilities

## Community Guidelines

### Communication
- **Be Respectful**: Treat all contributors with respect
- **Be Constructive**: Provide helpful feedback and suggestions
- **Stay On Topic**: Keep discussions focused on the project
- **Help Others**: Assist other contributors when possible

### Recognition
- Contributors are recognized in release notes
- Significant contributions may be highlighted in README
- All contributors are listed in project acknowledgments

## Getting Help

### Resources
- **Documentation**: Check docs/ directory first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Examples**: Look at existing plugins and code for patterns

### Contact
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions

## License

By contributing to BBMesh, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to BBMesh! Your help makes this project better for the entire Meshtastic community.