{ pkgs ? import <nixpkgs> {} }:

let
  # Define custom Python packages that might not be in nixpkgs
  customPythonPackages = pkgs.python311Packages;
  
  # Create a custom Python environment with all required dependencies
  pythonEnv = customPythonPackages.buildPythonPackage {
    pname = "planning-agent-analysis-env";
    version = "1.0.0";
    format = "wheel";
    
    # Since we're using buildPythonPackage just to get the right PYTHONPATH,
    # we'll use propagatedBuildInputs to include all our dependencies
    propagatedBuildInputs = with customPythonPackages; [
      jupyterlab
      notebook
      ipykernel
      numpy
      pandas
      matplotlib
      seaborn
      scipy
      scikit-learn
      plotly
      bokeh
      altair
      jsonschema
      pyyaml
      requests
      statsmodels
      debugpy
      
      # Additional packages for agent analysis
      networkx
      tqdm
      rich
      tabulate
      openpyxl
      xlsxwriter
      
      # For handling various data formats
      h5py
      pyarrow
      fastparquet
      
      # Async and networking
      aiohttp
      websockets
      
      # Testing and validation
      pytest
      hypothesis
    ];
    
    doCheck = false;
    src = ./.;
  };
  
in

pkgs.mkShell {
  name = "jupyter-planning-agent-analysis";
  
  packages = with pkgs; [
    # Jupyter ecosystem
    jupyter
    jupyterlab
    python311
    
    # Core analysis packages
    pythonEnv
    
    # System utilities
    git
    curl
    wget
    tree
    jq
    gnuplot
    
    # For better terminal experience
    bat
    fd
    ripgrep
  ];
  
  # Environment variables and setup
  shellHook = ''
    # Ensure the kernel is properly installed
    ${pkgs.python311}/bin/python -m ipykernel install --user --name=jupyter-planning-agent-analysis --display-name="Python (Planning Agent Analysis)"
    
    # Set up environment variables
    export PYTHONPATH="${pythonEnv}/${pythonEnv.sitePackages}:$PYTHONPATH"
    export MPLBACKEND=Agg
    
    # Create default directories
    mkdir -p notebooks data results configs
    
    # Initialize git if not already done
    if [ ! -d .git ]; then
      git init
      echo "*.ipynb" >> .gitignore
      echo "__pycache__/" >> .gitignore
      echo "*.pyc" >> .gitignore
      echo ".ipynb_checkpoints/" >> .gitignore
    fi
    
    echo "==============================================="
    echo "Jupyter Planning Agent Analysis Environment Ready!"
    echo "==============================================="
    echo "Project structure created:"
    echo "  ├── notebooks/     # Jupyter notebooks"
    echo "  ├── data/          # Input datasets"
    echo "  ├── results/       # Analysis results"
    echo "  └── configs/       # Configuration files"
    echo ""
    echo "Commands:"
    echo "  jupyter lab        # Start Jupyter Lab"
    echo "  jupyter notebook   # Start classic Jupyter Notebook"
    echo "  python             # Python interpreter with all packages"
    echo ""
    echo "Available kernel: 'Python (Planning Agent Analysis)'"
    echo "==============================================="
  '';
}