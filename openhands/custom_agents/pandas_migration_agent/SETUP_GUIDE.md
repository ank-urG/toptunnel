# Pandas Migration Agent Setup Guide

## Prerequisites

1. **OpenHands Installation**: Ensure OpenHands is properly installed
2. **Conda Environments**: Verify your conda environments exist:
   ```bash
   conda env list | grep -E "py36-1.1.10|pandas_115_final"
   ```

## Installation Steps

### 1. Copy the Agent to OpenHands Directory

```bash
# Option A: Copy to OpenHands installation
cp -r custom_agents/pandas_migration_agent /path/to/openhands/OpenHands/openhands/agenthub/

# Option B: Keep in custom location (recommended)
# Just note the full path to custom_agents directory
```

### 2. Create or Update config.toml

Create a `config.toml` file in your working directory or OpenHands config directory:

```toml
# Enable custom agents
custom_agents_enabled = true

# If using Option B above, specify the path
custom_agents_path = "/Users/ankurgupta/Learnings/toptunnel/openhands/custom_agents"

# Register the agent
[[agents.custom]]
name = "PandasMigrationAgent"
module_path = "pandas_migration_agent.agent"
class_name = "EnhancedPandasMigrationAgent"
display_name = "Pandas Migration Agent (0.19 → 1.1.5)"
```

### 3. Verify Agent Registration

```bash
# List available agents
openhands --list-agents

# You should see PandasMigrationAgent in the list
```

## Common Errors and Solutions

### Error: "Agent not found"

**Solution 1**: Check config.toml location
```bash
# OpenHands looks for config.toml in these locations:
# 1. Current directory
# 2. ~/.openhands/config.toml
# 3. /etc/openhands/config.toml

# Make sure your config.toml is in one of these locations
```

**Solution 2**: Use absolute paths
```toml
# In config.toml, use absolute path
custom_agents_path = "/absolute/path/to/custom_agents"
```

### Error: "Module not found"

**Solution**: Fix Python path issues
```bash
# Option 1: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/custom_agents"

# Option 2: Install as package
cd custom_agents/pandas_migration_agent
pip install -e .
```

### Error: "Import error"

**Solution**: Check dependencies
```python
# Create a simple test script
cat > test_import.py << EOF
import sys
sys.path.insert(0, '/path/to/custom_agents')
from pandas_migration_agent.agent import EnhancedPandasMigrationAgent
print("Import successful!")
EOF

python test_import.py
```

### Error: "Conda environment not found"

**Solution**: Verify conda environments
```bash
# Check if environments exist
conda env list

# If missing, the agent will fail when trying to run tests
# Update the environment names in the agent config
```

## Quick Setup Script

Create this setup script:

```bash
#!/bin/bash
# setup_pandas_agent.sh

# Set paths
OPENHANDS_DIR="$HOME/.openhands"
CUSTOM_AGENTS_DIR="$(pwd)/custom_agents"

# Create OpenHands config directory
mkdir -p "$OPENHANDS_DIR"

# Create config.toml
cat > "$OPENHANDS_DIR/config.toml" << EOF
# OpenHands Configuration
custom_agents_enabled = true
custom_agents_path = "$CUSTOM_AGENTS_DIR"

[[agents.custom]]
name = "PandasMigrationAgent"
module_path = "pandas_migration_agent.agent"
class_name = "EnhancedPandasMigrationAgent"
display_name = "Pandas Migration Agent (0.19 → 1.1.5)"
EOF

echo "Configuration created at: $OPENHANDS_DIR/config.toml"
echo "Custom agents path: $CUSTOM_AGENTS_DIR"

# Test import
python -c "
import sys
sys.path.insert(0, '$CUSTOM_AGENTS_DIR')
try:
    from pandas_migration_agent.agent import EnhancedPandasMigrationAgent
    print('✓ Agent module can be imported')
except Exception as e:
    print('✗ Import failed:', e)
"

# Check conda environments
echo -e "\nChecking conda environments:"
for env in "py36-1.1.10" "pandas_115_final"; do
    if conda env list | grep -q "$env"; then
        echo "✓ Found: $env"
    else
        echo "✗ Missing: $env"
    fi
done
```

## Running the Agent

Once properly configured:

```bash
# Method 1: Direct command
openhands --agent PandasMigrationAgent

# Method 2: With specific task
openhands --agent PandasMigrationAgent --task "Migrate /workspace/myproject"

# Method 3: With config file
openhands --config ~/.openhands/config.toml --agent PandasMigrationAgent
```

## Debugging

Enable debug logging:
```bash
# Set debug environment variable
export OPENHANDS_DEBUG=1

# Run with verbose output
openhands --agent PandasMigrationAgent --verbose

# Check logs
tail -f ~/.openhands/logs/openhands.log
```

## Alternative: Direct Python Usage

If command line fails, try direct Python:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/custom_agents')

from pandas_migration_agent.agent import EnhancedPandasMigrationAgent
from openhands.core.config import AgentConfig
from openhands.llm.llm import LLM

# Create agent
config = AgentConfig()
llm = LLM(...)  # Configure your LLM
agent = EnhancedPandasMigrationAgent(llm, config)

print("Agent created successfully!")
print(f"Agent version: {agent.VERSION}")
print(f"Available tools: {[tool.name for tool in agent.tools]}")
```

## Need More Help?

If you're still encountering errors:

1. Share the exact error message
2. Check OpenHands version: `openhands --version`
3. Verify Python version: `python --version`
4. Check if OpenHands works with built-in agents: `openhands --agent CodeActAgent`

The agent is designed to be compatible with OpenHands' custom agent system. If you're getting specific errors, please share them and I can provide more targeted solutions.