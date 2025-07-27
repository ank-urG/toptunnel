"""Enhanced Pandas Migration Agent for OpenHands.

This agent handles the migration of codebases from pandas 0.19.2 to 1.1.5,
ensuring backward compatibility and comprehensive testing.
"""

import os
import json
import re
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import yaml

from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    AgentFinishAction,
    CmdRunAction,
    FileReadAction,
    FileWriteAction,
    MessageAction,
)
from openhands.events.observation import (
    CmdOutputObservation,
    FileReadObservation,
    FileWriteObservation,
)
from openhands.llm.llm import LLM
from openhands.runtime.plugins import AgentSkillsRequirement, PluginRequirement

from .migration_rules import MigrationRuleEngine
from .backward_compatible_rules import BackwardCompatibleMigrationEngine
from .direct_replacement_rules import DirectReplacementEngine
from .test_runner import TestRunner
from .report_generator import MigrationReportGenerator
from .compatibility_checker import CompatibilityChecker
from .robust_migration_workflow import RobustMigrationWorkflow
from .utils import (
    find_python_files,
    backup_file,
    restore_file,
    parse_test_output,
    extract_pandas_imports,
)
from .tools import AnalyzeTool, MigrateTool, TestTool, ReportTool


class EnhancedPandasMigrationAgent(Agent):
    """Agent specialized for migrating pandas code from 0.19.2 to 1.1.5."""
    
    VERSION = '1.0'
    
    sandbox_plugins: List[PluginRequirement] = [
        AgentSkillsRequirement(
            name="pandas_migration",
            host_src="custom_agents/pandas_migration_agent/skills",
            sandbox_dest="/tmp/pandas_migration_skills"
        )
    ]
    
    def __init__(self, llm: LLM, config: AgentConfig):
        """Initialize the Pandas Migration Agent.
        
        Args:
            llm: Language model instance
            config: Agent configuration
        """
        super().__init__(llm, config)
        
        # Initialize components
        self.rule_engine = MigrationRuleEngine()
        self.backward_compatible_engine = BackwardCompatibleMigrationEngine()
        self.direct_replacement_engine = DirectReplacementEngine()  # NEW: Direct replacements
        self.test_runner = TestRunner()
        self.report_generator = MigrationReportGenerator()
        self.compatibility_checker = CompatibilityChecker()
        
        # Use direct replacements instead of compatibility wrappers
        self.use_direct_replacements = True
        self.use_backward_compatible = False  # Disable wrapper approach
        
        # Initialize robust workflow
        self.robust_workflow = RobustMigrationWorkflow(self)
        
        # Migration state
        self.migration_state = {
            'current_repo': None,
            'files_to_migrate': [],
            'migration_results': {},
            'test_results': {'before': {}, 'after': {}},
            'rollback_info': {},
            'pandas_versions': {'source': '0.19.2', 'target': '1.1.5'},
            'start_time': None,
            'end_time': None,
        }
        
        # Load configuration from YAML if available
        self._load_config()
        
        # Initialize tools
        self.analyze_tool = AnalyzeTool(self)
        self.migrate_tool = MigrateTool(self)
        self.test_tool = TestTool(self)
        self.report_tool = ReportTool(self)
        
        # Register tools for OpenHands
        self.tools = [
            self.analyze_tool,
            self.migrate_tool,
            self.test_tool,
            self.report_tool
        ]
        
        # Configuration
        self.config_options = {
            'auto_rollback_on_failure': True,
            'run_tests_before_migration': True,
            'run_tests_after_migration': True,
            'create_backups': True,
            'strict_compatibility': True,
            'max_retries': 3,
            'test_timeout': 300,  # 5 minutes per test suite
            'parallel_testing': False,
            'custom_import_mappings': {
                'pd.Panel': 'aqr.core.panel.Panel',
                'pd.ols': 'aqr.stats.ols.OLS',
                'pd.stats.ols.OLS': 'aqr.stats.ols.OLS',
            },
            'conda_environments': {
                '0.19.2': 'py36-1.1.10',
                '1.1.5': 'pandas_115_final'
            }
        }
    
    def step(self, state: State) -> Action:
        """Execute the next step in the migration process.
        
        Args:
            state: Current agent state
            
        Returns:
            Next action to perform
        """
        # Check if this is the first step
        if state.iteration == 0:
            return self._initialize_migration(state)
        
        # Get the last action and observation
        last_action = state.history[-2] if len(state.history) >= 2 else None
        last_observation = state.history[-1] if len(state.history) >= 1 else None
        
        # Determine next action based on current state
        if self.migration_state['current_repo'] is None:
            return MessageAction("Please specify the repository to migrate.")
        
        # Migration workflow stages
        stage = self._determine_current_stage(state)
        
        if stage == 'discovery':
            return self._discover_files_to_migrate(state)
        elif stage == 'pre_migration_testing':
            return self._run_pre_migration_tests(state)
        elif stage == 'migration':
            return self._perform_migration(state)
        elif stage == 'post_migration_testing':
            return self._run_post_migration_tests(state)
        elif stage == 'report_generation':
            return self._generate_final_report(state)
        elif stage == 'completion':
            return self._complete_migration(state)
        else:
            return MessageAction(f"Unknown migration stage: {stage}")
    
    def _initialize_migration(self, state: State) -> Action:
        """Initialize the migration process."""
        self.migration_state['start_time'] = datetime.now()
        
        # Parse user message for repository path
        user_message = state.get_current_user_intent()
        repo_path = self._extract_repo_path(user_message)
        
        if repo_path:
            self.migration_state['current_repo'] = repo_path
            return MessageAction(
                f"Starting pandas migration for repository: {repo_path}\\n"
                f"Source version: {self.migration_state['pandas_versions']['source']}\\n"
                f"Target version: {self.migration_state['pandas_versions']['target']}"
            )
        else:
            return MessageAction(
                "Welcome to the Pandas Migration Agent!\\n"
                "Please provide the repository path to migrate."
            )
    
    def _determine_current_stage(self, state: State) -> str:
        """Determine the current stage of migration."""
        if not self.migration_state['files_to_migrate']:
            return 'discovery'
        elif not self.migration_state['test_results']['before']:
            return 'pre_migration_testing'
        elif not self.migration_state['migration_results']:
            return 'migration'
        elif not self.migration_state['test_results']['after']:
            return 'post_migration_testing'
        elif not hasattr(self, '_report_generated'):
            return 'report_generation'
        else:
            return 'completion'
    
    def _discover_files_to_migrate(self, state: State) -> Action:
        """Discover Python files that need migration."""
        repo_path = self.migration_state['current_repo']
        
        return CmdRunAction(
            command=f"find {repo_path} -name '*.py' -type f | grep -E '\\.(py)$' | head -100",
            thought="Discovering Python files in the repository"
        )
    
    def _run_pre_migration_tests(self, state: State) -> Action:
        """Run tests before migration with pandas 0.19.2."""
        return MessageAction(
            "Running pre-migration tests with pandas 0.19.2...\\n"
            "This will establish a baseline for comparison."
        )
    
    def _perform_migration(self, state: State) -> Action:
        """Perform the actual migration using robust workflow."""
        repo_path = self.migration_state['current_repo']
        
        # Use the robust workflow for complete migration
        return MessageAction(
            "Starting robust migration workflow...\n"
            "This will:\n"
            "1. Discover safe Python files (excluding configs)\n"
            "2. Run tests with pandas 0.19.2\n"
            "3. Apply backward-compatible migrations\n"
            "4. Test in BOTH pandas environments\n"
            "5. Validate and rollback if needed"
        )
    
    def _run_post_migration_tests(self, state: State) -> Action:
        """Run tests after migration with pandas 1.1.5."""
        return MessageAction(
            "Running post-migration tests with pandas 1.1.5...\\n"
            "Checking for regressions and compatibility issues."
        )
    
    def _generate_final_report(self, state: State) -> Action:
        """Generate the final migration report."""
        report = self.report_generator.generate_report(self.migration_state)
        
        # Save report to file
        report_path = os.path.join(
            self.migration_state['current_repo'],
            f"pandas_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        return FileWriteAction(
            path=report_path,
            content=report,
            thought="Generating final migration report"
        )
    
    def _complete_migration(self, state: State) -> Action:
        """Complete the migration process."""
        self.migration_state['end_time'] = datetime.now()
        duration = self.migration_state['end_time'] - self.migration_state['start_time']
        
        summary = self._generate_summary()
        
        return AgentFinishAction(
            outputs={
                'duration': str(duration),
                'files_migrated': len(self.migration_state['migration_results']),
                'test_status': self._get_test_summary(),
                'report_path': self._get_report_path(),
            },
            thought=f"Migration completed successfully!\\n{summary}"
        )
    
    def _extract_repo_path(self, message: str) -> Optional[str]:
        """Extract repository path from user message."""
        # Simple extraction - can be enhanced with better parsing
        if 'repo:' in message:
            return message.split('repo:')[1].strip().split()[0]
        elif '/workspace/' in message:
            match = re.search(r'/workspace/[^\\s]+', message)
            if match:
                return match.group(0)
        return None
    
    def _generate_summary(self) -> str:
        """Generate a summary of the migration."""
        total_files = len(self.migration_state['migration_results'])
        successful = sum(1 for r in self.migration_state['migration_results'].values() if r.get('status') == 'success')
        failed = total_files - successful
        
        return (
            f"Migration Summary:\\n"
            f"- Total files processed: {total_files}\\n"
            f"- Successful migrations: {successful}\\n"
            f"- Failed migrations: {failed}\\n"
            f"- Test results: {self._get_test_summary()}"
        )
    
    def _get_test_summary(self) -> str:
        """Get a summary of test results."""
        before = self.migration_state['test_results']['before']
        after = self.migration_state['test_results']['after']
        
        if not before or not after:
            return "Tests not completed"
        
        return (
            f"Before: {before.get('passed', 0)} passed, {before.get('failed', 0)} failed | "
            f"After: {after.get('passed', 0)} passed, {after.get('failed', 0)} failed"
        )
    
    def _get_report_path(self) -> str:
        """Get the path to the generated report."""
        # This would be set when the report is generated
        return getattr(self, '_report_path', 'No report generated')
    
    def _load_config(self):
        """Load configuration from config.yaml if available."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.yaml_config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config.yaml: {e}")
                self.yaml_config = {}
        else:
            self.yaml_config = {}
    
    def _load_prompt(self, prompt_type: str = 'system') -> str:
        """Load prompt from file.
        
        Args:
            prompt_type: Type of prompt ('system' or 'user_template')
            
        Returns:
            Prompt content
        """
        if prompt_type == 'system':
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'system_prompt.md')
        else:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'user_prompt_template.md')
        
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r') as f:
                return f.read()
        else:
            logger.warning(f"Prompt file not found: {prompt_path}")
            return ""
    
    def get_system_message(self) -> str:
        """Get the system message for the agent."""
        return self._load_prompt('system')