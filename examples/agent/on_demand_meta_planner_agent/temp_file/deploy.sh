#!/usr/bin/env bash

# Deployment script for NixOS Agent Environment
# Handles deployment to different target environments

set -euo pipefail

# Default variables
DEPLOY_TARGET="local"
DEPLOY_ENVIRONMENT="production"
DOCKER_COMPOSE_FILE="docker-compose.yml"
K8S_MANIFEST_DIR="k8s"
HELM_CHART_DIR="helm"

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy the NixOS Agent Environment to various targets.

OPTIONS:
    --target TARGET     Deployment target (local|docker|kubernetes|cloud) [default: local]
    --env ENV           Deployment environment (development|staging|production) [default: production]
    --compose FILE      Docker Compose file path [default: docker-compose.yml]
    --k8s-dir DIR       Kubernetes manifest directory [default: k8s]
    --helm-dir DIR      Helm chart directory [default: helm]
    --dry-run           Show what would be deployed without actually deploying
    --help              Show this help message

EXAMPLES:
    $0                          # Deploy locally using Nix
    $0 --target docker          # Deploy using Docker Compose
    $0 --target kubernetes      # Deploy to Kubernetes cluster
    $0 --target docker --env staging  # Deploy staging environment to Docker
    $0 --dry-run --target kubernetes  # Preview Kubernetes deployment
EOF
}

# Parse command line arguments
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            DEPLOY_TARGET="$2"
            shift 2
            ;;
        --env)
            DEPLOY_ENVIRONMENT="$2"
            shift 2
            ;;
        --compose)
            DOCKER_COMPOSE_FILE="$2"
            shift 2
            ;;
        --k8s-dir)
            K8S_MANIFEST_DIR="$2"
            shift 2
            ;;
        --helm-dir)
            HELM_CHART_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
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

# Check if we're in the right directory
if [[ ! -f "flake.nix" ]]; then
    echo "Error: This script must be run from the project root directory"
    echo "Please cd to the nixos-agent-env directory first"
    exit 1
fi

echo "🚀 Deploying NixOS Agent Environment..."
echo "Target: $DEPLOY_TARGET"
echo "Environment: $DEPLOY_ENVIRONMENT"
[[ "$DRY_RUN" == "true" ]] && echo "Dry run: enabled"

# Set environment-specific variables
case $DEPLOY_ENVIRONMENT in
    development)
        IMAGE_TAG="dev"
        REPLICAS=1
        ;;
    staging)
        IMAGE_TAG="staging"
        REPLICAS=2
        ;;
    production)
        IMAGE_TAG="latest"
        REPLICAS=3
        ;;
    *)
        echo "Error: Invalid environment '$DEPLOY_ENVIRONMENT'"
        echo "Valid environments: development, staging, production"
        exit 1
        ;;
esac

# Deployment functions
deploy_local() {
    echo "Deploying to local Nix environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: nix build .#docker-image"
        echo "[DRY RUN] Would execute: nix develop --command agent-runner --env $DEPLOY_ENVIRONMENT"
        return 0
    fi
    
    # Build the environment
    nix build .#docker-image
    
    # Run the agent
    nix develop --command bash -c "agent-runner --env $DEPLOY_ENVIRONMENT"
}

deploy_docker() {
    echo "Deploying to Docker..."
    
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        echo "Error: Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would execute: docker-compose -f $DOCKER_COMPOSE_FILE up -d"
        return 0
    fi
    
    # Build and start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build
    
    echo "Docker services started successfully!"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
}

deploy_kubernetes() {
    echo "Deploying to Kubernetes..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        if command -v kubectl &> /dev/null; then
            echo "[DRY RUN] Would execute: kubectl apply -k $K8S_MANIFEST_DIR --dry-run=server"
        else
            echo "[DRY RUN] Would apply manifests from: $K8S_MANIFEST_DIR"
        fi
        return 0
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        echo "Error: kubectl not found. Please install kubectl to deploy to Kubernetes."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        echo "Error: Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Apply manifests
    kubectl apply -k "$K8S_MANIFEST_DIR"
    
    echo "Kubernetes deployment completed!"
    kubectl get pods -l app=nixos-agent-env
}

deploy_cloud() {
    echo "Deploying to cloud platform..."
    echo "Cloud deployment not yet implemented. Please use docker or kubernetes targets."
    exit 1
}

# Execute deployment based on target
case $DEPLOY_TARGET in
    local)
        deploy_local
        ;;
    docker)
        deploy_docker
        ;;
    kubernetes)
        deploy_kubernetes
        ;;
    cloud)
        deploy_cloud
        ;;
    *)
        echo "Error: Invalid deployment target '$DEPLOY_TARGET'"
        echo "Valid targets: local, docker, kubernetes, cloud"
        exit 1
        ;;
esac

echo "✅ Deployment completed successfully!"
echo "Environment: $DEPLOY_ENVIRONMENT"
echo "Target: $DEPLOY_TARGET"

# Post-deployment checks
if [[ "$DRY_RUN" == "false" ]]; then
    echo ""
    echo "🔍 Post-deployment verification:"
    case $DEPLOY_TARGET in
        local)
            echo "- Local Nix environment is ready"
            echo "- Use 'nix develop' to access the environment"
            ;;
        docker)
            echo "- Docker containers are running"
            echo "- Check logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs"
            ;;
        kubernetes)
            echo "- Kubernetes pods are deployed"
            echo "- Check status with: kubectl get pods -l app=nixos-agent-env"
            ;;
    esac
fi