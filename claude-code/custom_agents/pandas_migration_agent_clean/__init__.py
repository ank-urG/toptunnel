"""Pandas Migration Agent - Clean, Professional Implementation.

Migrates pandas 0.19.2 to 1.1.5 with DIRECT replacements only.
NO compatibility wrappers, NO monkey-patching, NO bullshit.
"""

from .core.agent import PandasMigrationAgent

__version__ = "2.0.0"
__all__ = ["PandasMigrationAgent"]