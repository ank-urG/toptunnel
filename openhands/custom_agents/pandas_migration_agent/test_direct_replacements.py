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


if __name__ == "__main__":
    print("Testing Direct Replacement Rules...")
    print("=" * 50)
    
    test_sort_replacement()
    test_ix_replacement()
    test_rolling_replacement()
    test_no_wrappers()
    test_panel_ols_replacement()
    test_value_methods()
    
    print("\n✅ All tests passed! Direct replacements working correctly.")
    print("\nThe agent will make clean, direct replacements without any")
    print("compatibility wrappers or conditional code.")