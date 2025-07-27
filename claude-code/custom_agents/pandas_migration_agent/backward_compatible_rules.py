"""Backward compatible migration rules for pandas 0.19.2 to 1.1.5.

These rules ensure the migrated code works in BOTH pandas versions.
"""

import re
import ast
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class CompatibilityStrategy(Enum):
    """Strategy for ensuring backward compatibility."""
    CONDITIONAL = "conditional"  # Use version checks
    WRAPPER = "wrapper"          # Use compatibility wrappers
    REPLACEMENT = "replacement"  # Use drop-in replacements


@dataclass
class BackwardCompatibleRule:
    """Rule that ensures backward compatibility."""
    name: str
    pattern: str
    priority: int
    description: str
    strategy: CompatibilityStrategy
    
    def apply(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Apply the migration rule ensuring backward compatibility."""
        changes = []
        
        if self.name == "ix_to_loc_iloc":
            # For .ix, we need to determine if it's label or position based
            return self._handle_ix_replacement(content, changes)
        
        elif self.name == "sort_compatibility":
            # sort() -> sort_values() with compatibility wrapper
            return self._handle_sort_compatibility(content, changes)
        
        elif self.name == "rolling_functions":
            # Handle rolling functions that work in both versions
            return self._handle_rolling_compatibility(content, changes)
        
        elif self.name == "panel_replacement":
            # Only replace if custom Panel is available
            return self._handle_panel_replacement(content, changes)
        
        elif self.name == "ols_replacement":
            # Only replace if custom OLS is available
            return self._handle_ols_replacement(content, changes)
        
        return content, changes
    
    def _handle_ix_replacement(self, content: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Handle .ix replacement with backward compatibility."""
        # Pattern to find .ix usage
        ix_pattern = r'(\w+)\.ix\[(.*?)\]'
        
        def replace_ix(match):
            var_name = match.group(1)
            index_expr = match.group(2)
            
            # Try to determine if it's positional or label based
            # This is a simplified heuristic - in practice, we'd need more context
            if re.match(r'^\d+$', index_expr.strip()):
                # Likely positional
                return f"{var_name}.iloc[{index_expr}]"
            elif ':' in index_expr and re.match(r'^\d+:\d+$', index_expr.replace(' ', '')):
                # Slice with numbers - positional
                return f"{var_name}.iloc[{index_expr}]"
            else:
                # Likely label-based
                return f"{var_name}.loc[{index_expr}]"
        
        new_content = re.sub(ix_pattern, replace_ix, content)
        
        if new_content != content:
            changes.append("Replaced .ix with .loc/.iloc based on usage pattern")
        
        return new_content, changes
    
    def _handle_sort_compatibility(self, content: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Handle sort() -> sort_values() with compatibility."""
        # First, check if sort() is used
        if '.sort(' not in content:
            return content, changes
        
        # Add compatibility wrapper at the top of the file
        compatibility_code = '''
# Pandas compatibility wrapper for sort
import pandas as pd
if not hasattr(pd.DataFrame, 'sort_values'):
    # pandas < 0.20.0
    pd.DataFrame.sort_values = pd.DataFrame.sort
    pd.Series.sort_values = pd.Series.sort
'''
        
        # Replace .sort( with .sort_values(
        new_content = re.sub(r'\.sort\s*\(', '.sort_values(', content)
        
        # Add compatibility code if not already present
        if 'sort_values = pd.DataFrame.sort' not in content:
            # Find the right place to insert (after imports)
            lines = content.split('\n')
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith(('import ', 'from ')):
                    import_end = i
                    break
            
            lines.insert(import_end, compatibility_code)
            new_content = '\n'.join(lines)
        
        changes.append("Replaced .sort() with .sort_values() and added compatibility wrapper")
        return new_content, changes
    
    def _handle_rolling_compatibility(self, content: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Handle rolling functions for compatibility."""
        # Pattern for pd.rolling_* functions
        rolling_pattern = r'pd\.(rolling_\w+)\s*\((.*?)\)'
        
        matches = list(re.finditer(rolling_pattern, content, re.DOTALL))
        if not matches:
            return content, changes
        
        # Add compatibility wrapper
        compatibility_code = '''
# Pandas compatibility wrapper for rolling functions
import pandas as pd
try:
    # Try new API first (pandas >= 0.18)
    pd.DataFrame.rolling
except AttributeError:
    # Fall back to old API
    def _rolling_wrapper(data, window, func_name, **kwargs):
        func = getattr(pd, f'rolling_{func_name}')
        return func(data, window, **kwargs)
    
    # Monkey patch for compatibility
    def rolling(self, window, **kwargs):
        class RollingWrapper:
            def __init__(self, data, window):
                self.data = data
                self.window = window
            def mean(self): return pd.rolling_mean(self.data, self.window)
            def sum(self): return pd.rolling_sum(self.data, self.window)
            def std(self): return pd.rolling_std(self.data, self.window)
            def var(self): return pd.rolling_var(self.data, self.window)
        return RollingWrapper(self, window)
    
    pd.DataFrame.rolling = rolling
    pd.Series.rolling = rolling
'''
        
        # Replace pd.rolling_* with compatible version
        new_content = content
        for match in reversed(matches):  # Reverse to maintain positions
            func_name = match.group(1).replace('rolling_', '')
            args = match.group(2)
            
            # Extract data and window arguments
            args_parts = args.split(',', 2)
            if len(args_parts) >= 2:
                data_arg = args_parts[0].strip()
                window_arg = args_parts[1].strip()
                extra_args = args_parts[2] if len(args_parts) > 2 else ''
                
                # Create compatible replacement
                if extra_args:
                    replacement = f"{data_arg}.rolling({window_arg}).{func_name}({extra_args})"
                else:
                    replacement = f"{data_arg}.rolling({window_arg}).{func_name}()"
                
                new_content = new_content[:match.start()] + replacement + new_content[match.end():]
        
        # Add compatibility code if not present
        if 'rolling_wrapper' not in new_content and new_content != content:
            lines = new_content.split('\n')
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith(('import ', 'from ')):
                    import_end = i
                    break
            
            lines.insert(import_end, compatibility_code)
            new_content = '\n'.join(lines)
            changes.append("Replaced rolling functions with compatible API and added wrapper")
        
        return new_content, changes
    
    def _handle_panel_replacement(self, content: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Handle Panel replacement only if custom implementation exists."""
        if 'pd.Panel' not in content:
            return content, changes
        
        # Add conditional import
        compatibility_code = '''
# Pandas Panel compatibility
try:
    from aqr.core.panel import Panel
except ImportError:
    # Fallback to pandas Panel if available
    try:
        from pandas import Panel
    except ImportError:
        # Panel not available in this pandas version
        raise ImportError("Panel is not available. Please install aqr.core.panel or use pandas < 0.25.0")
'''
        
        # Replace pd.Panel with Panel
        new_content = re.sub(r'pd\.Panel\s*\(', 'Panel(', content)
        
        # Add import if not present
        if 'from aqr.core.panel import Panel' not in content and new_content != content:
            lines = new_content.split('\n')
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith(('import ', 'from ')):
                    import_end = i
                    break
            
            lines.insert(import_end, compatibility_code)
            new_content = '\n'.join(lines)
            changes.append("Replaced pd.Panel with compatibility wrapper")
        
        return new_content, changes
    
    def _handle_ols_replacement(self, content: str, changes: List[str]) -> Tuple[str, List[str]]:
        """Handle OLS replacement only if custom implementation exists."""
        ols_patterns = ['pd.ols', 'pd.stats.ols']
        
        has_ols = any(pattern in content for pattern in ols_patterns)
        if not has_ols:
            return content, changes
        
        # Add conditional import
        compatibility_code = '''
# Pandas OLS compatibility
try:
    from aqr.stats.ols import OLS
except ImportError:
    # Fallback to pandas OLS if available
    try:
        from pandas.stats.api import ols as OLS
    except ImportError:
        # OLS not available in this pandas version
        raise ImportError("OLS is not available. Please install aqr.stats.ols or use pandas < 0.20.0")
'''
        
        # Replace various OLS patterns
        new_content = content
        new_content = re.sub(r'pd\.ols\s*\(', 'OLS(', new_content)
        new_content = re.sub(r'pd\.stats\.ols\.OLS\s*\(', 'OLS(', new_content)
        
        # Add import if not present
        if 'from aqr.stats.ols import OLS' not in new_content and new_content != content:
            lines = new_content.split('\n')
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith(('import ', 'from ')):
                    import_end = i
                    break
            
            lines.insert(import_end, compatibility_code)
            new_content = '\n'.join(lines)
            changes.append("Replaced pd.ols with compatibility wrapper")
        
        return new_content, changes


class BackwardCompatibleMigrationEngine:
    """Migration engine that ensures backward compatibility."""
    
    def __init__(self):
        """Initialize the migration engine."""
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[BackwardCompatibleRule]:
        """Initialize backward compatible rules."""
        return [
            BackwardCompatibleRule(
                name="ix_to_loc_iloc",
                pattern=r"\.ix\[",
                priority=1,
                description="Replace .ix with .loc/.iloc based on usage",
                strategy=CompatibilityStrategy.REPLACEMENT
            ),
            BackwardCompatibleRule(
                name="sort_compatibility",
                pattern=r"\.sort\s*\(",
                priority=2,
                description="Replace .sort() with .sort_values() + compatibility wrapper",
                strategy=CompatibilityStrategy.WRAPPER
            ),
            BackwardCompatibleRule(
                name="rolling_functions",
                pattern=r"pd\.rolling_",
                priority=3,
                description="Replace rolling functions with compatible API",
                strategy=CompatibilityStrategy.WRAPPER
            ),
            BackwardCompatibleRule(
                name="panel_replacement",
                pattern=r"pd\.Panel",
                priority=4,
                description="Replace Panel with compatibility import",
                strategy=CompatibilityStrategy.CONDITIONAL
            ),
            BackwardCompatibleRule(
                name="ols_replacement",
                pattern=r"pd\.(ols|stats\.ols)",
                priority=5,
                description="Replace OLS with compatibility import",
                strategy=CompatibilityStrategy.CONDITIONAL
            ),
        ]
    
    def apply_rules(self, content: str, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all backward compatible rules."""
        all_changes = []
        
        # CRITICAL: Check for imports that work in both versions - DO NOT CHANGE THEM
        if self._has_compatible_imports(content):
            # Skip any import-related changes for files with compatible imports
            all_changes.append({
                'rule': 'compatible_imports_check',
                'strategy': 'skip',
                'description': 'File uses imports that work in both pandas versions',
                'changes': ['No changes needed - imports are already compatible']
            })
        
        # Apply rules in priority order
        for rule in sorted(self.rules, key=lambda r: r.priority):
            if re.search(rule.pattern, content):
                content, changes = rule.apply(content, file_path)
                if changes:
                    all_changes.append({
                        'rule': rule.name,
                        'strategy': rule.strategy.value,
                        'description': rule.description,
                        'changes': changes
                    })
        
        return content, all_changes
    
    def _has_compatible_imports(self, content: str) -> bool:
        """Check if file uses imports that work in both pandas versions.
        
        IMPORTANT: These imports work in BOTH pandas 0.19.2 and 1.1.5,
        so they should NEVER be changed.
        """
        compatible_imports = [
            r'from\s+pandas\.util\.testing\s+import',
            r'import\s+pandas\.util\.testing',
            r'from\s+pandas\.util\s+import\s+testing',
            r'import\s+pandas\.util\.testing\s+as',
            r'pandas\.util\.testing',
            # Add more compatible imports as needed
            r'from\s+pandas\.tseries',
            r'import\s+pandas\.tseries',
            r'from\s+pandas\.compat',
            r'import\s+pandas\.compat',
        ]
        
        for pattern in compatible_imports:
            if re.search(pattern, content):
                return True
        
        return False
    
    def validate_compatibility(self, content: str) -> Dict[str, Any]:
        """Validate that the migrated code is backward compatible."""
        issues = []
        
        # Check for direct usage of new-only APIs
        new_only_patterns = [
            (r'\.to_numpy\(\)', 'to_numpy() only available in pandas >= 0.24.0'),
            (r'\.isna\(\)', 'isna() only available in pandas >= 0.21.0'),
            (r'\.notna\(\)', 'notna() only available in pandas >= 0.21.0'),
        ]
        
        for pattern, message in new_only_patterns:
            if re.search(pattern, content):
                issues.append(message)
        
        # Check imports are properly wrapped
        if 'from aqr.' in content and 'try:' not in content:
            issues.append("Custom imports should be wrapped in try/except for compatibility")
        
        return {
            'compatible': len(issues) == 0,
            'issues': issues
        }