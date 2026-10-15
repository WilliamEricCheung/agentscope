#!/bin/bash

# Start Jupyter Lab for Planning Agent Analysis
# This script should be run from within the nix shell environment

set -e

echo "Starting Jupyter Lab for Multi-round Planning Agent Robustness Analysis..."

# Check if we're in the nix shell
if [[ -z "$IN_NIX_SHELL" ]]; then
    echo "Warning: Not running in Nix shell. Starting nix-shell first..."
    exec nix-shell --run "./start-jupyter.sh"
fi

# Default port and host
PORT=${PORT:-8888}
HOST=${HOST:-localhost}

# Additional Jupyter options
JUPYTER_OPTS="--port=$PORT --ip=$HOST --no-browser"

# Check if user wants to open browser automatically
if [[ "$OPEN_BROWSER" == "true" ]]; then
    JUPYTER_OPTS="--port=$PORT --ip=$HOST"
fi

# Check if user wants to allow remote connections
if [[ "$ALLOW_REMOTE" == "true" ]]; then
    JUPYTER_OPTS="--port=$PORT --ip=0.0.0.0 --no-browser --allow-root"
fi

echo "Launching Jupyter Lab with options: $JUPYTER_OPTS"
echo "Notebook directory: $(pwd)/notebooks"

# Create notebooks directory if it doesn't exist
mkdir -p notebooks

# Start Jupyter Lab
cd notebooks
jupyter lab $JUPYTER_OPTS