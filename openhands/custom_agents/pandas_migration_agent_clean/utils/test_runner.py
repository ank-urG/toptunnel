"""Test runner for validating migrations."""

import os
import subprocess
import platform
from typing import Dict, Any, Optional


class TestRunner:
    """Runs tests in different pandas environments."""
    
    def __init__(self, conda_envs: Dict[str, str]):
        """Initialize with conda environment mapping."""
        self.conda_envs = conda_envs
        self.is_windows = platform.system() == 'Windows'
        
        # Check for custom Windows runtime paths
        self.custom_paths = {}
        if self.is_windows:
            custom_py36 = r"C:\LocalRuntimes\py36-1.1.10"
            if os.path.exists(custom_py36):
                self.custom_paths["py36-1.1.10"] = custom_py36
    
    def run_tests(self, repo_path: str, pandas_version: str) -> Dict[str, Any]:
        """Run tests in the specified pandas environment.
        
        Args:
            repo_path: Repository path
            pandas_version: Pandas version (e.g., "0.19.2" or "1.1.5")
            
        Returns:
            Test results dictionary
        """
        conda_env = self.conda_envs.get(pandas_version)
        if not conda_env:
            return {
                'error': f'No conda environment configured for pandas {pandas_version}'
            }
        
        # Detect test framework
        test_command = self._detect_test_command(repo_path)
        if not test_command:
            return {
                'error': 'No test framework detected',
                'passed': 0,
                'failed': 0
            }
        
        # Build the command
        if conda_env in self.custom_paths:
            # Use custom runtime path
            python_exe = os.path.join(self.custom_paths[conda_env], 
                                    "python.exe" if self.is_windows else "bin/python")
            if test_command.startswith("python"):
                cmd = test_command.replace("python", python_exe, 1)
            else:
                cmd = f"{python_exe} -m {test_command}"
        else:
            # Use conda run
            if test_command.startswith("python"):
                cmd = f"conda run -n {conda_env} {test_command}"
            else:
                cmd = f"conda run -n {conda_env} python -m {test_command}"
        
        # Run tests
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results (simplified - real implementation would parse output)
            return self._parse_test_output(result.stdout, result.stderr, result.returncode)
            
        except subprocess.TimeoutExpired:
            return {
                'error': 'Test execution timed out',
                'passed': 0,
                'failed': 0
            }
        except Exception as e:
            return {
                'error': str(e),
                'passed': 0,
                'failed': 0
            }
    
    def _detect_test_command(self, repo_path: str) -> Optional[str]:
        """Detect which test framework to use."""
        # Check for common test files/configs
        checks = [
            ('pytest.ini', 'pytest'),
            ('setup.cfg', 'pytest'),  # Often has pytest config
            ('tox.ini', 'pytest'),
            ('test', 'pytest'),  # test directory
            ('tests', 'pytest'),  # tests directory
            ('Makefile', None),  # Check makefile for test command
        ]
        
        for file_name, command in checks:
            path = os.path.join(repo_path, file_name)
            if os.path.exists(path):
                if file_name == 'Makefile' and command is None:
                    # Try to extract test command from Makefile
                    test_cmd = self._extract_makefile_test_command(path)
                    if test_cmd:
                        return test_cmd
                elif command:
                    return command
        
        # Default to pytest
        return 'pytest'
    
    def _extract_makefile_test_command(self, makefile_path: str) -> Optional[str]:
        """Extract test command from Makefile."""
        try:
            with open(makefile_path, 'r') as f:
                content = f.read()
                
            # Look for test target
            import re
            test_match = re.search(r'^test:.*\n\s+(.+)$', content, re.MULTILINE)
            if test_match:
                cmd = test_match.group(1).strip()
                # Clean up make-specific syntax
                cmd = cmd.lstrip('@').strip()
                return cmd
        except:
            pass
        
        return None
    
    def _parse_test_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse test output to extract results."""
        # Simple parsing - look for common patterns
        output = stdout + stderr
        
        # pytest patterns
        if 'passed' in output or 'failed' in output:
            import re
            # Look for pytest summary
            summary_match = re.search(r'(\d+) passed', output)
            passed = int(summary_match.group(1)) if summary_match else 0
            
            summary_match = re.search(r'(\d+) failed', output)
            failed = int(summary_match.group(1)) if summary_match else 0
            
            summary_match = re.search(r'(\d+) skipped', output)
            skipped = int(summary_match.group(1)) if summary_match else 0
            
            return {
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'returncode': returncode
            }
        
        # unittest patterns
        elif 'Ran ' in output and ' test' in output:
            import re
            match = re.search(r'Ran (\d+) tests?', output)
            total = int(match.group(1)) if match else 0
            
            if 'FAILED' in output:
                match = re.search(r'failures=(\d+)', output)
                failed = int(match.group(1)) if match else 1
                passed = total - failed
            else:
                passed = total
                failed = 0
            
            return {
                'passed': passed,
                'failed': failed,
                'skipped': 0,
                'returncode': returncode
            }
        
        # Fallback - use return code
        if returncode == 0:
            return {
                'passed': 1,
                'failed': 0,
                'skipped': 0,
                'returncode': returncode
            }
        else:
            return {
                'passed': 0,
                'failed': 1,
                'skipped': 0,
                'returncode': returncode
            }