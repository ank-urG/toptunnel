"""
File handling utilities for pandas migration
"""

import os
import chardet
from typing import List, Optional, Tuple


def find_python_files(
    directory: str,
    recursive: bool = True,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Find all Python files in a directory"""
    python_files = []
    exclude_patterns = exclude_patterns or [
        '__pycache__',
        '.git',
        '.pytest_cache',
        'venv',
        'env',
        '.env',
        'build',
        'dist'
    ]
    
    if recursive:
        for root, dirs, files in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    python_files.append(file_path)
    else:
        for file in os.listdir(directory):
            if file.endswith('.py'):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    python_files.append(file_path)
    
    return sorted(python_files)


def get_file_encoding(file_path: str) -> str:
    """Detect file encoding"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except:
        return 'utf-8'


def read_file_safely(file_path: str, encoding: Optional[str] = None) -> Tuple[str, str]:
    """Safely read a file with encoding detection
    
    Returns:
        Tuple of (content, encoding_used)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Try provided encoding first
    if encoding:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read(), encoding
        except UnicodeDecodeError:
            pass
    
    # Auto-detect encoding
    detected_encoding = get_file_encoding(file_path)
    
    # Try detected encoding
    try:
        with open(file_path, 'r', encoding=detected_encoding) as f:
            return f.read(), detected_encoding
    except UnicodeDecodeError:
        # Fallback to utf-8 with error handling
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(), 'utf-8'


def write_file_safely(
    file_path: str,
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> bool:
    """Safely write content to a file
    
    Returns:
        True if successful
    """
    try:
        # Create directory if needed
        if create_dirs:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        
        # Write file
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
    except Exception as e:
        raise IOError(f"Failed to write file {file_path}: {str(e)}")


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get information about a file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat = os.stat(file_path)
    
    return {
        'path': file_path,
        'name': os.path.basename(file_path),
        'directory': os.path.dirname(file_path),
        'size': stat.st_size,
        'modified': stat.st_mtime,
        'created': stat.st_ctime,
        'is_file': os.path.isfile(file_path),
        'is_dir': os.path.isdir(file_path),
        'extension': os.path.splitext(file_path)[1]
    }


def create_temp_file(content: str, suffix: str = '.py') -> str:
    """Create a temporary file with content
    
    Returns:
        Path to the temporary file
    """
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name


def copy_with_structure(
    source_file: str,
    dest_dir: str,
    preserve_structure: bool = True
) -> str:
    """Copy a file preserving directory structure
    
    Returns:
        Path to the copied file
    """
    import shutil
    
    if preserve_structure:
        # Get relative path from common root
        common_root = os.path.commonpath([source_file, os.getcwd()])
        rel_path = os.path.relpath(source_file, common_root)
        dest_path = os.path.join(dest_dir, rel_path)
    else:
        dest_path = os.path.join(dest_dir, os.path.basename(source_file))
    
    # Create destination directory
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Copy file
    shutil.copy2(source_file, dest_path)
    
    return dest_path


def find_imports_in_file(file_path: str) -> List[str]:
    """Find all imports in a Python file"""
    content, _ = read_file_safely(file_path)
    
    imports = []
    import re
    
    # Find import statements
    import_pattern = re.compile(r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$', re.MULTILINE)
    
    for match in import_pattern.finditer(content):
        if match.group(1):  # from X import Y
            imports.append(match.group(1))
        else:  # import X
            # Handle multiple imports
            import_list = match.group(2).split(',')
            for imp in import_list:
                imp = imp.strip().split(' as ')[0]  # Remove aliases
                imports.append(imp)
    
    return list(set(imports))  # Remove duplicates