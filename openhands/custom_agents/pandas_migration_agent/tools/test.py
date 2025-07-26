"""Test execution tool for pandas migration validation."""

from typing import Dict, Any, Optional
from ..test_runner import TestRunner


class TestTool:
    """Tool for running tests in different pandas environments."""
    
    name = "run_tests"
    description = "Run tests in specified pandas environment"
    
    def __init__(self, agent):
        """Initialize the test tool.
        
        Args:
            agent: Parent PandasMigrationAgent instance
        """
        self.agent = agent
        self.test_runner = TestRunner()
        
        # Use agent's conda environment configuration
        if hasattr(agent, 'config_options') and 'conda_environments' in agent.config_options:
            self.test_runner.conda_envs = agent.config_options['conda_environments']
    
    def __call__(self, 
                 repo_path: str,
                 pandas_version: str,
                 test_command: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Run tests in specified pandas environment.
        
        Args:
            repo_path: Repository path
            pandas_version: Pandas version to test with
            test_command: Custom test command
            **kwargs: Additional options
            
        Returns:
            Dictionary with test results
        """
        # Run tests
        test_result = self.test_runner.run_tests(
            repo_path=repo_path,
            pandas_version=pandas_version,
            test_command=test_command,
            environment_vars=kwargs.get('environment_vars')
        )
        
        # Convert to dictionary format
        return {
            'pandas_version': pandas_version,
            'framework': test_result.framework.value,
            'total_tests': test_result.total_tests,
            'passed': test_result.passed,
            'failed': test_result.failed,
            'skipped': test_result.skipped,
            'errors': test_result.errors,
            'duration': test_result.duration,
            'test_results': [
                {
                    'name': tr.name,
                    'status': tr.status,
                    'duration': tr.duration,
                    'message': tr.message,
                    'traceback': tr.traceback
                }
                for tr in test_result.test_results
            ],
            'coverage': test_result.coverage
        }
    
    def compare_results(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """Run tests in both environments and compare.
        
        Args:
            repo_path: Repository path
            **kwargs: Additional options
            
        Returns:
            Comparison results
        """
        # Run tests with pandas 0.19.2
        before = self(repo_path, "0.19.2", **kwargs)
        
        # Run tests with pandas 1.1.5
        after = self(repo_path, "1.1.5", **kwargs)
        
        # Compare results
        comparison = self.test_runner.compare_results(
            self._dict_to_test_suite_result(before),
            self._dict_to_test_suite_result(after)
        )
        
        return comparison
    
    def _dict_to_test_suite_result(self, result_dict: Dict[str, Any]):
        """Convert dictionary back to TestSuiteResult for comparison."""
        from ..test_runner import TestSuiteResult, TestResult, TestFramework
        
        return TestSuiteResult(
            framework=TestFramework(result_dict['framework']),
            total_tests=result_dict['total_tests'],
            passed=result_dict['passed'],
            failed=result_dict['failed'],
            skipped=result_dict['skipped'],
            errors=result_dict['errors'],
            duration=result_dict['duration'],
            test_results=[
                TestResult(
                    name=tr['name'],
                    status=tr['status'],
                    duration=tr['duration'],
                    message=tr['message'],
                    traceback=tr['traceback']
                )
                for tr in result_dict['test_results']
            ],
            coverage=result_dict['coverage'],
            pandas_version=result_dict['pandas_version']
        )