"""
Example usage of the Pandas Migration Agent
"""

import os
from typing import List, Dict, Any


def example_single_file_migration():
    """Example: Migrate a single file"""
    
    # Sample code that needs migration
    sample_code = '''
import pandas as pd
from pandas.tseries.offsets import DatetimeIndex

def analyze_data(data):
    # Create panel for 3D data
    panel = pd.Panel(data)
    
    # Run regression analysis
    results = pd.ols(panel['y'], panel['x'], pool=True)
    
    # Clean data
    clean_data = panel.valid()
    
    # Create time-based groups
    monthly = clean_data.groupby(pd.TimeGrouper('M'))
    
    # Stack data
    stacked = clean_data.stack()
    
    return results, monthly, stacked

def process_timeseries(df, start_date, end_date):
    # Create date index
    date_index = pd.DatetimeIndex(start_date, end_date, freq='D')
    
    # Subtract series from dataframe
    adjusted = df - df['baseline']
    
    # Add month offset
    df['next_month'] = df.index + pd.to_timedelta(1, unit='M')
    
    return df
'''
    
    print("Original code:")
    print(sample_code)
    print("\n" + "="*50 + "\n")
    
    # This would be called by the agent:
    # agent = Agent.get('PandasMigrationAgent')
    # result = agent.migrate_code(sample_code)
    
    # For demonstration, show expected output:
    migrated_code = '''
import pandas as pd
from pandas import DatetimeIndex
from aqr.core.panel import Panel
from aqr.stats.ols import OLS

def analyze_data(data):
    # Create panel for 3D data
    # Migrated from pd.Panel to aqr.core.panel.Panel for compatibility
    panel = Panel(data)
    
    # Run regression analysis
    # Migrated from pd.ols to aqr.stats.ols for pool functionality
    results = OLS(panel['y'], panel['x'], pool=True)
    
    # Clean data
    # Migrated from .valid() to .dropna()
    clean_data = panel.dropna()
    
    # Create time-based groups
    # Migrated from pd.TimeGrouper
    monthly = clean_data.groupby(pd.Grouper(freq='M'))
    
    # Stack data
    # Added empty DataFrame check for .stack() compatibility
    if clean_data.empty:
        stacked = pd.Series(dtype=object)
    else:
        stacked = clean_data.stack()
    
    return results, monthly, stacked

def process_timeseries(df, start_date, end_date):
    # Create date index
    # Migrated from pd.DatetimeIndex constructor
    date_index = pd.date_range(start_date, end_date, freq='D')
    
    # Subtract series from dataframe
    # Migrated DataFrame-Series operation for compatibility
    adjusted = df.sub(df['baseline'], axis=0)
    
    # Add month offset
    # Migrated from pd.to_timedelta with month unit
    df['next_month'] = df.index + pd.DateOffset(months=1)
    
    return df
'''
    
    print("Migrated code:")
    print(migrated_code)
    print("\n" + "="*50 + "\n")
    
    print("Migration Summary:")
    print("✅ Replaced pd.Panel with aqr.core.panel.Panel")
    print("✅ Replaced pd.ols with aqr.stats.ols.OLS")
    print("✅ Replaced .valid() with .dropna()")
    print("✅ Updated DatetimeIndex import path")
    print("✅ Replaced pd.TimeGrouper with pd.Grouper")
    print("✅ Added empty check for .stack() operation")
    print("✅ Replaced DatetimeIndex constructor with date_range")
    print("✅ Updated DataFrame-Series operations")
    print("✅ Replaced month timedelta with DateOffset")


def example_test_verification():
    """Example: Test verification workflow"""
    
    print("Test Verification Workflow:")
    print("="*50)
    
    # Simulate test results
    test_results = {
        "before_migration": {
            "pandas_019": {
                "environment": "py36-1.1.10",
                "pandas_version": "0.19.2",
                "success": True,
                "passed_tests": 10,
                "failed_tests": 0,
                "duration": 5.2
            },
            "pandas_115": {
                "environment": "pandas_115_final",
                "pandas_version": "1.1.5",
                "success": False,
                "passed_tests": 7,
                "failed_tests": 3,
                "duration": 4.8
            }
        },
        "after_migration": {
            "pandas_019": {
                "environment": "py36-1.1.10",
                "pandas_version": "0.19.2",
                "success": True,
                "passed_tests": 10,
                "failed_tests": 0,
                "duration": 5.3
            },
            "pandas_115": {
                "environment": "pandas_115_final",
                "pandas_version": "1.1.5",
                "success": True,
                "passed_tests": 10,
                "failed_tests": 0,
                "duration": 4.9
            }
        }
    }
    
    print("\nBefore Migration:")
    print(f"  pandas 0.19.2: ✅ {test_results['before_migration']['pandas_019']['passed_tests']} passed")
    print(f"  pandas 1.1.5:  ❌ {test_results['before_migration']['pandas_115']['failed_tests']} failed")
    
    print("\nAfter Migration:")
    print(f"  pandas 0.19.2: ✅ {test_results['after_migration']['pandas_019']['passed_tests']} passed")
    print(f"  pandas 1.1.5:  ✅ {test_results['after_migration']['pandas_115']['passed_tests']} passed")
    
    print("\n✅ Migration successful! All tests pass in both environments.")


def example_batch_migration():
    """Example: Batch migration of multiple files"""
    
    print("\nBatch Migration Example:")
    print("="*50)
    
    files_to_migrate = [
        "src/data_processing.py",
        "src/analysis/regression.py",
        "src/utils/dataframe_ops.py",
        "tests/test_processing.py"
    ]
    
    print(f"Found {len(files_to_migrate)} files with pandas usage:")
    for file in files_to_migrate:
        print(f"  - {file}")
    
    # Simulate migration results
    migration_results = [
        {"file": "src/data_processing.py", "changes": 3, "status": "✅ Success"},
        {"file": "src/analysis/regression.py", "changes": 5, "status": "✅ Success"},
        {"file": "src/utils/dataframe_ops.py", "changes": 2, "status": "✅ Success"},
        {"file": "tests/test_processing.py", "changes": 1, "status": "✅ Success"}
    ]
    
    print("\nMigration Results:")
    total_changes = 0
    for result in migration_results:
        print(f"  {result['status']} {result['file']} ({result['changes']} changes)")
        total_changes += result['changes']
    
    print(f"\nTotal: {total_changes} changes applied across {len(files_to_migrate)} files")


def example_aqr_library_check():
    """Example: Checking AQR library availability"""
    
    print("\nAQR Library Check:")
    print("="*50)
    
    required_modules = [
        "aqr.core.panel",
        "aqr.stats.ols",
        "aqr.utils.dataframe"
    ]
    
    print("Checking AQR libraries in C:\\Workspace:")
    
    # Simulate check results
    check_results = {
        "aqr.core.panel": (True, "C:\\Workspace\\aqr\\core\\panel.py"),
        "aqr.stats.ols": (True, "C:\\Workspace\\aqr\\stats\\ols.py"),
        "aqr.utils.dataframe": (False, None)
    }
    
    for module in required_modules:
        found, path = check_results[module]
        if found:
            print(f"  ✅ {module} - Found at {path}")
        else:
            print(f"  ❌ {module} - Not found")
    
    if not all(check_results[m][0] for m in required_modules):
        print("\n⚠️  Some required AQR modules are missing.")
        print("   Please ensure all modules are installed in C:\\Workspace")


def example_migration_report():
    """Example: Generate migration report"""
    
    print("\nMigration Report Example:")
    print("="*50)
    
    report = '''
# Pandas Migration Report

Date: 2024-01-15 14:30:00
Source Version: 0.19.2
Target Version: 1.1.5

## Summary
- Total Files Processed: 4
- Successful Migrations: 4
- Failed Migrations: 0
- Files with Test Regressions: 0

## Detailed Results

### src/data_processing.py
- Status: ✅ Success
- Changes Made:
  - Replaced pd.Panel with aqr.core.panel.Panel
  - Replaced .valid() with .dropna()
  - Added empty DataFrame check for .stack()
- Test Results:
  - py36-1.1.10 (0.19.2): ✅ (15 passed, 0 failed)
  - pandas_115_final (1.1.5): ✅ (15 passed, 0 failed)

### src/analysis/regression.py
- Status: ✅ Success
- Changes Made:
  - Replaced pd.ols with aqr.stats.ols.OLS
  - Updated DataFrame-Series operations
  - Fixed DatetimeIndex imports
  - Replaced pd.TimeGrouper with pd.Grouper
  - Added timestamp exception handling
- Test Results:
  - py36-1.1.10 (0.19.2): ✅ (8 passed, 0 failed)
  - pandas_115_final (1.1.5): ✅ (8 passed, 0 failed)

## Migration Rules Applied
- panel_to_aqr: 1 occurrence
- ols_to_aqr: 2 occurrences
- valid_to_dropna: 3 occurrences
- datetime_import_fix: 1 occurrence
- df_series_operations: 2 occurrences
- stack_empty_check: 1 occurrence
- timegrouper_to_grouper: 1 occurrence

## Recommendations
✅ All migrations completed successfully
✅ All tests pass in both pandas versions
✅ Code is now compatible with pandas 0.19.2 and 1.1.5
'''
    
    print(report)


if __name__ == "__main__":
    print("Pandas Migration Agent - Example Usage")
    print("="*70)
    
    # Run examples
    example_single_file_migration()
    example_test_verification()
    example_batch_migration()
    example_aqr_library_check()
    example_migration_report()
    
    print("\n" + "="*70)
    print("For actual usage, initialize the agent with:")
    print("  from openhands.controller.agent import Agent")
    print("  agent = Agent.get('PandasMigrationAgent')")
    print("  result = agent.migrate_file('your_file.py')")