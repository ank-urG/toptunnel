# Pandas Migration Agent for OpenHands

A powerful, automated agent for migrating Python codebases from pandas 0.19.2 to 1.1.5, ensuring backward compatibility and comprehensive testing throughout the process.

## Overview

The Pandas Migration Agent is designed to handle the complex task of upgrading pandas versions in large codebases with multiple microservices. It automatically identifies deprecated features, applies migration rules, runs tests in both environments, and generates detailed reports.

**Core Philosophy: "If it ain't broke, don't fix it!"** - The agent only modifies code that actually has compatibility issues. If your code already works in both pandas 0.19.2 and 1.1.5, it won't be touched.

## Key Features

### 🔍 Intelligent Code Analysis
- Automatically discovers Python files in your repository
- Identifies deprecated pandas features (Panel, OLS, ix, etc.)
- Analyzes pandas API usage patterns
- Performs AST-based code transformations

### 🔄 Automated Migration - Direct Replacements Only
- **Direct API replacements** that work in BOTH pandas 0.19.2 and 1.1.5
- **NO compatibility wrappers or monkey-patching**
- Handles custom import mappings (e.g., `pd.Panel` → `aqr.core.panel.Panel`)
- Clean code transformations (e.g., `.sort()` → `.sort_values()`, `.ix[]` → `.loc[]/.iloc[]`)
- Validates that no wrappers are added

### 🧪 Comprehensive Testing
- Runs tests in both pandas 0.19.2 and 1.1.5 environments
- Supports multiple test frameworks (pytest, unittest, nose)
- Uses existing conda environments (py36-1.1.10 for pandas 0.19.2, pandas_115_final for pandas 1.1.5)
- Compares test results to identify regressions

### 📊 Detailed Reporting
- Generates comprehensive migration reports in multiple formats (Markdown, HTML, JSON)
- Tracks all changes made to each file
- Identifies test regressions and improvements
- Provides actionable recommendations

### 🛡️ Safety Features
- Creates automatic backups before modifying files
- Supports rollback on migration failure
- Validates code syntax after migration
- Maintains strict backward compatibility
- **Never modifies imports that work in both versions** (e.g., `pandas.util.testing`)

## Prerequisites

Before using the agent, ensure you have the following conda environments set up:

1. **For pandas 0.19.2**: Environment named `py36-1.1.10`
   ```bash
   conda activate py36-1.1.10
   python -c "import pandas; print(pandas.__version__)"  # Should show 0.19.2
   ```

2. **For pandas 1.1.5**: Environment named `pandas_115_final`
   ```bash
   conda activate pandas_115_final
   python -c "import pandas; print(pandas.__version__)"  # Should show 1.1.5
   ```

## Installation

1. Place the agent in your OpenHands custom agents directory:
```bash
cp -r pandas_migration_agent /path/to/openhands/custom_agents/
```

2. Update your OpenHands configuration (`config.toml`):
```toml
custom_agents_enabled = true
custom_agents_path = "/path/to/openhands/custom_agents"

[[agents.custom]]
name = "PandasMigrationAgent"
module_path = "pandas_migration_agent.agent"
class_name = "EnhancedPandasMigrationAgent"
display_name = "Pandas Migration Agent (0.19 → 1.1.5)"
```

## Usage

### Basic Migration

```bash
# Start OpenHands with the migration agent
openhands --agent PandasMigrationAgent

# In the chat interface:
"Migrate the repository at /workspace/my-project from pandas 0.19.2 to 1.1.5"
```

### Advanced Configuration

The agent supports various configuration options:

```python
config_options = {
    'auto_rollback_on_failure': True,    # Rollback changes if tests fail
    'run_tests_before_migration': True,   # Run tests before starting
    'run_tests_after_migration': True,    # Run tests after migration
    'create_backups': True,               # Create file backups
    'strict_compatibility': True,         # Enforce strict compatibility
    'max_retries': 3,                    # Retry failed migrations
    'test_timeout': 300,                 # Test timeout in seconds
    'parallel_testing': False,           # Run tests in parallel
    'custom_import_mappings': {          # Custom import replacements
        'pd.Panel': 'aqr.core.panel.Panel',
        'pd.ols': 'aqr.stats.ols.OLS',
        'pd.stats.ols.OLS': 'aqr.stats.ols.OLS',
    },
    'conda_environments': {              # Conda environment names
        '0.19.2': 'py36-1.1.10',
        '1.1.5': 'pandas_115_final'
    }
}
```

## Migration Rules

The agent handles the following deprecated features:

### Critical Changes (Must Fix)
- **pd.Panel** → Custom Panel implementation or MultiIndex/xarray
- **pd.ols/pd.stats.ols** → Custom OLS implementation or statsmodels
- **.ix[]** → .loc[] (label-based) or .iloc[] (position-based)
- **.sort()** → .sort_values() or .sort_index()
- **.valid()** → .dropna()

### High Priority Changes
- **pd.rolling_mean()** → .rolling().mean()
- **pd.rolling_sum()** → .rolling().sum()
- **pd.rolling_std()** → .rolling().std()
- **pd.expanding_*()** → .expanding().*()

### Medium Priority Changes
- **.as_matrix()** → .values or .to_numpy()
- **.get_value()/.set_value()** → .at[] or .iat[]
- **.convert_objects()** → .infer_objects()

### Low Priority Changes
- **Categorical(order=True)** → Categorical(ordered=True)
- Various parameter name changes

## Output Files

After migration, the agent generates:

1. **Migration Report** (`pandas_migration_report_YYYYMMDD_HHMMSS.md`)
   - Executive summary with statistics
   - Detailed file changes
   - Test results comparison
   - Compatibility analysis
   - Recommendations

2. **Backup Files** (`.pandas_migration_backup/`)
   - Original file backups with timestamps
   - Metadata files with checksums

3. **Log Files**
   - Detailed migration logs
   - Test execution logs
   - Error traces

## Customizing Conda Environments

If your conda environments have different names, you can update the configuration:

```python
# In your agent configuration
agent.config_options['conda_environments'] = {
    '0.19.2': 'your_pandas_019_env',
    '1.1.5': 'your_pandas_115_env'
}
```

Or update the test runner directly:
```python
agent.test_runner.conda_envs = {
    "0.19.2": "your_pandas_019_env",
    "1.1.5": "your_pandas_115_env"
}
```

## Example Workflow

1. **Discovery Phase**
   - Agent scans repository for Python files
   - Identifies files using pandas
   - Analyzes deprecated feature usage

2. **Pre-Migration Testing**
   - Creates pandas 0.19.2 environment
   - Runs all tests to establish baseline
   - Records test results

3. **Migration Phase**
   - Applies migration rules to each file
   - Validates syntax after changes
   - Creates backups of modified files

4. **Post-Migration Testing**
   - Creates pandas 1.1.5 environment
   - Runs all tests again
   - Compares results with baseline

5. **Report Generation**
   - Generates comprehensive report
   - Identifies any test regressions
   - Provides recommendations

## Customization

### Adding Custom Migration Rules

```python
from migration_rules import MigrationRule, MigrationPriority

custom_rule = MigrationRule(
    name="custom_api_change",
    pattern=r"old_api_pattern",
    replacement="new_api_replacement",
    priority=MigrationPriority.HIGH,
    description="Description of the change",
    requires_import={"from new_module import new_api": "new_module"}
)

# Add to agent configuration
agent.rule_engine.add_custom_rule(custom_rule)
```

### Custom Test Commands

```python
# Specify custom test command for your project
"Run tests with: python -m pytest tests/ -v --cov=myproject"
```

## Troubleshooting

### Common Issues

1. **Import Errors After Migration**
   - Check custom_import_mappings configuration
   - Ensure replacement modules are installed

2. **Test Failures**
   - Review test regression section in report
   - Check for behavioral differences between pandas versions

3. **Syntax Errors**
   - Agent validates syntax, but complex transformations may fail
   - Manual intervention may be required for edge cases

### Debug Mode

Enable detailed logging:
```bash
export PANDAS_MIGRATION_DEBUG=1
openhands --agent PandasMigrationAgent
```

## Architecture

```
PandasMigrationAgent/
├── agent.py                 # Main agent class
├── migration_rules.py       # Migration rule engine
├── test_runner.py          # Test execution in different environments
├── compatibility_checker.py # Compatibility analysis
├── report_generator.py     # Report generation
└── utils.py               # Utility functions
```

## Contributing

To extend the agent:

1. Add new migration rules in `migration_rules.py`
2. Enhance test detection in `test_runner.py`
3. Add new compatibility checks in `compatibility_checker.py`
4. Improve report format in `report_generator.py`

## License

This agent is part of the OpenHands project and follows the same license terms.

## Support

For issues or questions:
- Check the generated migration report for specific guidance
- Review the troubleshooting section above
- Submit issues to the OpenHands repository