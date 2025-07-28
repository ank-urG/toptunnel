import os
import sys
from collections import deque
from typing import TYPE_CHECKING, List, Dict, Any, Optional

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam
    from openhands.events.action import Action
    from openhands.llm.llm import ModelResponse

from openhands.agenthub.codeact_agent import codeact_function_calling
from openhands.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
from openhands.agenthub.codeact_agent.tools.finish import FinishTool
from openhands.agenthub.codeact_agent.tools.str_replace_editor import create_str_replace_editor_tool
from openhands.agenthub.codeact_agent.tools.think import ThinkTool
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message
from openhands.events.action import AgentFinishAction, MessageAction
from openhands.events.event import Event
from openhands.llm.llm import LLM
from openhands.llm.llm_utils import check_tools
from openhands.memory.condenser import Condenser
from openhands.memory.condenser.condenser import Condensation, View
from openhands.memory.conversation_memory import ConversationMemory
from openhands.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from openhands.utils.prompt import PromptManager

# Import custom tools for pandas migration
from .tools.runtime_switch import RuntimeSwitchTool, TestRunnerTool
from .tools.migration_analyzer import MigrationAnalyzerTool
from .tools.code_transformer import CodeTransformerTool
from .tools.aqr_library_checker import AqrLibraryCheckerTool
from .tools.iterative_test_runner import IterativeTestRunnerTool, SingleTestRunnerTool


class PandasMigrationAgent(Agent):
    VERSION = '1.0'
    """
    A specialized agent for migrating pandas code from version 0.19.2 to 1.1.5 with backward compatibility.
    
    This agent handles:
    - Automated detection of pandas API changes
    - Code transformation with backward compatibility preservation
    - Runtime switching between pandas versions for testing
    - Integration with AQR internal libraries
    - Unit test verification in both environments
    """
    
    sandbox_plugins: list[PluginRequirement] = [
        AgentSkillsRequirement(),
        JupyterRequirement(),
    ]
    
    def __init__(
        self,
        llm: LLM,
        config: AgentConfig,
    ) -> None:
        """Initializes a new instance of the PandasMigrationAgent class.
        
        Parameters:
        - llm (LLM): The llm to be used by this agent
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(llm, config)
        self.pending_actions: deque['Action'] = deque()
        self.reset()
        self.tools = self._get_tools()
        
        # Pandas runtime configurations
        self.pandas_115_runtime = "pandas_115_final"
        self.pandas_019_runtime = "py36-1.1.10"
        self.aqr_workspace_path = "C:\\Workspace"
        
        # Track migration state
        self.migration_state = {
            'current_runtime': None,
            'files_processed': [],
            'test_results': {},
            'backward_compatible_changes': [],
            'failed_tests': []
        }
        
        # Create a ConversationMemory instance
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)
        
        self.condenser = Condenser.from_config(self.config.condenser)
        logger.debug(f'Using condenser: {type(self.condenser)}')
    
    @property
    def prompt_manager(self) -> PromptManager:
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager(
                prompt_dir=os.path.join(os.path.dirname(__file__), 'prompts'),
                system_prompt_filename='system_prompt.j2',
            )
        
        return self._prompt_manager
    
    def _get_tools(self) -> list['ChatCompletionToolParam']:
        """Get the tools available to the pandas migration agent."""
        tools = []
        
        # Basic tools
        tools.append(create_cmd_run_tool(use_short_description=False))
        tools.append(ThinkTool)
        tools.append(FinishTool)
        tools.append(create_str_replace_editor_tool(use_short_description=False))
        
        # Custom migration tools
        tools.append(RuntimeSwitchTool)
        tools.append(TestRunnerTool)
        tools.append(MigrationAnalyzerTool)
        tools.append(CodeTransformerTool)
        tools.append(AqrLibraryCheckerTool)
        tools.append(IterativeTestRunnerTool)
        tools.append(SingleTestRunnerTool)
        
        return tools
    
    def reset(self) -> None:
        """Resets the PandasMigrationAgent's internal state."""
        super().reset()
        self.pending_actions.clear()
        self.migration_state = {
            'current_runtime': None,
            'files_processed': [],
            'test_results': {},
            'backward_compatible_changes': [],
            'failed_tests': []
        }
    
    def step(self, state: State) -> 'Action':
        """Performs one step using the Pandas Migration Agent.
        
        This includes:
        - Analyzing code for pandas API changes
        - Switching between runtime environments
        - Running tests in both environments
        - Applying backward-compatible transformations
        
        Parameters:
        - state (State): used to get updated info
        
        Returns:
        - Action: The next action to take
        """
        # Continue with pending actions if any
        if self.pending_actions:
            return self.pending_actions.popleft()
        
        # Check for exit command
        latest_user_message = state.get_last_user_message()
        if latest_user_message and latest_user_message.content.strip() == '/exit':
            return AgentFinishAction()
        
        # Condense the events from the state
        condensed_history: list[Event] = []
        match self.condenser.condensed_history(state):
            case View(events=events):
                condensed_history = events
            
            case Condensation(action=condensation_action):
                return condensation_action
        
        logger.debug(
            f'Processing {len(condensed_history)} events from a total of {len(state.history)} events'
        )
        
        initial_user_message = self._get_initial_user_message(state.history)
        messages = self._get_messages(condensed_history, initial_user_message)
        
        # Add migration context to messages
        self._add_migration_context(messages)
        
        params: dict = {
            'messages': self.llm.format_messages_for_llm(messages),
        }
        params['tools'] = check_tools(self.tools, self.llm.config)
        params['extra_body'] = {'metadata': state.to_llm_metadata(agent_name=self.name)}
        
        response = self.llm.completion(**params)
        logger.debug(f'Response from LLM: {response}')
        
        actions = self.response_to_actions(response)
        logger.debug(f'Actions after response_to_actions: {actions}')
        
        for action in actions:
            self.pending_actions.append(action)
        
        return self.pending_actions.popleft()
    
    def _get_initial_user_message(self, history: list[Event]) -> MessageAction:
        """Finds the initial user message action from the full history."""
        initial_user_message: MessageAction | None = None
        for event in history:
            if isinstance(event, MessageAction) and event.source == 'user':
                initial_user_message = event
                break
        
        if initial_user_message is None:
            logger.error(
                f'CRITICAL: Could not find the initial user MessageAction in the full {len(history)} events history.'
            )
            raise ValueError(
                'Initial user message not found in history. Please report this issue.'
            )
        return initial_user_message
    
    def _get_messages(
        self, events: list[Event], initial_user_message: MessageAction
    ) -> list[Message]:
        """Constructs the message history for the LLM conversation."""
        if not self.prompt_manager:
            raise Exception('Prompt Manager not instantiated.')
        
        # Use ConversationMemory to process events
        messages = self.conversation_memory.process_events(
            condensed_history=events,
            initial_user_action=initial_user_message,
            max_message_chars=self.llm.config.max_message_chars,
            vision_is_active=self.llm.vision_is_active(),
        )
        
        if self.llm.is_caching_prompt_active():
            self.conversation_memory.apply_prompt_caching(messages)
        
        return messages
    
    def _add_migration_context(self, messages: list[Message]) -> None:
        """Add migration-specific context to the messages."""
        context_message = Message(
            role='system',
            content=f"""
Current Migration State:
- Active Runtime: {self.migration_state['current_runtime'] or 'None'}
- Files Processed: {len(self.migration_state['files_processed'])}
- Failed Tests: {len(self.migration_state['failed_tests'])}
- Backward Compatible Changes Applied: {len(self.migration_state['backward_compatible_changes'])}

Runtime Environments:
- pandas 1.1.5: {self.pandas_115_runtime}
- pandas 0.19.2: {self.pandas_019_runtime}
- AQR Workspace: {self.aqr_workspace_path}
"""
        )
        messages.append(context_message)
    
    def response_to_actions(self, response: 'ModelResponse') -> list['Action']:
        return codeact_function_calling.response_to_actions(
            response,
            mcp_tool_names=list(self.mcp_tools.keys()),
        )
    
    def run_tests_with_fix_workflow(
        self,
        test_files: List[str],
        environment: str,
        working_directory: str = "."
    ) -> Dict[str, Any]:
        """Run tests with iterative fix workflow
        
        This method implements the test-fix-rerun workflow:
        1. Run tests one by one
        2. Stop on first failure
        3. Attempt to fix the failing test
        4. Re-run the fixed test
        5. Continue to next test only after current passes
        """
        from .utils.test_utils import (
            find_test_config_file,
            build_pytest_command,
            run_test_with_retry,
            parse_test_output
        )
        
        results = {
            "total_tests": len(test_files),
            "passed": 0,
            "failed": 0,
            "fixed": 0,
            "stopped_at": None,
            "test_results": {}
        }
        
        # Find config file once
        config_file = find_test_config_file(working_directory)
        if config_file:
            logger.info(f"Found test config file: {config_file}")
        
        for test_file in test_files:
            logger.info(f"Running test: {test_file}")
            
            # Build pytest command with config
            test_command = build_pytest_command(test_file, config_file)
            
            # Run test with retry and fix attempts
            test_result = run_test_with_retry(
                test_file,
                environment,
                working_directory,
                max_retries=3,
                fix_callback=lambda info: self._attempt_test_fix(info)
            )
            
            results["test_results"][test_file] = test_result
            
            if test_result["success"]:
                results["passed"] += 1
                if test_result.get("attempts", 1) > 1:
                    results["fixed"] += 1
                    logger.info(f"Test {test_file} passed after {test_result['attempts']} attempts")
            else:
                results["failed"] += 1
                results["stopped_at"] = test_file
                logger.error(f"Test {test_file} failed after all attempts. Stopping.")
                break
        
        return results
    
    def _attempt_test_fix(self, fix_info: Dict[str, Any]) -> bool:
        """Attempt to fix a failing test
        
        Args:
            fix_info: Information about the failing test
        
        Returns:
            True if a fix was applied, False otherwise
        """
        test_name = fix_info["test_name"]
        error = fix_info["error"]
        attempt = fix_info["attempt"]
        
        logger.info(f"Attempting to fix {test_name} (attempt {attempt})")
        
        # Analyze the error to determine fix strategy
        if "AttributeError" in error and ".valid()" in error:
            # Fix .valid() -> .dropna()
            return self._fix_valid_method_error(test_name)
        elif "ImportError" in error and "Panel" in error:
            # Fix Panel import
            return self._fix_panel_import_error(test_name)
        elif "AttributeError" in error and "TimeGrouper" in error:
            # Fix TimeGrouper
            return self._fix_timegrouper_error(test_name)
        elif "OutOfBoundsDatetime" in error:
            # Fix timestamp overflow
            return self._fix_timestamp_overflow_error(test_name)
        
        # Generic fix attempt based on migration rules
        return self._apply_generic_migration_fix(test_name, error)
    
    def _fix_valid_method_error(self, test_file: str) -> bool:
        """Fix .valid() method errors"""
        try:
            from .rules import apply_migrations
            from .utils.file_utils import read_file_safely, write_file_safely
            
            content, encoding = read_file_safely(test_file)
            fixed_content, changes = apply_migrations(content, ["valid_method"])
            
            if changes:
                write_file_safely(test_file, fixed_content, encoding)
                logger.info(f"Applied valid() -> dropna() fix to {test_file}")
                return True
        except Exception as e:
            logger.error(f"Failed to fix valid method: {e}")
        
        return False
    
    def _fix_panel_import_error(self, test_file: str) -> bool:
        """Fix Panel import errors"""
        try:
            from .rules import apply_migrations
            from .utils.file_utils import read_file_safely, write_file_safely
            
            content, encoding = read_file_safely(test_file)
            fixed_content, changes = apply_migrations(content, ["panel_migration"])
            
            if changes:
                write_file_safely(test_file, fixed_content, encoding)
                logger.info(f"Applied Panel migration fix to {test_file}")
                return True
        except Exception as e:
            logger.error(f"Failed to fix Panel import: {e}")
        
        return False
    
    def _fix_timegrouper_error(self, test_file: str) -> bool:
        """Fix TimeGrouper errors"""
        try:
            from .rules import apply_migrations
            from .utils.file_utils import read_file_safely, write_file_safely
            
            content, encoding = read_file_safely(test_file)
            fixed_content, changes = apply_migrations(content, ["time_grouper"])
            
            if changes:
                write_file_safely(test_file, fixed_content, encoding)
                logger.info(f"Applied TimeGrouper fix to {test_file}")
                return True
        except Exception as e:
            logger.error(f"Failed to fix TimeGrouper: {e}")
        
        return False
    
    def _fix_timestamp_overflow_error(self, test_file: str) -> bool:
        """Fix timestamp overflow errors"""
        try:
            from .rules import apply_migrations
            from .utils.file_utils import read_file_safely, write_file_safely
            
            content, encoding = read_file_safely(test_file)
            fixed_content, changes = apply_migrations(content, ["out_of_bounds_datetime"])
            
            if changes:
                write_file_safely(test_file, fixed_content, encoding)
                logger.info(f"Applied timestamp overflow fix to {test_file}")
                return True
        except Exception as e:
            logger.error(f"Failed to fix timestamp overflow: {e}")
        
        return False
    
    def _apply_generic_migration_fix(self, test_file: str, error: str) -> bool:
        """Apply generic migration fixes based on error analysis"""
        try:
            from .rules import analyze_code, apply_migrations
            from .utils.file_utils import read_file_safely, write_file_safely
            
            content, encoding = read_file_safely(test_file)
            
            # Analyze code for issues
            analysis = analyze_code(content)
            
            if analysis["rules_triggered"]:
                # Apply all detected fixes
                rule_names = [r["rule"] for r in analysis["rules_triggered"]]
                fixed_content, changes = apply_migrations(content, rule_names)
                
                if changes:
                    write_file_safely(test_file, fixed_content, encoding)
                    logger.info(f"Applied {len(changes)} migration fixes to {test_file}")
                    return True
        except Exception as e:
            logger.error(f"Failed to apply generic fixes: {e}")
        
        return False