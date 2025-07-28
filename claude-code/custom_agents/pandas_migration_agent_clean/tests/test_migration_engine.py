"""Test the migration engine with real examples."""

import os
import tempfile
import shutil
from pandas_migration_agent_clean.core.migration_engine import MigrationEngine


def test_all_replacements():
    """Test that all replacements work correctly."""
    
    # Create test content with all deprecated APIs
    test_content = '''
import pandas as pd
import numpy as np
from pandas.tseries.offsets import DatetimeIndex
from pandas import Panel
from pandas.stats.api import ols

def process_data():
    # Create DataFrame
    df = pd.DataFrame({
        'A': [3, 1, 2],
        'B': [6, 4, 5],
        'date': pd.date_range('2020-01-01', periods=3)
    })
    
    # Deprecated: sort
    df = df.sort('A')
    
    # Deprecated: ix indexing
    val = df.ix[0, 'A']
    row = df.ix[0]
    
    # Deprecated: valid
    valid_df = df.valid()
    
    # Deprecated: as_matrix
    arr = df.as_matrix()
    
    # Deprecated: rolling functions
    ma = pd.rolling_mean(df['A'], window=2)
    ms = pd.rolling_sum(df['B'], window=2)
    
    # Deprecated: Panel
    panel = pd.Panel({
        'df1': df,
        'df2': df * 2
    })
    
    # Deprecated: TimeGrouper
    grouped = df.groupby(pd.TimeGrouper('M'))
    
    # Deprecated: get_value/set_value
    val2 = df.get_value(0, 'B')
    df.set_value(1, 'A', 100)
    
    # Deprecated: DatetimeIndex constructor
    idx = pd.DatetimeIndex('2020-01-01', '2020-12-31', freq='D')
    
    # Deprecated: to_timedelta with months
    offset = pd.to_timedelta(3, unit='M')
    
    # DataFrame subtraction
    adjusted = df - df['A']
    
    # OLS regression
    model = pd.ols(y=df['A'], x=df['B'])
    
    # Stack on potentially empty df
    stacked = df.stack()
    
    return df, panel, model
'''
    
    # Expected content after migration
    expected_patterns = [
        "df.sort_values('A')",  # sort -> sort_values
        "df.loc[0, 'A']",      # ix -> loc
        "df.iloc[0]",          # ix -> iloc  
        "df.dropna()",         # valid -> dropna
        "df.values",           # as_matrix -> values
        "df['A'].rolling(2).mean()",  # rolling_mean
        "from aqr.core.panel import Panel",  # Panel import
        "from aqr.stats.ols import OLS",     # OLS import
        "pd.Grouper(freq='M')",  # TimeGrouper -> Grouper
        "df.at[0, 'B']",       # get_value -> at
        "pd.date_range(",      # DatetimeIndex -> date_range
        "pd.DateOffset(months=3)",  # to_timedelta months
        "df.sub(df['A'], axis=0)",  # df - df[col]
        "if not df.empty else pd.Series(dtype=object)",  # stack safety
    ]
    
    # Create migration engine
    engine = MigrationEngine()
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        # Migrate the file
        result = engine.migrate_file(temp_file, create_backup=False)
        
        # Check result
        assert result['status'] == 'success', f"Migration failed: {result}"
        assert result['total_changes'] > 10, f"Too few changes: {result['total_changes']}"
        
        # Read migrated content
        with open(temp_file, 'r') as f:
            migrated_content = f.read()
        
        # Verify all expected patterns
        for pattern in expected_patterns:
            assert pattern in migrated_content, f"Pattern not found: {pattern}"
        
        # Verify deprecated patterns are gone
        deprecated = [
            ".sort('",
            ".ix[",
            ".valid()",
            ".as_matrix()",
            "pd.rolling_mean",
            "pd.Panel",
            "pd.ols",
            "pd.TimeGrouper",
            ".get_value(",
            ".set_value(",
            "from pandas.tseries.offsets import DatetimeIndex",
        ]
        
        for pattern in deprecated:
            assert pattern not in migrated_content, f"Deprecated pattern still present: {pattern}"
        
        print("✅ All replacements working correctly!")
        print(f"Total changes made: {result['total_changes']}")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_preserve_compatible_imports():
    """Test that compatible imports are NOT changed."""
    
    test_content = '''
# This import should NOT be changed
from pandas.util.testing import assert_frame_equal
import pandas as pd

def test_function():
    df = pd.DataFrame({'A': [1, 2, 3]})
    
    # This SHOULD be changed
    df = df.sort('A')
    val = df.ix[0, 'A']
    
    # Use the compatible import
    expected = pd.DataFrame({'A': [1, 2, 3]})
    assert_frame_equal(df, expected)
'''
    
    engine = MigrationEngine()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        # Migrate
        result = engine.migrate_file(temp_file, create_backup=False)
        
        # Read result
        with open(temp_file, 'r') as f:
            migrated = f.read()
        
        # Verify
        assert "from pandas.util.testing import assert_frame_equal" in migrated
        assert ".sort_values(" in migrated
        assert ".loc[" in migrated
        assert ".ix[" not in migrated
        
        print("✅ Compatible imports preserved correctly!")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == "__main__":
    print("Testing Migration Engine...")
    print("=" * 60)
    
    test_all_replacements()
    test_preserve_compatible_imports()
    
    print("\n✅ All tests passed!")