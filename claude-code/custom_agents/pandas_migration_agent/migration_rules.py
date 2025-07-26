"""Migration rules engine for pandas 0.19.2 to 1.1.5 migration."""

import re
import ast
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MigrationPriority(Enum):
    """Priority levels for migration rules."""
    CRITICAL = 1  # Must be fixed for code to work
    HIGH = 2      # Should be fixed for compatibility
    MEDIUM = 3    # Recommended to fix
    LOW = 4       # Optional improvements


@dataclass
class MigrationRule:
    """Represents a single migration rule."""
    name: str
    pattern: str
    replacement: str
    priority: MigrationPriority
    description: str
    test_pattern: Optional[str] = None
    requires_import: Optional[Dict[str, str]] = None
    
    def apply(self, content: str) -> Tuple[str, List[str]]:
        """Apply the migration rule to content.
        
        Returns:
            Tuple of (modified_content, list_of_changes_made)
        """
        changes = []
        original_content = content
        
        # Apply the main pattern replacement
        if self.test_pattern:
            # Use test pattern to check if rule applies
            if re.search(self.test_pattern, content):
                content, num_replacements = re.subn(self.pattern, self.replacement, content)
                if num_replacements > 0:
                    changes.append(f"Applied {self.name}: {num_replacements} replacements")
        else:
            content, num_replacements = re.subn(self.pattern, self.replacement, content)
            if num_replacements > 0:
                changes.append(f"Applied {self.name}: {num_replacements} replacements")
        
        # Add required imports if needed
        if self.requires_import and content != original_content:
            for import_stmt, module in self.requires_import.items():
                if module not in content:
                    # Add import at the top after other imports
                    import_lines = []
                    other_lines = []
                    for line in content.split('\\n'):
                        if line.strip().startswith(('import ', 'from ')) or not line.strip():
                            import_lines.append(line)
                        else:
                            other_lines.append(line)
                    
                    import_lines.append(import_stmt)
                    content = '\\n'.join(import_lines + other_lines)
                    changes.append(f"Added import: {import_stmt}")
        
        return content, changes


class MigrationRuleEngine:
    """Engine for applying pandas migration rules."""
    
    def __init__(self):
        """Initialize the migration rule engine with predefined rules."""
        self.rules = self._initialize_rules()
        self.custom_rules = []
        
    def _initialize_rules(self) -> List[MigrationRule]:
        """Initialize the default migration rules."""
        return [
            # Panel replacement
            MigrationRule(
                name="replace_pd_panel",
                pattern=r"pd\.Panel\s*\(",
                replacement="Panel(",
                priority=MigrationPriority.CRITICAL,
                description="Replace pd.Panel with custom Panel class",
                requires_import={"from aqr.core.panel import Panel": "aqr.core.panel"}
            ),
            
            # OLS replacement
            MigrationRule(
                name="replace_pd_ols",
                pattern=r"pd\.ols\s*\(",
                replacement="OLS(",
                priority=MigrationPriority.CRITICAL,
                description="Replace pd.ols with custom OLS class",
                requires_import={"from aqr.stats.ols import OLS": "aqr.stats.ols"}
            ),
            
            # stats.ols.OLS replacement
            MigrationRule(
                name="replace_pd_stats_ols",
                pattern=r"pd\.stats\.ols\.OLS\s*\(",
                replacement="OLS(",
                priority=MigrationPriority.CRITICAL,
                description="Replace pd.stats.ols.OLS with custom OLS class",
                requires_import={"from aqr.stats.ols import OLS": "aqr.stats.ols"}
            ),
            
            # ix indexer replacement
            MigrationRule(
                name="replace_ix_with_loc",
                pattern=r"\.ix\[",
                replacement=".loc[",
                priority=MigrationPriority.CRITICAL,
                description="Replace deprecated .ix indexer with .loc"
            ),
            
            # sort() to sort_values()
            MigrationRule(
                name="replace_sort_method",
                pattern=r"\.sort\s*\(",
                replacement=".sort_values(",
                priority=MigrationPriority.HIGH,
                description="Replace deprecated sort() with sort_values()"
            ),
            
            # valid() removal (requires custom handling)
            MigrationRule(
                name="replace_valid_method",
                pattern=r"\.valid\s*\(\s*\)",
                replacement=".dropna()",
                priority=MigrationPriority.HIGH,
                description="Replace deprecated valid() with dropna()"
            ),
            
            # Rolling functions
            MigrationRule(
                name="replace_rolling_mean",
                pattern=r"pd\.rolling_mean\s*\(",
                replacement="pd.DataFrame.rolling(",
                priority=MigrationPriority.HIGH,
                description="Replace pd.rolling_mean with .rolling().mean()",
                test_pattern=r"pd\.rolling_mean"
            ),
            
            MigrationRule(
                name="replace_rolling_sum",
                pattern=r"pd\.rolling_sum\s*\(",
                replacement="pd.DataFrame.rolling(",
                priority=MigrationPriority.HIGH,
                description="Replace pd.rolling_sum with .rolling().sum()",
                test_pattern=r"pd\.rolling_sum"
            ),
            
            MigrationRule(
                name="replace_rolling_std",
                pattern=r"pd\.rolling_std\s*\(",
                replacement="pd.DataFrame.rolling(",
                priority=MigrationPriority.HIGH,
                description="Replace pd.rolling_std with .rolling().std()",
                test_pattern=r"pd\.rolling_std"
            ),
            
            # as_matrix() to values
            MigrationRule(
                name="replace_as_matrix",
                pattern=r"\.as_matrix\s*\(\s*\)",
                replacement=".values",
                priority=MigrationPriority.MEDIUM,
                description="Replace deprecated as_matrix() with .values"
            ),
            
            # get_value/set_value to at
            MigrationRule(
                name="replace_get_value",
                pattern=r"\.get_value\s*\(",
                replacement=".at[",
                priority=MigrationPriority.MEDIUM,
                description="Replace deprecated get_value() with .at[]"
            ),
            
            MigrationRule(
                name="replace_set_value",
                pattern=r"\.set_value\s*\(",
                replacement=".at[",
                priority=MigrationPriority.MEDIUM,
                description="Replace deprecated set_value() with .at[]"
            ),
            
            # convert_objects to infer_objects
            MigrationRule(
                name="replace_convert_objects",
                pattern=r"\.convert_objects\s*\(",
                replacement=".infer_objects(",
                priority=MigrationPriority.MEDIUM,
                description="Replace deprecated convert_objects() with infer_objects()"
            ),
            
            # order parameter in categorical
            MigrationRule(
                name="replace_categorical_order",
                pattern=r"pd\.Categorical\s*\([^)]+order\s*=\s*True",
                replacement="pd.Categorical(ordered=True",
                priority=MigrationPriority.LOW,
                description="Replace 'order' parameter with 'ordered' in Categorical"
            ),
        ]
    
    def add_custom_rule(self, rule: MigrationRule):
        """Add a custom migration rule."""
        self.custom_rules.append(rule)
    
    def apply_rules(self, content: str, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all migration rules to the content.
        
        Args:
            content: File content to migrate
            filename: Name of the file being processed
            
        Returns:
            Tuple of (migrated_content, list_of_applied_changes)
        """
        all_changes = []
        original_content = content
        
        # Apply all rules in priority order
        sorted_rules = sorted(
            self.rules + self.custom_rules,
            key=lambda r: r.priority.value
        )
        
        for rule in sorted_rules:
            try:
                new_content, changes = rule.apply(content)
                if changes:
                    all_changes.append({
                        'rule': rule.name,
                        'priority': rule.priority.name,
                        'description': rule.description,
                        'changes': changes
                    })
                    content = new_content
            except Exception as e:
                all_changes.append({
                    'rule': rule.name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Perform AST-based transformations for complex cases
        try:
            content = self._apply_ast_transformations(content, all_changes)
        except Exception as e:
            all_changes.append({
                'rule': 'ast_transformation',
                'error': str(e),
                'status': 'failed'
            })
        
        # Validate the migrated code
        validation_result = self._validate_migration(content)
        if not validation_result['valid']:
            all_changes.append({
                'rule': 'validation',
                'status': 'warning',
                'issues': validation_result['issues']
            })
        
        return content, all_changes
    
    def _apply_ast_transformations(self, content: str, changes: List[Dict]) -> str:
        """Apply AST-based transformations for complex migrations."""
        try:
            tree = ast.parse(content)
            transformer = PandasASTTransformer()
            new_tree = transformer.visit(tree)
            
            if transformer.modifications_made:
                changes.append({
                    'rule': 'ast_transformation',
                    'description': 'Applied AST-based transformations',
                    'changes': transformer.modifications_made
                })
                return ast.unparse(new_tree)
        except:
            # If AST transformation fails, return original content
            pass
        
        return content
    
    def _validate_migration(self, content: str) -> Dict[str, Any]:
        """Validate the migrated code for common issues."""
        issues = []
        
        # Check for remaining deprecated patterns
        deprecated_patterns = [
            (r"\.ix\[", "ix indexer still present"),
            (r"pd\.Panel", "pd.Panel not fully migrated"),
            (r"\.as_matrix\(", "as_matrix() still present"),
            (r"pd\.rolling_", "Old rolling functions still present"),
        ]
        
        for pattern, message in deprecated_patterns:
            if re.search(pattern, content):
                issues.append(message)
        
        # Check for syntax errors
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }


class PandasASTTransformer(ast.NodeTransformer):
    """AST transformer for complex pandas migrations."""
    
    def __init__(self):
        self.modifications_made = []
    
    def visit_Call(self, node):
        """Transform function calls."""
        # Handle rolling functions with more complex patterns
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'pd' and 
                node.func.attr.startswith('rolling_')):
                
                # Extract the operation (mean, sum, std, etc.)
                operation = node.func.attr.replace('rolling_', '')
                
                # Transform pd.rolling_X(data, window) to data.rolling(window).X()
                if len(node.args) >= 2:
                    data_arg = node.args[0]
                    window_arg = node.args[1]
                    
                    # Create the new rolling().operation() call
                    new_node = ast.Call(
                        func=ast.Attribute(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=data_arg,
                                    attr='rolling',
                                    ctx=ast.Load()
                                ),
                                args=[window_arg],
                                keywords=node.keywords
                            ),
                            attr=operation,
                            ctx=ast.Load()
                        ),
                        args=[],
                        keywords=[]
                    )
                    
                    self.modifications_made.append(
                        f"Transformed pd.{node.func.attr} to .rolling().{operation}()"
                    )
                    return new_node
        
        return self.generic_visit(node)