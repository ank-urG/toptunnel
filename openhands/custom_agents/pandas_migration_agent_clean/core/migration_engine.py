"""Core migration engine that applies all replacement rules."""

import os
import ast
from typing import Tuple, List, Dict, Any

from ..rules.replacement_rules import MigrationRules
from ..rules.complex_replacements import ComplexReplacements
from ..utils.file_utils import read_file, write_file, create_backup


class MigrationEngine:
    """Engine that performs the actual code migration."""
    
    def __init__(self):
        """Initialize the migration engine."""
        self.simple_rules = MigrationRules()
        self.complex_rules = ComplexReplacements()
        
        # DO NOT CHANGE these imports - they work in both versions
        self.preserve_imports = [
            'pandas.util.testing',
            'pandas.compat',
            'pandas.tseries',  # Some parts work in both
        ]
    
    def migrate_file(self, file_path: str, create_backup: bool = True) -> Dict[str, Any]:
        """Migrate a single Python file.
        
        Returns:
            Dict with migration results including status, changes made, etc.
        """
        result = {
            'file': file_path,
            'status': 'pending',
            'changes': [],
            'error': None,
            'backup_path': None
        }
        
        try:
            # Read the file
            content = read_file(file_path)
            original_content = content
            
            # Check if file needs migration
            if not self._needs_migration(content):
                result['status'] = 'skipped'
                result['reason'] = 'No pandas usage or deprecated APIs found'
                return result
            
            # Create backup if requested
            if create_backup:
                backup_path = create_backup(file_path)
                result['backup_path'] = backup_path
            
            # Apply simple regex-based rules
            content, simple_changes = self.simple_rules.apply_simple_rules(content)
            result['changes'].extend(simple_changes)
            
            # Apply complex replacements
            content, complex_changes = self.complex_rules.apply_all(content)
            result['changes'].extend(complex_changes)
            
            # Validate the migrated code
            if not self._validate_syntax(content):
                result['status'] = 'error'
                result['error'] = 'Syntax error after migration'
                return result
            
            # Check if any changes were made
            if content == original_content:
                result['status'] = 'unchanged'
                result['reason'] = 'No deprecated APIs found'
                return result
            
            # Write the migrated content
            write_file(file_path, content)
            
            result['status'] = 'success'
            result['total_changes'] = sum(c.get('count', 1) for c in result['changes'])
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def _needs_migration(self, content: str) -> bool:
        """Check if a file needs migration."""
        # Skip if no pandas usage
        if 'pandas' not in content and 'pd.' not in content:
            return False
        
        # Check for deprecated APIs
        deprecated_patterns = [
            r'\.sort\s*\(',
            r'\.valid\s*\(',
            r'\.ix\[',
            r'\.as_matrix\s*\(',
            r'pd\.rolling_',
            r'pd\.Panel',
            r'pd\.ols',
            r'pd\.TimeGrouper',
            r'\.get_value\s*\(',
            r'\.set_value\s*\(',
            r'\.sortlevel\s*\(',
            r'pd\.to_timedelta.*unit\s*=\s*["\']M["\']',
            r'from\s+pandas\.tseries\.offsets\s+import\s+DatetimeIndex',
        ]
        
        import re
        for pattern in deprecated_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _validate_syntax(self, content: str) -> bool:
        """Validate Python syntax after migration."""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    
    def get_migration_preview(self, file_path: str) -> Dict[str, Any]:
        """Get a preview of what would be changed without modifying the file."""
        try:
            content = read_file(file_path)
            
            # Apply rules without writing
            migrated_content, all_changes = self._apply_all_rules(content)
            
            return {
                'file': file_path,
                'changes': all_changes,
                'would_modify': content != migrated_content,
                'line_diff': self._generate_line_diff(content, migrated_content)
            }
        except Exception as e:
            return {
                'file': file_path,
                'error': str(e)
            }
    
    def _apply_all_rules(self, content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all migration rules to content."""
        all_changes = []
        
        # Apply simple rules
        content, simple_changes = self.simple_rules.apply_simple_rules(content)
        all_changes.extend(simple_changes)
        
        # Apply complex rules
        content, complex_changes = self.complex_rules.apply_all(content)
        all_changes.extend(complex_changes)
        
        return content, all_changes
    
    def _generate_line_diff(self, original: str, modified: str) -> List[Dict[str, Any]]:
        """Generate a simple line diff for preview."""
        diff = []
        
        original_lines = original.split('\n')
        modified_lines = modified.split('\n')
        
        for i, (orig, mod) in enumerate(zip(original_lines, modified_lines), 1):
            if orig != mod:
                diff.append({
                    'line': i,
                    'original': orig,
                    'modified': mod
                })
        
        return diff[:10]  # Limit to first 10 changes for preview