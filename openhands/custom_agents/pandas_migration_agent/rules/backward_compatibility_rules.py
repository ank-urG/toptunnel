"""
Backward compatibility rules for pandas migration from 0.19.2 to 1.1.5
"""

from typing import Dict, List, Tuple, Optional, Any
import re
import ast


class MigrationRule:
    """Base class for migration rules"""
    
    def __init__(self, name: str, description: str, risk_level: str = "low"):
        self.name = name
        self.description = description
        self.risk_level = risk_level
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        """Detect if this rule applies to the given code"""
        raise NotImplementedError
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        """Apply the transformation"""
        raise NotImplementedError


class PanelMigrationRule(MigrationRule):
    """pd.Panel -> aqr.core.panel.Panel"""
    
    def __init__(self):
        super().__init__(
            "panel_migration",
            "Replace pd.Panel with aqr.core.panel.Panel",
            "medium"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Pattern 1: pd.Panel(...)
        pattern1 = re.compile(r'pd\.Panel\s*\(')
        for match in pattern1.finditer(code):
            detections.append({
                'pattern': 'pd.Panel',
                'start': match.start(),
                'end': match.start() + len('pd.Panel'),
                'line': code[:match.start()].count('\n') + 1
            })
        
        # Pattern 2: pandas.Panel(...)
        pattern2 = re.compile(r'pandas\.Panel\s*\(')
        for match in pattern2.finditer(code):
            detections.append({
                'pattern': 'pandas.Panel',
                'start': match.start(),
                'end': match.start() + len('pandas.Panel'),
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Add import if not present
        import_line = "from aqr.core.panel import Panel\n"
        if "from aqr.core.panel import Panel" not in code:
            # Add import after other imports
            lines = code.split('\n')
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_idx = i + 1
            lines.insert(import_idx, import_line.strip())
            code = '\n'.join(lines)
        
        # Replace pd.Panel with Panel
        if detection['pattern'] == 'pd.Panel':
            code = code[:detection['start']] + 'Panel' + code[detection['end']:]
        elif detection['pattern'] == 'pandas.Panel':
            code = code[:detection['start']] + 'Panel' + code[detection['end']:]
        
        return code


class OlsMigrationRule(MigrationRule):
    """pd.ols() -> statsmodels or aqr.stats.ols"""
    
    def __init__(self):
        super().__init__(
            "ols_migration",
            "Replace pd.ols with appropriate alternative",
            "high"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Find pd.ols calls with context
        pattern = re.compile(r'pd\.ols\s*\([^)]+\)')
        for match in pattern.finditer(code):
            # Extract the full call
            call_text = match.group(0)
            
            # Check if it has pool parameter
            has_pool = 'pool' in call_text
            
            detections.append({
                'pattern': 'pd.ols',
                'start': match.start(),
                'end': match.end(),
                'call_text': call_text,
                'has_pool': has_pool,
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        if detection['has_pool']:
            # Use aqr.stats.ols for pool parameter
            import_line = "from aqr.stats.ols import OLS\n"
            if "from aqr.stats.ols import OLS" not in code:
                lines = code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_idx = i + 1
                lines.insert(import_idx, import_line.strip())
                code = '\n'.join(lines)
            
            # Replace pd.ols with OLS
            new_call = detection['call_text'].replace('pd.ols', 'OLS')
            # Ensure pool=True is set if y is DataFrame
            if 'pool=' not in new_call:
                new_call = new_call[:-1] + ', pool=True)'
            
            code = code[:detection['start']] + new_call + code[detection['end']:]
        else:
            # Use statsmodels for simple case
            import_lines = [
                "import statsmodels.api as sm",
                "from statsmodels.tools import add_constant"
            ]
            for import_line in import_lines:
                if import_line not in code:
                    lines = code.split('\n')
                    import_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            import_idx = i + 1
                    lines.insert(import_idx, import_line)
                    code = '\n'.join(lines)
            
            # Transform pd.ols(y, x) to sm.OLS(y, add_constant(x))
            # This is a simplified transformation - real implementation would parse arguments
            call_text = detection['call_text']
            # Extract arguments (simplified)
            args_text = call_text[len('pd.ols('):-1]
            args = [arg.strip() for arg in args_text.split(',')]
            
            if len(args) >= 2:
                y_arg = args[0]
                x_arg = args[1]
                new_call = f"sm.OLS({y_arg}, add_constant({x_arg}))"
                code = code[:detection['start']] + new_call + code[detection['end']:]
        
        return code


class ValidMethodRule(MigrationRule):
    """df.valid() / series.valid() -> df.dropna() / series.dropna()"""
    
    def __init__(self):
        super().__init__(
            "valid_method",
            "Replace .valid() with .dropna()",
            "low"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        pattern = re.compile(r'\.valid\s*\(\s*\)')
        for match in pattern.finditer(code):
            detections.append({
                'pattern': '.valid()',
                'start': match.start(),
                'end': match.end(),
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        return code[:detection['start']] + '.dropna()' + code[detection['end']:]


class DatetimeIndexImportRule(MigrationRule):
    """Fix DatetimeIndex import path"""
    
    def __init__(self):
        super().__init__(
            "datetime_index_import",
            "Fix DatetimeIndex import from pandas.tseries.offsets",
            "low"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        pattern = re.compile(r'from\s+pandas\.tseries\.offsets\s+import\s+.*DatetimeIndex')
        for match in pattern.finditer(code):
            detections.append({
                'pattern': 'pandas.tseries.offsets import',
                'start': match.start(),
                'end': match.end(),
                'line': code[:match.start()].count('\n') + 1,
                'full_match': match.group(0)
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Replace the import
        new_import = "from pandas import DatetimeIndex"
        return code[:detection['start']] + new_import + code[detection['end']:]


class DatetimeIndexConstructorRule(MigrationRule):
    """pd.DatetimeIndex(start, end, freq) -> pd.date_range(start, end, freq)"""
    
    def __init__(self):
        super().__init__(
            "datetime_index_constructor",
            "Replace DatetimeIndex constructor with date_range",
            "medium"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Match pd.DatetimeIndex with 3 arguments (start, end, freq pattern)
        pattern = re.compile(r'pd\.DatetimeIndex\s*\([^,]+,[^,]+,[^)]+\)')
        for match in pattern.finditer(code):
            call_text = match.group(0)
            # Simple heuristic: if it has freq, it's likely the constructor pattern
            if 'freq' in call_text or call_text.count(',') == 2:
                detections.append({
                    'pattern': 'pd.DatetimeIndex',
                    'start': match.start(),
                    'end': match.start() + len('pd.DatetimeIndex'),
                    'full_call': call_text,
                    'line': code[:match.start()].count('\n') + 1
                })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        return code[:detection['start']] + 'pd.date_range' + code[detection['end']:]


class DataFrameSeriesOpRule(MigrationRule):
    """df - series -> df.sub(series, axis=0)"""
    
    def __init__(self):
        super().__init__(
            "dataframe_series_op",
            "Replace DataFrame-Series operations with explicit methods",
            "medium"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # This is a simplified detection - real implementation would use AST
        # Pattern: variable - variable (where one might be df and other series)
        pattern = re.compile(r'(\w+)\s*-\s*(\w+)\[([\'"][^\'"]+[\'"])\]')
        for match in pattern.finditer(code):
            detections.append({
                'pattern': 'df-series',
                'start': match.start(),
                'end': match.end(),
                'df_var': match.group(1),
                'series_expr': match.group(0),
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Replace df - df[col] with df.sub(df[col], axis=0)
        new_expr = f"{detection['df_var']}.sub({detection['series_expr'].split(' - ')[1]}, axis=0)"
        return code[:detection['start']] + new_expr + code[detection['end']:]


class StackEmptyDataFrameRule(MigrationRule):
    """Handle df.stack() for empty DataFrames"""
    
    def __init__(self):
        super().__init__(
            "stack_empty_df",
            "Add validation for empty DataFrame stack operations",
            "medium"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Find .stack() calls
        pattern = re.compile(r'(\w+)\.stack\s*\(\s*\)')
        for match in pattern.finditer(code):
            var_name = match.group(1)
            detections.append({
                'pattern': '.stack()',
                'start': match.start(),
                'end': match.end(),
                'var_name': var_name,
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Find the appropriate indentation
        line_start = code.rfind('\n', 0, detection['start']) + 1
        indentation = ' ' * (detection['start'] - line_start)
        
        # Create the safe version
        var = detection['var_name']
        safe_stack = f"""if {var}.empty:
{indentation}    result = pd.Series(dtype=object)
{indentation}else:
{indentation}    result = {var}.stack()"""
        
        # Replace the line containing the stack call
        lines = code.split('\n')
        line_num = detection['line'] - 1
        lines[line_num] = safe_stack
        
        return '\n'.join(lines)


class TimeGrouperRule(MigrationRule):
    """pd.TimeGrouper -> pd.Grouper"""
    
    def __init__(self):
        super().__init__(
            "time_grouper",
            "Replace TimeGrouper with Grouper",
            "low"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        pattern = re.compile(r'pd\.TimeGrouper\s*\(')
        for match in pattern.finditer(code):
            detections.append({
                'pattern': 'pd.TimeGrouper',
                'start': match.start(),
                'end': match.start() + len('pd.TimeGrouper'),
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Replace pd.TimeGrouper with pd.Grouper
        new_code = code[:detection['start']] + 'pd.Grouper' + code[detection['end']:]
        
        # Ensure freq parameter is used
        # Find the opening parenthesis
        paren_pos = detection['end']
        # Simple check if first argument looks like a frequency string
        next_chars = new_code[paren_pos:paren_pos+10]
        if next_chars.startswith("('") or next_chars.startswith('("'):
            # Likely a frequency string, add freq=
            new_code = new_code[:paren_pos+1] + 'freq=' + new_code[paren_pos+1:]
        
        return new_code


class OutOfBoundsDatetimeRule(MigrationRule):
    """Handle OutOfBoundsDatetime exceptions"""
    
    def __init__(self):
        super().__init__(
            "out_of_bounds_datetime",
            "Add exception handling for timestamp operations",
            "medium"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Look for timestamp arithmetic that might overflow
        # Pattern: variable + variable * variable (common in offset calculations)
        pattern = re.compile(r'(\w+)\s*\+\s*(\w+)\s*\*\s*(\w+)')
        for match in pattern.finditer(code):
            # Check if any variable might be a date/timestamp
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_end = code.find('\n', match.end())
            if line_end == -1:
                line_end = len(code)
            
            line = code[line_start:line_end]
            if any(word in line.lower() for word in ['date', 'time', 'offset', 'end', 'start']):
                detections.append({
                    'pattern': 'timestamp_arithmetic',
                    'start': line_start,
                    'end': line_end,
                    'expression': match.group(0),
                    'line': code[:match.start()].count('\n') + 1
                })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Wrap in try-except
        line = code[detection['start']:detection['end']]
        indentation = ' ' * (len(line) - len(line.lstrip()))
        
        wrapped = f"""{indentation}try:
{indentation}    {line.strip()}
{indentation}except (OverflowError, pd.errors.OutOfBoundsDatetime):
{indentation}    import warnings
{indentation}    from pandas import Timestamp
{indentation}    warnings.warn("Offset beyond Timestamp range. Defaulting to max timestamp", UserWarning)
{indentation}    {detection['expression'].split()[0]} = Timestamp.max"""
        
        return code[:detection['start']] + wrapped + code[detection['end']:]


class MonthOffsetRule(MigrationRule):
    """pd.to_timedelta(n, unit='M') -> pd.DateOffset(months=n)"""
    
    def __init__(self):
        super().__init__(
            "month_offset",
            "Replace month timedelta with DateOffset",
            "low"
        )
    
    def detect(self, code: str) -> List[Dict[str, Any]]:
        detections = []
        
        # Find pd.to_timedelta with unit='M'
        pattern = re.compile(r'pd\.to_timedelta\s*\([^,]+,\s*unit\s*=\s*[\'"]M[\'"]\s*\)')
        for match in pattern.finditer(code):
            detections.append({
                'pattern': 'pd.to_timedelta',
                'start': match.start(),
                'end': match.end(),
                'call': match.group(0),
                'line': code[:match.start()].count('\n') + 1
            })
        
        return detections
    
    def transform(self, code: str, detection: Dict[str, Any]) -> str:
        # Extract the first argument
        call = detection['call']
        # Simple extraction - real implementation would parse properly
        arg_start = call.find('(') + 1
        arg_end = call.find(',')
        months_arg = call[arg_start:arg_end].strip()
        
        new_call = f"pd.DateOffset(months={months_arg})"
        return code[:detection['start']] + new_call + code[detection['end']:]


# Registry of all rules
MIGRATION_RULES = [
    PanelMigrationRule(),
    OlsMigrationRule(),
    ValidMethodRule(),
    DatetimeIndexImportRule(),
    DatetimeIndexConstructorRule(),
    DataFrameSeriesOpRule(),
    StackEmptyDataFrameRule(),
    TimeGrouperRule(),
    OutOfBoundsDatetimeRule(),
    MonthOffsetRule(),
]


def analyze_code(code: str) -> Dict[str, Any]:
    """Analyze code and return all applicable migration rules"""
    results = {
        'rules_triggered': [],
        'total_issues': 0,
        'risk_assessment': 'low'
    }
    
    risk_scores = {'low': 0, 'medium': 1, 'high': 2}
    max_risk = 0
    
    for rule in MIGRATION_RULES:
        detections = rule.detect(code)
        if detections:
            results['rules_triggered'].append({
                'rule': rule.name,
                'description': rule.description,
                'detections': detections,
                'risk_level': rule.risk_level
            })
            results['total_issues'] += len(detections)
            max_risk = max(max_risk, risk_scores[rule.risk_level])
    
    # Set overall risk level
    for risk_name, score in risk_scores.items():
        if score == max_risk:
            results['risk_assessment'] = risk_name
            break
    
    return results


def apply_migrations(code: str, rules_to_apply: Optional[List[str]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Apply migration rules to code
    
    Returns:
        Tuple of (transformed_code, changes_made)
    """
    changes_made = []
    
    for rule in MIGRATION_RULES:
        if rules_to_apply and rule.name not in rules_to_apply:
            continue
        
        detections = rule.detect(code)
        # Apply transformations in reverse order to maintain positions
        for detection in reversed(detections):
            try:
                old_code = code
                code = rule.transform(code, detection)
                if code != old_code:
                    changes_made.append({
                        'rule': rule.name,
                        'line': detection['line'],
                        'description': rule.description
                    })
            except Exception as e:
                # Log but continue with other transformations
                changes_made.append({
                    'rule': rule.name,
                    'line': detection['line'],
                    'error': str(e)
                })
    
    return code, changes_made