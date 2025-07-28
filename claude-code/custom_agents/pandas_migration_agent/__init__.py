from .agent import PandasMigrationAgent
from openhands.controller.agent import Agent

# Register the agent with OpenHands
Agent.register('PandasMigrationAgent', PandasMigrationAgent)

__all__ = ['PandasMigrationAgent']