"""
Iterative test runner tool for pandas migration
"""

from typing import Dict, List, Any, Optional
from litellm import ChatCompletionToolParam


IterativeTestRunnerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "run_tests_iteratively",
        "description": """Run tests iteratively with automatic fix-and-retry workflow.
        
        This tool implements the required test workflow:
        1. Automatically detects and uses unittest.ini/cfg or it_test.ini/cfg
        2. Runs tests one by one
        3. STOPS on first failure
        4. Attempts to fix the failing test
        5. Re-runs ONLY the failing test
        6. Repeats fix-rerun cycle until test passes (max 3 attempts)
        7. Only moves to next test after current one passes
        
        Config file search order:
        - unittest.ini
        - unittest.cfg
        - it_test.ini
        - it_test.cfg""",
        "parameters": {
            "type": "object",
            "properties": {
                "test_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of test files to run"
                },
                "environment": {
                    "type": "string",
                    "enum": ["pandas_115_final", "py36-1.1.10"],
                    "description": "Runtime environment to use"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for tests",
                    "default": "."
                },
                "max_fix_attempts": {
                    "type": "integer",
                    "description": "Maximum fix attempts per test",
                    "default": 3
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": "Whether to automatically attempt fixes",
                    "default": True
                }
            },
            "required": ["test_files", "environment"]
        }
    }
}


SingleTestRunnerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "run_single_test",
        "description": """Run a single test with config file detection.
        
        Useful for running specific test functions:
        - pytest -c unittest.ini test_file.py::TestClass::test_method
        - Automatically uses config file if found""",
        "parameters": {
            "type": "object",
            "properties": {
                "test_spec": {
                    "type": "string",
                    "description": "Test specification (e.g., 'test_file.py::test_function')"
                },
                "environment": {
                    "type": "string",
                    "enum": ["pandas_115_final", "py36-1.1.10"],
                    "description": "Runtime environment"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory",
                    "default": "."
                }
            },
            "required": ["test_spec", "environment"]
        }
    }
}


def run_tests_iteratively_implementation(
    test_files: List[str],
    environment: str,
    working_directory: str = ".",
    max_fix_attempts: int = 3,
    auto_fix: bool = True
) -> Dict[str, Any]:
    """Implementation of iterative test runner"""
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from utils.test_utils import (
        find_test_config_file,
        build_pytest_command,
        run_test_with_retry,
        run_tests_in_environment
    )
    
    result = {
        "environment": environment,
        "config_file": None,
        "total_tests": len(test_files),
        "passed": 0,
        "failed": 0,
        "fixed": 0,
        "stopped_early": False,
        "stopped_at": None,
        "test_results": {}
    }
    
    # Find config file
    config_file = find_test_config_file(working_directory)
    if config_file:
        result["config_file"] = config_file
    
    # Run tests iteratively
    for test_file in test_files:
        # Build command with config
        if 'pytest' in test_file or test_file.endswith('.py'):
            test_command = build_pytest_command(test_file, config_file)
        else:
            test_command = test_file  # Already a full command
        
        # Run with retry if auto_fix is enabled
        if auto_fix:
            test_result = run_test_with_retry(
                test_file,
                environment,
                working_directory,
                max_retries=max_fix_attempts,
                fix_callback=attempt_auto_fix
            )
        else:
            # Run without retry
            test_result = run_tests_in_environment(
                test_command,
                environment,
                working_directory
            )
        
        result["test_results"][test_file] = test_result
        
        if test_result["success"]:
            result["passed"] += 1
            if test_result.get("attempts", 1) > 1:
                result["fixed"] += 1
        else:
            result["failed"] += 1
            result["stopped_early"] = True
            result["stopped_at"] = test_file
            # STOP on first failure as required
            break
    
    return result


def run_single_test_implementation(
    test_spec: str,
    environment: str,
    working_directory: str = "."
) -> Dict[str, Any]:
    """Run a single test with config detection"""
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from utils.test_utils import (
        find_test_config_file,
        build_pytest_command,
        run_tests_in_environment
    )
    
    # Find config file
    config_file = find_test_config_file(working_directory)
    
    # Build command
    test_command = build_pytest_command(test_spec, config_file)
    
    # Run test
    result = run_tests_in_environment(
        test_command,
        environment,
        working_directory
    )
    
    result["config_file"] = config_file
    result["test_spec"] = test_spec
    
    return result


def attempt_auto_fix(fix_info: Dict[str, Any]) -> bool:
    """Attempt to automatically fix a failing test"""
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from rules import analyze_code, apply_migrations
    from utils.file_utils import read_file_safely, write_file_safely
    
    test_name = fix_info["test_name"]
    error = fix_info["error"]
    output = fix_info["output"]
    
    # Determine test file path
    if '::' in test_name:
        test_file = test_name.split('::')[0]
    else:
        test_file = test_name
    
    if not os.path.exists(test_file):
        return False
    
    try:
        # Read test file
        content, encoding = read_file_safely(test_file)
        
        # Analyze for migration issues
        analysis = analyze_code(content)
        
        # Determine which rules to apply based on error
        rules_to_apply = []
        
        if "AttributeError" in error:
            if ".valid()" in error:
                rules_to_apply.append("valid_method")
            elif "TimeGrouper" in error:
                rules_to_apply.append("time_grouper")
        elif "ImportError" in error:
            if "Panel" in error:
                rules_to_apply.append("panel_migration")
            elif "DatetimeIndex" in error:
                rules_to_apply.append("datetime_index_import")
        elif "OutOfBoundsDatetime" in error:
            rules_to_apply.append("out_of_bounds_datetime")
        elif "TypeError" in error and "DatetimeIndex" in error:
            rules_to_apply.append("datetime_index_constructor")
        
        # If no specific rules identified, apply all detected
        if not rules_to_apply and analysis["rules_triggered"]:
            rules_to_apply = [r["rule"] for r in analysis["rules_triggered"]]
        
        if rules_to_apply:
            # Apply migrations
            fixed_content, changes = apply_migrations(content, rules_to_apply)
            
            if changes:
                # Write fixed content
                write_file_safely(test_file, fixed_content, encoding)
                return True
    
    except Exception:
        pass
    
    return False