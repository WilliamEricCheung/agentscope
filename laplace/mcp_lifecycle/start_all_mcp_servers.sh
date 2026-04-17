#!/bin/bash
set -e

MANIFEST="laplace_mcp_manifest.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed. Please install jq first."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not installed."
  exit 1
fi

jq -c '.servers | to_entries[] | {name: .key, container: .value.server_config.container_name, cmd: .value.docker_run_command}' "$MANIFEST" | while read -r row; do
  name=$(echo "$row" | jq -r '.name')
  container=$(echo "$row" | jq -r '.container')
  cmd=$(echo "$row" | jq -r '.cmd | @sh')

  if [ -n "$container" ]; then
    echo "Recreating container for ${name}: ${container}"
    docker rm -f "$container" >/dev/null 2>&1 || true
  fi

  echo "Running: $cmd"
  # shellcheck disable=SC2086
  eval $cmd

  if [ -n "$container" ]; then
    sleep 1
    if ! docker ps --format '{{.Names}}' | grep -Fxq "$container"; then
      echo "ERROR: container is not running after start: ${container}" >&2
      exit 1
    fi

    if [ -z "$(docker port "$container" 2>/dev/null)" ]; then
      echo "ERROR: no published host ports for ${container}." >&2
      echo "Inspect HostConfig.PortBindings:" >&2
      docker inspect "$container" --format '{{json .HostConfig.PortBindings}}' >&2 || true
      echo "Inspect NetworkSettings.Ports:" >&2
      docker inspect "$container" --format '{{json .NetworkSettings.Ports}}' >&2 || true
      exit 1
    fi
  fi
done
