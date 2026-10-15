{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python39
    pkgs.python39Packages.numpy
    pkgs.python39Packages.scipy
    pkgs.python39Packages.matplotlib
    pkgs.python39Packages.pandas
    pkgs.python39Packages.scikit-learn
    pkgs.python39Packages.jupyter
    pkgs.git
    pkgs.jq
    pkgs.postgresql
  ];
  
  shellHook = ''
    export PYTHONPATH="${pkgs.python39Packages.numpy}/lib/python3.9/site-packages:$PYTHONPATH"
    echo "Research environment activated!"
    echo "Available tools: python, jupyter, git, psql"
  '';
}