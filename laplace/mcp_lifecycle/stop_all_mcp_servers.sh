#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST="$REPO_ROOT/src/agentscope/mcp/server_config/laplace_mcp_manifest.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed. Please install jq first."
  exit 1
fi

jq -r '.servers[].server_config.container_name' "$MANIFEST" | while read -r cname; do
  if [ -n "$cname" ]; then
    echo "Stopping: $cname"
    docker stop "$cname" || true
  fi
done
