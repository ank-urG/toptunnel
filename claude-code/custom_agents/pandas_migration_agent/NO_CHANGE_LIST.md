# APIs and Imports That Should NEVER Be Changed

## Critical: These Work in BOTH pandas 0.19.2 and 1.1.5

### Testing Utilities
- `pandas.util.testing` - Available in both versions
- `from pandas.util.testing import assert_frame_equal`
- `from pandas.util.testing import assert_series_equal`
- `from pandas.util.testing import assert_index_equal`
- `import pandas.util.testing as tm`
- `pd.util.testing.*`

### Time Series
- `pandas.tseries` - Available in both versions
- `from pandas.tseries.offsets import *`
- `from pandas.tseries.frequencies import *`

### Compatibility Module
- `pandas.compat` - Available in both versions
- `from pandas.compat import *`

### Core APIs That Work in Both
- `pd.DataFrame` - No changes needed
- `pd.Series` - No changes needed
- `pd.Index` - No changes needed
- `pd.read_csv` - No changes needed
- `pd.to_datetime` - No changes needed
- `pd.merge` - No changes needed
- `pd.concat` - No changes needed

## Why This Matters

The agent was previously changing `pandas.util.testing` imports even though they work perfectly in BOTH pandas versions. This violates our core principle: **"If it ain't broke, don't fix it!"**

## Implementation

The agent now:
1. Checks if a file uses any of these compatible imports
2. Tests the file in both pandas environments
3. If it works in both, marks it as "skipped" with reason
4. Never applies any migration rules to these files

## Example

```python
# This file should NEVER be changed by the agent
from pandas.util.testing import assert_frame_equal

def test_my_function():
    result = my_function()
    expected = pd.DataFrame({'A': [1, 2, 3]})
    assert_frame_equal(result, expected)
```

Even if wrapped in try/except, if it works in both versions, leave it alone!