# Pandas Migration Agent Structure

This document outlines the complete structure of the Pandas Migration Agent for OpenHands.

## Directory Structure

```
pandas_migration_agent/
├── __init__.py                  # Package initialization and exports
├── agent.py                     # Main agent class (EnhancedPandasMigrationAgent)
├── migration_rules.py           # Migration rule engine with AST transformations
├── test_runner.py               # Test execution using conda environments
├── compatibility_checker.py     # Compatibility analysis and validation
├── report_generator.py          # Multi-format report generation
├── utils.py                     # Utility functions for file operations
├── config.yaml                  # Main configuration file
├── config.json                  # Legacy configuration (for reference)
├── README.md                    # Comprehensive documentation
├── example_usage.py             # Usage examples and patterns
├── test_agent.py                # Basic unit tests
│
├── prompts/                     # Agent prompts directory
│   ├── system_prompt.md         # System instructions for the agent
│   └── user_prompt_template.md  # Template for user prompts
│
└── tools/                       # Agent tools directory
    ├── __init__.py              # Tools package initialization
    ├── analyze.py               # AnalyzeTool - Repository analysis
    ├── migrate.py               # MigrateTool - Code migration
    ├── test.py                  # TestTool - Test execution
    └── report.py                # ReportTool - Report generation
```

## Key Components

### Core Modules

1. **agent.py**
   - Main `EnhancedPandasMigrationAgent` class
   - Inherits from OpenHands' `Agent` base class
   - Manages migration workflow and state
   - Loads configuration and prompts
   - Registers tools for OpenHands integration

2. **migration_rules.py**
   - `MigrationRuleEngine` class for applying migration patterns
   - `MigrationRule` dataclass for defining rules
   - `PandasASTTransformer` for complex AST-based transformations
   - Priority-based rule application (Critical → High → Medium → Low)

3. **test_runner.py**
   - `TestRunner` class for executing tests
   - Uses existing conda environments (no venv creation)
   - Supports pytest, unittest, and nose frameworks
   - Compares test results between pandas versions

4. **compatibility_checker.py**
   - `CompatibilityChecker` class for code analysis
   - Identifies deprecated features and compatibility issues
   - Uses both regex patterns and AST analysis
   - Generates compatibility reports

5. **report_generator.py**
   - `MigrationReportGenerator` class
   - Supports multiple formats (Markdown, HTML, JSON)
   - Comprehensive reporting with statistics and recommendations

### Configuration

- **config.yaml**: Main configuration file with all settings
- **config.json**: Legacy format (kept for reference)
- Conda environments configured:
  - pandas 0.19.2: `py36-1.1.10`
  - pandas 1.1.5: `pandas_115_final`

### Tools

Each tool is a callable class that integrates with the agent:

1. **AnalyzeTool**: Analyzes repository for pandas usage
2. **MigrateTool**: Applies migration rules to files
3. **TestTool**: Runs tests in conda environments
4. **ReportTool**: Generates migration reports

### Prompts

- **system_prompt.md**: Defines agent behavior and capabilities
- **user_prompt_template.md**: Template for user interactions

## Integration with OpenHands

To use this agent, add to your `config.toml`:

```toml
custom_agents_enabled = true
custom_agents_path = "/path/to/custom_agents"

[[agents.custom]]
name = "PandasMigrationAgent"
module_path = "pandas_migration_agent.agent"
class_name = "EnhancedPandasMigrationAgent"
display_name = "Pandas Migration Agent (0.19 → 1.1.5)"
```

## Features

- **Automated Migration**: Handles all deprecated pandas features
- **Custom Import Mappings**: Maps to your replacement modules
- **Test Validation**: Runs tests in both environments
- **Comprehensive Reporting**: Detailed analysis and recommendations
- **Safety Features**: Automatic backups and rollback support
- **Extensible Design**: Easy to add new rules and features

## Workflow

1. **Discovery**: Find Python files using pandas
2. **Analysis**: Identify deprecated features
3. **Pre-migration Testing**: Run tests with pandas 0.19.2
4. **Migration**: Apply rules and validate syntax
5. **Post-migration Testing**: Run tests with pandas 1.1.5
6. **Reporting**: Generate comprehensive report

The agent ensures zero test regressions and maintains backward compatibility throughout the migration process.