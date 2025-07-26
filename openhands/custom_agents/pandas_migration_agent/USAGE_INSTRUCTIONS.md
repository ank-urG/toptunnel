# Pandas Migration Agent - Usage Instructions

## Critical Requirements

This agent is designed to migrate pandas code from 0.19.2 to 1.1.5 while ensuring **100% backward compatibility**. The migrated code MUST work in BOTH pandas versions.

## What the Agent Does

1. **Protects Configuration Files**: NEVER modifies setup.py, requirements.txt, or any config files
2. **Pre-Migration Check**: Tests if code already works in both versions - if yes, NO changes made
3. **Ensures Backward Compatibility**: All migrations use compatibility wrappers  
4. **Mandatory Testing**: Runs tests in BOTH environments before and after migration
5. **Automatic Rollback**: Reverts changes if tests fail or compatibility breaks

## Correct Usage

### In OpenHands CLI/App:

```
User: Migrate my repository at /workspace/myproject from pandas 0.19.2 to 1.1.5

Agent: 
1. Discovering Python files (excluding configs)...
2. Checking which files actually need migration...
3. Running tests with pandas 0.19.2...
4. Applying migrations ONLY to incompatible files...
5. Testing in both environments...
6. Generating report...
```

### What Gets Modified:

✅ **ONLY Python source files** (.py files in src/, lib/, app/, etc.)
❌ **NEVER modifies**:
- setup.py, setup.cfg, pyproject.toml
- requirements*.txt, Pipfile, poetry.lock
- pytest.ini, tox.ini, Makefile
- Any configuration files

### Migration Examples:

1. **`.ix` indexer** → Determines context and uses `.loc` or `.iloc`
2. **`.sort()`** → `.sort_values()` with compatibility wrapper
3. **`pd.rolling_mean()`** → `.rolling().mean()` with fallback
4. **`pd.Panel`** → Conditional import with try/except
5. **`pd.ols`** → Conditional import with fallback

## Backward Compatible Migrations

The agent adds compatibility code like:

```python
# For sort() -> sort_values()
if not hasattr(pd.DataFrame, 'sort_values'):
    pd.DataFrame.sort_values = pd.DataFrame.sort

# For rolling functions
try:
    pd.DataFrame.rolling  # New API
except AttributeError:
    # Fallback to old API
    def rolling(self, window):
        # Compatibility wrapper
```

## Testing Workflow

The agent MUST:
1. Run tests with pandas 0.19.2 (baseline)
2. Apply migrations
3. Run tests with pandas 0.19.2 (verify compatibility)
4. Run tests with pandas 1.1.5 (verify upgrade works)
5. Compare results and check for regressions

## Expected Output

```
Migration Summary:
- Files analyzed: 50
- Files migrated: 12 (only those using pandas)
- Config files skipped: 5
- Tests before: 100 passed, 2 failed
- Tests after (0.19.2): 100 passed, 2 failed ✓ (no regression)
- Tests after (1.1.5): 100 passed, 2 failed ✓
- Status: SUCCESS - Backward compatible
```

## If Migration Fails

The agent will:
1. Report which files failed
2. Show test regressions
3. Automatically rollback changes
4. Provide detailed error report

## Important Notes

- The agent uses conda environments: `py36-1.1.10` (pandas 0.19.2) and `pandas_115_final` (pandas 1.1.5)
- All changes are backed up before modification
- The goal is ZERO test regressions
- Config files are NEVER touched

## Troubleshooting

If the agent isn't working correctly:

1. **Check conda environments exist**:
   ```bash
   conda env list | grep -E "py36-1.1.10|pandas_115_final"
   ```

2. **Verify test command**:
   The agent tries: pytest, unittest, nose
   Specify if different: "Use test command: make test"

3. **Review excluded files**:
   Check the discovery phase output to see what was excluded

## Example Interaction

```
User: Migrate /workspace/trading-system from pandas 0.19.2 to 1.1.5

Agent: Starting Pandas Migration Agent v1.0
- Repository: /workspace/trading-system
- Source: pandas 0.19.2 (env: py36-1.1.10)
- Target: pandas 1.1.5 (env: pandas_115_final)

Phase 1: Discovery
- Found 127 Python files
- Excluded 8 config files (setup.py, requirements.txt, etc.)
- Identified 23 files using pandas

Phase 1.5: Compatibility Check
- Checking which files actually need migration...
- Already compatible: 18 files (will NOT be modified)
- Need migration: 5 files (using deprecated APIs)
- No pandas usage: 96 files

Phase 2: Pre-migration Testing
- Running: pytest -xvs
- Environment: py36-1.1.10 (pandas 0.19.2)
- Results: 245 passed, 3 failed

Phase 3: Migration
- Migrating ONLY the 5 files that need changes...
- Skipping 18 files that already work in both versions ✓
- Applied backward-compatible rules to 5 files
- All syntax valid ✓
- All changes include compatibility wrappers ✓

Phase 4: Post-migration Testing
- Testing with pandas 0.19.2: 245 passed, 3 failed ✓
- Testing with pandas 1.1.5: 245 passed, 3 failed ✓
- No regressions detected ✓

Phase 5: Report Generation
- Report saved to: pandas_migration_report_20240726_143022.md

STATUS: Migration completed successfully!
All code is backward compatible with both pandas versions.
```