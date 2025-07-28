"""Main migration workflow that orchestrates the entire process."""

import os
import time
from typing import Dict, List, Any
from datetime import datetime

from ..core.migration_engine import MigrationEngine
from ..utils.file_discovery import discover_python_files
from ..utils.test_runner import TestRunner
from ..utils.report_generator import ReportGenerator


class MigrationWorkflow:
    """Orchestrates the complete migration workflow."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the workflow with configuration."""
        self.config = config
        self.engine = MigrationEngine()
        self.test_runner = TestRunner(config.get('conda_envs', {}))
        self.report_generator = ReportGenerator()
        
        # Workflow phases
        self.phases = [
            'discovery',
            'pre_migration_tests',
            'migration',
            'post_migration_tests',
            'report_generation'
        ]
    
    def execute(self, repo_path: str) -> Dict[str, Any]:
        """Execute the complete migration workflow.
        
        Args:
            repo_path: Path to the repository to migrate
            
        Returns:
            Complete results including status, stats, and report path
        """
        print(f"\n{'='*60}")
        print(f"Starting Pandas Migration Workflow")
        print(f"Repository: {repo_path}")
        print(f"{'='*60}\n")
        
        results = {
            'repo_path': repo_path,
            'start_time': datetime.now(),
            'phases': {},
            'stats': {
                'files_analyzed': 0,
                'files_migrated': 0,
                'files_skipped': 0,
                'total_changes': 0,
                'tests_passed': 0,
                'tests_failed': 0,
            },
            'status': 'pending'
        }
        
        try:
            # Phase 1: Discovery
            print("📁 Phase 1: Discovering Python files...")
            files = self._discovery_phase(repo_path)
            results['phases']['discovery'] = {
                'status': 'complete',
                'files_found': len(files)
            }
            results['stats']['files_analyzed'] = len(files)
            print(f"   Found {len(files)} Python files\n")
            
            # Phase 2: Pre-migration tests (optional)
            if self.config.get('run_tests', True):
                print("🧪 Phase 2: Running pre-migration tests...")
                pre_test_results = self._test_phase(repo_path, 'pre')
                results['phases']['pre_tests'] = pre_test_results
                print(f"   Tests: {pre_test_results['passed']} passed, {pre_test_results['failed']} failed\n")
            
            # Phase 3: Migration
            print("🔧 Phase 3: Applying migrations...")
            migration_results = self._migration_phase(files)
            results['phases']['migration'] = migration_results
            results['stats']['files_migrated'] = migration_results['migrated']
            results['stats']['files_skipped'] = migration_results['skipped']
            results['stats']['total_changes'] = migration_results['total_changes']
            print(f"   Migrated: {migration_results['migrated']} files")
            print(f"   Skipped: {migration_results['skipped']} files")
            print(f"   Total changes: {migration_results['total_changes']}\n")
            
            # Phase 4: Post-migration tests (optional)
            if self.config.get('run_tests', True):
                print("🧪 Phase 4: Running post-migration tests...")
                post_test_results = self._test_phase(repo_path, 'post')
                results['phases']['post_tests'] = post_test_results
                results['stats']['tests_passed'] = post_test_results['passed']
                results['stats']['tests_failed'] = post_test_results['failed']
                print(f"   Tests: {post_test_results['passed']} passed, {post_test_results['failed']} failed\n")
                
                # Check for regressions
                if 'pre_tests' in results['phases']:
                    pre_failed = results['phases']['pre_tests']['failed']
                    post_failed = post_test_results['failed']
                    if post_failed > pre_failed:
                        print(f"   ⚠️  WARNING: {post_failed - pre_failed} new test failures!")
            
            # Phase 5: Report generation
            if self.config.get('generate_report', True):
                print("📊 Phase 5: Generating report...")
                report_path = self._report_phase(results)
                results['report_path'] = report_path
                print(f"   Report saved: {report_path}\n")
            
            results['status'] = 'success'
            results['end_time'] = datetime.now()
            results['duration'] = str(results['end_time'] - results['start_time'])
            
            print(f"{'='*60}")
            print(f"✅ Migration completed successfully!")
            print(f"Duration: {results['duration']}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            print(f"\n❌ Migration failed: {e}")
        
        return results
    
    def _discovery_phase(self, repo_path: str) -> List[str]:
        """Discover all Python files to migrate."""
        # Patterns to exclude
        exclude_patterns = [
            '__pycache__',
            '.git',
            'venv',
            '.venv',
            'env',
            '.env',
            'build',
            'dist',
            '.tox',
            '*.egg-info',
        ]
        
        # Discover Python files
        files = discover_python_files(repo_path, exclude_patterns)
        
        # Filter out test files if configured
        if not self.config.get('migrate_tests', True):
            files = [f for f in files if 'test' not in os.path.basename(f).lower()]
        
        return files
    
    def _test_phase(self, repo_path: str, phase: str) -> Dict[str, Any]:
        """Run tests in the specified pandas environment."""
        # Determine which pandas version to use
        if phase == 'pre':
            version = self.config.get('source_version', '0.19.2')
        else:
            # Test in both versions for post-migration
            version = self.config.get('target_version', '1.1.5')
        
        # Run tests
        test_results = self.test_runner.run_tests(repo_path, version)
        
        return {
            'pandas_version': version,
            'passed': test_results.get('passed', 0),
            'failed': test_results.get('failed', 0),
            'skipped': test_results.get('skipped', 0),
            'duration': test_results.get('duration', 0),
        }
    
    def _migration_phase(self, files: List[str]) -> Dict[str, Any]:
        """Apply migrations to all files."""
        results = {
            'migrated': 0,
            'skipped': 0,
            'errors': 0,
            'total_changes': 0,
            'file_results': []
        }
        
        for i, file_path in enumerate(files, 1):
            print(f"\r   Processing: {i}/{len(files)} files...", end='', flush=True)
            
            # Migrate the file
            file_result = self.engine.migrate_file(
                file_path, 
                create_backup=self.config.get('create_backups', True)
            )
            
            # Update stats
            if file_result['status'] == 'success':
                results['migrated'] += 1
                results['total_changes'] += file_result.get('total_changes', 0)
            elif file_result['status'] == 'skipped' or file_result['status'] == 'unchanged':
                results['skipped'] += 1
            else:
                results['errors'] += 1
            
            results['file_results'].append(file_result)
        
        print()  # New line after progress
        return results
    
    def _report_phase(self, results: Dict[str, Any]) -> str:
        """Generate the migration report."""
        report_path = os.path.join(
            results['repo_path'],
            f"pandas_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        # Generate report
        self.report_generator.generate(results, report_path)
        
        return report_path