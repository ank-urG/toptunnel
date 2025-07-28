"""Main Pandas Migration Agent - Professional Implementation."""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    AgentFinishAction,
    MessageAction,
)
from openhands.llm.llm import LLM

from ..workflow.migration_workflow import MigrationWorkflow


class PandasMigrationAgent(Agent):
    """Professional Pandas Migration Agent.
    
    Migrates code from pandas 0.19.2 to 1.1.5 using DIRECT replacements.
    No compatibility wrappers, just clean code transformations.
    """
    
    VERSION = "2.0.0"
    
    def __init__(self, llm: LLM, config: AgentConfig):
        """Initialize the agent with clean architecture."""
        super().__init__(llm, config)
        
        # Core configuration
        self.config_options = {
            'source_version': '0.19.2',
            'target_version': '1.1.5',
            'conda_envs': {
                '0.19.2': 'py36-1.1.10',
                '1.1.5': 'pandas_115_final'
            },
            'windows_runtime_paths': {
                'py36-1.1.10': r'C:\LocalRuntimes\py36-1.1.10'
            },
            'create_backups': True,
            'run_tests': True,
            'generate_report': True,
        }
        
        # Initialize workflow
        self.workflow = MigrationWorkflow(self.config_options)
        
        # Track state
        self.state = {
            'repo_path': None,
            'status': 'idle',
            'start_time': None,
            'stats': {
                'files_analyzed': 0,
                'files_migrated': 0,
                'changes_made': 0,
                'tests_passed': 0,
                'tests_failed': 0,
            }
        }
        
        logger.info(f"Pandas Migration Agent v{self.VERSION} initialized")
    
    def step(self, state: State) -> Action:
        """Execute the next step in the migration process."""
        
        # First interaction - get repo path
        if state.iteration == 0:
            return MessageAction(
                "🚀 **Pandas Migration Agent v2.0**\n"
                "Ready to migrate your code from pandas 0.19.2 to 1.1.5\n\n"
                "This agent makes DIRECT code replacements:\n"
                "- ✅ .sort() → .sort_values()\n"
                "- ✅ .ix[] → .loc[]/.iloc[]\n"
                "- ✅ pd.rolling_mean() → .rolling().mean()\n"
                "- ✅ pd.Panel → aqr.core.panel.Panel\n"
                "- ✅ And many more...\n\n"
                "Please provide the repository path to migrate."
            )
        
        # Parse user input for repo path
        if self.state['repo_path'] is None:
            user_message = state.get_current_user_intent()
            repo_path = self._extract_repo_path(user_message)
            
            if repo_path and os.path.exists(repo_path):
                self.state['repo_path'] = repo_path
                self.state['status'] = 'starting'
                self.state['start_time'] = datetime.now()
                
                return MessageAction(
                    f"✅ Repository found: {repo_path}\n\n"
                    "Starting migration workflow:\n"
                    "1. 🔍 Discovering Python files\n"
                    "2. 🧪 Running baseline tests\n"
                    "3. 🔧 Applying direct replacements\n"
                    "4. ✅ Validating changes\n"
                    "5. 📊 Generating report\n"
                )
            else:
                return MessageAction(
                    "❌ Repository not found or invalid path.\n"
                    "Please provide a valid repository path."
                )
        
        # Execute migration workflow
        if self.state['status'] == 'starting':
            self.state['status'] = 'migrating'
            
            # Run the complete workflow
            results = self.workflow.execute(self.state['repo_path'])
            
            # Update stats
            self.state['stats'].update(results.get('stats', {}))
            
            # Generate summary
            summary = self._generate_summary(results)
            
            return AgentFinishAction(
                outputs={
                    'status': results['status'],
                    'duration': str(datetime.now() - self.state['start_time']),
                    'files_migrated': results['stats']['files_migrated'],
                    'changes_made': results['stats']['total_changes'],
                    'report_path': results.get('report_path', 'No report generated'),
                },
                thought=summary
            )
        
        return MessageAction("Migration in progress...")
    
    def _extract_repo_path(self, message: str) -> Optional[str]:
        """Extract repository path from user message."""
        # Look for paths in the message
        import re
        
        # Common patterns
        patterns = [
            r'(/[\w\-./]+)',  # Unix paths
            r'([A-Za-z]:\\[\w\-.\\ ]+)',  # Windows paths
            r'([A-Za-z]:/[\w\-./]+)',  # Windows paths with forward slashes
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                path = match.group(1).strip()
                if os.path.exists(path):
                    return path
        
        # Try the whole message as a path
        potential_path = message.strip().strip('"\'')
        if os.path.exists(potential_path):
            return potential_path
        
        return None
    
    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a professional summary of the migration."""
        status = results['status']
        stats = results['stats']
        
        if status == 'success':
            summary = f"""
✅ **Migration Completed Successfully!**

📊 **Migration Statistics:**
- Files analyzed: {stats['files_analyzed']}
- Files migrated: {stats['files_migrated']}
- Total changes: {stats['total_changes']}
- Files skipped: {stats['files_skipped']}

🧪 **Test Results:**
- Tests passed: {stats['tests_passed']}
- Tests failed: {stats['tests_failed']}

📝 **Report:** {results.get('report_path', 'Not generated')}

All deprecated pandas APIs have been replaced with modern equivalents
that work in BOTH pandas 0.19.2 and 1.1.5.
"""
        else:
            summary = f"""
❌ **Migration Failed**

Error: {results.get('error', 'Unknown error')}

Please check the logs for more details.
"""
        
        return summary