"""File filtering to ensure only appropriate files are modified."""

import os
from typing import List, Tuple, Dict
from pathlib import Path


class FileFilter:
    """Ensures only appropriate Python files are modified, excluding configs."""
    
    # Files that should NEVER be modified
    FORBIDDEN_FILES = {
        'setup.py',
        'setup.cfg',
        'pyproject.toml',
        'requirements.txt',
        'requirements.in',
        'requirements-dev.txt',
        'requirements-test.txt',
        'Pipfile',
        'Pipfile.lock',
        'poetry.lock',
        'environment.yml',
        'environment.yaml',
        'conda-requirements.txt',
        'tox.ini',
        '.pre-commit-config.yaml',
        'Makefile',
        'pytest.ini',
        '.coveragerc',
        'MANIFEST.in',
    }
    
    # Directories to skip
    FORBIDDEN_DIRS = {
        '__pycache__',
        '.git',
        '.tox',
        '.pytest_cache',
        '.mypy_cache',
        'venv',
        '.venv',
        'env',
        '.env',
        'build',
        'dist',
        '.egg-info',
        'node_modules',
        '.idea',
        '.vscode',
    }
    
    # Patterns in file paths to skip
    FORBIDDEN_PATTERNS = [
        'site-packages',
        'lib/python',
        '/migrations/',
        '/alembic/',
        'vendor/',
        'third_party/',
        'external/',
    ]
    
    @classmethod
    def is_safe_to_modify(cls, file_path: str) -> Tuple[bool, str]:
        """Check if a file is safe to modify.
        
        Args:
            file_path: Path to check
            
        Returns:
            Tuple of (is_safe, reason_if_not_safe)
        """
        path = Path(file_path)
        
        # Check if it's a Python file
        if not file_path.endswith('.py'):
            return False, "Not a Python file"
        
        # Check forbidden files
        if path.name in cls.FORBIDDEN_FILES:
            return False, f"Configuration file: {path.name}"
        
        # Check forbidden directories
        for part in path.parts:
            if part in cls.FORBIDDEN_DIRS:
                return False, f"Forbidden directory: {part}"
        
        # Check forbidden patterns
        path_str = str(path)
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern in path_str:
                return False, f"Forbidden pattern: {pattern}"
        
        # Check if it's a test configuration file
        if 'conftest.py' in path.name:
            return False, "Test configuration file"
        
        # Check if it's a settings/config module
        if any(name in path.name.lower() for name in ['config', 'settings', 'conf']):
            # Allow if it's clearly application code, not build config
            if 'django' in path_str.lower() or 'flask' in path_str.lower():
                return True, ""
            # Be cautious with generic config files
            return False, "Possible configuration file"
        
        return True, ""
    
    @classmethod
    def filter_files(cls, files: List[str]) -> Dict[str, List[str]]:
        """Filter a list of files into safe and unsafe categories.
        
        Args:
            files: List of file paths
            
        Returns:
            Dict with 'safe' and 'unsafe' file lists
        """
        result = {
            'safe': [],
            'unsafe': []
        }
        
        for file_path in files:
            is_safe, reason = cls.is_safe_to_modify(file_path)
            if is_safe:
                result['safe'].append(file_path)
            else:
                result['unsafe'].append((file_path, reason))
        
        return result
    
    @classmethod
    def get_safe_python_files(cls, directory: str) -> List[str]:
        """Get all Python files that are safe to modify.
        
        Args:
            directory: Root directory to search
            
        Returns:
            List of safe Python file paths
        """
        safe_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip forbidden directories
            dirs[:] = [d for d in dirs if d not in cls.FORBIDDEN_DIRS]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    is_safe, _ = cls.is_safe_to_modify(file_path)
                    if is_safe:
                        safe_files.append(file_path)
        
        return safe_files