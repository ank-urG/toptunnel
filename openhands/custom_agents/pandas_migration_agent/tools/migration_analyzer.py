"""
Code analysis tool for detecting pandas migration issues
"""

import ast
import re
from typing import Dict, List, Any, Optional
from litellm import ChatCompletionToolParam


MigrationAnalyzerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "analyze_for_migration",
        "description": """Analyze Python code to detect pandas API changes between versions 0.19.2 and 1.1.5.
        
        This tool:
        - Identifies deprecated or changed pandas APIs
        - Detects import issues
        - Finds patterns that may cause compatibility problems
        - Suggests appropriate migration strategies
        - Checks for AQR library dependencies""",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to analyze"
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional file path for context"
                },
                "deep_analysis": {
                    "type": "boolean",
                    "description": "Whether to perform deep AST-based analysis",
                    "default": True
                }
            },
            "required": ["code"]
        }
    }
}


class PandasAPIVisitor(ast.NodeVisitor):
    """AST visitor to detect pandas API usage patterns"""
    
    def __init__(self):
        self.issues = []
        self.imports = {}
        self.pandas_calls = []
        self.aqr_imports = []
    
    def visit_Import(self, node):
        for alias in node.names:
            if 'pandas' in alias.name:
                self.imports[alias.asname or alias.name] = alias.name
            if 'aqr' in alias.name:
                self.aqr_imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            if 'pandas' in node.module:
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
            if 'aqr' in node.module:
                self.aqr_imports.append(node.module)
            
            # Check for problematic imports
            if node.module == 'pandas.tseries.offsets':
                for alias in node.names:
                    if alias.name == 'DatetimeIndex':
                        self.issues.append({
                            'type': 'import_change',
                            'line': node.lineno,
                            'description': 'DatetimeIndex import from pandas.tseries.offsets is deprecated',
                            'fix': 'from pandas import DatetimeIndex'
                        })
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Check for pd.Panel
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id in self.imports and 
                'pandas' in self.imports[node.func.value.id]):
                
                attr_name = node.func.attr
                
                # Check for Panel
                if attr_name == 'Panel':
                    self.issues.append({
                        'type': 'api_removal',
                        'line': node.lineno,
                        'description': 'pd.Panel is removed in pandas 1.0+',
                        'fix': 'from aqr.core.panel import Panel'
                    })
                
                # Check for ols
                elif attr_name == 'ols':
                    # Check if pool parameter is used
                    has_pool = any(kw.arg == 'pool' for kw in node.keywords)
                    if has_pool:
                        self.issues.append({
                            'type': 'api_removal',
                            'line': node.lineno,
                            'description': 'pd.ols with pool parameter',
                            'fix': 'from aqr.stats.ols import OLS'
                        })
                    else:
                        self.issues.append({
                            'type': 'api_removal',
                            'line': node.lineno,
                            'description': 'pd.ols is removed',
                            'fix': 'import statsmodels.api as sm; sm.OLS(y, sm.add_constant(x))'
                        })
                
                # Check for DatetimeIndex constructor
                elif attr_name == 'DatetimeIndex' and len(node.args) >= 3:
                    self.issues.append({
                        'type': 'api_change',
                        'line': node.lineno,
                        'description': 'DatetimeIndex(start, end, freq) constructor pattern',
                        'fix': 'pd.date_range(start, end, freq)'
                    })
                
                # Check for TimeGrouper
                elif attr_name == 'TimeGrouper':
                    self.issues.append({
                        'type': 'api_deprecation',
                        'line': node.lineno,
                        'description': 'pd.TimeGrouper is deprecated',
                        'fix': 'pd.Grouper(freq=...)'
                    })
                
                # Check for to_timedelta with unit='M'
                elif attr_name == 'to_timedelta':
                    for kw in node.keywords:
                        if kw.arg == 'unit' and isinstance(kw.value, ast.Str) and kw.value.s == 'M':
                            self.issues.append({
                                'type': 'api_change',
                                'line': node.lineno,
                                'description': "pd.to_timedelta with unit='M' is not supported",
                                'fix': 'pd.DateOffset(months=n)'
                            })
        
        # Check for .valid() method calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'valid'):
            self.issues.append({
                'type': 'api_removal',
                'line': node.lineno,
                'description': '.valid() method is removed',
                'fix': '.dropna()'
            })
        
        # Check for .stack() calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'stack'):
            self.issues.append({
                'type': 'behavior_change',
                'line': node.lineno,
                'description': '.stack() may fail on empty DataFrames',
                'fix': 'Add empty DataFrame check before .stack()'
            })
        
        self.generic_visit(node)
    
    def visit_BinOp(self, node):
        # Check for DataFrame - Series operations
        if isinstance(node.op, ast.Sub):
            # This is a simplified check
            self.issues.append({
                'type': 'potential_issue',
                'line': node.lineno,
                'description': 'DataFrame-Series subtraction behavior may have changed',
                'fix': 'Consider using .sub(series, axis=0) for explicit behavior'
            })
        
        self.generic_visit(node)


def analyze_code_implementation(
    code: str,
    file_path: Optional[str] = None,
    deep_analysis: bool = True
) -> Dict[str, Any]:
    """Analyze code for pandas migration issues"""
    
    result = {
        "file_path": file_path,
        "issues": [],
        "aqr_dependencies": [],
        "risk_level": "low",
        "statistics": {
            "total_issues": 0,
            "by_type": {}
        }
    }
    
    # Quick pattern-based analysis
    patterns = [
        (r'pd\.Panel', 'pd.Panel usage detected'),
        (r'pd\.ols', 'pd.ols usage detected'),
        (r'\.valid\(\)', '.valid() method usage detected'),
        (r'pd\.TimeGrouper', 'pd.TimeGrouper usage detected'),
        (r'from\s+pandas\.tseries\.offsets', 'Deprecated import path detected'),
        (r'pd\.to_timedelta.*unit\s*=\s*[\'"]M[\'"]', 'Month timedelta usage detected'),
    ]
    
    for pattern, description in patterns:
        matches = re.finditer(pattern, code)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            result["issues"].append({
                "type": "pattern_match",
                "line": line_num,
                "description": description,
                "pattern": pattern
            })
    
    # Deep AST-based analysis
    if deep_analysis:
        try:
            tree = ast.parse(code)
            visitor = PandasAPIVisitor()
            visitor.visit(tree)
            
            # Add AST-detected issues
            result["issues"].extend(visitor.issues)
            result["aqr_dependencies"] = visitor.aqr_imports
            
        except SyntaxError as e:
            result["errors"] = f"Syntax error in code: {e}"
    
    # Calculate statistics
    result["statistics"]["total_issues"] = len(result["issues"])
    for issue in result["issues"]:
        issue_type = issue.get("type", "unknown")
        result["statistics"]["by_type"][issue_type] = \
            result["statistics"]["by_type"].get(issue_type, 0) + 1
    
    # Determine risk level
    if result["statistics"]["total_issues"] == 0:
        result["risk_level"] = "none"
    elif result["statistics"]["total_issues"] < 5:
        result["risk_level"] = "low"
    elif result["statistics"]["total_issues"] < 10:
        result["risk_level"] = "medium"
    else:
        result["risk_level"] = "high"
    
    # Add recommendations
    result["recommendations"] = generate_recommendations(result["issues"])
    
    return result


def generate_recommendations(issues: List[Dict[str, Any]]) -> List[str]:
    """Generate migration recommendations based on issues found"""
    recommendations = []
    
    issue_types = {issue.get("type") for issue in issues}
    
    if "api_removal" in issue_types:
        recommendations.append(
            "Critical: This code uses removed APIs. Migration is required for pandas 1.1.5 compatibility."
        )
    
    if "import_change" in issue_types:
        recommendations.append(
            "Update import statements to use new paths compatible with pandas 1.1.5."
        )
    
    if "behavior_change" in issue_types:
        recommendations.append(
            "Test thoroughly: Some operations may behave differently between versions."
        )
    
    if any("aqr" in str(issue) for issue in issues):
        recommendations.append(
            "Ensure AQR libraries are available by adding C:\\Workspace to PYTHONPATH."
        )
    
    if not recommendations:
        recommendations.append(
            "No major compatibility issues detected. Test in both environments to confirm."
        )
    
    return recommendations