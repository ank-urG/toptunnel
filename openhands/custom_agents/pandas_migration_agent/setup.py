"""Setup script for Pandas Migration Agent."""

from setuptools import setup, find_packages

setup(
    name="pandas-migration-agent",
    version="1.0.0",
    description="Automated agent for migrating pandas from 0.19.2 to 1.1.5",
    author="OpenHands Community",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'pandas_migration_agent': [
            'config.yaml',
            'config.json',
            'prompts/*.md',
            'tools/*.py',
        ],
    },
    install_requires=[
        # Note: OpenHands should already be installed
        # These are additional requirements
        'pyyaml',
    ],
    python_requires='>=3.8',
    entry_points={
        'openhands.agents': [
            'PandasMigrationAgent = pandas_migration_agent.agent:EnhancedPandasMigrationAgent',
        ],
    },
)