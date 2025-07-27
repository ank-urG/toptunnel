"""Test direct replacement rules to ensure they work correctly."""

import os
import tempfile
from direct_replacement_rules import DirectReplacementEngine


def test_sort_replacement():
    """Test .sort() -> .sort_values() replacement."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
df = pd.DataFrame({'A': [3, 1, 2], 'B': [6, 4, 5]})
df = df.sort('A')
df2 = df.sort(['A', 'B'], ascending=[True, False])
"""
    
    expected = """
import pandas as pd
df = pd.DataFrame({'A': [3, 1, 2], 'B': [6, 4, 5]})
df = df.sort_values('A')
df2 = df.sort_values(['A', 'B'], ascending=[True, False])
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert '.sort(' not in result
    assert '.sort_values(' in result
    assert len(changes) > 0
    print("✓ sort() -> sort_values() replacement works")


def test_ix_replacement():
    """Test .ix[] -> .loc[]/.iloc[] replacement."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
val1 = df.ix[0, 'A']
val2 = df.ix[0]
val3 = df.ix[0:2]
val4 = df.ix['row1', 'col1']
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert '.ix[' not in result
    assert '.iloc[0, ' in result or '.loc[0, ' in result
    assert len(changes) > 0
    print("✓ .ix[] -> .loc[]/.iloc[] replacement works")


def test_rolling_replacement():
    """Test pd.rolling_* -> .rolling().* replacement."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
df = pd.DataFrame({'price': [100, 101, 102, 103, 104]})
ma = pd.rolling_mean(df['price'], 3)
vol = pd.rolling_std(df['price'], 5)
total = pd.rolling_sum(df['price'], 2)
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert 'pd.rolling_' not in result
    assert '.rolling(' in result
    assert '.mean()' in result
    assert '.std()' in result
    assert '.sum()' in result
    print("✓ pd.rolling_* -> .rolling().* replacement works")


def test_no_wrappers():
    """Test that no compatibility wrappers are added."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
df = df.sort('A')
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    
    # Validate no wrappers were added
    validation = engine.validate_changes(original, result)
    assert validation['valid'], "Code should not contain wrappers"
    assert not validation.get('has_wrappers', False)
    
    # Check for wrapper patterns
    assert 'if not hasattr' not in result
    assert 'compatibility wrapper' not in result.lower()
    assert 'monkey patch' not in result.lower()
    print("✓ No compatibility wrappers added")


def test_panel_ols_replacement():
    """Test Panel and OLS replacements."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
from pandas import Panel
panel = pd.Panel(data)
model = pd.ols(y=df['y'], x=df['x'])
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert 'from aqr.core.panel import Panel' in result
    assert 'from aqr.stats.ols import OLS' in result
    assert 'pd.Panel(' not in result
    assert 'pd.ols(' not in result
    print("✓ Panel and OLS replacements work")


def test_value_methods():
    """Test get_value/set_value replacements."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
val = df.get_value(0, 'A')
df.set_value(1, 'A', 10)
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert '.get_value(' not in result
    assert '.set_value(' not in result
    assert '.at[' in result
    print("✓ get_value/set_value -> .at[] replacement works")


def test_valid_replacement():
    """Test .valid() -> .dropna() replacement."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
s = pd.Series([1, 2, np.nan, 4])
valid_data = s.valid()
df_valid = df.valid()
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert '.valid()' not in result
    assert '.dropna()' in result
    print("✓ .valid() -> .dropna() replacement works")


def test_timegroup_replacement():
    """Test TimeGrouper replacements."""
    engine = DirectReplacementEngine()
    
    original = """
import pandas as pd
grouped = df.groupby(pd.TimeGrouper('BM'))
grouped2 = df.groupby(pd.TimeGrouper(freq='D'))
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert 'pd.TimeGrouper' not in result
    assert "pd.Grouper(freq='BM')" in result
    assert '.Grouper(freq=' in result
    print("✓ TimeGrouper -> Grouper replacement works")


def test_datetimeindex_import():
    """Test DatetimeIndex import fix."""
    engine = DirectReplacementEngine()
    
    original = """
from pandas.tseries.offsets import DatetimeIndex
import pandas as pd
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert 'from pandas.tseries.offsets import DatetimeIndex' not in result
    assert 'from pandas import DatetimeIndex' in result
    print("✓ DatetimeIndex import fix works")


def test_stack_empty_check():
    """Test stack() empty DataFrame handling."""
    engine = DirectReplacementEngine()
    
    original = """
result = df.stack()
stacked = my_df.stack()
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert 'if not df.empty' in result or 'df.empty' in result
    assert 'pd.Series(dtype=object)' in result
    print("✓ stack() empty DataFrame handling works")


def test_df_subtraction():
    """Test DataFrame - Series replacement."""
    engine = DirectReplacementEngine()
    
    original = """
result = df - df['col1']
adjusted = prices - prices['baseline']
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert '.sub(' in result
    assert 'axis=0' in result
    print("✓ DataFrame subtraction replacement works")


def test_to_timedelta_months():
    """Test pd.to_timedelta with months replacement."""
    engine = DirectReplacementEngine()
    
    original = """
offset = pd.to_timedelta(3, unit='M')
delta = pd.to_timedelta(1, unit='M')
"""
    
    result, changes = engine.apply_rules(original, "test.py")
    assert "pd.to_timedelta" not in result or "unit='M'" not in result
    assert "pd.DateOffset(months=" in result
    print("✓ to_timedelta months replacement works")


if __name__ == "__main__":
    print("Testing Direct Replacement Rules...")
    print("=" * 50)
    
    # Original tests
    test_sort_replacement()
    test_ix_replacement()
    test_rolling_replacement()
    test_no_wrappers()
    test_panel_ols_replacement()
    test_value_methods()
    
    # New tests for backward compatibility changes
    print("\nTesting New Backward Compatibility Rules...")
    print("-" * 50)
    test_valid_replacement()
    test_timegroup_replacement()
    test_datetimeindex_import()
    test_stack_empty_check()
    test_df_subtraction()
    test_to_timedelta_months()
    
    print("\n✅ All tests passed! Direct replacements working correctly.")
    print("\nThe agent will make clean, direct replacements without any")
    print("compatibility wrappers or conditional code.")