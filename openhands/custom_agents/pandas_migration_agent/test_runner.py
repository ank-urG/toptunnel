"""Test runner for pandas migration validation."""

import os
import sys
import subprocess
import tempfile
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    NOSE = "nose"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Represents a single test result."""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Represents results from a test suite."""
    framework: TestFramework
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    test_results: List[TestResult]
    coverage: Optional[Dict[str, Any]] = None
    pandas_version: Optional[str] = None


class TestRunner:
    """Handles test execution in different pandas environments."""
    
    def __init__(self):
        """Initialize the test runner."""
        # Map pandas versions to conda environment names
        self.conda_envs = {
            "0.19.2": "py36-1.1.10",
            "1.1.5": "pandas_115_final"
        }
        self.test_timeout = 300  # 5 minutes default
        
    def run_tests(self, 
                  repo_path: str, 
                  pandas_version: str,
                  test_command: Optional[str] = None,
                  environment_vars: Optional[Dict[str, str]] = None) -> TestSuiteResult:
        """Run tests in a specific pandas environment.
        
        Args:
            repo_path: Path to the repository
            pandas_version: Pandas version to use (e.g., "0.19.2" or "1.1.5")
            test_command: Custom test command to run
            environment_vars: Additional environment variables
            
        Returns:
            TestSuiteResult with test outcomes
        """
        # Detect test framework if not specified
        if not test_command:
            framework, test_command = self._detect_test_framework(repo_path)
        else:
            framework = TestFramework.UNKNOWN
        
        # Get conda environment name
        conda_env = self._get_conda_env(pandas_version)
        if not conda_env:
            raise ValueError(f"No conda environment configured for pandas {pandas_version}")
        
        # Prepare environment
        env = os.environ.copy()
        if environment_vars:
            env.update(environment_vars)
        
        # Run tests
        try:
            result = self._execute_tests(
                conda_env, 
                repo_path, 
                test_command, 
                env,
                pandas_version
            )
            result.framework = framework
            result.pandas_version = pandas_version
            return result
        except Exception as e:
            return TestSuiteResult(
                framework=framework,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[
                    TestResult(
                        name="test_execution_error",
                        status="error",
                        duration=0.0,
                        message=str(e)
                    )
                ],
                pandas_version=pandas_version
            )
    
    def _detect_test_framework(self, repo_path: str) -> Tuple[TestFramework, str]:
        """Detect the test framework used in the repository.
        
        Returns:
            Tuple of (framework, test_command)
        """
        repo_path = Path(repo_path)
        
        # Check for pytest
        if (repo_path / "pytest.ini").exists() or \
           (repo_path / "pyproject.toml").exists() or \
           (repo_path / "setup.cfg").exists():
            # Check if pytest is configured
            return TestFramework.PYTEST, "pytest -v --tb=short"
        
        # Check for unittest
        if (repo_path / "test").exists() or \
           any(repo_path.glob("test_*.py")) or \
           any(repo_path.glob("*_test.py")):
            return TestFramework.UNITTEST, "python -m unittest discover -v"
        
        # Check for nose
        if (repo_path / ".noserc").exists() or \
           (repo_path / "nose.cfg").exists():
            return TestFramework.NOSE, "nosetests -v"
        
        # Default to pytest
        return TestFramework.PYTEST, "pytest -v --tb=short"
    
    def _get_conda_env(self, pandas_version: str) -> Optional[str]:
        """Get the conda environment name for a specific pandas version.
        
        Args:
            pandas_version: Pandas version
            
        Returns:
            Conda environment name or None if not configured
        """
        return self.conda_envs.get(pandas_version)
    
    def _check_conda_env(self, env_name: str) -> bool:
        """Check if a conda environment exists.
        
        Args:
            env_name: Name of the conda environment
            
        Returns:
            True if environment exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            return env_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def _execute_tests(self, 
                       conda_env: str,
                       repo_path: str,
                       test_command: str,
                       env: Dict[str, str],
                       pandas_version: str) -> TestSuiteResult:
        """Execute tests and parse results.
        
        Args:
            conda_env: Name of conda environment
            repo_path: Path to repository
            test_command: Test command to execute
            env: Environment variables
            pandas_version: Pandas version being tested
            
        Returns:
            TestSuiteResult with parsed results
        """
        # Check if conda environment exists
        if not self._check_conda_env(conda_env):
            raise ValueError(f"Conda environment '{conda_env}' not found. Please ensure it exists.")
        
        # Add XML output for better parsing
        xml_output = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
        xml_output.close()
        
        # Modify test command to output XML
        if "pytest" in test_command:
            test_command += f" --junitxml={xml_output.name}"
        elif "unittest" in test_command:
            test_command = test_command.replace("unittest", "xmlrunner")
        
        # Prepare the command to run in conda environment
        # Use conda run to execute in the specific environment
        if test_command.startswith("python"):
            full_command = f"conda run -n {conda_env} {test_command}"
        else:
            full_command = f"conda run -n {conda_env} python -m {test_command}"
        
        # Execute tests
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                cwd=repo_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )
            
            # Parse results
            if os.path.exists(xml_output.name):
                return self._parse_xml_results(xml_output.name, pandas_version)
            else:
                return self._parse_text_results(result.stdout, result.stderr, pandas_version)
            
        except subprocess.TimeoutExpired:
            return TestSuiteResult(
                framework=TestFramework.UNKNOWN,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=self.test_timeout,
                test_results=[
                    TestResult(
                        name="test_timeout",
                        status="error",
                        duration=self.test_timeout,
                        message=f"Tests timed out after {self.test_timeout} seconds"
                    )
                ],
                pandas_version=pandas_version
            )
        finally:
            try:
                os.unlink(xml_output.name)
            except:
                pass
    
    def _parse_xml_results(self, xml_path: str, pandas_version: str) -> TestSuiteResult:
        """Parse JUnit XML test results.
        
        Args:
            xml_path: Path to XML results file
            pandas_version: Pandas version used
            
        Returns:
            TestSuiteResult with parsed results
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract summary statistics
            if root.tag == "testsuites":
                # Multiple test suites
                total_tests = sum(int(ts.get("tests", 0)) for ts in root.findall("testsuite"))
                failures = sum(int(ts.get("failures", 0)) for ts in root.findall("testsuite"))
                errors = sum(int(ts.get("errors", 0)) for ts in root.findall("testsuite"))
                skipped = sum(int(ts.get("skipped", 0)) for ts in root.findall("testsuite"))
                time = sum(float(ts.get("time", 0)) for ts in root.findall("testsuite"))
                test_cases = []
                for ts in root.findall("testsuite"):
                    test_cases.extend(ts.findall("testcase"))
            else:
                # Single test suite
                total_tests = int(root.get("tests", 0))
                failures = int(root.get("failures", 0))
                errors = int(root.get("errors", 0))
                skipped = int(root.get("skipped", 0))
                time = float(root.get("time", 0))
                test_cases = root.findall("testcase")
            
            # Parse individual test results
            test_results = []
            for test_case in test_cases:
                name = f"{test_case.get('classname', '')}.{test_case.get('name', '')}"
                duration = float(test_case.get("time", 0))
                
                # Determine status
                failure = test_case.find("failure")
                error = test_case.find("error")
                skipped_elem = test_case.find("skipped")
                
                if failure is not None:
                    status = "failed"
                    message = failure.get("message", "")
                    traceback = failure.text
                elif error is not None:
                    status = "error"
                    message = error.get("message", "")
                    traceback = error.text
                elif skipped_elem is not None:
                    status = "skipped"
                    message = skipped_elem.get("message", "")
                    traceback = None
                else:
                    status = "passed"
                    message = None
                    traceback = None
                
                test_results.append(TestResult(
                    name=name,
                    status=status,
                    duration=duration,
                    message=message,
                    traceback=traceback
                ))
            
            passed = len([t for t in test_results if t.status == "passed"])
            
            return TestSuiteResult(
                framework=TestFramework.UNKNOWN,
                total_tests=total_tests,
                passed=passed,
                failed=failures,
                skipped=skipped,
                errors=errors,
                duration=time,
                test_results=test_results,
                pandas_version=pandas_version
            )
            
        except Exception as e:
            return self._create_error_result(str(e), pandas_version)
    
    def _parse_text_results(self, stdout: str, stderr: str, pandas_version: str) -> TestSuiteResult:
        """Parse text-based test results.
        
        Args:
            stdout: Standard output from test run
            stderr: Standard error from test run
            pandas_version: Pandas version used
            
        Returns:
            TestSuiteResult with parsed results
        """
        # Try to parse pytest output
        if "pytest" in stdout or "py.test" in stdout:
            return self._parse_pytest_output(stdout, pandas_version)
        
        # Try to parse unittest output
        if "Ran " in stdout and " test" in stdout:
            return self._parse_unittest_output(stdout, pandas_version)
        
        # Generic parsing
        return self._create_generic_result(stdout, stderr, pandas_version)
    
    def _parse_pytest_output(self, output: str, pandas_version: str) -> TestSuiteResult:
        """Parse pytest text output."""
        import re
        
        # Extract summary line
        summary_match = re.search(r"(\d+) passed.*?(\d+) failed.*?(\d+) skipped", output)
        if summary_match:
            passed = int(summary_match.group(1))
            failed = int(summary_match.group(2))
            skipped = int(summary_match.group(3))
            total = passed + failed + skipped
        else:
            # Alternative pattern
            match = re.search(r"(\d+) test.*? (\d+) passed", output)
            if match:
                total = int(match.group(1))
                passed = int(match.group(2))
                failed = total - passed
                skipped = 0
            else:
                return self._create_generic_result(output, "", pandas_version)
        
        # Extract duration
        duration_match = re.search(r"in ([\d.]+)s", output)
        duration = float(duration_match.group(1)) if duration_match else 0.0
        
        return TestSuiteResult(
            framework=TestFramework.PYTEST,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=0,
            duration=duration,
            test_results=[],  # Could parse individual tests from verbose output
            pandas_version=pandas_version
        )
    
    def _parse_unittest_output(self, output: str, pandas_version: str) -> TestSuiteResult:
        """Parse unittest text output."""
        import re
        
        # Extract test count
        match = re.search(r"Ran (\d+) test", output)
        if not match:
            return self._create_generic_result(output, "", pandas_version)
        
        total = int(match.group(1))
        
        # Check for OK
        if "OK" in output:
            passed = total
            failed = 0
            errors = 0
        else:
            # Extract failures and errors
            failures_match = re.search(r"failures=(\d+)", output)
            errors_match = re.search(r"errors=(\d+)", output)
            
            failed = int(failures_match.group(1)) if failures_match else 0
            errors = int(errors_match.group(1)) if errors_match else 0
            passed = total - failed - errors
        
        return TestSuiteResult(
            framework=TestFramework.UNITTEST,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=0,
            errors=errors,
            duration=0.0,  # unittest doesn't report duration by default
            test_results=[],
            pandas_version=pandas_version
        )
    
    def _create_generic_result(self, stdout: str, stderr: str, pandas_version: str) -> TestSuiteResult:
        """Create a generic result when parsing fails."""
        # Check if tests seemed to run
        if "test" in stdout.lower() or "test" in stderr.lower():
            # Tests ran but we can't parse results
            return TestSuiteResult(
                framework=TestFramework.UNKNOWN,
                total_tests=1,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[
                    TestResult(
                        name="unparseable_results",
                        status="error",
                        duration=0.0,
                        message="Could not parse test results",
                        traceback=stdout[:1000] + "\\n" + stderr[:1000]
                    )
                ],
                pandas_version=pandas_version
            )
        else:
            # No tests found
            return TestSuiteResult(
                framework=TestFramework.UNKNOWN,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=[],
                pandas_version=pandas_version
            )
    
    def _create_error_result(self, error_message: str, pandas_version: str) -> TestSuiteResult:
        """Create an error result."""
        return TestSuiteResult(
            framework=TestFramework.UNKNOWN,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            duration=0.0,
            test_results=[
                TestResult(
                    name="test_execution_error",
                    status="error",
                    duration=0.0,
                    message=error_message
                )
            ],
            pandas_version=pandas_version
        )
    
    def compare_results(self, 
                       before: TestSuiteResult, 
                       after: TestSuiteResult) -> Dict[str, Any]:
        """Compare test results before and after migration.
        
        Args:
            before: Test results with old pandas version
            after: Test results with new pandas version
            
        Returns:
            Dictionary with comparison results
        """
        # Find regressions (tests that passed before but fail after)
        before_passed = {t.name for t in before.test_results if t.status == "passed"}
        after_failed = {t.name for t in after.test_results if t.status in ["failed", "error"]}
        regressions = before_passed.intersection(after_failed)
        
        # Find improvements (tests that failed before but pass after)
        before_failed = {t.name for t in before.test_results if t.status in ["failed", "error"]}
        after_passed = {t.name for t in after.test_results if t.status == "passed"}
        improvements = before_failed.intersection(after_passed)
        
        # Calculate compatibility score
        if before.total_tests > 0:
            compatibility_score = (after.passed / before.total_tests) * 100
        else:
            compatibility_score = 100.0 if after.total_tests == 0 else 0.0
        
        return {
            "before": {
                "total": before.total_tests,
                "passed": before.passed,
                "failed": before.failed,
                "errors": before.errors,
                "pandas_version": before.pandas_version
            },
            "after": {
                "total": after.total_tests,
                "passed": after.passed,
                "failed": after.failed,
                "errors": after.errors,
                "pandas_version": after.pandas_version
            },
            "regressions": list(regressions),
            "improvements": list(improvements),
            "compatibility_score": compatibility_score,
            "status": "success" if len(regressions) == 0 else "regression"
        }