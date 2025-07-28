"""
Test running and comparison utilities for pandas migration
"""

import subprocess
import re
import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple


def find_test_config_file(working_directory: str = ".") -> Optional[str]:
    """Find test configuration file (unittest.ini/cfg or it_test.ini/cfg)
    
    Args:
        working_directory: Directory to search for config files
    
    Returns:
        Path to the config file if found, None otherwise
    """
    config_files = [
        'unittest.ini',
        'unittest.cfg',
        'it_test.ini',
        'it_test.cfg'
    ]
    
    # Search in working directory and parent directories
    current_dir = os.path.abspath(working_directory)
    
    while True:
        for config_file in config_files:
            config_path = os.path.join(current_dir, config_file)
            if os.path.exists(config_path):
                return config_path
        
        # Move to parent directory
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # Reached root directory
            break
        current_dir = parent_dir
    
    return None


def build_pytest_command(
    test_target: str,
    config_file: Optional[str] = None,
    additional_args: Optional[List[str]] = None
) -> str:
    """Build pytest command with config file if available
    
    Args:
        test_target: Test file or directory to run
        config_file: Path to config file (unittest.ini/cfg or it_test.ini/cfg)
        additional_args: Additional arguments to pass to pytest
    
    Returns:
        Complete pytest command
    """
    cmd_parts = ['pytest']
    
    if config_file:
        cmd_parts.extend(['-c', config_file])
    
    if additional_args:
        cmd_parts.extend(additional_args)
    
    cmd_parts.append(test_target)
    
    return ' '.join(cmd_parts)


def run_tests_in_environment(
    test_command: str,
    environment: str,
    working_directory: str = ".",
    timeout: int = 300,
    capture_output: bool = True
) -> Dict[str, Any]:
    """Run tests in a specific pandas environment
    
    Args:
        test_command: Command to run tests (e.g., 'pytest test_file.py')
        environment: Environment name ('pandas_115_final' or 'py36-1.1.10')
        working_directory: Directory to run tests in
        timeout: Maximum time to wait for tests (seconds)
        capture_output: Whether to capture test output
    
    Returns:
        Dictionary with test results
    """
    result = {
        'environment': environment,
        'success': False,
        'return_code': -1,
        'output': '',
        'errors': '',
        'passed_tests': 0,
        'failed_tests': 0,
        'skipped_tests': 0,
        'test_details': [],
        'pandas_version': None,
        'duration': 0.0
    }
    
    # Prepare environment activation
    if environment == 'pandas_115_final':
        activate_cmd = 'activate pandas_115_final'
    elif environment == 'py36-1.1.10':
        activate_cmd = r'C:\LocalRuntimes\py36-1.1.10\Scripts\activate'
    else:
        result['errors'] = f"Unknown environment: {environment}"
        return result
    
    # Combine activation and test command
    if sys.platform == 'win32':
        full_command = f"{activate_cmd} && {test_command}"
    else:
        full_command = f"source {activate_cmd} && {test_command}"
    
    # Run tests
    import time
    start_time = time.time()
    
    try:
        process = subprocess.run(
            full_command,
            shell=True,
            cwd=working_directory,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        
        result['duration'] = time.time() - start_time
        result['return_code'] = process.returncode
        result['output'] = process.stdout if capture_output else ''
        result['errors'] = process.stderr if capture_output else ''
        result['success'] = process.returncode == 0
        
        # Parse test output
        parsed_results = parse_test_output(result['output'] + result['errors'])
        result.update(parsed_results)
        
        # Get pandas version
        version_cmd = f"{activate_cmd} && python -c \"import pandas; print(pandas.__version__)\""
        version_process = subprocess.run(
            version_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if version_process.returncode == 0:
            result['pandas_version'] = version_process.stdout.strip()
        
    except subprocess.TimeoutExpired:
        result['errors'] = f"Test execution timed out after {timeout} seconds"
    except Exception as e:
        result['errors'] = f"Error running tests: {str(e)}"
    
    return result


def parse_test_output(output: str) -> Dict[str, Any]:
    """Parse test output to extract test results
    
    Supports pytest and unittest output formats
    """
    results = {
        'passed_tests': 0,
        'failed_tests': 0,
        'skipped_tests': 0,
        'test_details': []
    }
    
    # Try pytest format first
    pytest_summary = re.search(
        r'(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?',
        output
    )
    
    if pytest_summary:
        results['passed_tests'] = int(pytest_summary.group(1) or 0)
        results['skipped_tests'] = int(pytest_summary.group(2) or 0)
        results['failed_tests'] = int(pytest_summary.group(3) or 0)
        
        # Extract individual test results
        test_pattern = re.compile(r'(PASSED|FAILED|SKIPPED)\s+([^\s]+)')
        for match in test_pattern.finditer(output):
            results['test_details'].append({
                'status': match.group(1),
                'test_name': match.group(2)
            })
    
    # Try unittest format
    else:
        unittest_pattern = re.compile(r'Ran (\d+) tests? in [\d.]+s')
        match = unittest_pattern.search(output)
        if match:
            total_tests = int(match.group(1))
            
            if 'OK' in output:
                results['passed_tests'] = total_tests
            else:
                # Count failures and errors
                failures = len(re.findall(r'FAIL:', output))
                errors = len(re.findall(r'ERROR:', output))
                results['failed_tests'] = failures + errors
                results['passed_tests'] = total_tests - results['failed_tests']
    
    # Extract error details
    if results['failed_tests'] > 0:
        # Extract failure information
        failure_pattern = re.compile(
            r'FAILED\s+([^\s]+)\s*-\s*(.+?)(?=FAILED|PASSED|$)',
            re.DOTALL
        )
        for match in failure_pattern.finditer(output):
            results['test_details'].append({
                'status': 'FAILED',
                'test_name': match.group(1),
                'error_message': match.group(2).strip()
            })
    
    return results


def compare_outputs(output1: str, output2: str) -> Dict[str, Any]:
    """Compare two test outputs for differences
    
    Returns:
        Dictionary with comparison results
    """
    comparison = {
        'identical': output1 == output2,
        'differences': [],
        'similarity_score': 0.0
    }
    
    if comparison['identical']:
        comparison['similarity_score'] = 1.0
        return comparison
    
    # Split outputs into lines for comparison
    lines1 = output1.strip().split('\n')
    lines2 = output2.strip().split('\n')
    
    # Use difflib for comparison
    import difflib
    differ = difflib.unified_diff(lines1, lines2, lineterm='')
    diff_lines = list(differ)
    
    if diff_lines:
        comparison['differences'] = diff_lines
    
    # Calculate similarity score
    sequence_matcher = difflib.SequenceMatcher(None, output1, output2)
    comparison['similarity_score'] = sequence_matcher.ratio()
    
    # Extract specific differences
    added_lines = [line[1:] for line in diff_lines if line.startswith('+') and not line.startswith('+++')]
    removed_lines = [line[1:] for line in diff_lines if line.startswith('-') and not line.startswith('---')]
    
    if added_lines:
        comparison['added_in_second'] = added_lines
    if removed_lines:
        comparison['removed_from_first'] = removed_lines
    
    return comparison


def format_test_report(
    test_results: Dict[str, Any],
    environment: str,
    include_details: bool = True
) -> str:
    """Format test results into a readable report"""
    lines = [
        f"Test Results for {environment}",
        "=" * 50,
        f"Pandas Version: {test_results.get('pandas_version', 'Unknown')}",
        f"Status: {'✅ PASSED' if test_results['success'] else '❌ FAILED'}",
        f"Duration: {test_results.get('duration', 0):.2f} seconds",
        "",
        "Summary:",
        f"  Passed: {test_results['passed_tests']}",
        f"  Failed: {test_results['failed_tests']}",
        f"  Skipped: {test_results['skipped_tests']}",
    ]
    
    if include_details and test_results.get('test_details'):
        lines.extend(["", "Test Details:"])
        for detail in test_results['test_details']:
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'SKIPPED': '⏭️'
            }.get(detail['status'], '❓')
            
            lines.append(f"  {status_icon} {detail['test_name']}")
            
            if detail.get('error_message'):
                error_lines = detail['error_message'].split('\n')
                for error_line in error_lines[:3]:  # Show first 3 lines of error
                    lines.append(f"      {error_line}")
                if len(error_lines) > 3:
                    lines.append("      ...")
    
    if test_results.get('errors'):
        lines.extend(["", "Errors:", test_results['errors']])
    
    return '\n'.join(lines)


def run_parallel_tests(
    test_command: str,
    environments: List[str],
    working_directory: str = "."
) -> Dict[str, Dict[str, Any]]:
    """Run tests in multiple environments in parallel
    
    Returns:
        Dictionary mapping environment names to test results
    """
    import concurrent.futures
    
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(environments)) as executor:
        future_to_env = {
            executor.submit(
                run_tests_in_environment,
                test_command,
                env,
                working_directory
            ): env
            for env in environments
        }
        
        for future in concurrent.futures.as_completed(future_to_env):
            env = future_to_env[future]
            try:
                results[env] = future.result()
            except Exception as e:
                results[env] = {
                    'environment': env,
                    'success': False,
                    'errors': f"Exception running tests: {str(e)}"
                }
    
    return results


def validate_test_compatibility(
    results_019: Dict[str, Any],
    results_115: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Validate that tests pass in both pandas versions
    
    Returns:
        Tuple of (is_compatible, list_of_issues)
    """
    issues = []
    
    # Both should succeed
    if not results_019['success']:
        issues.append(f"Tests fail in pandas 0.19.2: {results_019['failed_tests']} failures")
    
    if not results_115['success']:
        issues.append(f"Tests fail in pandas 1.1.5: {results_115['failed_tests']} failures")
    
    # Check for regressions
    if results_019['success'] and not results_115['success']:
        issues.append("REGRESSION: Tests that pass in 0.19.2 fail in 1.1.5")
    
    # Check test count changes
    total_019 = results_019['passed_tests'] + results_019['failed_tests']
    total_115 = results_115['passed_tests'] + results_115['failed_tests']
    
    if total_019 != total_115:
        issues.append(f"Test count mismatch: {total_019} in 0.19.2 vs {total_115} in 1.1.5")
    
    # Check for new failures
    if results_019.get('test_details') and results_115.get('test_details'):
        failed_019 = {t['test_name'] for t in results_019['test_details'] if t['status'] == 'FAILED'}
        failed_115 = {t['test_name'] for t in results_115['test_details'] if t['status'] == 'FAILED'}
        
        new_failures = failed_115 - failed_019
        if new_failures:
            issues.append(f"New test failures in 1.1.5: {', '.join(new_failures)}")
    
    is_compatible = len(issues) == 0
    
    return is_compatible, issues


def run_test_with_retry(
    test_name: str,
    environment: str,
    working_directory: str = ".",
    max_retries: int = 3,
    fix_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """Run a single test with retry logic and fix attempts
    
    Args:
        test_name: Specific test to run (e.g., 'test_file.py::test_function')
        environment: Environment name
        working_directory: Directory to run tests in
        max_retries: Maximum number of retry attempts
        fix_callback: Optional callback function to fix the test
    
    Returns:
        Test result dictionary
    """
    # Find config file
    config_file = find_test_config_file(working_directory)
    
    # Build test command
    test_command = build_pytest_command(test_name, config_file)
    
    attempt = 0
    last_result = None
    
    while attempt < max_retries:
        # Run the test
        result = run_tests_in_environment(
            test_command,
            environment,
            working_directory
        )
        
        last_result = result
        
        if result['success']:
            # Test passed
            result['attempts'] = attempt + 1
            return result
        
        # Test failed
        attempt += 1
        
        if fix_callback and attempt < max_retries:
            # Try to fix the test
            fix_info = {
                'test_name': test_name,
                'environment': environment,
                'error': result.get('errors', ''),
                'output': result.get('output', ''),
                'attempt': attempt
            }
            
            fix_applied = fix_callback(fix_info)
            
            if not fix_applied:
                # Cannot fix, stop retrying
                break
    
    # All attempts failed
    if last_result:
        last_result['attempts'] = attempt
        last_result['max_retries_reached'] = True
    
    return last_result


def run_tests_iteratively(
    test_list: List[str],
    environment: str,
    working_directory: str = ".",
    stop_on_failure: bool = True,
    fix_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """Run tests iteratively with fix-and-retry logic
    
    Args:
        test_list: List of tests to run
        environment: Environment name
        working_directory: Directory to run tests in
        stop_on_failure: Whether to stop on first failure
        fix_callback: Optional callback to fix failed tests
    
    Returns:
        Dictionary with overall results and individual test results
    """
    results = {
        'environment': environment,
        'total_tests': len(test_list),
        'passed_tests': 0,
        'failed_tests': 0,
        'fixed_tests': 0,
        'test_results': {},
        'stopped_early': False
    }
    
    for test_name in test_list:
        # Run test with retry
        test_result = run_test_with_retry(
            test_name,
            environment,
            working_directory,
            fix_callback=fix_callback
        )
        
        results['test_results'][test_name] = test_result
        
        if test_result['success']:
            results['passed_tests'] += 1
            if test_result.get('attempts', 1) > 1:
                results['fixed_tests'] += 1
        else:
            results['failed_tests'] += 1
            
            if stop_on_failure:
                results['stopped_early'] = True
                results['stopped_at'] = test_name
                break
    
    return results