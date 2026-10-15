#!/usr/bin/env bash

# Build environment script for NixOS Agent Environment
# Supports both local Nix environment and Docker builds

set -euo pipefail

# Default variables
BUILD_TYPE="local"
DOCKER_TAG="latest"
NIX_BUILD_FLAGS="--no-link"

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Build the NixOS Agent Environment for robustness evaluation.

OPTIONS:
    --docker        Build Docker image instead of local environment
    --tag TAG       Docker tag to use (default: latest)
    --dev           Build development version (with extra tools)
    --prod          Build production version (minimal)
    --help          Show this help message

EXAMPLES:
    $0                          # Build local Nix environment
    $0 --docker                 # Build Docker image
    $0 --docker --tag v1.0.0    # Build Docker image with specific tag
    $0 --docker --dev           # Build development Docker image
    $0 --docker --prod          # Build production Docker image
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            BUILD_TYPE="docker"
            shift
            ;;
        --tag)
            DOCKER_TAG="$2"
            shift 2
            ;;
        --dev)
            BUILD_VARIANT="dev"
            shift
            ;;
        --prod)
            BUILD_VARIANT="prod"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if Nix is available
if ! command -v nix &> /dev/null; then
    echo "Error: Nix is not installed or not in PATH"
    echo "Please install Nix from https://nixos.org/nix/"
    exit 1
fi

echo "🚀 Building NixOS Agent Environment..."
echo "Build type: $BUILD_TYPE"
[[ -n "${BUILD_VARIANT:-}" ]] && echo "Variant: $BUILD_VARIANT"
[[ "$BUILD_TYPE" == "docker" ]] && echo "Docker tag: $DOCKER_TAG"

if [[ "$BUILD_TYPE" == "local" ]]; then
    # Build local Nix environment
    echo "Building local Nix environment..."
    nix build $NIX_BUILD_FLAGS
    
    echo "✅ Local environment built successfully!"
    echo "Use 'nix develop' to enter the development shell"
    
elif [[ "$BUILD_TYPE" == "docker" ]]; then
    # Build Docker image
    echo "Building Docker image..."
    
    if [[ -n "${BUILD_VARIANT:-}" ]]; then
        if [[ "$BUILD_VARIANT" == "dev" ]]; then
            nix build .#docker-dev-image $NIX_BUILD_FLAGS
        elif [[ "$BUILD_VARIANT" == "prod" ]]; then
            nix build .#docker-image $NIX_BUILD_FLAGS
        fi
    else
        # Default to production image
        nix build .#docker-image $NIX_BUILD_FLAGS
    fi
    
    # Load the image into Docker
    echo "Loading image into Docker..."
    docker load < result
    
    # Tag the image appropriately
    IMAGE_ID=$(docker images -q | head -n 1)
    if [[ -n "$IMAGE_ID" ]]; then
        if [[ -n "${BUILD_VARIANT:-}" ]]; then
            if [[ "$BUILD_VARIANT" == "dev" ]]; then
                docker tag "$IMAGE_ID" "nixos-agent-env-dev:$DOCKER_TAG"
            else
                docker tag "$IMAGE_ID" "nixos-agent-env:$DOCKER_TAG"
            fi
        else
            docker tag "$IMAGE_ID" "nixos-agent-env:$DOCKER_TAG"
        fi
        
        echo "✅ Docker image built successfully!"
        echo "Image: nixos-agent-env${BUILD_VARIANT:+-$BUILD_VARIANT}:$DOCKER_TAG"
        echo "Run with: docker run -it nixos-agent-env${BUILD_VARIANT:+-$BUILD_VARIANT}:$DOCKER_TAG"
    else
        echo "❌ Failed to build Docker image"
        exit 1
    fi
fi

echo "🎉 Build completed successfully!"