# Pandas Migration Agent v2.0

A professional, production-ready agent for migrating pandas code from version 0.19.2 to 1.1.5.

## 🎯 Key Features

- **Direct Replacements Only**: No compatibility wrappers, no monkey-patching, just clean code transformations
- **Comprehensive Coverage**: Handles all major deprecated pandas APIs
- **Smart Detection**: Only modifies files that actually need changes
- **Test Integration**: Runs tests before and after migration
- **Professional Reports**: Generates detailed migration reports
- **Windows Support**: Works with custom runtime paths on Windows

## 📁 Clean Architecture

```
pandas_migration_agent_clean/
├── core/               # Core agent and engine
│   ├── agent.py       # Main agent class
│   └── migration_engine.py
├── rules/             # Migration rules
│   ├── replacement_rules.py    # Simple regex rules
│   └── complex_replacements.py # Complex transformations
├── workflow/          # Migration workflow
│   └── migration_workflow.py
├── utils/             # Utilities
│   ├── file_utils.py
│   ├── file_discovery.py
│   ├── test_runner.py
│   └── report_generator.py
├── config/            # Configuration
│   ├── metadata.json
│   └── agent_config.toml
├── docs/              # Documentation
└── tests/             # Test suite
```

## 🚀 Quick Start

### 1. Using with OpenHands

```python
# The agent will be available in OpenHands after installation
# Simply select "PandasMigrationAgent" when starting a session
```

### 2. Standalone Usage

```python
from pandas_migration_agent_clean import PandasMigrationAgent
from pandas_migration_agent_clean.workflow import MigrationWorkflow

# Configure the agent
config = {
    'conda_envs': {
        '0.19.2': 'py36-1.1.10',
        '1.1.5': 'pandas_115_final'
    },
    'create_backups': True,
    'run_tests': True
}

# Run migration
workflow = MigrationWorkflow(config)
results = workflow.execute('/path/to/your/repo')
```

## 🔧 What Gets Replaced

### Direct API Replacements

| Before | After | Description |
|--------|-------|-------------|
| `df.sort('col')` | `df.sort_values('col')` | DataFrame sorting |
| `df.ix[0, 'A']` | `df.loc[0, 'A']` | Label-based indexing |
| `df.ix[0]` | `df.iloc[0]` | Position-based indexing |
| `df.valid()` | `df.dropna()` | Remove invalid values |
| `df.as_matrix()` | `df.values` | Get numpy array |
| `pd.rolling_mean(s, 5)` | `s.rolling(5).mean()` | Rolling operations |
| `pd.Panel(data)` | `Panel(data)` | Using aqr.core.panel |
| `pd.ols(y, x)` | `OLS(y, x)` | Using aqr.stats.ols |
| `pd.TimeGrouper('M')` | `pd.Grouper(freq='M')` | Time grouping |

### Complex Transformations

1. **Empty DataFrame Stack**: Adds safety check
   ```python
   # Before: df.stack()
   # After: (df.stack() if not df.empty else pd.Series(dtype=object))
   ```

2. **DataFrame Subtraction**: Explicit axis specification
   ```python
   # Before: df - df['baseline']
   # After: df.sub(df['baseline'], axis=0)
   ```

3. **Timestamp Overflow**: Adds exception handling
   ```python
   # Wraps timestamp calculations in try-except with fallback to Timestamp.max
   ```

## 📊 Migration Workflow

1. **Discovery Phase**: Finds all Python files
2. **Pre-Migration Tests**: Runs tests with pandas 0.19.2
3. **Migration Phase**: Applies direct replacements
4. **Post-Migration Tests**: Validates with both pandas versions
5. **Report Generation**: Creates comprehensive report

## ⚙️ Configuration

### Conda Environments

The agent expects these conda environments:
- `py36-1.1.10`: For pandas 0.19.2
- `pandas_115_final`: For pandas 1.1.5

### Windows Custom Paths

On Windows, it supports custom runtime paths:
```toml
[windows_runtime_paths]
"py36-1.1.10" = "C:\\LocalRuntimes\\py36-1.1.10"
```

## 📝 Migration Report

The agent generates a detailed report including:
- Executive summary with statistics
- List of migrated files and changes
- Test results comparison
- Common replacements made
- Recommendations

## ✅ Best Practices

1. **Always backup**: The agent creates backups by default
2. **Review changes**: Inspect critical files after migration
3. **Run full tests**: Ensure tests pass in both environments
4. **Check edge cases**: Pay attention to data-dependent operations

## 🚫 What It Does NOT Do

- ❌ No compatibility wrappers
- ❌ No monkey-patching
- ❌ No conditional imports
- ❌ No runtime version checks
- ❌ Does NOT modify imports that work in both versions (like pandas.util.testing)

## 🛠️ Troubleshooting

### Tests Not Found
- The agent looks for pytest, unittest, or test commands in Makefile
- Specify test command in configuration if using custom test runner

### Migration Failures
- Check the migration report for specific errors
- Ensure all dependencies are installed in both environments
- Verify file permissions

### Windows Issues
- Ensure conda environments are properly activated
- Check custom runtime paths in configuration

## 📄 License

This agent is part of the OpenHands project and follows the same license terms.