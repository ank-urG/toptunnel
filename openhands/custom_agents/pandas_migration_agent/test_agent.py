#!/usr/bin/env python3
"""Basic tests for the Pandas Migration Agent."""

import sys
import tempfile
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_agents.pandas_migration_agent.migration_rules import MigrationRuleEngine, MigrationRule, MigrationPriority
from custom_agents.pandas_migration_agent.compatibility_checker import CompatibilityChecker
from custom_agents.pandas_migration_agent.utils import validate_python_syntax, extract_pandas_imports


def test_migration_rules():
    """Test migration rule engine."""
    print("Testing Migration Rules...")
    
    # Test code with deprecated features
    test_code = '''
import pandas as pd

# Create Panel (deprecated)
panel = pd.Panel(data)

# Use ix indexer (deprecated)
df.ix[0, 'column']

# Use sort (deprecated)
df.sort('column')

# Use valid (deprecated)
df.valid()

# Use rolling_mean (deprecated)
result = pd.rolling_mean(df, window=5)

# Use as_matrix (deprecated)
matrix = df.as_matrix()
'''
    
    rule_engine = MigrationRuleEngine()
    migrated_code, changes = rule_engine.apply_rules(test_code, "test.py")
    
    print(f"Applied {len(changes)} migration rules")
    for change in changes:
        print(f"  - {change['rule']}: {change.get('description', 'No description')}")
    
    # Verify changes were made
    assert 'pd.Panel' not in migrated_code
    assert '.ix[' not in migrated_code
    assert '.sort(' not in migrated_code
    assert '.valid()' not in migrated_code
    assert 'pd.rolling_mean' not in migrated_code
    assert '.as_matrix()' not in migrated_code
    
    print("✓ Migration rules test passed\n")


def test_compatibility_checker():
    """Test compatibility checker."""
    print("Testing Compatibility Checker...")
    
    test_code = '''
import pandas as pd
from pandas.lib import something  # problematic import

df = pd.DataFrame()
df.ix[0, 1] = 5  # deprecated indexer
result = df.sort('column')  # deprecated method
panel = pd.Panel()  # removed class
'''
    
    checker = CompatibilityChecker()
    issues = checker.check_file("test.py", test_code)
    
    print(f"Found {len(issues)} compatibility issues:")
    for issue in issues:
        print(f"  - Line {issue.line_number}: {issue.description} [{issue.level.value}]")
    
    # Verify issues were found
    assert len(issues) > 0
    assert any('ix' in issue.description for issue in issues)
    assert any('Panel' in issue.description for issue in issues)
    assert any('pandas.lib' in issue.description for issue in issues)
    
    print("✓ Compatibility checker test passed\n")


def test_import_extraction():
    """Test pandas import extraction."""
    print("Testing Import Extraction...")
    
    test_code = '''
import pandas as pd
import numpy as np
from pandas import DataFrame, Series
from pandas.plotting import scatter_matrix
import pandas.testing as tm
'''
    
    imports = extract_pandas_imports(test_code)
    
    print("Extracted imports:")
    print(f"  - Direct imports: {imports['pandas']}")
    print(f"  - Module imports: {imports['pandas_modules']}")
    print(f"  - Aliases: {imports['pandas_aliases']}")
    
    assert 'pandas' in imports['pandas']
    assert 'pandas.DataFrame' in imports['pandas_modules']
    assert 'pandas.Series' in imports['pandas_modules']
    
    print("✓ Import extraction test passed\n")


def test_syntax_validation():
    """Test syntax validation."""
    print("Testing Syntax Validation...")
    
    valid_code = "import pandas as pd\ndf = pd.DataFrame()"
    invalid_code = "import pandas as pd\ndf = pd.DataFrame(]"  # syntax error
    
    is_valid1, error1 = validate_python_syntax(valid_code)
    is_valid2, error2 = validate_python_syntax(invalid_code)
    
    assert is_valid1 == True
    assert error1 is None
    assert is_valid2 == False
    assert error2 is not None
    
    print(f"Valid code check: {is_valid1}")
    print(f"Invalid code check: {is_valid2} (Error: {error2})")
    print("✓ Syntax validation test passed\n")


def test_full_migration_flow():
    """Test a simple migration flow."""
    print("Testing Full Migration Flow...")
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
import pandas as pd

# Test deprecated features
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})

# Use ix (deprecated)
value = df.ix[0, 'A']

# Use sort (deprecated)
sorted_df = df.sort('A')

# Use as_matrix (deprecated)
matrix = df.as_matrix()

# Use Panel (removed)
panel = pd.Panel()

print("Original code executed")
''')
        test_file = f.name
    
    try:
        # Read original content
        with open(test_file, 'r') as f:
            original_content = f.read()
        
        # Apply migration
        rule_engine = MigrationRuleEngine()
        migrated_content, changes = rule_engine.apply_rules(original_content, test_file)
        
        # Validate migrated code
        is_valid, error = validate_python_syntax(migrated_content)
        
        print(f"Migration applied {len(changes)} changes")
        print(f"Migrated code is valid: {is_valid}")
        
        # Check compatibility
        checker = CompatibilityChecker()
        remaining_issues = checker.check_file(test_file, migrated_content)
        
        print(f"Remaining compatibility issues: {len(remaining_issues)}")
        
        # Basic assertions
        assert is_valid == True
        assert len(changes) > 0
        assert '.ix[' not in migrated_content
        assert '.sort(' not in migrated_content
        
        print("✓ Full migration flow test passed\n")
        
    finally:
        # Cleanup
        os.unlink(test_file)


def main():
    """Run all tests."""
    print("=" * 50)
    print("Pandas Migration Agent Tests")
    print("=" * 50)
    print()
    
    try:
        test_migration_rules()
        test_compatibility_checker()
        test_import_extraction()
        test_syntax_validation()
        test_full_migration_flow()
        
        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()