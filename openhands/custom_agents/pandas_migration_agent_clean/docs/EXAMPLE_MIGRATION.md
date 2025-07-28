# Example Migration: Before and After

## Original Code (pandas 0.19.2)

```python
import pandas as pd
import numpy as np
from pandas.tseries.offsets import DatetimeIndex
from pandas import Panel
from pandas.stats.api import ols

class DataProcessor:
    def __init__(self):
        self.data = pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=100),
            'price': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': ['AAPL'] * 50 + ['GOOGL'] * 50
        })
    
    def analyze(self):
        # Sort by date
        self.data = self.data.sort('date')
        
        # Get first price using ix
        first_price = self.data.ix[0, 'price']
        
        # Calculate rolling statistics
        self.data['ma_20'] = pd.rolling_mean(self.data['price'], 20)
        self.data['vol_std'] = pd.rolling_std(self.data['volume'], 10)
        
        # Group by month
        monthly = self.data.groupby(pd.TimeGrouper('M')).agg({
            'price': 'mean',
            'volume': 'sum'
        })
        
        # Remove invalid rows
        clean_data = self.data.valid()
        
        # Create panel for multi-symbol analysis
        panel = pd.Panel({
            symbol: group for symbol, group in self.data.groupby('symbol')
        })
        
        # Run regression
        model = pd.ols(y=self.data['price'], x=self.data['volume'])
        
        # Get matrix representation
        price_matrix = self.data[['price', 'volume']].as_matrix()
        
        # Set specific value
        self.data.set_value(0, 'flag', 'START')
        
        return {
            'first_price': first_price,
            'monthly': monthly,
            'panel': panel,
            'model': model,
            'matrix': price_matrix
        }
```

## Migrated Code (works in both 0.19.2 and 1.1.5)

```python
import pandas as pd
import numpy as np
from pandas import DatetimeIndex
from aqr.core.panel import Panel
from aqr.stats.ols import OLS

class DataProcessor:
    def __init__(self):
        self.data = pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=100),
            'price': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100),
            'symbol': ['AAPL'] * 50 + ['GOOGL'] * 50
        })
    
    def analyze(self):
        # Sort by date
        self.data = self.data.sort_values('date')
        
        # Get first price using loc
        first_price = self.data.loc[0, 'price']
        
        # Calculate rolling statistics
        self.data['ma_20'] = self.data['price'].rolling(20).mean()
        self.data['vol_std'] = self.data['volume'].rolling(10).std()
        
        # Group by month
        monthly = self.data.groupby(pd.Grouper(freq='M')).agg({
            'price': 'mean',
            'volume': 'sum'
        })
        
        # Remove invalid rows
        clean_data = self.data.dropna()
        
        # Create panel for multi-symbol analysis
        panel = Panel({
            symbol: group for symbol, group in self.data.groupby('symbol')
        })
        
        # Run regression
        model = OLS(y=self.data['price'], x=self.data['volume'])
        
        # Get matrix representation
        price_matrix = self.data[['price', 'volume']].values
        
        # Set specific value
        self.data.at[0, 'flag'] = 'START'
        
        return {
            'first_price': first_price,
            'monthly': monthly,
            'panel': panel,
            'model': model,
            'matrix': price_matrix
        }
```

## Summary of Changes

1. ✅ **Import statements** updated for DatetimeIndex, Panel, and OLS
2. ✅ **`.sort()`** → **`.sort_values()`**
3. ✅ **`.ix[]`** → **`.loc[]`** (label-based access)
4. ✅ **`pd.rolling_mean()`** → **`.rolling().mean()`**
5. ✅ **`pd.rolling_std()`** → **`.rolling().std()`**
6. ✅ **`pd.TimeGrouper()`** → **`pd.Grouper(freq=)`**
7. ✅ **`.valid()`** → **`.dropna()`**
8. ✅ **`pd.Panel`** → **`Panel`** from aqr.core.panel
9. ✅ **`pd.ols()`** → **`OLS()`** from aqr.stats.ols
10. ✅ **`.as_matrix()`** → **`.values`**
11. ✅ **`.set_value()`** → **`.at[]`** assignment

All changes are **direct replacements** that work in both pandas versions. No compatibility wrappers or conditional imports!