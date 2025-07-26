"""Test code compatibility across pandas versions before making changes."""

import tempfile
import subprocess
import os
from typing import Tuple, Dict, Any, Optional
import ast
import json


class CompatibilityTester:
    """Tests if code already works in both pandas versions."""
    
    def __init__(self, conda_envs: Dict[str, str]):
        """Initialize the compatibility tester.
        
        Args:
            conda_envs: Mapping of pandas versions to conda environment names
        """
        self.conda_envs = conda_envs
    
    def test_code_compatibility(self, file_path: str) -> Dict[str, Any]:
        """Test if a file works in both pandas versions.
        
        Args:
            file_path: Path to Python file to test
            
        Returns:
            Dict with compatibility results
        """
        results = {
            'file_path': file_path,
            'compatible_019': False,
            'compatible_115': False,
            'needs_migration': True,
            'errors': {}
        }
        
        # Test in pandas 0.19.2
        result_019 = self._test_file_in_env(file_path, "0.19.2")
        results['compatible_019'] = result_019['success']
        if not result_019['success']:
            results['errors']['0.19.2'] = result_019['error']
        
        # Test in pandas 1.1.5
        result_115 = self._test_file_in_env(file_path, "1.1.5")
        results['compatible_115'] = result_115['success']
        if not result_115['success']:
            results['errors']['1.1.5'] = result_115['error']
        
        # Determine if migration is needed
        if results['compatible_019'] and results['compatible_115']:
            results['needs_migration'] = False
        
        return results
    
    def _test_file_in_env(self, file_path: str, pandas_version: str) -> Dict[str, Any]:
        """Test a file in specific pandas environment.
        
        Args:
            file_path: Path to test
            pandas_version: Pandas version to test with
            
        Returns:
            Dict with test results
        """
        conda_env = self.conda_envs.get(pandas_version)
        if not conda_env:
            return {'success': False, 'error': f'No conda env for pandas {pandas_version}'}
        
        # Create a test script that imports and executes the file
        test_script = f'''
import sys
import traceback

try:
    # Import the file
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", "{file_path}")
    module = importlib.util.module_from_spec(spec)
    
    # Check for syntax errors and import errors
    spec.loader.exec_module(module)
    
    print("SUCCESS: File imports without errors")
except SyntaxError as e:
    print(f"SYNTAX_ERROR: {{e}}")
    sys.exit(1)
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(2)
except Exception as e:
    print(f"RUNTIME_ERROR: {{e}}")
    traceback.print_exc()
    sys.exit(3)
'''
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_script_path = f.name
        
        try:
            # Run test in conda environment
            cmd = f"conda run -n {conda_env} python {test_script_path}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse results
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                error_msg = result.stdout + result.stderr
                if 'SYNTAX_ERROR' in error_msg:
                    return {'success': False, 'error': 'Syntax error', 'details': error_msg}
                elif 'IMPORT_ERROR' in error_msg:
                    # Import errors might be due to pandas API differences
                    return {'success': False, 'error': 'Import error', 'details': error_msg}
                else:
                    return {'success': False, 'error': 'Runtime error', 'details': error_msg}
                    
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            # Clean up
            try:
                os.unlink(test_script_path)
            except:
                pass
    
    def check_pandas_api_usage(self, file_path: str) -> Dict[str, Any]:
        """Analyze what pandas APIs are used in a file.
        
        Args:
            file_path: Path to analyze
            
        Returns:
            Dict with API usage information
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # APIs that might need migration
        potentially_incompatible = {
            'ix': r'\.ix\[',
            'sort': r'\.sort\(',
            'valid': r'\.valid\(',
            'as_matrix': r'\.as_matrix\(',
            'Panel': r'pd\.Panel',
            'ols': r'pd\.ols',
            'rolling_mean': r'pd\.rolling_mean',
            'rolling_sum': r'pd\.rolling_sum',
            'rolling_std': r'pd\.rolling_std',
        }
        
        usage = {}
        for api, pattern in potentially_incompatible.items():
            import re
            if re.search(pattern, content):
                usage[api] = True
        
        return {
            'uses_potentially_incompatible_apis': len(usage) > 0,
            'apis_used': list(usage.keys())
        }


class PreMigrationChecker:
    """Checks files before migration to avoid unnecessary changes."""
    
    def __init__(self, compatibility_tester: CompatibilityTester):
        """Initialize the checker.
        
        Args:
            compatibility_tester: CompatibilityTester instance
        """
        self.tester = compatibility_tester
    
    def should_migrate_file(self, file_path: str) -> Tuple[bool, str]:
        """Determine if a file needs migration.
        
        Args:
            file_path: Path to check
            
        Returns:
            Tuple of (should_migrate, reason)
        """
        # First, check if it uses pandas at all
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'pandas' not in content and 'pd.' not in content:
                return False, "No pandas usage detected"
            
        except Exception as e:
            return False, f"Cannot read file: {e}"
        
        # Check if it uses potentially incompatible APIs
        api_check = self.tester.check_pandas_api_usage(file_path)
        if not api_check['uses_potentially_incompatible_apis']:
            return False, "No potentially incompatible pandas APIs used"
        
        # Test compatibility in both environments
        compat_result = self.tester.test_code_compatibility(file_path)
        
        if not compat_result['needs_migration']:
            return False, "Already compatible with both pandas versions"
        
        # File needs migration
        reasons = []
        if not compat_result['compatible_019']:
            reasons.append("Fails in pandas 0.19.2")
        if not compat_result['compatible_115']:
            reasons.append("Fails in pandas 1.1.5")
        reasons.append(f"Uses: {', '.join(api_check['apis_used'])}")
        
        return True, " | ".join(reasons)
    
    def check_directory(self, directory: str, safe_files: list) -> Dict[str, Any]:
        """Check all files in a directory for migration needs.
        
        Args:
            directory: Directory to check
            safe_files: List of files that are safe to modify
            
        Returns:
            Dict with files categorized by migration needs
        """
        results = {
            'already_compatible': [],
            'needs_migration': [],
            'no_pandas': [],
            'errors': []
        }
        
        for file_path in safe_files:
            try:
                should_migrate, reason = self.should_migrate_file(file_path)
                
                if 'No pandas usage' in reason:
                    results['no_pandas'].append(file_path)
                elif 'Already compatible' in reason or 'No potentially incompatible' in reason:
                    results['already_compatible'].append({
                        'file': file_path,
                        'reason': reason
                    })
                elif should_migrate:
                    results['needs_migration'].append({
                        'file': file_path,
                        'reason': reason
                    })
                    
            except Exception as e:
                results['errors'].append({
                    'file': file_path,
                    'error': str(e)
                })
        
        return results