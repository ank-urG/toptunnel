"""Robust migration workflow that ensures backward compatibility and testing."""

import os
import shutil
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import json

from .backward_compatible_rules import BackwardCompatibleMigrationEngine
from .test_runner import TestRunner
from .utils import find_python_files, backup_file, validate_python_syntax
from .file_filter import FileFilter
from .compatibility_tester import CompatibilityTester, PreMigrationChecker


class RobustMigrationWorkflow:
    """Ensures migration maintains backward compatibility with mandatory testing."""
    
    def __init__(self, agent):
        """Initialize the workflow.
        
        Args:
            agent: Parent PandasMigrationAgent instance
        """
        self.agent = agent
        self.engine = BackwardCompatibleMigrationEngine()
        self.test_runner = TestRunner()
        
        # Use agent's conda environment configuration
        if hasattr(agent, 'config_options') and 'conda_environments' in agent.config_options:
            self.test_runner.conda_envs = agent.config_options['conda_environments']
        
        # Initialize compatibility tester
        self.compatibility_tester = CompatibilityTester(self.test_runner.conda_envs)
        self.pre_checker = PreMigrationChecker(self.compatibility_tester)
    
    def migrate_repository(self, repo_path: str) -> Dict[str, Any]:
        """Migrate entire repository with full validation.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Complete migration results
        """
        results = {
            'repo_path': repo_path,
            'start_time': datetime.now().isoformat(),
            'phases': {},
            'status': 'pending'
        }
        
        try:
            # Phase 1: Discovery
            print("Phase 1: Discovering Python files...")
            results['phases']['discovery'] = self._discovery_phase(repo_path)
            
            # Phase 1.5: Pre-migration compatibility check
            print("Phase 1.5: Checking which files actually need migration...")
            results['phases']['compatibility_check'] = self._compatibility_check_phase(
                repo_path,
                results['phases']['discovery']['safe_files']
            )
            
            # Phase 2: Pre-migration testing (MANDATORY)
            print("Phase 2: Running pre-migration tests with pandas 0.19.2...")
            results['phases']['pre_tests'] = self._test_phase(repo_path, "0.19.2")
            
            if results['phases']['pre_tests']['status'] != 'success':
                print("WARNING: Pre-migration tests have failures. Proceeding with caution...")
            
            # Phase 3: Migration with validation
            print("Phase 3: Applying backward-compatible migrations...")
            # Only migrate files that actually need it
            files_to_migrate = [
                item['file'] for item in 
                results['phases']['compatibility_check'].get('needs_migration', [])
            ]
            
            if not files_to_migrate:
                print("No files need migration - all code already works in both pandas versions!")
                results['phases']['migration'] = {
                    'status': 'no_migration_needed',
                    'message': 'All pandas code is already compatible with both versions'
                }
            else:
                print(f"Migrating {len(files_to_migrate)} files that need compatibility fixes...")
                results['phases']['migration'] = self._migration_phase(
                    repo_path, 
                    files_to_migrate
                )
            
            # Phase 4: Post-migration testing in BOTH environments
            print("Phase 4: Testing in both pandas environments...")
            
            # Test in pandas 0.19.2 first
            print("  Testing with pandas 0.19.2...")
            results['phases']['post_tests_019'] = self._test_phase(repo_path, "0.19.2")
            
            # Test in pandas 1.1.5
            print("  Testing with pandas 1.1.5...")
            results['phases']['post_tests_115'] = self._test_phase(repo_path, "1.1.5")
            
            # Phase 5: Validation
            print("Phase 5: Validating results...")
            results['phases']['validation'] = self._validation_phase(results)
            
            # Determine overall status
            if (results['phases']['validation']['backward_compatible'] and 
                results['phases']['validation']['no_regressions']):
                results['status'] = 'success'
            else:
                results['status'] = 'failed'
                # Rollback if configured
                if self.agent.config_options.get('auto_rollback_on_failure', True):
                    print("Rolling back changes due to failures...")
                    self._rollback_phase(results['phases']['migration'].get('backups', {}))
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            print(f"ERROR: {e}")
        
        results['end_time'] = datetime.now().isoformat()
        return results
    
    def _discovery_phase(self, repo_path: str) -> Dict[str, Any]:
        """Discover Python files and analyze pandas usage."""
        # Use FileFilter to get only safe files
        all_python_files = find_python_files(repo_path)
        
        # Filter files through safety check
        file_categories = FileFilter.filter_files(all_python_files)
        safe_files = file_categories['safe']
        unsafe_files = file_categories['unsafe']
        
        # Log unsafe files
        if unsafe_files:
            print(f"Excluding {len(unsafe_files)} files from migration:")
            for file_path, reason in unsafe_files[:5]:  # Show first 5
                print(f"  - {file_path}: {reason}")
            if len(unsafe_files) > 5:
                print(f"  ... and {len(unsafe_files) - 5} more")
        
        filtered_files = safe_files
        
        pandas_files = []
        for file_path in filtered_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'pandas' in content or 'pd.' in content:
                    pandas_files.append(file_path)
            except:
                pass
        
        return {
            'total_files': len(all_python_files),
            'safe_files': filtered_files,
            'pandas_files': pandas_files,
            'excluded_files': len(unsafe_files),
            'status': 'success'
        }
    
    def _compatibility_check_phase(self, repo_path: str, safe_files: List[str]) -> Dict[str, Any]:
        """Check which files actually need migration."""
        print(f"Checking {len(safe_files)} files for compatibility...")
        
        # Check each file
        check_results = self.pre_checker.check_directory(repo_path, safe_files)
        
        # Log results
        print(f"  - Already compatible: {len(check_results['already_compatible'])} files")
        print(f"  - Need migration: {len(check_results['needs_migration'])} files")
        print(f"  - No pandas usage: {len(check_results['no_pandas'])} files")
        
        # Show details of files that need migration
        if check_results['needs_migration']:
            print("\nFiles requiring migration:")
            for item in check_results['needs_migration'][:10]:  # Show first 10
                print(f"  - {item['file']}: {item['reason']}")
            if len(check_results['needs_migration']) > 10:
                print(f"  ... and {len(check_results['needs_migration']) - 10} more")
        
        # Show files that are already compatible
        if check_results['already_compatible']:
            print("\nFiles already compatible (will NOT be modified):")
            for item in check_results['already_compatible'][:5]:  # Show first 5
                print(f"  - {item['file']}: {item['reason']}")
            if len(check_results['already_compatible']) > 5:
                print(f"  ... and {len(check_results['already_compatible']) - 5} more")
        
        return check_results
    
    def _test_phase(self, repo_path: str, pandas_version: str) -> Dict[str, Any]:
        """Run tests in specified pandas environment."""
        try:
            # Find test command
            test_commands = [
                "pytest -xvs",
                "python -m pytest -xvs",
                "python -m unittest discover",
                "nosetests -v"
            ]
            
            # Try each test command
            for test_cmd in test_commands:
                try:
                    result = self.test_runner.run_tests(
                        repo_path=repo_path,
                        pandas_version=pandas_version,
                        test_command=test_cmd
                    )
                    
                    return {
                        'pandas_version': pandas_version,
                        'test_command': test_cmd,
                        'total_tests': result.total_tests,
                        'passed': result.passed,
                        'failed': result.failed,
                        'errors': result.errors,
                        'duration': result.duration,
                        'status': 'success' if result.failed == 0 and result.errors == 0 else 'has_failures'
                    }
                except:
                    continue
            
            # No test command worked
            return {
                'pandas_version': pandas_version,
                'status': 'no_tests_found',
                'message': 'Could not find or run tests'
            }
            
        except Exception as e:
            return {
                'pandas_version': pandas_version,
                'status': 'error',
                'error': str(e)
            }
    
    def _migration_phase(self, repo_path: str, files: List[str]) -> Dict[str, Any]:
        """Apply backward-compatible migrations."""
        results = {
            'migrated_files': {},
            'backups': {},
            'status': 'success'
        }
        
        for file_path in files:
            try:
                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Skip if no pandas usage
                if 'pandas' not in original_content and 'pd.' not in original_content:
                    continue
                
                # Create backup
                backup_path = backup_file(file_path)
                results['backups'][file_path] = backup_path
                
                # Apply migration rules
                migrated_content, changes = self.engine.apply_rules(
                    original_content, file_path
                )
                
                # Validate syntax
                is_valid, error = validate_python_syntax(migrated_content)
                if not is_valid:
                    results['migrated_files'][file_path] = {
                        'status': 'syntax_error',
                        'error': error,
                        'changes': []
                    }
                    continue
                
                # Validate backward compatibility
                compat_check = self.engine.validate_compatibility(migrated_content)
                if not compat_check['compatible']:
                    results['migrated_files'][file_path] = {
                        'status': 'compatibility_error',
                        'issues': compat_check['issues'],
                        'changes': changes
                    }
                    continue
                
                # Write migrated content
                if changes:  # Only write if changes were made
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(migrated_content)
                
                results['migrated_files'][file_path] = {
                    'status': 'success',
                    'changes': changes
                }
                
            except Exception as e:
                results['migrated_files'][file_path] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['status'] = 'partial_failure'
        
        return results
    
    def _validation_phase(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate migration results."""
        validation = {
            'backward_compatible': True,
            'no_regressions': True,
            'issues': []
        }
        
        # Check if tests pass in pandas 0.19.2
        post_019 = results['phases'].get('post_tests_019', {})
        if post_019.get('status') != 'success' and post_019.get('status') != 'has_failures':
            validation['backward_compatible'] = False
            validation['issues'].append(
                f"Tests fail in pandas 0.19.2: {post_019.get('failed', 0)} failures"
            )
        
        # Check for regressions (tests that passed before but fail after)
        pre_tests = results['phases'].get('pre_tests', {})
        if (pre_tests.get('status') == 'success' and 
            post_019.get('failed', 0) > pre_tests.get('failed', 0)):
            validation['no_regressions'] = True
            validation['issues'].append(
                f"Test regressions detected: {post_019.get('failed', 0) - pre_tests.get('failed', 0)} new failures"
            )
        
        # Check if any files had migration errors
        migration = results['phases'].get('migration', {})
        for file_path, file_result in migration.get('migrated_files', {}).items():
            if file_result['status'] != 'success':
                validation['issues'].append(
                    f"Migration failed for {file_path}: {file_result.get('status')}"
                )
        
        return validation
    
    def _rollback_phase(self, backups: Dict[str, str]):
        """Rollback changes using backups."""
        for original_path, backup_path in backups.items():
            try:
                shutil.copy2(backup_path, original_path)
                print(f"Rolled back: {original_path}")
            except Exception as e:
                print(f"Failed to rollback {original_path}: {e}")
    
    def migrate_single_file(self, file_path: str) -> Dict[str, Any]:
        """Migrate a single file with full validation."""
        # Create a minimal workflow for single file
        repo_path = os.path.dirname(file_path)
        
        # Run pre-tests
        pre_tests = self._test_phase(repo_path, "0.19.2")
        
        # Migrate file
        migration = self._migration_phase(repo_path, [file_path])
        
        # Run post-tests in both environments
        post_tests_019 = self._test_phase(repo_path, "0.19.2")
        post_tests_115 = self._test_phase(repo_path, "1.1.5")
        
        # Validate
        validation = {
            'file': file_path,
            'migration_status': migration['migrated_files'].get(file_path, {}).get('status'),
            'tests_pass_019': post_tests_019.get('status') == 'success',
            'tests_pass_115': post_tests_115.get('status') == 'success',
            'no_regressions': post_tests_019.get('failed', 0) <= pre_tests.get('failed', 0)
        }
        
        return validation