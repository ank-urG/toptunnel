# APIs and Imports That Should NEVER Be Changed

## Critical: These Work in BOTH pandas 0.19.2 and 1.1.5

**IMPORTANT CLARIFICATION**: The agent will NOT change these specific imports, BUT it will still fix other deprecated APIs in the same file!

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

## Example - Mixed File Behavior

```python
# This import will NOT be changed - it works in both versions
from pandas.util.testing import assert_frame_equal

import pandas as pd

def test_function():
    df = pd.DataFrame({'A': [1, 2, 3]})
    
    # BUT these deprecated APIs in the same file WILL be changed:
    sorted_df = df.sort('A')           # -> df.sort_values('A')
    val = df.ix[0, 'A']                # -> df.loc[0, 'A']
    panel = pd.Panel(data)             # -> Panel(data) with aqr import
    valid = df.valid()                 # -> df.dropna()
    
    # This compatible import usage remains unchanged
    assert_frame_equal(result, expected)
```

**Summary**: The agent is smart enough to:
1. Leave `pandas.util.testing` imports alone (they work in both versions)
2. Still fix other deprecated APIs in the same file
3. Not skip the entire file just because it has compatible imports