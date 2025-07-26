"""Utility functions for pandas migration agent."""

import os
import re
import shutil
import ast
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import hashlib
import json
from datetime import datetime


def find_python_files(directory: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
    """Find all Python files in a directory.
    
    Args:
        directory: Root directory to search
        exclude_patterns: List of regex patterns to exclude
        
    Returns:
        List of Python file paths
    """
    exclude_patterns = exclude_patterns or [
        r'__pycache__',
        r'\.pyc$',
        r'\.pyo$',
        r'venv/',
        r'\.venv/',
        r'env/',
        r'\.env/',
        r'\.git/',
        r'\.tox/',
        r'build/',
        r'dist/',
        r'\.egg-info/',
    ]
    
    python_files = []
    
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if not any(re.search(p, os.path.join(root, d)) for p in exclude_patterns)]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if not any(re.search(p, file_path) for p in exclude_patterns):
                    python_files.append(file_path)
    
    return sorted(python_files)


def backup_file(file_path: str, backup_dir: Optional[str] = None) -> str:
    """Create a backup of a file.
    
    Args:
        file_path: Path to file to backup
        backup_dir: Directory to store backup (default: .pandas_migration_backup)
        
    Returns:
        Path to backup file
    """
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(file_path), '.pandas_migration_backup')
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create unique backup name with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = os.path.basename(file_path)
    backup_name = f"{file_name}.{timestamp}.backup"
    backup_path = os.path.join(backup_dir, backup_name)
    
    shutil.copy2(file_path, backup_path)
    
    # Also create a hash of the original file for verification
    with open(file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    # Store metadata
    metadata_path = backup_path + '.meta'
    with open(metadata_path, 'w') as f:
        json.dump({
            'original_path': file_path,
            'backup_time': timestamp,
            'file_hash': file_hash,
        }, f)
    
    return backup_path


def restore_file(file_path: str, backup_path: str) -> bool:
    """Restore a file from backup.
    
    Args:
        file_path: Original file path to restore to
        backup_path: Path to backup file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        shutil.copy2(backup_path, file_path)
        return True
    except Exception as e:
        print(f"Failed to restore {file_path} from {backup_path}: {e}")
        return False


def extract_pandas_imports(content: str) -> Dict[str, List[str]]:
    """Extract pandas-related imports from Python code.
    
    Args:
        content: Python file content
        
    Returns:
        Dictionary mapping import types to lists of imported items
    """
    imports = {
        'pandas': [],
        'pandas_modules': [],
        'pandas_aliases': {},
        'other_imports': []
    }
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'pandas' or alias.name.startswith('pandas.'):
                        imports['pandas'].append(alias.name)
                        if alias.asname:
                            imports['pandas_aliases'][alias.asname] = alias.name
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == 'pandas' or node.module.startswith('pandas.')):
                    for alias in node.names:
                        imports['pandas_modules'].append(f"{node.module}.{alias.name}")
                        if alias.asname:
                            imports['pandas_aliases'][alias.asname] = f"{node.module}.{alias.name}"
    
    except SyntaxError:
        # Fall back to regex parsing if AST fails
        import_pattern = r'^\\s*(?:from\\s+(pandas[\\w.]*))\\s+import\\s+([\\w,\\s]+)|^\\s*import\\s+(pandas[\\w.]*)'
        
        for line in content.split('\\n'):
            match = re.match(import_pattern, line)
            if match:
                if match.group(1):  # from pandas.x import y
                    module = match.group(1)
                    items = match.group(2).split(',')
                    for item in items:
                        item = item.strip()
                        if ' as ' in item:
                            name, alias = item.split(' as ')
                            imports['pandas_modules'].append(f"{module}.{name.strip()}")
                            imports['pandas_aliases'][alias.strip()] = f"{module}.{name.strip()}"
                        else:
                            imports['pandas_modules'].append(f"{module}.{item}")
                elif match.group(3):  # import pandas.x
                    imports['pandas'].append(match.group(3))
    
    return imports


def parse_test_output(output: str, test_framework: str = 'pytest') -> Dict[str, Any]:
    """Parse test output to extract results.
    
    Args:
        output: Test command output
        test_framework: Testing framework used
        
    Returns:
        Dictionary with parsed test results
    """
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'duration': 0.0,
        'failed_tests': [],
        'passed_tests': [],
        'framework': test_framework
    }
    
    if test_framework == 'pytest':
        # Parse pytest output
        summary_pattern = r'(\\d+) passed.*?(\\d+) failed.*?(\\d+) skipped.*?in ([\\d.]+)s'
        match = re.search(summary_pattern, output)
        if match:
            results['passed'] = int(match.group(1))
            results['failed'] = int(match.group(2))
            results['skipped'] = int(match.group(3))
            results['duration'] = float(match.group(4))
            results['total'] = results['passed'] + results['failed'] + results['skipped']
        
        # Extract failed test names
        failed_pattern = r'FAILED (.+?) - '
        results['failed_tests'] = re.findall(failed_pattern, output)
        
        # Extract passed test names (if verbose)
        passed_pattern = r'PASSED (.+?)\\s'
        results['passed_tests'] = re.findall(passed_pattern, output)
    
    elif test_framework == 'unittest':
        # Parse unittest output
        summary_pattern = r'Ran (\\d+) test.*?in ([\\d.]+)s'
        match = re.search(summary_pattern, output)
        if match:
            results['total'] = int(match.group(1))
            results['duration'] = float(match.group(2))
        
        if 'OK' in output:
            results['passed'] = results['total']
        else:
            # Extract failures and errors
            failures_match = re.search(r'failures=(\\d+)', output)
            errors_match = re.search(r'errors=(\\d+)', output)
            
            if failures_match:
                results['failed'] = int(failures_match.group(1))
            if errors_match:
                results['errors'] = int(errors_match.group(1))
            
            results['passed'] = results['total'] - results['failed'] - results['errors']
    
    return results


def analyze_pandas_usage(file_path: str) -> Dict[str, Any]:
    """Analyze pandas usage in a Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        Dictionary with pandas usage analysis
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    analysis = {
        'file': file_path,
        'imports': extract_pandas_imports(content),
        'deprecated_features': [],
        'pandas_api_calls': [],
        'dataframe_methods': [],
        'series_methods': [],
        'index_operations': []
    }
    
    # Find deprecated features
    deprecated_patterns = {
        'pd.Panel': r'\\bpd\\.Panel\\b',
        'pd.ols': r'\\bpd\\.ols\\b',
        '.ix': r'\\.ix\\[',
        '.sort()': r'\\.sort\\s*\\(',
        '.valid()': r'\\.valid\\s*\\(',
        'pd.rolling_mean': r'\\bpd\\.rolling_mean\\b',
        '.as_matrix()': r'\\.as_matrix\\s*\\(',
        '.get_value()': r'\\.get_value\\s*\\(',
        '.set_value()': r'\\.set_value\\s*\\(',
    }
    
    lines = content.split('\\n')
    for feature, pattern in deprecated_patterns.items():
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                analysis['deprecated_features'].append({
                    'feature': feature,
                    'line': i,
                    'code': line.strip()
                })
    
    # Count pandas API calls
    api_patterns = [
        (r'\\bpd\\.DataFrame\\b', 'DataFrame'),
        (r'\\bpd\\.Series\\b', 'Series'),
        (r'\\bpd\\.read_csv\\b', 'read_csv'),
        (r'\\bpd\\.read_excel\\b', 'read_excel'),
        (r'\\bpd\\.merge\\b', 'merge'),
        (r'\\bpd\\.concat\\b', 'concat'),
        (r'\\bpd\\.pivot_table\\b', 'pivot_table'),
    ]
    
    for pattern, name in api_patterns:
        count = len(re.findall(pattern, content))
        if count > 0:
            analysis['pandas_api_calls'].append({'api': name, 'count': count})
    
    return analysis


def create_migration_summary(results: Dict[str, List[Dict[str, Any]]]) -> str:
    """Create a summary of migration results.
    
    Args:
        results: Dictionary mapping file paths to migration results
        
    Returns:
        Formatted summary string
    """
    total_files = len(results)
    successful = sum(1 for file_results in results.values() 
                    if any(r.get('status') == 'success' for r in file_results))
    failed = total_files - successful
    
    total_changes = sum(len(file_results) for file_results in results.values())
    
    deprecated_counts = {}
    for file_results in results.values():
        for result in file_results:
            if 'deprecated_feature' in result:
                feature = result['deprecated_feature']
                deprecated_counts[feature] = deprecated_counts.get(feature, 0) + 1
    
    summary = f"""
Migration Summary
================

Files Processed: {total_files}
Successful: {successful}
Failed: {failed}
Total Changes: {total_changes}

Deprecated Features Found:
"""
    
    for feature, count in sorted(deprecated_counts.items(), key=lambda x: x[1], reverse=True):
        summary += f"  - {feature}: {count} occurrences\\n"
    
    return summary


def validate_python_syntax(content: str) -> Tuple[bool, Optional[str]]:
    """Validate Python syntax.
    
    Args:
        content: Python code content
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def get_project_metadata(project_path: str) -> Dict[str, Any]:
    """Extract project metadata.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Dictionary with project metadata
    """
    metadata = {
        'name': os.path.basename(project_path),
        'path': project_path,
        'python_files': 0,
        'test_files': 0,
        'requirements': [],
        'setup_py': False,
        'pyproject_toml': False,
        'size_mb': 0
    }
    
    # Count Python files
    python_files = find_python_files(project_path)
    metadata['python_files'] = len(python_files)
    metadata['test_files'] = len([f for f in python_files if 'test' in f.lower()])
    
    # Check for requirements files
    req_files = ['requirements.txt', 'requirements.in', 'Pipfile', 'pyproject.toml']
    for req_file in req_files:
        req_path = os.path.join(project_path, req_file)
        if os.path.exists(req_path):
            metadata['requirements'].append(req_file)
    
    # Check for setup files
    metadata['setup_py'] = os.path.exists(os.path.join(project_path, 'setup.py'))
    metadata['pyproject_toml'] = os.path.exists(os.path.join(project_path, 'pyproject.toml'))
    
    # Calculate project size
    total_size = 0
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                try:
                    total_size += os.path.getsize(os.path.join(root, file))
                except:
                    pass
    
    metadata['size_mb'] = round(total_size / (1024 * 1024), 2)
    
    return metadata