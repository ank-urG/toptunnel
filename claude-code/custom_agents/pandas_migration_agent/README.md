# Pandas Migration Agent

A specialized OpenHands agent for migrating pandas code from version 0.19.2 to 1.1.5 while maintaining backward compatibility.

## Overview

The Pandas Migration Agent automates the process of updating pandas code to work with newer versions while ensuring the code continues to function correctly in older environments. This is particularly useful for organizations that need to maintain compatibility across different pandas versions during a gradual migration process.

## Features

- **Automated API Migration**: Detects and transforms deprecated pandas APIs
- **Backward Compatibility**: Ensures code works in both pandas 0.19.2 and 1.1.5
- **Runtime Environment Switching**: Tests code in both environments automatically
- **AQR Library Integration**: Handles internal AQR library dependencies
- **Iterative Test Workflow**: Stops on failure, fixes, and reruns individual tests
- **Test Config Detection**: Automatically uses unittest.ini/cfg or it_test.ini/cfg
- **Safe Transformations**: Only modifies code that needs changes
- **Detailed Reporting**: Generates migration reports with test results

## Supported Migrations

### 1. Panel API Migration
- `pd.Panel` → `aqr.core.panel.Panel`

### 2. OLS Function Migration
- Simple: `pd.ols(y, x)` → `statsmodels.api.OLS(y, add_constant(x))`
- With pool: `pd.ols(y, x, pool=True)` → `aqr.stats.ols.OLS(...)`

### 3. Method Replacements
- `.valid()` → `.dropna()`
- `pd.TimeGrouper()` → `pd.Grouper(freq=...)`

### 4. Import Path Updates
- `from pandas.tseries.offsets import DatetimeIndex` → `from pandas import DatetimeIndex`

### 5. Constructor Changes
- `pd.DatetimeIndex(start, end, freq)` → `pd.date_range(start, end, freq)`

### 6. Operation Compatibility
- `df - series` → `df.sub(series, axis=0)`
- Empty DataFrame handling for `.stack()`
- Month offset handling: `pd.to_timedelta(1, unit='M')` → `pd.DateOffset(months=1)`

### 7. Exception Handling
- Adds `OutOfBoundsDatetime` exception handling for timestamp operations

## Usage

### Basic Migration

```python
from openhands.controller.agent import Agent

# Initialize the agent
agent = Agent.get('PandasMigrationAgent')

# Migrate a single file
result = agent.migrate_file(
    file_path='path/to/your/file.py',
    test_command='pytest test_file.py'
)
```

### Batch Migration

```python
# Migrate all Python files in a directory
results = agent.migrate_directory(
    directory='path/to/project',
    test_pattern='test_*.py',
    exclude_patterns=['venv', '__pycache__']
)
```

## Configuration

The agent can be configured through `config.toml`:

```toml
[migration]
source_version = "0.19.2"
target_version = "1.1.5"
backward_compatible = true
preserve_functionality = true

[runtimes.pandas_115]
name = "pandas_115_final"
pandas_version = "1.1.5"

[runtimes.pandas_019]
name = "py36-1.1.10"
pandas_version = "0.19.2"
location = "C:\\LocalRuntimes"

[aqr]
workspace_path = "C:\\Workspace"
auto_add_to_path = true
```

## Runtime Environments

The agent requires two Python environments:

1. **pandas 1.1.5 environment**: `pandas_115_final`
2. **pandas 0.19.2 environment**: `py36-1.1.10` (located at `C:\LocalRuntimes`)

## Test Configuration

The agent automatically detects and uses test configuration files:
- **unittest.ini** or **unittest.cfg**: Standard unit test configuration
- **it_test.ini** or **it_test.cfg**: Integration test configuration

When found, tests are run with: `pytest -c <config_file> <test_file>`

## AQR Library Setup

For AQR internal libraries:
1. Ensure libraries are available at `C:\Workspace`
2. The agent automatically adds this path to PYTHONPATH when needed
3. Required modules: `aqr.core.panel`, `aqr.stats.ols`

## Workflow

1. **Analysis**: Scans code for pandas API usage and compatibility issues
2. **Config Detection**: Finds unittest.ini/cfg or it_test.ini/cfg files
3. **Testing (Before)**: Runs tests with proper config in both environments
4. **Transformation**: Applies only necessary backward-compatible changes
5. **Iterative Testing**: 
   - Runs tests one by one
   - Stops on first failure
   - Fixes the failing test
   - Reruns only that test
   - Continues only after test passes
6. **Verification**: Ensures all tests pass in both environments
7. **Reporting**: Generates detailed migration report

## Safety Features

- **Backup Creation**: Automatically backs up files before modification
- **Syntax Validation**: Ensures code remains valid Python
- **Test-Driven**: Won't proceed if tests fail after migration
- **Rollback Support**: Can restore original files if migration fails
- **Minimal Changes**: Only modifies code that needs migration

## Example Migration

### Before:
```python
import pandas as pd
from pandas.tseries.offsets import DatetimeIndex

# Create panel
panel = pd.Panel(data)

# Run regression
results = pd.ols(y, x, pool=True)

# Clean data
clean_df = df.valid()

# Group by time
grouped = df.groupby(pd.TimeGrouper('M'))
```

### After:
```python
import pandas as pd
from pandas import DatetimeIndex
from aqr.core.panel import Panel
from aqr.stats.ols import OLS

# Create panel
panel = Panel(data)

# Run regression
results = OLS(y, x, pool=True)

# Clean data
clean_df = df.dropna()

# Group by time
grouped = df.groupby(pd.Grouper(freq='M'))
```

## Troubleshooting

### Common Issues

1. **AQR Libraries Not Found**
   - Ensure `C:\Workspace` contains the required AQR modules
   - Check that PYTHONPATH includes the workspace directory

2. **Runtime Not Available**
   - Verify that both pandas environments are properly installed
   - Check activation commands in config.toml

3. **Tests Failing After Migration**
   - Review the migration report for specific failures
   - Some edge cases may require manual intervention
   - Check for version-specific test assumptions

## Contributing

To extend the agent with new migration rules:

1. Add new rule class in `rules/backward_compatibility_rules.py`
2. Implement `detect()` and `transform()` methods
3. Add the rule to `MIGRATION_RULES` list
4. Update documentation with the new pattern

## License

MIT License - See LICENSE file for details