# Pandas API Compatibility Between 0.19.2 and 1.1.5

## Deprecated APIs and Their Direct Replacements

### 1. DataFrame/Series.sort() → sort_values()
- **Deprecated**: `df.sort('column')` 
- **Replacement**: `df.sort_values('column')`
- **Available in both**: YES - sort_values() was introduced in 0.17.0

### 2. DataFrame.ix[] → .loc[] or .iloc[]
- **Deprecated**: `df.ix[0, 'A']`
- **Replacement**: 
  - Label-based: `df.loc[0, 'A']`
  - Position-based: `df.iloc[0, 0]`
- **Available in both**: YES - loc/iloc available since 0.11.0

### 3. pd.rolling_mean() → .rolling().mean()
- **Deprecated**: `pd.rolling_mean(df, window=5)`
- **Replacement**: `df.rolling(window=5).mean()`
- **Available in both**: YES - rolling() available since 0.18.0

### 4. pd.rolling_sum() → .rolling().sum()
- **Deprecated**: `pd.rolling_sum(df, window=5)`
- **Replacement**: `df.rolling(window=5).sum()`
- **Available in both**: YES

### 5. pd.rolling_std() → .rolling().std()
- **Deprecated**: `pd.rolling_std(df, window=5)`
- **Replacement**: `df.rolling(window=5).std()`
- **Available in both**: YES

### 6. Series.valid() → Series.notna() or Series.notnull()
- **Deprecated**: `series.valid()`
- **Replacement**: `series.notnull()` (NOT notna() - that's too new)
- **Available in both**: YES - notnull() available in both

### 7. as_matrix() → values
- **Deprecated**: `df.as_matrix()`
- **Replacement**: `df.values`
- **Available in both**: YES - values available in both

### 8. pd.TimeGrouper → pd.Grouper
- **Deprecated**: `pd.TimeGrouper(freq='M')`
- **Replacement**: `pd.Grouper(freq='M')`
- **Available in both**: YES - Grouper available since 0.16.1

### 9. Panel → MultiIndex DataFrame (NO direct replacement)
- **Deprecated**: `pd.Panel()`
- **Custom Replacement**: Use aqr.core.panel.Panel
- **Note**: No direct pandas replacement works in both versions

### 10. pd.ols() → statsmodels or custom (NO direct replacement)
- **Deprecated**: `pd.ols()`
- **Custom Replacement**: Use aqr.stats.ols.OLS
- **Note**: No direct pandas replacement works in both versions

### 11. convert_objects() → infer_objects() (NOT compatible)
- **Deprecated**: `df.convert_objects()`
- **Note**: infer_objects() only in 0.21.0+, so NO direct replacement

### 12. get_value()/set_value() → at[] or iat[]
- **Deprecated**: `df.get_value(0, 'A')`
- **Replacement**: `df.at[0, 'A']` or `df.iat[0, 0]`
- **Available in both**: YES - at/iat available since 0.20.0 (CHECK THIS)

## Summary of Direct Replacements That Work in Both Versions:

1. `.sort()` → `.sort_values()`
2. `.ix[]` → `.loc[]` or `.iloc[]`
3. `pd.rolling_*()` → `.rolling().*()` 
4. `.valid()` → `.notnull()`
5. `.as_matrix()` → `.values`
6. `pd.TimeGrouper` → `pd.Grouper`
7. `.sortlevel()` → `.sort_index(level=...)`

## APIs That Need Custom Handling:
1. Panel - Use aqr.core.panel.Panel
2. OLS - Use aqr.stats.ols.OLS
3. convert_objects - No direct replacement