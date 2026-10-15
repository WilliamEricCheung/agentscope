#!/bin/bash

# Make the script executable
chmod +x start-jupyter.sh

echo "Setup complete! To use this environment:"

echo ""
echo "Option 1: Enter the Nix shell and start Jupyter manually"
echo "  nix-shell"
echo "  jupyter lab"
echo ""

echo "Option 2: Use the startup script"
echo "  ./start-jupyter.sh"
echo ""

echo "Option 3: Start with custom options"
echo "  PORT=9999 ./start-jupyter.sh          # Use different port"
echo "  OPEN_BROWSER=true ./start-jupyter.sh  # Open browser automatically"
echo "  ALLOW_REMOTE=true ./start-jupyter.sh  # Allow remote connections"
echo ""

echo "The environment includes:"
echo "- Jupyter Lab and Notebook"
echo "- Python 3.11 with scientific computing stack"
echo "- Data analysis libraries (pandas, numpy, scipy)"
echo "- Visualization tools (matplotlib, seaborn, plotly, bokeh)"
echo "- Machine learning libraries (scikit-learn)"
echo "- Network analysis (networkx)"
echo "- Development tools (pytest, black, flake8)"
echo "- Async networking support (aiohttp, websockets)"
echo ""

echo "Project structure:"
echo "notebooks/ - Place your Jupyter notebooks here"
echo "data/      - Store input datasets here"  
echo "results/   - Save analysis results here"
echo "configs/   - Keep configuration files here"