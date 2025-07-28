"""Direct replacement rules for pandas migration.

IMPORTANT: These are DIRECT replacements only. 
No compatibility wrappers, no monkey-patching, no conditional imports.
Just clean, direct API replacements that work in both versions.
"""

import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class ReplacementRule:
    """A single replacement rule."""
    name: str
    pattern: str
    replacement: str
    description: str
    priority: int = 10


class MigrationRules:
    """All pandas migration rules with DIRECT replacements only."""
    
    def __init__(self):
        """Initialize all replacement rules."""
        self.rules = self._create_rules()
    
    def _create_rules(self) -> List[ReplacementRule]:
        """Create all replacement rules in priority order."""
        return [
            # ========== HIGH PRIORITY - COMMON PATTERNS ==========
            
            # DataFrame/Series operations
            ReplacementRule(
                name="sort_to_sort_values",
                pattern=r'\.sort\s*\(',
                replacement='.sort_values(',
                description="Replace .sort() with .sort_values()",
                priority=1
            ),
            
            ReplacementRule(
                name="valid_to_dropna",
                pattern=r'\.valid\s*\(\s*\)',
                replacement='.dropna()',
                description="Replace .valid() with .dropna()",
                priority=1
            ),
            
            ReplacementRule(
                name="as_matrix_to_values",
                pattern=r'\.as_matrix\s*\(\s*\)',
                replacement='.values',
                description="Replace .as_matrix() with .values",
                priority=1
            ),
            
            # Indexing
            ReplacementRule(
                name="sortlevel_to_sort_index",
                pattern=r'\.sortlevel\s*\(',
                replacement='.sort_index(level=',
                description="Replace .sortlevel() with .sort_index(level=)",
                priority=2
            ),
            
            # ========== GROUPING OPERATIONS ==========
            
            ReplacementRule(
                name="timegrouper_to_grouper",
                pattern=r'pd\.TimeGrouper\s*\(',
                replacement='pd.Grouper(freq=',
                description="Replace pd.TimeGrouper() with pd.Grouper(freq=)",
                priority=3
            ),
            
            ReplacementRule(
                name="timegrouper_with_freq",
                pattern=r"pd\.TimeGrouper\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
                replacement=r"pd.Grouper(freq='\1')",
                description="Replace pd.TimeGrouper('X') with pd.Grouper(freq='X')",
                priority=3
            ),
            
            # ========== DATE/TIME OPERATIONS ==========
            
            ReplacementRule(
                name="datetimeindex_import",
                pattern=r'from\s+pandas\.tseries\.offsets\s+import\s+DatetimeIndex',
                replacement='from pandas import DatetimeIndex',
                description="Fix DatetimeIndex import path",
                priority=4
            ),
            
            ReplacementRule(
                name="to_timedelta_months",
                pattern=r"pd\.to_timedelta\s*\(\s*(\d+)\s*,\s*unit\s*=\s*['\"]M['\"]\s*\)",
                replacement=r'pd.DateOffset(months=\1)',
                description="Replace pd.to_timedelta(n, unit='M') with pd.DateOffset(months=n)",
                priority=4
            ),
            
            # ========== PANEL AND OLS ==========
            
            ReplacementRule(
                name="panel_import",
                pattern=r'from\s+pandas\s+import\s+Panel',
                replacement='from aqr.core.panel import Panel',
                description="Replace pandas Panel import with aqr.core.panel",
                priority=5
            ),
            
            ReplacementRule(
                name="pd_panel",
                pattern=r'pd\.Panel\s*\(',
                replacement='Panel(',
                description="Replace pd.Panel() with Panel() from aqr",
                priority=5
            ),
            
            ReplacementRule(
                name="ols_import",
                pattern=r'from\s+pandas\.stats\.api\s+import\s+ols',
                replacement='from aqr.stats.ols import OLS as ols',
                description="Replace pandas ols import with aqr.stats.ols",
                priority=5
            ),
            
            ReplacementRule(
                name="pd_ols",
                pattern=r'pd\.ols\s*\(',
                replacement='OLS(',
                description="Replace pd.ols() with OLS() from aqr",
                priority=5
            ),
        ]
    
    def apply_simple_rules(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all simple regex-based rules."""
        changes = []
        modified = content
        
        # Sort rules by priority
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if re.search(rule.pattern, modified):
                new_content, count = re.subn(rule.pattern, rule.replacement, modified)
                if count > 0:
                    modified = new_content
                    changes.append({
                        'rule': rule.name,
                        'description': rule.description,
                        'count': count
                    })
        
        return modified, changes