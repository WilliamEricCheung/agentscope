# Multi-round Planning Agent Robustness Experiment Environment

This Nix flake provides a reproducible environment for conducting multi-round planning agent robustness experiments with all necessary dependencies.

## Features

- **Python 3.11** environment with all required packages
- **Machine Learning Libraries**: PyTorch, TensorFlow with GPU support
- **LLM Tools**: Hugging Face Transformers, LangChain
- **Experiment Management**: Weights & Biases (wandb), MLflow
- **Data Processing**: Pandas, NumPy, Matplotlib, Scikit-learn
- **Development Tools**: Jupyter, IPython, debugging utilities
- **GPU Support**: CUDA and cuDNN integration
- **Full Reproducibility**: Locked dependencies via Nix

## Prerequisites

- Nix package manager (version 2.4 or higher)
- Flakes enabled (add `experimental-features = nix-command flakes` to `/etc/nix/nix.conf`)

## Usage

### Enter Development Shell

```bash
# Clone this repository
git clone <repository-url>
cd planning-agent-robustness

# Enter the development environment
nix develop
```

### Build the Environment Package

```bash
# Build the Python environment package
nix build

# The built environment will be available at ./result
```

### Run Jupyter Notebook

```bash
# Enter development shell first
nix develop

# Start Jupyter with the configured environment
jupyter notebook
```

### Use in NixOS Configuration

If you're using NixOS, you can integrate this flake into your system configuration:

```nix
# In your configuration.nix or home-manager configuration
{
  imports = [ /path/to/this/flake ];
  
  # The environment will be available system-wide
}
```

## GPU Support

The environment includes CUDA and cuDNN libraries. To ensure proper GPU functionality:

1. Make sure you have NVIDIA drivers installed on your system
2. Verify CUDA availability in the environment:
   ```bash
   nix develop
   python -c "import torch; print(torch.cuda.is_available())"
   ```

## Package Versions

All packages are pinned to specific versions through Nixpkgs, ensuring reproducibility across different systems and time periods.

## Customization

To add or modify packages:

1. Edit the `propagatedBuildInputs` list in `flake.nix`
2. Rebuild the environment with `nix develop` or `nix build`

## Troubleshooting

### CUDA Issues

If you encounter CUDA-related errors:

- Ensure your system has compatible NVIDIA drivers
- Verify that your GPU is supported by the CUDA version in Nixpkgs
- You may need to override the CUDA version by modifying the flake

### Memory Issues

Building this environment requires significant memory. If you encounter out-of-memory errors:

- Increase swap space
- Use `--max-jobs 1` flag: `nix develop --max-jobs 1`

## License

MIT License - see LICENSE file for details.