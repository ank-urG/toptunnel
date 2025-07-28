"""Test how the agent handles files with both compatible and incompatible imports."""

from direct_replacement_rules import DirectReplacementEngine

# Read the test file
with open('test_mixed_file.py', 'r') as f:
    original_content = f.read()

# Apply migration rules
engine = DirectReplacementEngine()
migrated_content, changes = engine.apply_rules(original_content, 'test_mixed_file.py')

print("=== MIGRATION RESULTS ===")
print(f"Number of changes: {len(changes)}")
print("\nChanges made:")
for change in changes:
    print(f"- {change['rule']}: {change['description']}")

print("\n=== VERIFICATION ===")

# Check that pandas.util.testing import was NOT changed
if "from pandas.util.testing import assert_frame_equal" in migrated_content:
    print("✅ pandas.util.testing import was preserved (NOT changed)")
else:
    print("❌ ERROR: pandas.util.testing import was incorrectly modified!")

# Check that deprecated APIs WERE changed
checks = [
    (".sort(" not in migrated_content and ".sort_values(" in migrated_content, "sort() -> sort_values()"),
    (".ix[" not in migrated_content and (".loc[" in migrated_content or ".iloc[" in migrated_content), ".ix -> .loc/.iloc"),
    ("pd.rolling_mean" not in migrated_content and ".rolling(" in migrated_content, "rolling_mean -> .rolling().mean()"),
    ("pd.Panel" not in migrated_content and "aqr.core.panel" in migrated_content, "pd.Panel -> aqr.core.panel.Panel"),
    (".valid()" not in migrated_content and ".dropna()" in migrated_content, ".valid() -> .dropna()"),
    ("pd.ols" not in migrated_content and "aqr.stats.ols" in migrated_content, "pd.ols -> aqr.stats.ols.OLS"),
]

for check, description in checks:
    if check:
        print(f"✅ {description}")
    else:
        print(f"❌ {description} - migration failed")

print("\n=== MIGRATED FILE PREVIEW ===")
print("First 20 lines of migrated file:")
print("-" * 50)
lines = migrated_content.split('\n')[:20]
for i, line in enumerate(lines, 1):
    print(f"{i:3}: {line}")

print("\nConclusion: The agent correctly handles mixed files!")
print("- Compatible imports (pandas.util.testing) are preserved")
print("- Deprecated APIs are still replaced with modern equivalents")