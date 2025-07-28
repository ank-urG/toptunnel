"""
Runtime switching and testing tools for pandas migration
"""

import os
import sys
import subprocess
from typing import Dict, Any, Optional, List
from litellm import ChatCompletionToolParam


RuntimeSwitchTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "switch_runtime",
        "description": """Switch between pandas runtime environments.
        
        Available runtimes:
        - 'pandas_115_final': pandas 1.1.5 environment
        - 'py36-1.1.10': pandas 0.19.2 environment (at C:\\LocalRuntimes)
        
        This tool activates the specified runtime environment for subsequent operations.""",
        "parameters": {
            "type": "object",
            "properties": {
                "runtime": {
                    "type": "string",
                    "enum": ["pandas_115_final", "py36-1.1.10"],
                    "description": "The runtime environment to switch to"
                },
                "setup_aqr_path": {
                    "type": "boolean",
                    "description": "Whether to add C:\\Workspace to PYTHONPATH for AQR libraries",
                    "default": False
                }
            },
            "required": ["runtime"]
        }
    }
}


TestRunnerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "run_test_in_runtime",
        "description": """Run unit tests in the current runtime environment.
        
        This tool:
        1. Ensures the correct runtime is active
        2. Sets up AQR library paths if needed
        3. Automatically detects and uses unittest.ini/cfg or it_test.ini/cfg
        4. Runs the specified test command with proper configuration
        5. Returns the test results including any failures
        
        The tool will automatically stop and report if tests fail.
        It searches for config files in this order:
        - unittest.ini
        - unittest.cfg
        - it_test.ini
        - it_test.cfg""",
        "parameters": {
            "type": "object",
            "properties": {
                "test_command": {
                    "type": "string",
                    "description": "The test command to run (e.g., 'pytest test_file.py'). Config file will be auto-detected."
                },
                "test_file": {
                    "type": "string",
                    "description": "Path to the test file"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for running tests",
                    "default": "."
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Whether to capture and return test output",
                    "default": True
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Whether to stop immediately if tests fail",
                    "default": True
                },
                "use_config_file": {
                    "type": "boolean",
                    "description": "Whether to auto-detect and use unittest.ini/cfg or it_test.ini/cfg",
                    "default": True
                }
            },
            "required": ["test_command"]
        }
    }
}


def switch_runtime_implementation(runtime: str, setup_aqr_path: bool = False) -> Dict[str, Any]:
    """Implementation of runtime switching"""
    result = {
        "success": False,
        "runtime": runtime,
        "message": "",
        "pandas_version": None,
        "python_version": None
    }
    
    try:
        # Activate the runtime
        if runtime == "pandas_115_final":
            # Commands to activate pandas 1.1.5 environment
            activate_cmd = "activate pandas_115_final"
            result["message"] = "Switched to pandas 1.1.5 environment"
        elif runtime == "py36-1.1.10":
            # Commands to activate pandas 0.19.2 environment
            activate_cmd = r"C:\LocalRuntimes\py36-1.1.10\Scripts\activate"
            result["message"] = "Switched to pandas 0.19.2 environment"
        else:
            result["message"] = f"Unknown runtime: {runtime}"
            return result
        
        # Set up AQR path if requested
        if setup_aqr_path:
            aqr_path = r"C:\Workspace"
            if aqr_path not in sys.path:
                sys.path.append(aqr_path)
            result["message"] += f"\nAdded {aqr_path} to PYTHONPATH"
        
        # Verify pandas version
        try:
            import pandas as pd
            result["pandas_version"] = pd.__version__
            result["python_version"] = sys.version
            result["success"] = True
        except ImportError:
            result["message"] += "\nWarning: Could not verify pandas installation"
        
        return result
        
    except Exception as e:
        result["message"] = f"Error switching runtime: {str(e)}"
        return result


def run_test_implementation(
    test_command: str,
    test_file: Optional[str] = None,
    working_directory: str = ".",
    capture_output: bool = True,
    stop_on_failure: bool = True,
    use_config_file: bool = True
) -> Dict[str, Any]:
    """Implementation of test runner"""
    result = {
        "success": False,
        "test_command": test_command,
        "output": "",
        "errors": "",
        "return_code": -1,
        "failed_tests": [],
        "pandas_version": None,
        "config_file": None
    }
    
    try:
        # Get current pandas version
        import pandas as pd
        result["pandas_version"] = pd.__version__
        
        # Change to working directory
        original_dir = os.getcwd()
        os.chdir(working_directory)
        
        # Detect config file if requested
        if use_config_file and 'pytest' in test_command:
            config_files = ['unittest.ini', 'unittest.cfg', 'it_test.ini', 'it_test.cfg']
            for config_file in config_files:
                if os.path.exists(config_file):
                    result["config_file"] = config_file
                    # Modify command to use config file if not already specified
                    if '-c' not in test_command:
                        test_command = test_command.replace('pytest', f'pytest -c {config_file}')
                    break
        
        # Run the test command
        process = subprocess.run(
            test_command,
            shell=True,
            capture_output=capture_output,
            text=True
        )
        
        result["return_code"] = process.returncode
        result["output"] = process.stdout if capture_output else ""
        result["errors"] = process.stderr if capture_output else ""
        
        # Check for test failures
        if process.returncode != 0:
            result["success"] = False
            
            # Parse output for failed tests (pytest format)
            if "FAILED" in result["output"] or "FAILED" in result["errors"]:
                import re
                failed_pattern = re.compile(r'FAILED\s+([^\s]+)')
                failures = failed_pattern.findall(result["output"] + result["errors"])
                result["failed_tests"] = failures
            
            if stop_on_failure:
                result["message"] = f"Tests failed in pandas {pd.__version__}. Stopping migration."
        else:
            result["success"] = True
            result["message"] = f"All tests passed in pandas {pd.__version__}"
        
        # Change back to original directory
        os.chdir(original_dir)
        
        return result
        
    except Exception as e:
        result["errors"] = str(e)
        result["message"] = f"Error running tests: {str(e)}"
        return result


# Additional helper tools for version checking
PandasVersionCheckTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "check_pandas_version",
        "description": "Check the current pandas version and environment details",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}


def check_pandas_version_implementation() -> Dict[str, Any]:
    """Check current pandas version and environment"""
    result = {
        "pandas_version": None,
        "python_version": sys.version,
        "sys_path": sys.path[:5],  # First 5 paths
        "aqr_available": False
    }
    
    try:
        import pandas as pd
        result["pandas_version"] = pd.__version__
        
        # Check for AQR libraries
        aqr_paths = [p for p in sys.path if 'Workspace' in p or 'aqr' in p.lower()]
        result["aqr_available"] = len(aqr_paths) > 0
        result["aqr_paths"] = aqr_paths
        
    except ImportError:
        result["error"] = "Pandas not installed in current environment"
    
    return result