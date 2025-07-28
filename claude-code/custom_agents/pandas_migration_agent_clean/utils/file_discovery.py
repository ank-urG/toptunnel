"""File discovery utilities."""

import os
import fnmatch
from typing import List


def discover_python_files(root_path: str, exclude_patterns: List[str] = None) -> List[str]:
    """Discover all Python files in a directory tree.
    
    Args:
        root_path: Root directory to search
        exclude_patterns: List of patterns to exclude
        
    Returns:
        List of Python file paths
    """
    if exclude_patterns is None:
        exclude_patterns = []
    
    python_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Check if current directory should be excluded
        dir_name = os.path.basename(dirpath)
        if any(fnmatch.fnmatch(dir_name, pattern) for pattern in exclude_patterns):
            dirnames[:] = []  # Don't recurse into this directory
            continue
        
        # Check if path contains excluded pattern
        if any(pattern in dirpath for pattern in exclude_patterns):
            continue
        
        # Collect Python files
        for filename in filenames:
            if filename.endswith('.py'):
                file_path = os.path.join(dirpath, filename)
                
                # Skip if file matches exclude pattern
                if any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns):
                    continue
                
                python_files.append(file_path)
    
    return sorted(python_files)