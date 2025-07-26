"""Compatibility checker for pandas migration."""

import ast
import re
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CompatibilityLevel(Enum):
    """Levels of compatibility issues."""
    BREAKING = "breaking"      # Will definitely break
    WARNING = "warning"        # May cause issues
    DEPRECATED = "deprecated"  # Still works but deprecated
    INFO = "info"             # Informational only


@dataclass
class CompatibilityIssue:
    """Represents a compatibility issue found in code."""
    level: CompatibilityLevel
    category: str
    description: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


class CompatibilityChecker:
    """Checks code compatibility between pandas versions."""
    
    def __init__(self):
        """Initialize the compatibility checker."""
        self.known_issues = self._initialize_known_issues()
        
    def _initialize_known_issues(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize database of known compatibility issues."""
        return {
            # API changes
            "api_changes": [
                {
                    "pattern": r"pd\.Panel",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "pd.Panel removed in pandas 1.0",
                    "suggestion": "Use MultiIndex or xarray for 3D data"
                },
                {
                    "pattern": r"pd\.ols|pd\.stats\.ols",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "Statistical functions moved out of pandas",
                    "suggestion": "Use statsmodels or custom implementation"
                },
                {
                    "pattern": r"\.ix\[",
                    "level": CompatibilityLevel.BREAKING,
                    "description": ".ix indexer removed",
                    "suggestion": "Use .loc for label-based or .iloc for position-based indexing"
                },
                {
                    "pattern": r"\.sort\(",
                    "level": CompatibilityLevel.BREAKING,
                    "description": ".sort() removed",
                    "suggestion": "Use .sort_values() or .sort_index()"
                },
                {
                    "pattern": r"\.valid\(\)",
                    "level": CompatibilityLevel.BREAKING,
                    "description": ".valid() method removed",
                    "suggestion": "Use .dropna() instead"
                },
            ],
            
            # Function changes
            "function_changes": [
                {
                    "pattern": r"pd\.rolling_mean|pd\.rolling_sum|pd\.rolling_std",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "Rolling functions removed from top-level API",
                    "suggestion": "Use .rolling().mean(), .rolling().sum(), etc."
                },
                {
                    "pattern": r"pd\.expanding_mean|pd\.expanding_sum",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "Expanding functions removed from top-level API",
                    "suggestion": "Use .expanding().mean(), .expanding().sum(), etc."
                },
                {
                    "pattern": r"pd\.ewma",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "pd.ewma removed",
                    "suggestion": "Use .ewm().mean()"
                },
            ],
            
            # Method changes
            "method_changes": [
                {
                    "pattern": r"\.as_matrix\(\)",
                    "level": CompatibilityLevel.DEPRECATED,
                    "description": ".as_matrix() deprecated",
                    "suggestion": "Use .values or .to_numpy()"
                },
                {
                    "pattern": r"\.get_value\(|\.set_value\(",
                    "level": CompatibilityLevel.DEPRECATED,
                    "description": "get_value/set_value deprecated",
                    "suggestion": "Use .at[] or .iat[] accessors"
                },
                {
                    "pattern": r"\.convert_objects\(",
                    "level": CompatibilityLevel.DEPRECATED,
                    "description": "convert_objects deprecated",
                    "suggestion": "Use .infer_objects() or specific astype()"
                },
                {
                    "pattern": r"\.select\(",
                    "level": CompatibilityLevel.BREAKING,
                    "description": ".select() method removed",
                    "suggestion": "Use .loc[] with callable"
                },
            ],
            
            # Parameter changes
            "parameter_changes": [
                {
                    "pattern": r"order\s*=\s*True",
                    "level": CompatibilityLevel.WARNING,
                    "description": "'order' parameter renamed to 'ordered' in Categorical",
                    "suggestion": "Use 'ordered=True' instead"
                },
                {
                    "pattern": r"fill_value\s*=\s*None",
                    "level": CompatibilityLevel.WARNING,
                    "description": "fill_value=None behavior changed in some operations",
                    "suggestion": "Explicitly specify fill_value or use default"
                },
            ],
            
            # Import changes
            "import_changes": [
                {
                    "pattern": r"from pandas\.lib import",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "pandas.lib module removed",
                    "suggestion": "Import from pandas directly"
                },
                {
                    "pattern": r"from pandas\.util\.decorators",
                    "level": CompatibilityLevel.BREAKING,
                    "description": "pandas.util.decorators moved",
                    "suggestion": "Import from pandas._libs or find alternative"
                },
            ],
            
            # Data type changes
            "dtype_changes": [
                {
                    "pattern": r"\.astype\(['\"]category['\"]",
                    "level": CompatibilityLevel.WARNING,
                    "description": "Category dtype behavior may have changed",
                    "suggestion": "Test category conversions carefully"
                },
                {
                    "pattern": r"datetime64\[ns, ",
                    "level": CompatibilityLevel.WARNING,
                    "description": "Timezone-aware datetime handling changed",
                    "suggestion": "Review timezone handling code"
                },
            ],
        }
    
    def check_file(self, file_path: str, content: str) -> List[CompatibilityIssue]:
        """Check a file for compatibility issues.
        
        Args:
            file_path: Path to the file being checked
            content: File content
            
        Returns:
            List of compatibility issues found
        """
        issues = []
        
        # Check using regex patterns
        issues.extend(self._check_patterns(content))
        
        # Check using AST analysis
        try:
            tree = ast.parse(content)
            issues.extend(self._check_ast(tree, content))
        except SyntaxError as e:
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.BREAKING,
                category="syntax",
                description=f"Syntax error: {e}",
                line_number=e.lineno,
                suggestion="Fix syntax errors before migration"
            ))
        
        # Check imports
        issues.extend(self._check_imports(content))
        
        # Sort by severity and line number
        issues.sort(key=lambda x: (
            list(CompatibilityLevel).index(x.level),
            x.line_number or 0
        ))
        
        return issues
    
    def _check_patterns(self, content: str) -> List[CompatibilityIssue]:
        """Check content against known patterns."""
        issues = []
        lines = content.split('\\n')
        
        for category, patterns in self.known_issues.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        issues.append(CompatibilityIssue(
                            level=pattern_info["level"],
                            category=category,
                            description=pattern_info["description"],
                            line_number=i,
                            suggestion=pattern_info["suggestion"],
                            code_snippet=line.strip()
                        ))
        
        return issues
    
    def _check_ast(self, tree: ast.AST, content: str) -> List[CompatibilityIssue]:
        """Check AST for compatibility issues."""
        issues = []
        
        class CompatibilityVisitor(ast.NodeVisitor):
            def __init__(self, parent_checker):
                self.checker = parent_checker
                self.issues = []
            
            def visit_Call(self, node):
                # Check for problematic function calls
                if isinstance(node.func, ast.Attribute):
                    # Check DataFrame/Series method calls
                    if node.func.attr in ['sort', 'valid', 'as_matrix', 'get_value', 'set_value']:
                        self.issues.append(CompatibilityIssue(
                            level=CompatibilityLevel.BREAKING,
                            category="method_call",
                            description=f"Method .{node.func.attr}() is removed or deprecated",
                            line_number=node.lineno,
                            column=node.col_offset,
                            suggestion=self._get_method_suggestion(node.func.attr)
                        ))
                    
                    # Check for ix accessor
                    if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'ix':
                        self.issues.append(CompatibilityIssue(
                            level=CompatibilityLevel.BREAKING,
                            category="indexing",
                            description="ix indexer is removed",
                            line_number=node.lineno,
                            column=node.col_offset,
                            suggestion="Use .loc for label-based or .iloc for position-based indexing"
                        ))
                
                # Check for top-level pandas functions
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'pd':
                        if node.func.attr in ['Panel', 'ols', 'rolling_mean', 'rolling_sum']:
                            self.issues.append(CompatibilityIssue(
                                level=CompatibilityLevel.BREAKING,
                                category="api_call",
                                description=f"pd.{node.func.attr} is removed",
                                line_number=node.lineno,
                                column=node.col_offset,
                                suggestion=self._get_function_suggestion(node.func.attr)
                            ))
                
                self.generic_visit(node)
            
            def _get_method_suggestion(self, method):
                suggestions = {
                    'sort': "Use .sort_values() or .sort_index()",
                    'valid': "Use .dropna()",
                    'as_matrix': "Use .values or .to_numpy()",
                    'get_value': "Use .at[] or .iat[]",
                    'set_value': "Use .at[] or .iat[]",
                }
                return suggestions.get(method, "Find alternative method")
            
            def _get_function_suggestion(self, func):
                suggestions = {
                    'Panel': "Use MultiIndex or xarray for 3D data",
                    'ols': "Use statsmodels or custom implementation",
                    'rolling_mean': "Use .rolling().mean()",
                    'rolling_sum': "Use .rolling().sum()",
                }
                return suggestions.get(func, "Find alternative function")
        
        visitor = CompatibilityVisitor(self)
        visitor.visit(tree)
        return visitor.issues
    
    def _check_imports(self, content: str) -> List[CompatibilityIssue]:
        """Check import statements for compatibility."""
        issues = []
        lines = content.split('\\n')
        
        for i, line in enumerate(lines, 1):
            # Check for problematic imports
            if 'from pandas.lib' in line:
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.BREAKING,
                    category="import",
                    description="pandas.lib module removed",
                    line_number=i,
                    suggestion="Import from pandas directly",
                    code_snippet=line.strip()
                ))
            
            if 'from pandas.util.decorators' in line:
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.BREAKING,
                    category="import",
                    description="pandas.util.decorators moved",
                    line_number=i,
                    suggestion="Find alternative import",
                    code_snippet=line.strip()
                ))
            
            # Check for Panel import
            if re.search(r'from pandas import.*Panel', line) or 'import pandas.Panel' in line:
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.BREAKING,
                    category="import",
                    description="Panel class removed from pandas",
                    line_number=i,
                    suggestion="Use custom Panel implementation or alternative",
                    code_snippet=line.strip()
                ))
        
        return issues
    
    def check_dependencies(self, requirements: List[str]) -> List[CompatibilityIssue]:
        """Check dependency compatibility.
        
        Args:
            requirements: List of requirement strings
            
        Returns:
            List of compatibility issues with dependencies
        """
        issues = []
        
        for req in requirements:
            # Check for packages that may have compatibility issues
            if 'pandas' in req and '<1.0' in req:
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.WARNING,
                    category="dependency",
                    description=f"Dependency pins old pandas: {req}",
                    suggestion="Update to allow pandas>=1.1.5"
                ))
            
            # Check for known incompatible packages
            incompatible_patterns = [
                ('pandas-datareader<0.9', 'Update to pandas-datareader>=0.9'),
                ('statsmodels<0.10', 'Update to statsmodels>=0.10'),
                ('xlrd<2.0', 'Update to xlrd>=2.0 or use openpyxl'),
            ]
            
            for pattern, suggestion in incompatible_patterns:
                if pattern in req:
                    issues.append(CompatibilityIssue(
                        level=CompatibilityLevel.WARNING,
                        category="dependency",
                        description=f"Potentially incompatible: {req}",
                        suggestion=suggestion
                    ))
        
        return issues
    
    def generate_compatibility_report(self, 
                                    all_issues: Dict[str, List[CompatibilityIssue]]) -> str:
        """Generate a compatibility report.
        
        Args:
            all_issues: Dictionary mapping file paths to lists of issues
            
        Returns:
            Formatted compatibility report
        """
        total_issues = sum(len(issues) for issues in all_issues.values())
        breaking_count = sum(
            1 for issues in all_issues.values() 
            for issue in issues 
            if issue.level == CompatibilityLevel.BREAKING
        )
        
        report = [
            "# Pandas Migration Compatibility Report",
            "",
            f"**Total Issues Found:** {total_issues}",
            f"**Breaking Changes:** {breaking_count}",
            "",
            "## Summary by Severity",
            ""
        ]
        
        # Count by level
        level_counts = {}
        for level in CompatibilityLevel:
            count = sum(
                1 for issues in all_issues.values() 
                for issue in issues 
                if issue.level == level
            )
            if count > 0:
                level_counts[level] = count
                report.append(f"- **{level.value.title()}:** {count} issues")
        
        report.extend(["", "## Issues by File", ""])
        
        # Group by file
        for file_path, issues in sorted(all_issues.items()):
            if not issues:
                continue
            
            report.append(f"### {file_path}")
            report.append(f"*{len(issues)} issues found*")
            report.append("")
            
            # Group by severity within file
            for level in CompatibilityLevel:
                level_issues = [i for i in issues if i.level == level]
                if level_issues:
                    report.append(f"#### {level.value.title()} Issues")
                    for issue in level_issues:
                        report.append(f"- **Line {issue.line_number or 'N/A'}:** {issue.description}")
                        if issue.code_snippet:
                            report.append(f"  ```python")
                            report.append(f"  {issue.code_snippet}")
                            report.append(f"  ```")
                        if issue.suggestion:
                            report.append(f"  **Suggestion:** {issue.suggestion}")
                    report.append("")
        
        return "\\n".join(report)