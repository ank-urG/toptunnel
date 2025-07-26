"""Pandas Migration Agent for OpenHands.

This agent automates the migration of codebases from pandas 0.19.2 to 1.1.5,
handling deprecated features and ensuring backward compatibility.
"""

from .agent import EnhancedPandasMigrationAgent

__all__ = ['EnhancedPandasMigrationAgent']