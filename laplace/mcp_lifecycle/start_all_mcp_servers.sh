#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST="$REPO_ROOT/src/agentscope/mcp/server_config/laplace_mcp_manifest.json"
START_RETRIES="${START_RETRIES:-3}"

is_container_running() {
  local container_name="$1"
  docker ps --format '{{.Names}}' | grep -Fxq "$container_name"
}

has_published_ports() {
  local container_name="$1"
  local docker_port_output
  local network_ports

  docker_port_output=$(docker port "$container_name" 2>/dev/null || true)
  if [ -n "$docker_port_output" ]; then
    return 0
  fi

  network_ports=$(docker inspect "$container_name" --format '{{json .NetworkSettings.Ports}}' 2>/dev/null || true)
  if [ -n "$network_ports" ] && [ "$network_ports" != "null" ] && [ "$network_ports" != "{}" ]; then
    if echo "$network_ports" | jq -e 'to_entries | any(.value != null and (.value | length) > 0)' >/dev/null 2>&1; then
      return 0
    fi
  fi

  return 1
}

wait_for_published_ports() {
  local container_name="$1"
  local attempts="${2:-5}"
  local attempt

  for attempt in $(seq 1 "$attempts"); do
    if has_published_ports "$container_name"; then
      return 0
    fi
    sleep 1
  done

  return 1
}

print_port_debug_info() {
  local container_name="$1"
  echo "Inspect HostConfig.PortBindings:" >&2
  docker inspect "$container_name" --format '{{json .HostConfig.PortBindings}}' >&2 || true
  echo "Inspect NetworkSettings.Ports:" >&2
  docker inspect "$container_name" --format '{{json .NetworkSettings.Ports}}' >&2 || true
}

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
    if is_container_running "$container"; then
      if has_published_ports "$container"; then
        echo "Container already running for ${name}: ${container}; skipping."
        continue
      fi

      echo "Container running without published ports for ${name}: ${container}; recreating."
      print_port_debug_info "$container"
      docker rm -f "$container" >/dev/null 2>&1 || true
    else
      docker rm -f "$container" >/dev/null 2>&1 || true
      echo "Creating container for ${name}: ${container}"
    fi
  fi

  started=false
  for attempt in $(seq 1 "$START_RETRIES"); do
    echo "Running: $cmd"
    # shellcheck disable=SC2086
    eval $cmd

    if [ -z "$container" ]; then
      started=true
      break
    fi

    if is_container_running "$container" && wait_for_published_ports "$container"; then
      started=true
      break
    fi

    echo "WARN: start attempt ${attempt}/${START_RETRIES} did not expose a usable host port for ${container}." >&2
    print_port_debug_info "$container"
    docker rm -f "$container" >/dev/null 2>&1 || true
  done

  if [ "$started" != true ]; then
    if [ -n "$container" ] && ! is_container_running "$container"; then
      echo "ERROR: container is not running after start: ${container}" >&2
    else
      echo "ERROR: no published host ports for ${container}." >&2
      print_port_debug_info "$container"
    fi
    exit 1
  fi
done
