"""
AQR library checker and path configuration tool
"""

import os
import sys
import subprocess
from typing import Dict, List, Any, Optional
from litellm import ChatCompletionToolParam


AqrLibraryCheckerTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "check_aqr_libraries",
        "description": """Check for AQR internal libraries and configure paths.
        
        This tool:
        - Checks if AQR libraries are available in the current environment
        - Searches for AQR libraries in C:\\Workspace
        - Adds necessary paths to PYTHONPATH
        - Verifies specific AQR module imports
        - Reports missing dependencies""",
        "parameters": {
            "type": "object",
            "properties": {
                "required_modules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of AQR modules to check (e.g., ['aqr.core.panel', 'aqr.stats.ols'])"
                },
                "workspace_path": {
                    "type": "string",
                    "description": "Path to AQR workspace",
                    "default": "C:\\Workspace"
                },
                "add_to_path": {
                    "type": "boolean",
                    "description": "Whether to add workspace to PYTHONPATH if not present",
                    "default": True
                },
                "search_subdirs": {
                    "type": "boolean",
                    "description": "Whether to search subdirectories for AQR modules",
                    "default": True
                }
            },
            "required": ["required_modules"]
        }
    }
}


def check_aqr_libraries_implementation(
    required_modules: List[str],
    workspace_path: str = "C:\\Workspace",
    add_to_path: bool = True,
    search_subdirs: bool = True
) -> Dict[str, Any]:
    """Check and configure AQR libraries"""
    
    result = {
        "success": False,
        "workspace_path": workspace_path,
        "workspace_exists": False,
        "pythonpath_updated": False,
        "modules_status": {},
        "found_paths": {},
        "missing_modules": [],
        "recommendations": []
    }
    
    # Check if workspace exists
    if os.path.exists(workspace_path):
        result["workspace_exists"] = True
    else:
        result["recommendations"].append(f"Workspace path {workspace_path} not found")
        return result
    
    # Add to PYTHONPATH if requested
    if add_to_path and workspace_path not in sys.path:
        sys.path.insert(0, workspace_path)
        result["pythonpath_updated"] = True
        result["recommendations"].append(f"Added {workspace_path} to PYTHONPATH")
    
    # Check each required module
    for module in required_modules:
        module_found = False
        module_path = None
        
        # Try to import the module
        try:
            exec(f"import {module}")
            module_found = True
            # Try to get module path
            try:
                imported_module = eval(module.split('.')[0])
                if hasattr(imported_module, '__file__'):
                    module_path = imported_module.__file__
            except:
                pass
        except ImportError:
            # Module not directly importable
            pass
        
        # If not found and search_subdirs is True, search in workspace
        if not module_found and search_subdirs:
            module_parts = module.split('.')
            
            # Search for the module structure in workspace
            search_paths = []
            
            # Convert module path to file path
            # e.g., aqr.core.panel -> aqr/core/panel.py or aqr/core/panel/__init__.py
            relative_path = os.path.join(*module_parts)
            
            possible_files = [
                os.path.join(workspace_path, relative_path + '.py'),
                os.path.join(workspace_path, relative_path, '__init__.py')
            ]
            
            for file_path in possible_files:
                if os.path.exists(file_path):
                    module_found = True
                    module_path = file_path
                    break
            
            # Also check if we need to add a subdirectory to path
            if not module_found:
                # Check if aqr is in a subdirectory
                for root, dirs, files in os.walk(workspace_path):
                    if module_parts[0] in dirs:
                        sub_path = root
                        if sub_path not in sys.path:
                            sys.path.insert(0, sub_path)
                            result["recommendations"].append(f"Added {sub_path} to PYTHONPATH")
                        
                        # Try import again
                        try:
                            exec(f"import {module}")
                            module_found = True
                            module_path = os.path.join(sub_path, *module_parts)
                        except ImportError:
                            pass
                        break
        
        # Update status
        result["modules_status"][module] = module_found
        if module_found:
            result["found_paths"][module] = module_path
        else:
            result["missing_modules"].append(module)
    
    # Generate recommendations
    if result["missing_modules"]:
        result["recommendations"].append(
            f"Missing modules: {', '.join(result['missing_modules'])}"
        )
        result["recommendations"].append(
            "Ensure these modules are installed in the AQR workspace"
        )
    
    # Overall success
    result["success"] = len(result["missing_modules"]) == 0
    
    return result


# Additional helper tool for finding AQR modules
FindAqrModulesTool: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "find_aqr_modules",
        "description": "Search for available AQR modules in the workspace",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "Path to search for AQR modules",
                    "default": "C:\\Workspace"
                },
                "pattern": {
                    "type": "string",
                    "description": "Pattern to match module names (e.g., 'ols', 'panel')"
                }
            }
        }
    }
}


def find_aqr_modules_implementation(
    workspace_path: str = "C:\\Workspace",
    pattern: Optional[str] = None
) -> Dict[str, Any]:
    """Find available AQR modules in workspace"""
    
    result = {
        "workspace_path": workspace_path,
        "modules_found": [],
        "module_paths": {}
    }
    
    if not os.path.exists(workspace_path):
        result["error"] = f"Workspace path {workspace_path} not found"
        return result
    
    # Search for Python files that might be AQR modules
    for root, dirs, files in os.walk(workspace_path):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and not file.startswith('_'):
                # Construct module path
                rel_path = os.path.relpath(os.path.join(root, file), workspace_path)
                module_path = rel_path.replace(os.sep, '.').replace('.py', '')
                
                # Check if it's an AQR module
                if module_path.startswith('aqr.'):
                    if pattern is None or pattern.lower() in module_path.lower():
                        result["modules_found"].append(module_path)
                        result["module_paths"][module_path] = os.path.join(root, file)
        
        # Check for __init__.py to identify packages
        if '__init__.py' in files:
            rel_path = os.path.relpath(root, workspace_path)
            if rel_path != '.':
                package_path = rel_path.replace(os.sep, '.')
                if package_path.startswith('aqr'):
                    if pattern is None or pattern.lower() in package_path.lower():
                        if package_path not in result["modules_found"]:
                            result["modules_found"].append(package_path)
                            result["module_paths"][package_path] = os.path.join(root, '__init__.py')
    
    result["modules_found"].sort()
    result["total_found"] = len(result["modules_found"])
    
    return result