#!/bin/bash
set -e

MANIFEST="laplace_mcp_manifest.json"

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
