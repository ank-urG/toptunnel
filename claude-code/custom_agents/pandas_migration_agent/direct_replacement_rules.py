"""Direct replacement rules for pandas migration without compatibility wrappers.

This module replaces deprecated pandas APIs with their direct equivalents
that work in BOTH pandas 0.19.2 and 1.1.5.
"""

import re
import ast
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class DirectReplacementRule:
    """A rule for direct API replacement."""
    name: str
    pattern: str
    replacement: str
    description: str
    complex: bool = False  # Whether it needs AST transformation
    

class DirectReplacementEngine:
    """Engine that makes direct code replacements without wrappers."""
    
    def __init__(self):
        """Initialize the direct replacement engine."""
        self.rules = self._initialize_rules()
        
    def _initialize_rules(self) -> List[DirectReplacementRule]:
        """Initialize direct replacement rules that work in both pandas versions."""
        return [
            # Simple regex-based replacements
            DirectReplacementRule(
                name="sort_to_sort_values",
                pattern=r'\.sort\s*\(',
                replacement='.sort_values(',
                description="Replace .sort() with .sort_values() - available since pandas 0.17.0"
            ),
            DirectReplacementRule(
                name="as_matrix_to_values",
                pattern=r'\.as_matrix\s*\(\s*\)',
                replacement='.values',
                description="Replace .as_matrix() with .values - available in both versions"
            ),
            DirectReplacementRule(
                name="valid_to_notnull",
                pattern=r'\.valid\s*\(\s*\)',
                replacement='.notnull()',
                description="Replace .valid() with .notnull() - available in both versions"
            ),
            DirectReplacementRule(
                name="TimeGrouper_to_Grouper",
                pattern=r'pd\.TimeGrouper\s*\(',
                replacement='pd.Grouper(',
                description="Replace pd.TimeGrouper with pd.Grouper - available since 0.16.1"
            ),
            DirectReplacementRule(
                name="sortlevel_to_sort_index",
                pattern=r'\.sortlevel\s*\(',
                replacement='.sort_index(level=',
                description="Replace .sortlevel() with .sort_index(level=) - available in both"
            ),
            # Panel and OLS need custom handling
            DirectReplacementRule(
                name="panel_import",
                pattern=r'from\s+pandas\s+import\s+Panel',
                replacement='from aqr.core.panel import Panel',
                description="Replace pandas Panel with custom implementation"
            ),
            DirectReplacementRule(
                name="pd_panel",
                pattern=r'pd\.Panel\s*\(',
                replacement='Panel(',  # Assumes Panel is imported
                description="Replace pd.Panel with Panel from aqr.core.panel"
            ),
            DirectReplacementRule(
                name="ols_import",
                pattern=r'from\s+pandas\.stats\.api\s+import\s+ols',
                replacement='from aqr.stats.ols import OLS as ols',
                description="Replace pandas OLS with custom implementation"
            ),
            DirectReplacementRule(
                name="pd_ols",
                pattern=r'pd\.ols\s*\(',
                replacement='OLS(',  # Assumes OLS is imported
                description="Replace pd.ols with OLS from aqr.stats.ols"
            ),
        ]
    
    def apply_rules(self, content: str, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all direct replacement rules."""
        all_changes = []
        modified_content = content
        
        # Apply simple regex replacements first
        for rule in self.rules:
            if not rule.complex and re.search(rule.pattern, modified_content):
                modified_content, count = re.subn(rule.pattern, rule.replacement, modified_content)
                if count > 0:
                    all_changes.append({
                        'rule': rule.name,
                        'description': rule.description,
                        'count': count
                    })
        
        # Handle rolling functions
        modified_content, rolling_changes = self._handle_rolling_functions(modified_content)
        if rolling_changes:
            all_changes.extend(rolling_changes)
        
        # Handle .ix replacements (complex)
        modified_content, ix_changes = self._handle_ix_replacement(modified_content)
        if ix_changes:
            all_changes.extend(ix_changes)
        
        # Handle get_value/set_value
        modified_content, value_changes = self._handle_value_methods(modified_content)
        if value_changes:
            all_changes.extend(value_changes)
        
        # Add necessary imports if Panel or OLS was replaced
        modified_content = self._add_necessary_imports(modified_content, all_changes)
        
        return modified_content, all_changes
    
    def _handle_rolling_functions(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Handle pd.rolling_* function replacements."""
        changes = []
        modified = content
        
        # Pattern for pd.rolling_* functions
        rolling_pattern = r'pd\.(rolling_(\w+))\s*\(([^,]+),\s*(\d+)(.*?)\)'
        
        def replace_rolling(match):
            func_name = match.group(2)  # mean, sum, std, etc.
            data_arg = match.group(3)
            window = match.group(4)
            extra_args = match.group(5)
            
            # Direct replacement that works in both versions
            return f"{data_arg}.rolling({window}{extra_args}).{func_name}()"
        
        new_content, count = re.subn(rolling_pattern, replace_rolling, modified)
        if count > 0:
            changes.append({
                'rule': 'rolling_functions',
                'description': 'Replace pd.rolling_* with .rolling().* - available since 0.18.0',
                'count': count
            })
            modified = new_content
        
        return modified, changes
    
    def _handle_ix_replacement(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Handle .ix replacements by analyzing usage context."""
        changes = []
        
        # Pattern to find .ix usage
        ix_pattern = r'(\w+)\.ix\[(.*?)\]'
        
        def replace_ix(match):
            var_name = match.group(1)
            index_expr = match.group(2)
            
            # Simple heuristic: if index is purely numeric, use iloc
            # Otherwise use loc (this covers most cases correctly)
            if re.match(r'^\d+$', index_expr.strip()):
                return f"{var_name}.iloc[{index_expr}]"
            elif ':' in index_expr and all(part.strip().isdigit() or part.strip() == '' 
                                          for part in index_expr.split(':')):
                # Numeric slice like 0:5
                return f"{var_name}.iloc[{index_expr}]"
            else:
                # Label-based or mixed indexing
                return f"{var_name}.loc[{index_expr}]"
        
        new_content, count = re.subn(ix_pattern, replace_ix, content)
        if count > 0:
            changes.append({
                'rule': 'ix_replacement',
                'description': 'Replace .ix with .loc/.iloc - available in both versions',
                'count': count
            })
        
        return new_content, changes
    
    def _handle_value_methods(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Handle get_value/set_value replacements."""
        changes = []
        modified = content
        
        # get_value replacement
        get_pattern = r'\.get_value\s*\(([^,]+),\s*([^)]+)\)'
        
        def replace_get_value(match):
            row = match.group(1)
            col = match.group(2)
            # Use .at for label-based scalar access
            return f".at[{row}, {col}]"
        
        modified, count1 = re.subn(get_pattern, replace_get_value, modified)
        
        # set_value replacement
        set_pattern = r'\.set_value\s*\(([^,]+),\s*([^,]+),\s*([^)]+)\)'
        
        def replace_set_value(match):
            row = match.group(1)
            col = match.group(2)
            value = match.group(3)
            # This needs to be handled differently - return a marker
            return f"._SET_VALUE_[{row}, {col}] = {value}"
        
        modified, count2 = re.subn(set_pattern, replace_set_value, modified)
        
        # Fix the set_value markers
        if count2 > 0:
            # Replace the markers with proper syntax
            modified = re.sub(r'(\w+)\._SET_VALUE_\[([^,]+),\s*([^\]]+)\]\s*=\s*(.+)', 
                            r'\1.at[\2, \3] = \4', modified)
        
        if count1 > 0 or count2 > 0:
            changes.append({
                'rule': 'value_methods',
                'description': 'Replace get_value/set_value with .at[] - available in both',
                'count': count1 + count2
            })
        
        return modified, changes
    
    def _add_necessary_imports(self, content: str, changes: List[Dict]) -> str:
        """Add necessary imports if Panel or OLS was replaced."""
        lines = content.split('\n')
        
        # Check if we need to add imports
        needs_panel = any(c['rule'] in ['panel_import', 'pd_panel'] for c in changes)
        needs_ols = any(c['rule'] in ['ols_import', 'pd_ols'] for c in changes)
        
        if not needs_panel and not needs_ols:
            return content
        
        # Find where to insert imports (after other imports)
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
            elif import_end > 0 and line.strip() and not line.strip().startswith('#'):
                break
        
        # Add imports if needed
        imports_to_add = []
        
        if needs_panel and 'from aqr.core.panel import Panel' not in content:
            imports_to_add.append('from aqr.core.panel import Panel')
            
        if needs_ols and 'from aqr.stats.ols import OLS' not in content:
            imports_to_add.append('from aqr.stats.ols import OLS')
        
        if imports_to_add:
            for imp in reversed(imports_to_add):
                lines.insert(import_end, imp)
        
        return '\n'.join(lines)
    
    def validate_changes(self, original: str, modified: str) -> Dict[str, Any]:
        """Validate that changes don't break the code."""
        try:
            # Check syntax
            ast.parse(modified)
            
            # Check that no compatibility wrappers were added
            wrapper_patterns = [
                'if not hasattr(',
                'compatibility wrapper',
                'monkey patch',
                'pd.DataFrame.sort_values = pd.DataFrame.sort',
                'try:.*pd.DataFrame.rolling.*except AttributeError:'
            ]
            
            has_wrappers = any(re.search(pattern, modified, re.IGNORECASE | re.DOTALL) 
                             for pattern in wrapper_patterns)
            
            return {
                'valid': not has_wrappers,
                'has_wrappers': has_wrappers,
                'syntax_valid': True
            }
            
        except SyntaxError as e:
            return {
                'valid': False,
                'syntax_valid': False,
                'error': str(e)
            }