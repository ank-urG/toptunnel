"""Complex replacement patterns that need special handling."""

import re
import ast
from typing import Tuple, List, Dict, Any


class ComplexReplacements:
    """Handles complex pandas API replacements."""
    
    def apply_all(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all complex replacements."""
        all_changes = []
        
        # Apply each complex replacement
        content, changes = self.handle_ix_indexing(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_rolling_functions(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_get_set_value(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_empty_stack(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_datetimeindex_constructor(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_df_subtraction(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_ols_pool_parameter(content)
        all_changes.extend(changes)
        
        content, changes = self.handle_timestamp_overflow(content)
        all_changes.extend(changes)
        
        content, changes = self.add_required_imports(content, all_changes)
        all_changes.extend(changes)
        
        return content, all_changes
    
    def handle_ix_indexing(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Replace .ix[] with .loc[] or .iloc[] based on usage."""
        changes = []
        
        # Pattern to find .ix usage
        ix_pattern = r'(\w+)\.ix\[(.*?)\]'
        
        def replace_ix(match):
            var_name = match.group(1)
            index_expr = match.group(2)
            
            # Determine if it's positional or label-based
            # Check for pure integers or integer slices
            if re.match(r'^\d+$', index_expr.strip()):
                # Single integer - positional
                return f"{var_name}.iloc[{index_expr}]"
            elif re.match(r'^\d+\s*:\s*\d*$|^\s*:\s*\d+$|^\d+\s*:$', index_expr.strip()):
                # Integer slice - positional
                return f"{var_name}.iloc[{index_expr}]"
            elif ',' in index_expr:
                # Multi-dimensional indexing
                parts = index_expr.split(',', 1)
                first_part = parts[0].strip()
                second_part = parts[1].strip()
                
                # Check if both parts are integers
                if re.match(r'^\d+$', first_part) and re.match(r'^\d+$', second_part):
                    return f"{var_name}.iloc[{index_expr}]"
                else:
                    return f"{var_name}.loc[{index_expr}]"
            else:
                # Default to label-based
                return f"{var_name}.loc[{index_expr}]"
        
        new_content, count = re.subn(ix_pattern, replace_ix, content)
        if count > 0:
            changes.append({
                'rule': 'ix_replacement',
                'description': f'Replaced {count} .ix[] with .loc[]/.iloc[]',
                'count': count
            })
        
        return new_content, changes
    
    def handle_rolling_functions(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Replace pd.rolling_* functions with .rolling().* methods."""
        changes = []
        
        # Pattern for pd.rolling_* functions
        rolling_funcs = ['mean', 'sum', 'std', 'var', 'min', 'max', 'median', 'count']
        
        for func in rolling_funcs:
            pattern = rf'pd\.rolling_{func}\s*\(([^,]+),\s*(\d+)(.*?)\)'
            
            def make_replacer(func_name):
                def replacer(match):
                    data = match.group(1).strip()
                    window = match.group(2)
                    extra = match.group(3).rstrip(')')
                    return f"{data}.rolling({window}{extra}).{func_name}()"
                return replacer
            
            new_content, count = re.subn(pattern, make_replacer(func), content)
            if count > 0:
                content = new_content
                changes.append({
                    'rule': f'rolling_{func}',
                    'description': f'Replaced pd.rolling_{func}() with .rolling().{func}()',
                    'count': count
                })
        
        return content, changes
    
    def handle_get_set_value(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Replace get_value/set_value with .at[] accessor."""
        changes = []
        
        # Handle get_value
        get_pattern = r'\.get_value\s*\(([^,]+),\s*([^)]+)\)'
        
        def replace_get(match):
            row = match.group(1).strip()
            col = match.group(2).strip()
            return f".at[{row}, {col}]"
        
        new_content, count1 = re.subn(get_pattern, replace_get, content)
        
        # Handle set_value - more complex as it's a statement
        set_pattern = r'(\w+)\.set_value\s*\(([^,]+),\s*([^,]+),\s*([^)]+)\)'
        
        def replace_set(match):
            df_name = match.group(1)
            row = match.group(2).strip()
            col = match.group(3).strip()
            value = match.group(4).strip()
            # This creates a temporary marker
            return f"_SETVALUE_{df_name}[{row},{col}]={value}_"
        
        if count1 > 0:
            content = new_content
        
        temp_content, count2 = re.subn(set_pattern, replace_set, content)
        
        # Now replace the markers with proper syntax
        if count2 > 0:
            marker_pattern = r'_SETVALUE_(\w+)\[([^,]+),([^\]]+)\]=(.+?)_'
            
            def fix_set(match):
                df_name = match.group(1)
                row = match.group(2).strip()
                col = match.group(3).strip()
                value = match.group(4).strip()
                return f"{df_name}.at[{row}, {col}] = {value}"
            
            content, _ = re.subn(marker_pattern, fix_set, temp_content)
        
        if count1 > 0 or count2 > 0:
            changes.append({
                'rule': 'get_set_value',
                'description': f'Replaced get_value/set_value with .at[]',
                'count': count1 + count2
            })
        
        return content, changes
    
    def handle_empty_stack(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Add empty DataFrame check for .stack() operations."""
        changes = []
        
        # Pattern for .stack() calls
        stack_pattern = r'(\w+)\.stack\s*\(\s*\)'
        
        def replace_stack(match):
            var_name = match.group(1)
            # Wrap in conditional to handle empty DataFrames
            return f"({var_name}.stack() if not {var_name}.empty else pd.Series(dtype=object))"
        
        new_content, count = re.subn(stack_pattern, replace_stack, content)
        if count > 0:
            changes.append({
                'rule': 'empty_stack_check',
                'description': 'Added empty DataFrame check for .stack()',
                'count': count
            })
        
        return new_content, changes
    
    def handle_datetimeindex_constructor(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Replace pd.DatetimeIndex constructor with pd.date_range."""
        changes = []
        
        # Pattern for pd.DatetimeIndex(start, end, freq)
        dt_pattern = r'pd\.DatetimeIndex\s*\(([^,]+),\s*([^,]+),\s*freq\s*=\s*([^)]+)\)'
        
        def replace_dt(match):
            start = match.group(1).strip()
            end = match.group(2).strip()
            freq = match.group(3).strip()
            return f"pd.date_range({start}, {end}, freq={freq})"
        
        new_content, count = re.subn(dt_pattern, replace_dt, content)
        if count > 0:
            changes.append({
                'rule': 'datetimeindex_constructor',
                'description': 'Replaced pd.DatetimeIndex() with pd.date_range()',
                'count': count
            })
        
        return new_content, changes
    
    def handle_df_subtraction(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Replace df - df[col] with explicit .sub() method."""
        changes = []
        
        # Pattern for df - df[col]
        sub_pattern = r'(\w+)\s*-\s*\1\[([^\]]+)\]'
        
        def replace_sub(match):
            df_name = match.group(1)
            col = match.group(2)
            return f"{df_name}.sub({df_name}[{col}], axis=0)"
        
        new_content, count = re.subn(sub_pattern, replace_sub, content)
        if count > 0:
            changes.append({
                'rule': 'df_subtraction',
                'description': 'Replaced df - df[col] with .sub()',
                'count': count
            })
        
        return new_content, changes
    
    def handle_ols_pool_parameter(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Add pool=True to OLS calls when y is a DataFrame."""
        changes = []
        modified = content
        
        # Pattern for OLS calls
        ols_pattern = r'OLS\s*\(([^)]+)\)'
        
        matches = list(re.finditer(ols_pattern, modified))
        modifications = 0
        
        for match in reversed(matches):  # Work backwards to preserve positions
            args = match.group(1)
            
            # Check if y parameter looks like a DataFrame
            y_match = re.search(r'y\s*=\s*([^,\)]+)', args)
            if y_match:
                y_value = y_match.group(1).strip()
                
                # Check if y is likely a DataFrame
                if ('df' in y_value.lower() or 
                    'dataframe' in y_value.lower() or 
                    y_value.endswith(']') and '[' in y_value):
                    
                    # Check if pool is already present
                    if 'pool' not in args:
                        # Add pool=True
                        start = match.start()
                        end = match.end()
                        new_call = f"OLS({args}, pool=True)"
                        modified = modified[:start] + new_call + modified[end:]
                        modifications += 1
        
        if modifications > 0:
            changes.append({
                'rule': 'ols_pool_parameter',
                'description': 'Added pool=True to OLS calls with DataFrame y',
                'count': modifications
            })
        
        return modified, changes
    
    def handle_timestamp_overflow(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Add try-except for timestamp overflow operations."""
        changes = []
        
        # Look for offset calculations that might overflow
        # Pattern: variable = something + something * something
        offset_pattern = r'^(\s*)(\w+)\s*=\s*(\w+)\s*\+\s*(\w+)\s*\*\s*(\w+)(.*)$'
        
        lines = content.split('\n')
        new_lines = []
        modifications = 0
        
        for line in lines:
            match = re.match(offset_pattern, line)
            if match and any(keyword in line.lower() for keyword in ['offset', 'end', 'timestamp']):
                indent = match.group(1)
                var_name = match.group(2)
                
                # Wrap in try-except
                new_lines.extend([
                    f"{indent}try:",
                    f"{indent}    {line.strip()}",
                    f"{indent}except (OverflowError, pd.errors.OutOfBoundsDatetime):",
                    f"{indent}    import warnings",
                    f"{indent}    from pandas import Timestamp",
                    f"{indent}    msg = 'Offset beyond Timestamp range. Defaulting to max timestamp %s' % Timestamp.max",
                    f"{indent}    warnings.warn(msg, UserWarning)",
                    f"{indent}    {var_name} = Timestamp.max"
                ])
                modifications += 1
            else:
                new_lines.append(line)
        
        if modifications > 0:
            changes.append({
                'rule': 'timestamp_overflow',
                'description': 'Added overflow handling for timestamp calculations',
                'count': modifications
            })
            return '\n'.join(new_lines), changes
        
        return content, changes
    
    def add_required_imports(self, content: str, existing_changes: List[Dict]) -> Tuple[str, List[Dict[str, Any]]]:
        """Add necessary imports based on replacements made."""
        changes = []
        
        # Check what imports we need
        needs_panel = any(c['rule'] in ['panel_import', 'pd_panel'] for c in existing_changes)
        needs_ols = any(c['rule'] in ['ols_import', 'pd_ols', 'ols_pool_parameter'] for c in existing_changes)
        
        if not needs_panel and not needs_ols:
            return content, changes
        
        lines = content.split('\n')
        
        # Find where to insert imports
        import_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_line = i + 1
        
        # Add imports if not already present
        imports_added = []
        
        if needs_panel and 'from aqr.core.panel import Panel' not in content:
            lines.insert(import_line, 'from aqr.core.panel import Panel')
            imports_added.append('Panel')
            import_line += 1
        
        if needs_ols and 'from aqr.stats.ols import OLS' not in content:
            lines.insert(import_line, 'from aqr.stats.ols import OLS')
            imports_added.append('OLS')
        
        if imports_added:
            changes.append({
                'rule': 'add_imports',
                'description': f'Added imports for: {", ".join(imports_added)}',
                'count': len(imports_added)
            })
            return '\n'.join(lines), changes
        
        return content, changes