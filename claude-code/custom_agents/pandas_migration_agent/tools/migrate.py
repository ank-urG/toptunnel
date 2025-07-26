"""Migration tool for applying pandas migration rules."""

from typing import Dict, List, Any, Tuple
from ..migration_rules import MigrationRuleEngine
from ..utils import backup_file, validate_python_syntax


class MigrateTool:
    """Tool for migrating pandas code."""
    
    name = "migrate_pandas_code"
    description = "Apply migration rules to update deprecated pandas features"
    
    def __init__(self, agent):
        """Initialize the migration tool.
        
        Args:
            agent: Parent PandasMigrationAgent instance
        """
        self.agent = agent
        self.rule_engine = MigrationRuleEngine()
    
    def __call__(self, file_path: str, create_backup: bool = True, **kwargs) -> Dict[str, Any]:
        """Migrate a single file.
        
        Args:
            file_path: Path to file to migrate
            create_backup: Whether to create backup
            **kwargs: Additional options
            
        Returns:
            Dictionary with migration results
        """
        result = {
            'file_path': file_path,
            'status': 'pending',
            'backup_path': None,
            'changes': [],
            'error': None,
            'syntax_valid': False
        }
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create backup if requested
            if create_backup:
                backup_path = backup_file(file_path)
                result['backup_path'] = backup_path
            
            # Apply migration rules
            migrated_content, changes = self.rule_engine.apply_rules(
                original_content, file_path
            )
            result['changes'] = changes
            
            # Validate syntax
            is_valid, error = validate_python_syntax(migrated_content)
            result['syntax_valid'] = is_valid
            
            if not is_valid:
                result['status'] = 'failed'
                result['error'] = f"Syntax error after migration: {error}"
                return result
            
            # Write migrated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(migrated_content)
            
            result['status'] = 'success'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        return result
    
    def migrate_files(self, file_paths: List[str], **kwargs) -> Dict[str, Dict[str, Any]]:
        """Migrate multiple files.
        
        Args:
            file_paths: List of file paths to migrate
            **kwargs: Additional options
            
        Returns:
            Dictionary mapping file paths to migration results
        """
        results = {}
        
        for file_path in file_paths:
            results[file_path] = self(file_path, **kwargs)
        
        return results