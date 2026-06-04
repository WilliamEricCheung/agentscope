#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_ROOT="${PROFILE_OUTPUT_ROOT:-$SCRIPT_DIR/runs}"
RUN_ID="${PROFILE_RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
OUTPUT_DIR="$OUTPUT_ROOT/$RUN_ID"

export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src:${PYTHONPATH:-}"

mkdir -p "$OUTPUT_DIR"

python "$SCRIPT_DIR/profile_mcp_servers.py" \
  --manifest-path "$REPO_ROOT/src/agentscope/mcp/server_config/laplace_mcp_manifest.json" \
  --iterations "${PROFILE_REPEATS:-10}" \
  --request-timeout "${PROFILE_TIMEOUT:-30}" \
  --startup-timeout "${PROFILE_TCP_READY_TIMEOUT:-120}" \
  --startup-interval "${PROFILE_STARTUP_INTERVAL:-0.5}" \
  --results-path "$OUTPUT_DIR/profile_results.json" \
  --report-path "$OUTPUT_DIR/report.md" \
  "$@"
