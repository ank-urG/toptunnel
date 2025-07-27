"""
Test file demonstrating all backward compatibility changes.
This file shows BEFORE and AFTER for each change.
"""

# ============================================
# 1. DataFrame Operations
# ============================================

# BEFORE: Stack fails on empty DataFrame
def old_stack_operation():
    import pandas as pd
    df = pd.DataFrame()  # empty
    result = df.stack()  # This would fail
    return result

# AFTER: Stack handles empty DataFrame
def new_stack_operation():
    import pandas as pd
    df = pd.DataFrame()  # empty
    result = (df.stack() if not df.empty else pd.Series(dtype=object))
    return result

# BEFORE: valid() method
def old_valid_method():
    import pandas as pd
    import numpy as np
    s = pd.Series([1, 2, np.nan, 4])
    valid_data = s.valid()
    df_valid = df.valid()
    return valid_data

# AFTER: dropna() method
def new_valid_method():
    import pandas as pd
    import numpy as np
    s = pd.Series([1, 2, np.nan, 4])
    valid_data = s.dropna()
    df_valid = df.dropna()
    return valid_data

# ============================================
# 2. Import Path Changes
# ============================================

# BEFORE: DatetimeIndex from tseries.offsets
from pandas.tseries.offsets import DatetimeIndex

# AFTER: DatetimeIndex from pandas directly
from pandas import DatetimeIndex

# ============================================
# 3. Date/Time Operations
# ============================================

# BEFORE: DatetimeIndex constructor
def old_datetimeindex():
    import pandas as pd
    idx = pd.DatetimeIndex('2020-01-01', '2020-12-31', freq='D')
    return idx

# AFTER: date_range function
def new_datetimeindex():
    import pandas as pd
    idx = pd.date_range('2020-01-01', '2020-12-31', freq='D')
    return idx

# BEFORE: DataFrame subtraction
def old_df_subtraction():
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    result = df - df['A']
    adjusted = prices - prices['baseline']
    return result

# AFTER: Explicit sub method
def new_df_subtraction():
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    result = df.sub(df['A'], axis=0)
    adjusted = prices.sub(prices['baseline'], axis=0)
    return result

# ============================================
# 4. Statistical Operations
# ============================================

# BEFORE: pd.ols without pool parameter
def old_ols_usage():
    import pandas as pd
    from pandas.stats.api import ols
    # When y is a DataFrame
    model = pd.ols(y=returns_df, x=factors_df)
    return model

# AFTER: OLS with pool=True for DataFrame y
def new_ols_usage():
    from aqr.stats.ols import OLS
    # When y is a DataFrame, add pool=True
    model = OLS(y=returns_df, x=factors_df, pool=True)
    return model

# ============================================
# 5. Error Handling
# ============================================

# BEFORE: Timestamp overflow not handled
def old_timestamp_calc():
    offset_end = end + head * offset  # Could overflow
    return offset_end

# AFTER: Timestamp overflow handled
def new_timestamp_calc():
    try:
        offset_end = end + head * offset
    except (OverflowError, pd.errors.OutOfBoundsDatetime):
        import warnings
        from pandas import Timestamp
        msg = 'Offset beyond Timestamp range. Defaulting to max timestamp %s' % Timestamp.max
        warnings.warn(msg, UserWarning)
        offset_end = Timestamp.max
    return offset_end

# ============================================
# 6. Grouping Operations
# ============================================

# BEFORE: TimeGrouper
def old_grouping():
    import pandas as pd
    grouped = df.groupby(pd.TimeGrouper('BM'))
    grouped2 = df.groupby(pd.TimeGrouper(freq='D'))
    return grouped

# AFTER: Grouper with freq parameter
def new_grouping():
    import pandas as pd
    grouped = df.groupby(pd.Grouper(freq='BM'))
    grouped2 = df.groupby(pd.Grouper(freq='D'))
    return grouped

# BEFORE: to_timedelta with months
def old_timedelta():
    import pandas as pd
    offset = pd.to_timedelta(3, unit='M')
    monthly = pd.to_timedelta(1, unit='M')
    return offset

# AFTER: DateOffset for months
def new_timedelta():
    import pandas as pd
    offset = pd.DateOffset(months=3)
    monthly = pd.DateOffset(months=1)
    return offset

# ============================================
# Additional Complex Operations
# ============================================

# BEFORE: Multiple deprecated features together
def complex_old_code():
    import pandas as pd
    import numpy as np
    from pandas.tseries.offsets import DatetimeIndex
    
    # Create data
    df = pd.DataFrame({
        'date': pd.DatetimeIndex('2020-01-01', '2020-12-31', freq='D'),
        'value': np.random.randn(365),
        'category': ['A', 'B'] * 182 + ['A']
    })
    
    # Sort
    df = df.sort('date')
    
    # Group by month
    monthly = df.groupby(pd.TimeGrouper('M')).mean()
    
    # Use ix
    first_val = df.ix[0, 'value']
    
    # Valid values only
    valid_df = df.valid()
    
    # Panel usage
    panel = pd.Panel({
        'df1': df,
        'df2': df.shift(1)
    })
    
    # Rolling mean
    ma = pd.rolling_mean(df['value'], 20)
    
    return df, monthly, panel, ma

# AFTER: All replacements applied
def complex_new_code():
    import pandas as pd
    import numpy as np
    from pandas import DatetimeIndex
    from aqr.core.panel import Panel
    
    # Create data
    df = pd.DataFrame({
        'date': pd.date_range('2020-01-01', '2020-12-31', freq='D'),
        'value': np.random.randn(365),
        'category': ['A', 'B'] * 182 + ['A']
    })
    
    # Sort
    df = df.sort_values('date')
    
    # Group by month
    monthly = df.groupby(pd.Grouper(freq='M')).mean()
    
    # Use loc
    first_val = df.loc[0, 'value']
    
    # Valid values only
    valid_df = df.dropna()
    
    # Panel usage
    panel = Panel({
        'df1': df,
        'df2': df.shift(1)
    })
    
    # Rolling mean
    ma = df['value'].rolling(20).mean()
    
    return df, monthly, panel, ma

print("This file demonstrates all backward compatibility changes")
print("The agent will transform the BEFORE code into the AFTER code")
print("All transformations use direct replacements that work in both pandas 0.19.2 and 1.1.5")