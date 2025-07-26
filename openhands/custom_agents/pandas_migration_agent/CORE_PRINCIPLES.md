# Core Principles of Pandas Migration Agent

## 1. DO NO HARM

**If it ain't broke, don't fix it!**

- Code that already works in BOTH pandas 0.19.2 and 1.1.5 is NOT touched
- The agent tests compatibility BEFORE making any changes
- Only files with actual compatibility issues are modified

## 2. CONFIGURATION SANCTITY

**NEVER modify configuration files:**
- ❌ setup.py, setup.cfg, pyproject.toml
- ❌ requirements*.txt, Pipfile, poetry.lock  
- ❌ pytest.ini, tox.ini, Makefile
- ❌ Any build or package configuration

## 3. BACKWARD COMPATIBILITY

**All migrations MUST work in both versions:**
- Uses compatibility wrappers, not direct replacements
- Adds fallback code for older pandas
- Tests in BOTH environments to verify

## 4. TEST-DRIVEN MIGRATION

**Every migration is validated:**
1. Test baseline with pandas 0.19.2
2. Apply migrations
3. Test with pandas 0.19.2 (must still work!)
4. Test with pandas 1.1.5 (must also work!)
5. No regressions allowed

## 5. MINIMAL CHANGES

**Only change what's necessary:**
- Pre-check every file for compatibility
- Skip files that already work in both versions
- Apply minimal compatibility wrappers

## Example: What Gets Changed vs What Doesn't

### File A: Already Compatible ✅
```python
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
df = df.sort_values('A')  # Already using sort_values
result = df.loc[0, 'A']   # Already using loc
```
**Result: NO CHANGES - Already works in both versions**

### File B: Needs Migration ⚠️
```python
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3]})
df = df.sort('A')         # Deprecated
result = df.ix[0, 'A']    # Deprecated
```
**Result: MIGRATED with compatibility wrappers**

### File C: Configuration ❌
```python
# setup.py
setup(
    name='mypackage',
    install_requires=['pandas>=0.19.2']
)
```
**Result: NEVER TOUCHED - Config files are sacred**

## The Golden Rule

The agent follows this decision tree:

1. Is it a config file? → **SKIP**
2. Does it use pandas? → If no, **SKIP**
3. Does it already work in both versions? → **SKIP**
4. Does it use deprecated APIs? → **MIGRATE with compatibility**

This ensures:
- Minimal disruption to your codebase
- No unnecessary changes
- Maximum compatibility
- Zero configuration changes