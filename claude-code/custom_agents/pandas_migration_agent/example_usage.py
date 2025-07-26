#!/usr/bin/env python3
"""Example usage of the Pandas Migration Agent.

This script demonstrates how to use the agent programmatically
or integrate it into your CI/CD pipeline.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pandas_migration_agent.agent import EnhancedPandasMigrationAgent
from pandas_migration_agent.migration_rules import MigrationRule, MigrationPriority
from openhands.core.config import AgentConfig
from openhands.llm.llm import LLM


def main():
    """Main function demonstrating agent usage."""
    parser = argparse.ArgumentParser(description='Pandas Migration Agent Example')
    parser.add_argument('repo_path', help='Path to repository to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without making changes')
    parser.add_argument('--skip-tests', action='store_true', help='Skip test execution')
    parser.add_argument('--report-format', choices=['markdown', 'html', 'json'], default='markdown',
                       help='Report output format')
    args = parser.parse_args()
    
    # Example 1: Basic Migration
    print("=== Example 1: Basic Migration ===")
    basic_migration_example(args.repo_path)
    
    # Example 2: Custom Configuration
    print("\n=== Example 2: Custom Configuration ===")
    custom_config_example(args.repo_path)
    
    # Example 3: Adding Custom Rules
    print("\n=== Example 3: Custom Migration Rules ===")
    custom_rules_example(args.repo_path)
    
    # Example 4: CI/CD Integration
    print("\n=== Example 4: CI/CD Integration ===")
    cicd_integration_example(args.repo_path)


def basic_migration_example(repo_path: str):
    """Basic migration with default settings."""
    print(f"Migrating repository: {repo_path}")
    
    # In real usage, these would be properly initialized
    # This is a simplified example
    config = AgentConfig()
    llm = None  # Would be initialized with actual LLM
    
    # Create agent instance
    agent = EnhancedPandasMigrationAgent(llm, config)
    
    # Set repository
    agent.migration_state['current_repo'] = repo_path
    
    print("Migration configuration:")
    print(f"  Source pandas: {agent.migration_state['pandas_versions']['source']}")
    print(f"  Target pandas: {agent.migration_state['pandas_versions']['target']}")
    print(f"  Auto rollback: {agent.config_options['auto_rollback_on_failure']}")
    print(f"  Create backups: {agent.config_options['create_backups']}")
    
    # In real usage, the agent would be run through OpenHands
    # This shows the configuration that would be used


def custom_config_example(repo_path: str):
    """Migration with custom configuration."""
    config = AgentConfig()
    llm = None
    
    agent = EnhancedPandasMigrationAgent(llm, config)
    
    # Customize configuration
    agent.config_options.update({
        'auto_rollback_on_failure': False,  # Don't auto-rollback
        'test_timeout': 600,  # 10 minute timeout
        'parallel_testing': True,  # Enable parallel tests
        'custom_import_mappings': {
            'pd.Panel': 'mycompany.compat.panel.Panel',
            'pd.ols': 'mycompany.compat.regression.OLS',
            'pd.stats.api': 'mycompany.compat.stats',
        }
    })
    
    print("Custom configuration applied:")
    for key, value in agent.config_options.items():
        print(f"  {key}: {value}")


def custom_rules_example(repo_path: str):
    """Add custom migration rules."""
    config = AgentConfig()
    llm = None
    
    agent = EnhancedPandasMigrationAgent(llm, config)
    
    # Add custom rule for company-specific API
    custom_rule = MigrationRule(
        name="replace_custom_rolling_window",
        pattern=r"pd\.custom_rolling_window\(",
        replacement="pd.DataFrame.rolling(",
        priority=MigrationPriority.HIGH,
        description="Replace custom rolling window function",
        test_pattern=r"pd\.custom_rolling_window"
    )
    
    agent.rule_engine.add_custom_rule(custom_rule)
    
    # Add rule for internal function
    internal_rule = MigrationRule(
        name="update_internal_api",
        pattern=r"from pandas\.internal import (\w+)",
        replacement=r"from pandas._internal import \1",
        priority=MigrationPriority.MEDIUM,
        description="Update internal API imports"
    )
    
    agent.rule_engine.add_custom_rule(internal_rule)
    
    print(f"Added {len(agent.rule_engine.custom_rules)} custom rules")
    for rule in agent.rule_engine.custom_rules:
        print(f"  - {rule.name}: {rule.description}")


def cicd_integration_example(repo_path: str):
    """Example CI/CD integration."""
    print("CI/CD Integration Script:")
    print("```bash")
    print("#!/bin/bash")
    print("# pandas_migration_ci.sh")
    print("")
    print("# Run migration in CI environment")
    print("export PANDAS_MIGRATION_CI=1")
    print("export PANDAS_MIGRATION_REPO=$1")
    print("")
    print("# Run OpenHands with migration agent")
    print("openhands \\")
    print("  --agent PandasMigrationAgent \\")
    print("  --no-interactive \\")
    print("  --output-dir ./migration_results \\")
    print(f"  --command 'Migrate repository at {repo_path} from pandas 0.19.2 to 1.1.5'")
    print("")
    print("# Check migration status")
    print("if [ -f ./migration_results/migration_report.md ]; then")
    print("  echo 'Migration completed successfully'")
    print("  ")
    print("  # Check for test regressions")
    print("  if grep -q 'Test Regressions: 0' ./migration_results/migration_report.md; then")
    print("    echo 'No test regressions found'")
    print("    exit 0")
    print("  else")
    print("    echo 'Test regressions detected!'")
    print("    exit 1")
    print("  fi")
    print("else")
    print("  echo 'Migration failed'")
    print("  exit 1")
    print("fi")
    print("```")


def advanced_usage_examples():
    """Show advanced usage patterns."""
    print("\n=== Advanced Usage Examples ===\n")
    
    # Example: Selective file migration
    print("1. Selective File Migration:")
    print("```python")
    print("# Migrate only specific files")
    print("agent.migration_state['files_to_migrate'] = [")
    print("    'src/data_processing.py',")
    print("    'src/analytics/stats.py',")
    print("    'tests/test_data.py'")
    print("]")
    print("```\n")
    
    # Example: Custom test commands
    print("2. Custom Test Commands:")
    print("```python")
    print("# Use custom test command")
    print("test_result = agent.test_runner.run_tests(")
    print("    repo_path='/workspace/project',")
    print("    pandas_version='1.1.5',")
    print("    test_command='make test-unit',")
    print("    environment_vars={'PYTEST_OPTS': '-v -x'}")
    print(")")
    print("```\n")
    
    # Example: Incremental migration
    print("3. Incremental Migration:")
    print("```python")
    print("# Migrate in phases")
    print("phases = [")
    print("    {'pattern': 'src/core/*.py', 'priority': 'critical'},")
    print("    {'pattern': 'src/utils/*.py', 'priority': 'high'},")
    print("    {'pattern': 'tests/*.py', 'priority': 'medium'},")
    print("]")
    print("")
    print("for phase in phases:")
    print("    files = find_files_matching(phase['pattern'])")
    print("    agent.migrate_files(files)")
    print("    if not agent.run_tests():")
    print("        print(f'Phase {phase} failed')")
    print("        break")
    print("```\n")
    
    # Example: Custom compatibility checks
    print("4. Custom Compatibility Checks:")
    print("```python")
    print("# Add custom compatibility check")
    print("def check_custom_api(content: str) -> List[CompatibilityIssue]:")
    print("    issues = []")
    print("    if 'my_custom_api' in content:")
    print("        issues.append(CompatibilityIssue(")
    print("            level=CompatibilityLevel.WARNING,")
    print("            category='custom',")
    print("            description='Custom API needs update',")
    print("            suggestion='Update to new custom API'")
    print("        ))")
    print("    return issues")
    print("")
    print("agent.compatibility_checker.add_custom_check(check_custom_api)")
    print("```")


if __name__ == "__main__":
    # Run main examples
    main()
    
    # Show advanced examples
    advanced_usage_examples()