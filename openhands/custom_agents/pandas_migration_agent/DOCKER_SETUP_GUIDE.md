# Pandas Migration Agent - Docker/Web App Setup Guide

## Overview

This guide explains how to set up the Pandas Migration Agent for OpenHands when running through Docker or the web app interface (`openhands-app`).

## Setup Methods

### Method 1: Mount Custom Agents Directory (Recommended)

When running the OpenHands Docker container, mount your custom agents directory:

```bash
# Run OpenHands container with custom agents mounted
docker run -it \
  -v /path/to/your/custom_agents:/app/custom_agents \
  -v /path/to/your/workspace:/workspace \
  -p 3000:3000 \
  openhands/openhands:latest
```

Then configure the app to use custom agents:

```bash
# Inside the container or in your conda env
export CUSTOM_AGENTS_PATH="/app/custom_agents"
export CUSTOM_AGENTS_ENABLED=true
```

### Method 2: Add to OpenHands Image

Create a Dockerfile to include the agent:

```dockerfile
FROM openhands/openhands:latest

# Copy custom agent
COPY ./custom_agents/pandas_migration_agent /app/openhands/agenthub/pandas_migration_agent

# Install agent dependencies
RUN cd /app/openhands/agenthub/pandas_migration_agent && \
    pip install pyyaml

# Update agent registry
RUN echo "from openhands.agenthub.pandas_migration_agent import EnhancedPandasMigrationAgent" >> \
    /app/openhands/agenthub/__init__.py
```

### Method 3: Configure Through Environment

For `openhands-app`, set these environment variables:

```bash
# In your conda environment before running openhands-app
export OPENHANDS_CONFIG_FILE="/path/to/custom/config.toml"
export CUSTOM_AGENTS_ENABLED=true
export CUSTOM_AGENTS_PATH="/absolute/path/to/custom_agents"

# Run the app
openhands-app
```

## Configuration File

Create `config.toml` in your OpenHands config directory:

```toml
# OpenHands Configuration for Web App
[app]
mode = "development"
host = "0.0.0.0"
port = 3000

[agents]
# Enable custom agents
custom_agents_enabled = true
custom_agents_path = "/path/to/custom_agents"

# Default agent (optional)
default_agent = "PandasMigrationAgent"

[[agents.custom]]
name = "PandasMigrationAgent"
module_path = "pandas_migration_agent.agent"
class_name = "EnhancedPandasMigrationAgent"
display_name = "Pandas Migration Agent (0.19 → 1.1.5)"
icon = "🐼"
description = "Automated pandas version migration with testing"

# Agent-specific settings
[agents.custom.settings]
conda_environments = { "0.19.2" = "py36-1.1.10", "1.1.5" = "pandas_115_final" }
auto_rollback = true
create_backups = true
```

## Web UI Integration

The agent should appear in the web UI agent selector. To ensure proper integration:

### 1. Agent Discovery

Make sure the agent is discoverable by creating `metadata.json`:

```json
{
  "name": "PandasMigrationAgent",
  "display_name": "Pandas Migration Agent",
  "version": "1.0.0",
  "description": "Automated migration from pandas 0.19.2 to 1.1.5",
  "author": "OpenHands Community",
  "icon": "🐼",
  "tags": ["migration", "pandas", "python"],
  "category": "Development Tools",
  "sample_prompts": [
    "Migrate my repository from pandas 0.19.2 to 1.1.5",
    "Analyze my code for pandas compatibility issues"
  ]
}
```

### 2. Conda Environment Access

Since you're using conda environments, ensure they're accessible:

```bash
# Check if conda is available in the OpenHands environment
conda env list

# If not, you may need to:
# 1. Mount conda installation directory
# 2. Or install conda in the Docker image
# 3. Or modify test_runner.py to use a different method
```

### 3. Workspace Configuration

Configure workspace access in the web UI:

```yaml
# workspace_config.yaml
workspaces:
  default:
    path: "/workspace"
    mount_conda: true
    conda_path: "/opt/conda"
    available_envs:
      - py36-1.1.10
      - pandas_115_final
```

## Troubleshooting Web App Issues

### Agent Not Appearing in UI

1. Check browser console for errors:
   ```javascript
   // In browser console
   console.log(window.AVAILABLE_AGENTS);
   ```

2. Verify agent registration:
   ```bash
   # In the OpenHands environment
   python -c "
   from openhands.controller.agent import Agent
   print('Registered agents:', Agent._registry.keys())
   "
   ```

### Import Errors

If you see import errors in the web UI:

1. Check Python path:
   ```bash
   echo $PYTHONPATH
   # Should include path to custom_agents
   ```

2. Test import manually:
   ```python
   import sys
   sys.path.append('/path/to/custom_agents')
   from pandas_migration_agent.agent import EnhancedPandasMigrationAgent
   ```

### Conda Environment Issues

For conda access in Docker/web app:

```bash
# Option 1: Mount conda from host
docker run -v ~/anaconda3:/opt/conda ...

# Option 2: Modify test_runner.py to use Docker exec
# Instead of 'conda run', use:
# docker exec -it <container> conda run -n <env> <command>

# Option 3: Use virtual environments instead
# Modify test_runner.py to create venvs with specific pandas versions
```

## Quick Start Script

Create this script to set up everything:

```bash
#!/bin/bash
# setup_web_agent.sh

# Get OpenHands app directory
OPENHANDS_DIR=$(python -c "import openhands; print(openhands.__path__[0])")
AGENT_DIR="$OPENHANDS_DIR/agenthub/pandas_migration_agent"

# Create agent directory
mkdir -p "$AGENT_DIR"

# Copy agent files
cp -r ./custom_agents/pandas_migration_agent/* "$AGENT_DIR/"

# Create metadata for UI
cat > "$AGENT_DIR/metadata.json" << 'EOF'
{
  "name": "PandasMigrationAgent",
  "display_name": "Pandas Migration Agent",
  "version": "1.0.0",
  "description": "Automated pandas migration with testing",
  "icon": "🐼"
}
EOF

# Update __init__.py
echo "from .agent import EnhancedPandasMigrationAgent" >> "$AGENT_DIR/__init__.py"

# Register in agenthub
echo "from openhands.agenthub.pandas_migration_agent import EnhancedPandasMigrationAgent" >> \
  "$OPENHANDS_DIR/agenthub/__init__.py"

echo "Agent installed at: $AGENT_DIR"
echo "Restart openhands-app to see the agent"
```

## Using the Agent in Web UI

Once set up:

1. Open the OpenHands web interface
2. Click on the agent selector dropdown
3. Select "Pandas Migration Agent"
4. Enter your migration request, e.g.:
   - "Migrate the repository at /workspace/myproject from pandas 0.19.2 to 1.1.5"
   - "Analyze /workspace/myproject for pandas compatibility issues"

## Alternative: Direct Installation

If you have access to modify the OpenHands installation:

```bash
# Navigate to OpenHands installation
cd /path/to/openhands/installation

# Copy agent to agenthub
cp -r /path/to/custom_agents/pandas_migration_agent openhands/agenthub/

# Install as editable package
cd openhands/agenthub/pandas_migration_agent
pip install -e .

# Restart the web app
```

The agent should now appear in the web UI's agent selector!
    "name": "PandasMigrationAgent",
    "display_name": "Pandas Migration Agent",
    "version": "1.0.0",
    "description": "Automated migration from pandas 0.19.2 to 1.1.5 with backward compatibility",
    "author": "OpenHands Community",
    "tags": ["migration", "pandas", "python", "automation"],
    "icon": "🐼",  # Emoji icon for UI
    "capabilities": [
        "Analyze repository for pandas usage",
        "Identify deprecated features",
        "Apply migration rules automatically",
        "Run tests in both pandas versions",
        "Generate comprehensive reports"
    ],
    "requirements": [
        "Conda environments: py36-1.1.10 (pandas 0.19.2), pandas_115_final (pandas 1.1.5)",
        "Python 3.6+ in target repository"
    ],
    "sample_prompts": [
        "Migrate my repository from pandas 0.19.2 to 1.1.5",
        "Analyze my code for pandas compatibility issues",
        "Run migration with test validation",
        "Generate a migration report for my project"
    ]
}

# Web UI configuration
WEB_UI_CONFIG = {
    "show_in_agent_list": True,
    "category": "Development Tools",
    "priority": 10,  # Higher number = higher in list
    "beta": False,
    "requires_auth": False,
    "max_iterations": 100,
    "default_max_budget": 10.0
}