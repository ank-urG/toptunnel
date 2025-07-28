"""
Code transformation tool for applying backward-compatible pandas migrations
"""

from typing import Dict, List, Any, Optional, Tuple
from litellm import ChatCompletionToolParam
import re
import ast


CodeTransformerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "transform_code",
        "description": """Transform Python code to be backward-compatible between pandas 0.19.2 and 1.1.5.
        
        This tool:
        - Applies specific transformation rules based on detected issues
        - Ensures code works in both pandas versions
        - Preserves original functionality
        - Adds necessary imports and exception handling
        - Only modifies code that needs migration""",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to transform"
                },
                "transformations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "panel_to_aqr",
                            "ols_to_statsmodels",
                            "ols_to_aqr",
                            "valid_to_dropna",
                            "fix_datetime_imports",
                            "datetime_index_to_date_range",
                            "df_series_ops",
                            "stack_empty_check",
                            "timegrouper_to_grouper",
                            "month_offset_fix",
                            "add_timestamp_exception_handling"
                        ]
                    },
                    "description": "List of transformations to apply"
                },
                "preserve_comments": {
                    "type": "boolean",
                    "description": "Whether to preserve comments in the code",
                    "default": True
                },
                "add_migration_comments": {
                    "type": "boolean",
                    "description": "Whether to add comments explaining migrations",
                    "default": True
                }
            },
            "required": ["code", "transformations"]
        }
    }
}


class CodeTransformer:
    """Handles code transformations for pandas migration"""
    
    def __init__(self, add_comments: bool = True):
        self.add_comments = add_comments
        self.imports_added = set()
    
    def transform(self, code: str, transformations: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply requested transformations to code"""
        changes = []
        
        for transformation in transformations:
            transformer_method = getattr(self, f"_transform_{transformation}", None)
            if transformer_method:
                old_code = code
                code = transformer_method(code)
                if code != old_code:
                    changes.append({
                        "transformation": transformation,
                        "applied": True
                    })
            else:
                changes.append({
                    "transformation": transformation,
                    "applied": False,
                    "reason": "Unknown transformation"
                })
        
        # Add any required imports at the top
        if self.imports_added:
            code = self._add_imports(code)
        
        return code, changes
    
    def _add_imports(self, code: str) -> str:
        """Add required imports at the appropriate location"""
        lines = code.split('\n')
        
        # Find where to insert imports (after existing imports)
        import_insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_insert_idx = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                # First non-import, non-comment line
                break
        
        # Insert imports
        for imp in sorted(self.imports_added):
            lines.insert(import_insert_idx, imp)
            import_insert_idx += 1
        
        # Add blank line after imports if needed
        if import_insert_idx > 0 and lines[import_insert_idx].strip():
            lines.insert(import_insert_idx, '')
        
        return '\n'.join(lines)
    
    def _transform_panel_to_aqr(self, code: str) -> str:
        """Transform pd.Panel to aqr.core.panel.Panel"""
        # Add import
        self.imports_added.add("from aqr.core.panel import Panel")
        
        # Replace pd.Panel with Panel
        code = re.sub(r'\bpd\.Panel\b', 'Panel', code)
        code = re.sub(r'\bpandas\.Panel\b', 'Panel', code)
        
        if self.add_comments:
            # Add migration comment
            code = re.sub(
                r'(Panel\s*\()',
                r'# Migrated from pd.Panel to aqr.core.panel.Panel for compatibility\n\1',
                code,
                count=1
            )
        
        return code
    
    def _transform_ols_to_statsmodels(self, code: str) -> str:
        """Transform simple pd.ols to statsmodels"""
        # Add imports
        self.imports_added.add("import statsmodels.api as sm")
        self.imports_added.add("from statsmodels.tools import add_constant")
        
        # Simple pattern: pd.ols(y, x)
        def replace_ols(match):
            indent = match.group(1)
            args = match.group(2)
            # Simple parsing - assumes y, x pattern
            args_list = [arg.strip() for arg in args.split(',')]
            if len(args_list) >= 2:
                y_arg = args_list[0]
                x_arg = args_list[1]
                replacement = f"{indent}sm.OLS({y_arg}, add_constant({x_arg}))"
                if self.add_comments:
                    replacement = f"{indent}# Migrated from pd.ols to statsmodels\n{replacement}"
                return replacement
            return match.group(0)
        
        code = re.sub(
            r'(\s*)pd\.ols\s*\(([^)]+)\)',
            replace_ols,
            code
        )
        
        return code
    
    def _transform_ols_to_aqr(self, code: str) -> str:
        """Transform pd.ols with pool parameter to aqr.stats.ols"""
        # Add import
        self.imports_added.add("from aqr.stats.ols import OLS")
        
        # Pattern for pd.ols with pool
        def replace_ols_pool(match):
            indent = match.group(1)
            full_call = match.group(0)
            
            # Check if pool parameter exists
            if 'pool' in full_call:
                replacement = full_call.replace('pd.ols', 'OLS')
            else:
                # Add pool=True for DataFrame inputs
                replacement = full_call[:-1] + ', pool=True)'
                replacement = replacement.replace('pd.ols', 'OLS')
            
            if self.add_comments:
                return f"{indent}# Migrated from pd.ols to aqr.stats.ols for pool functionality\n{replacement}"
            return replacement
        
        # Only transform pd.ols calls that have pool or multiple parameters
        code = re.sub(
            r'(\s*)pd\.ols\s*\([^)]*pool[^)]*\)',
            replace_ols_pool,
            code
        )
        
        return code
    
    def _transform_valid_to_dropna(self, code: str) -> str:
        """Transform .valid() to .dropna()"""
        code = re.sub(r'\.valid\s*\(\s*\)', '.dropna()', code)
        
        if self.add_comments and '.dropna()' in code:
            # Add comment on first occurrence
            code = re.sub(
                r'(.dropna\(\))',
                r'# Migrated from .valid() to .dropna()\n\1',
                code,
                count=1
            )
        
        return code
    
    def _transform_fix_datetime_imports(self, code: str) -> str:
        """Fix DatetimeIndex imports"""
        # Replace old import path
        code = re.sub(
            r'from\s+pandas\.tseries\.offsets\s+import\s+([^;\n]+)',
            lambda m: f"from pandas import {m.group(1)}",
            code
        )
        
        if self.add_comments:
            code = re.sub(
                r'(from pandas import.*DatetimeIndex)',
                r'# Migrated import path for DatetimeIndex\n\1',
                code,
                count=1
            )
        
        return code
    
    def _transform_datetime_index_to_date_range(self, code: str) -> str:
        """Transform DatetimeIndex constructor to date_range"""
        # Pattern: pd.DatetimeIndex(start, end, freq)
        code = re.sub(
            r'pd\.DatetimeIndex\s*\(([^,]+),([^,]+),([^)]+)\)',
            r'pd.date_range(\1,\2,\3)',
            code
        )
        
        if self.add_comments and 'pd.date_range' in code:
            code = re.sub(
                r'(pd\.date_range)',
                r'# Migrated from pd.DatetimeIndex constructor\n\1',
                code,
                count=1
            )
        
        return code
    
    def _transform_df_series_ops(self, code: str) -> str:
        """Transform DataFrame-Series operations"""
        # Pattern: df - df[col] -> df.sub(df[col], axis=0)
        def replace_df_series_op(match):
            df_var = match.group(1)
            series_expr = match.group(2)
            
            replacement = f"{df_var}.sub({series_expr}, axis=0)"
            if self.add_comments:
                return f"# Migrated DataFrame-Series operation for compatibility\n{replacement}"
            return replacement
        
        # Simple pattern - would need more sophisticated parsing for complex cases
        code = re.sub(
            r'(\w+)\s*-\s*((?:\w+\[[\'"][^\'"]+[\'"]\])|(?:\w+\.\w+))',
            replace_df_series_op,
            code
        )
        
        return code
    
    def _transform_stack_empty_check(self, code: str) -> str:
        """Add empty DataFrame check before .stack()"""
        # Find .stack() calls and add safety check
        lines = code.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            if '.stack()' in line:
                # Extract variable name
                match = re.search(r'(\w+)\.stack\(\)', line)
                if match:
                    var_name = match.group(1)
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    
                    if self.add_comments:
                        new_lines.append(f"{indent_str}# Added empty DataFrame check for .stack() compatibility")
                    
                    new_lines.append(f"{indent_str}if {var_name}.empty:")
                    new_lines.append(f"{indent_str}    result = pd.Series(dtype=object)")
                    new_lines.append(f"{indent_str}else:")
                    new_lines.append(f"{indent_str}    {line.strip()}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _transform_timegrouper_to_grouper(self, code: str) -> str:
        """Transform TimeGrouper to Grouper"""
        # Replace pd.TimeGrouper with pd.Grouper
        code = re.sub(r'pd\.TimeGrouper\s*\(', 'pd.Grouper(freq=', code)
        
        # Fix if frequency is first positional argument
        code = re.sub(
            r'pd\.Grouper\(freq=([\'"][^"\']+[\'"])\)',
            r'pd.Grouper(freq=\1)',
            code
        )
        
        if self.add_comments and 'pd.Grouper' in code:
            code = re.sub(
                r'(pd\.Grouper)',
                r'# Migrated from pd.TimeGrouper\n\1',
                code,
                count=1
            )
        
        return code
    
    def _transform_month_offset_fix(self, code: str) -> str:
        """Transform month timedelta to DateOffset"""
        # Pattern: pd.to_timedelta(n, unit='M')
        def replace_month_timedelta(match):
            indent = match.group(1) if match.group(1) else ''
            n_value = match.group(2)
            
            replacement = f"{indent}pd.DateOffset(months={n_value})"
            if self.add_comments:
                return f"{indent}# Migrated from pd.to_timedelta with month unit\n{replacement}"
            return replacement
        
        code = re.sub(
            r'(\s*)pd\.to_timedelta\s*\(([^,]+),\s*unit\s*=\s*[\'"]M[\'"]\s*\)',
            replace_month_timedelta,
            code
        )
        
        return code
    
    def _transform_add_timestamp_exception_handling(self, code: str) -> str:
        """Add exception handling for timestamp operations"""
        # Look for patterns like: end + offset
        lines = code.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            # Simple pattern matching for date arithmetic
            if re.search(r'\w+\s*\+\s*\w+\s*\*\s*\w+', line) and \
               any(word in line.lower() for word in ['date', 'time', 'offset', 'end', 'start']):
                
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                
                if self.add_comments:
                    new_lines.append(f"{indent_str}# Added exception handling for potential timestamp overflow")
                
                new_lines.append(f"{indent_str}try:")
                new_lines.append(f"{indent_str}    {line.strip()}")
                new_lines.append(f"{indent_str}except (OverflowError, pd.errors.OutOfBoundsDatetime):")
                new_lines.append(f"{indent_str}    import warnings")
                new_lines.append(f"{indent_str}    from pandas import Timestamp")
                new_lines.append(f"{indent_str}    warnings.warn('Offset beyond Timestamp range. Defaulting to max timestamp', UserWarning)")
                new_lines.append(f"{indent_str}    # Set to max timestamp - adjust variable name as needed")
                new_lines.append(f"{indent_str}    result = Timestamp.max")
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)


def transform_code_implementation(
    code: str,
    transformations: List[str],
    preserve_comments: bool = True,
    add_migration_comments: bool = True
) -> Dict[str, Any]:
    """Implementation of code transformation"""
    
    result = {
        "success": False,
        "original_code": code,
        "transformed_code": code,
        "changes_made": [],
        "errors": []
    }
    
    try:
        transformer = CodeTransformer(add_comments=add_migration_comments)
        transformed_code, changes = transformer.transform(code, transformations)
        
        result["transformed_code"] = transformed_code
        result["changes_made"] = changes
        result["success"] = True
        
        # Count actual changes
        changes_applied = sum(1 for c in changes if c.get("applied", False))
        result["summary"] = f"Applied {changes_applied} of {len(transformations)} requested transformations"
        
    except Exception as e:
        result["errors"].append(str(e))
        result["success"] = False
    
    return result