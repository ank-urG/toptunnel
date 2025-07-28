"""
Test file with both compatible imports (that should NOT change)
and deprecated APIs (that SHOULD change).
"""

# This import should NOT be changed - it works in both versions
from pandas.util.testing import assert_frame_equal

import pandas as pd
import numpy as np

def test_dataframe_operations():
    """Test with deprecated APIs that need fixing."""
    
    # Create test data
    df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'date': pd.date_range('2020-01-01', periods=3)
    })
    
    # This SHOULD be changed: .sort() -> .sort_values()
    sorted_df = df.sort('A')
    
    # This SHOULD be changed: .ix -> .loc
    first_val = df.ix[0, 'A']
    
    # This SHOULD be changed: pd.rolling_mean -> .rolling().mean()
    rolling_avg = pd.rolling_mean(df['A'], window=2)
    
    # This SHOULD be changed: pd.Panel -> aqr.core.panel.Panel
    panel = pd.Panel({
        'df1': df,
        'df2': df * 2
    })
    
    # This SHOULD be changed: .valid() -> .dropna()
    valid_data = df.valid()
    
    # This SHOULD be changed: pd.ols -> aqr.stats.ols.OLS
    model = pd.ols(y=df['A'], x=df['B'])
    
    # Use the compatible import (this part is fine)
    expected = pd.DataFrame({'A': [1, 2, 3]})
    assert_frame_equal(df[['A']], expected)
    
    return sorted_df, first_val, rolling_avg, panel, valid_data, model


# Expected output after migration:
# - pandas.util.testing import remains UNCHANGED
# - All deprecated APIs are replaced with their modern equivalents
# - The file will have both unchanged imports and changed deprecated code