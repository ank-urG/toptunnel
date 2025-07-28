"""
Utility functions for pandas migration
"""

import os
import shutil
import ast
import json
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """Result of running tests in an environment"""
    environment: str
    pandas_version: str
    success: bool
    passed_tests: int = 0
    failed_tests: int = 0
    errors: List[str] = field(default_factory=list)
    output: str = ""
    duration: float = 0.0


@dataclass
class MigrationResult:
    """Result of a migration operation"""
    file_path: str
    success: bool
    changes_made: List[Dict[str, Any]] = field(default_factory=list)
    test_results: Dict[str, TestResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_performed: bool = False


@dataclass
class MigrationContext:
    """Context for migration operations"""
    source_version: str = "0.19.2"
    target_version: str = "1.1.5"
    backup_dir: str = ".pandas_migration_backup"
    aqr_workspace: str = "C:\\Workspace"
    pandas_115_runtime: str = "pandas_115_final"
    pandas_019_runtime: str = "py36-1.1.10"
    test_command: Optional[str] = None
    preserve_functionality: bool = True
    stop_on_failure: bool = True


def create_backup(file_path: str, backup_dir: str = ".pandas_migration_backup") -> str:
    """Create a backup of a file before migration"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup file name with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path)
    backup_name = f"{base_name}.{timestamp}.backup"
    backup_path = os.path.join(backup_dir, backup_name)
    
    # Copy file
    shutil.copy2(file_path, backup_path)
    
    return backup_path


def restore_backup(backup_path: str, original_path: str) -> bool:
    """Restore a file from backup"""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    
    shutil.copy2(backup_path, original_path)
    return True


def validate_code_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """Validate Python code syntax"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def extract_pandas_version(code: str) -> Optional[str]:
    """Try to extract pandas version requirement from code"""
    # Look for version checks or requirements
    version_patterns = [
        r'pandas[>=<]=*([0-9.]+)',
        r'pd\.__version__[>=<]=*[\'"]([0-9.]+)[\'"]',
        r'PANDAS_VERSION\s*=\s*[\'"]([0-9.]+)[\'"]'
    ]
    
    import re
    for pattern in version_patterns:
        match = re.search(pattern, code)
        if match:
            return match.group(1)
    
    return None


def compare_test_results(before: TestResult, after: TestResult) -> Dict[str, Any]:
    """Compare test results before and after migration"""
    comparison = {
        "regression": False,
        "improvement": False,
        "changes": []
    }
    
    # Check for regressions
    if before.success and not after.success:
        comparison["regression"] = True
        comparison["changes"].append("Tests that passed before now fail")
    
    # Check for improvements
    if not before.success and after.success:
        comparison["improvement"] = True
        comparison["changes"].append("Tests that failed before now pass")
    
    # Compare test counts
    if after.failed_tests > before.failed_tests:
        comparison["regression"] = True
        comparison["changes"].append(
            f"Failed tests increased from {before.failed_tests} to {after.failed_tests}"
        )
    elif after.failed_tests < before.failed_tests:
        comparison["improvement"] = True
        comparison["changes"].append(
            f"Failed tests decreased from {before.failed_tests} to {after.failed_tests}"
        )
    
    # Check for new errors
    new_errors = set(after.errors) - set(before.errors)
    if new_errors:
        comparison["regression"] = True
        comparison["changes"].append(f"New errors: {list(new_errors)}")
    
    return comparison


def generate_migration_report(
    results: List[MigrationResult],
    context: MigrationContext,
    output_file: Optional[str] = None
) -> str:
    """Generate a comprehensive migration report"""
    report_lines = [
        "# Pandas Migration Report",
        f"\nDate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source Version: {context.source_version}",
        f"Target Version: {context.target_version}",
        "\n## Summary",
        f"- Total Files Processed: {len(results)}",
        f"- Successful Migrations: {sum(1 for r in results if r.success)}",
        f"- Failed Migrations: {sum(1 for r in results if not r.success)}",
        f"- Files with Test Regressions: {sum(1 for r in results if any(t.success == False for t in r.test_results.values()))}",
    ]
    
    # Detailed results
    report_lines.append("\n## Detailed Results")
    
    for result in results:
        report_lines.append(f"\n### {result.file_path}")
        report_lines.append(f"- Status: {'✅ Success' if result.success else '❌ Failed'}")
        
        if result.changes_made:
            report_lines.append("- Changes Made:")
            for change in result.changes_made:
                report_lines.append(f"  - {change.get('description', change)}")
        
        if result.test_results:
            report_lines.append("- Test Results:")
            for env, test_result in result.test_results.items():
                status = '✅' if test_result.success else '❌'
                report_lines.append(
                    f"  - {env} ({test_result.pandas_version}): {status} "
                    f"({test_result.passed_tests} passed, {test_result.failed_tests} failed)"
                )
        
        if result.errors:
            report_lines.append("- Errors:")
            for error in result.errors:
                report_lines.append(f"  - {error}")
        
        if result.warnings:
            report_lines.append("- Warnings:")
            for warning in result.warnings:
                report_lines.append(f"  - {warning}")
    
    # Migration rules applied
    report_lines.append("\n## Migration Rules Applied")
    all_changes = []
    for result in results:
        for change in result.changes_made:
            rule = change.get('rule', change.get('transformation', 'unknown'))
            if rule not in all_changes:
                all_changes.append(rule)
    
    for rule in sorted(all_changes):
        count = sum(1 for r in results 
                   for c in r.changes_made 
                   if c.get('rule', c.get('transformation')) == rule)
        report_lines.append(f"- {rule}: {count} occurrences")
    
    # Recommendations
    report_lines.append("\n## Recommendations")
    
    failed_files = [r.file_path for r in results if not r.success]
    if failed_files:
        report_lines.append("- Review and manually fix the following failed migrations:")
        for file in failed_files:
            report_lines.append(f"  - {file}")
    
    regression_files = [
        r.file_path for r in results 
        if any(not t.success for t in r.test_results.values())
    ]
    if regression_files:
        report_lines.append("- Investigate test failures in:")
        for file in regression_files:
            report_lines.append(f"  - {file}")
    
    report = '\n'.join(report_lines)
    
    # Save to file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
    
    return report


def identify_migration_candidates(
    directory: str,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Identify Python files that might need migration"""
    candidates = []
    exclude_patterns = exclude_patterns or []
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                # Check exclusions
                if any(pattern in file_path for pattern in exclude_patterns):
                    continue
                
                # Quick check for pandas usage
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'pandas' in content or 'pd.' in content:
                            candidates.append(file_path)
                except:
                    # Skip files that can't be read
                    pass
    
    return candidates


def validate_migration_safety(
    original_code: str,
    migrated_code: str
) -> Tuple[bool, List[str]]:
    """Validate that migration preserves code structure and safety"""
    issues = []
    
    # Check syntax
    original_valid, _ = validate_code_syntax(original_code)
    migrated_valid, error = validate_code_syntax(migrated_code)
    
    if original_valid and not migrated_valid:
        issues.append(f"Migration introduced syntax error: {error}")
        return False, issues
    
    # Compare AST structure (simplified)
    try:
        original_ast = ast.parse(original_code)
        migrated_ast = ast.parse(migrated_code)
        
        # Count major elements
        original_functions = len([n for n in ast.walk(original_ast) if isinstance(n, ast.FunctionDef)])
        migrated_functions = len([n for n in ast.walk(migrated_ast) if isinstance(n, ast.FunctionDef)])
        
        if original_functions != migrated_functions:
            issues.append("Migration changed number of functions")
        
        original_classes = len([n for n in ast.walk(original_ast) if isinstance(n, ast.ClassDef)])
        migrated_classes = len([n for n in ast.walk(migrated_ast) if isinstance(n, ast.ClassDef)])
        
        if original_classes != migrated_classes:
            issues.append("Migration changed number of classes")
        
    except Exception as e:
        issues.append(f"AST comparison failed: {str(e)}")
    
    return len(issues) == 0, issues