# Direct Replacement Examples

## What This Agent Does

This agent makes **direct code replacements** that work in BOTH pandas 0.19.2 and 1.1.5. 

**NO compatibility wrappers, NO monkey-patching, NO conditional imports!**

## Examples of Direct Replacements

### 1. DataFrame.sort() → sort_values()
```python
# BEFORE (only works in pandas 0.19.2)
df = df.sort('column_name')
df = df.sort(['col1', 'col2'], ascending=[True, False])

# AFTER (works in BOTH 0.19.2 and 1.1.5)
df = df.sort_values('column_name')
df = df.sort_values(['col1', 'col2'], ascending=[True, False])
```

### 2. .ix[] → .loc[] or .iloc[]
```python
# BEFORE (deprecated)
value = df.ix[0, 'A']
row = df.ix[5]
subset = df.ix[0:5, 'A':'C']

# AFTER (works in both versions)
value = df.loc[0, 'A']      # label-based
row = df.iloc[5]            # position-based
subset = df.loc[0:5, 'A':'C']  # label-based slicing
```

### 3. pd.rolling_mean() → .rolling().mean()
```python
# BEFORE (old API)
result = pd.rolling_mean(df['price'], window=20)
result = pd.rolling_sum(df['volume'], window=5)
result = pd.rolling_std(df['returns'], window=30)

# AFTER (works in both versions)
result = df['price'].rolling(window=20).mean()
result = df['volume'].rolling(window=5).sum()
result = df['returns'].rolling(window=30).std()
```

### 4. .as_matrix() → .values
```python
# BEFORE (deprecated)
array = df.as_matrix()
array = df[['A', 'B']].as_matrix()

# AFTER (works in both versions)
array = df.values
array = df[['A', 'B']].values
```

### 5. Series.valid() → Series.notnull()
```python
# BEFORE (removed)
mask = series.valid()

# AFTER (works in both versions)
mask = series.notnull()
```

### 6. pd.TimeGrouper → pd.Grouper
```python
# BEFORE (deprecated)
grouped = df.groupby(pd.TimeGrouper(freq='M'))

# AFTER (works in both versions)
grouped = df.groupby(pd.Grouper(freq='M'))
```

### 7. Panel → Custom Implementation
```python
# BEFORE (removed from pandas)
from pandas import Panel
panel = pd.Panel(data)

# AFTER (using your custom implementation)
from aqr.core.panel import Panel
panel = Panel(data)
```

### 8. pd.ols() → Custom Implementation
```python
# BEFORE (removed from pandas)
model = pd.ols(y=df['y'], x=df[['x1', 'x2']])

# AFTER (using your custom implementation)
from aqr.stats.ols import OLS
model = OLS(y=df['y'], x=df[['x1', 'x2']])
```

## What the Agent Does NOT Do

❌ **NO Compatibility Wrappers:**
```python
# WRONG - Agent will NOT generate this
if not hasattr(pd.DataFrame, 'sort_values'):
    pd.DataFrame.sort_values = pd.DataFrame.sort
```

❌ **NO Conditional Imports:**
```python
# WRONG - Agent will NOT generate this
try:
    from pandas.testing import assert_frame_equal
except ImportError:
    from pandas.util.testing import assert_frame_equal
```

❌ **NO Monkey Patching:**
```python
# WRONG - Agent will NOT generate this
def rolling_compatibility(self, window):
    try:
        return self.rolling(window)
    except AttributeError:
        return pd.rolling_mean(self, window)
```

## Summary

The agent makes clean, direct replacements using APIs that exist in BOTH pandas versions. Your migrated code will look like modern pandas code but will run perfectly in pandas 0.19.2!