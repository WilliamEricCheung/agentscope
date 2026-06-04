# MCP Server Profile

This directory contains a cold-start profiler for the Laplace MCP manifest.

The profiler reads [src/agentscope/mcp/server_config/laplace_mcp_manifest.json](../../src/agentscope/mcp/server_config/laplace_mcp_manifest.json), profiles every `ready_for_prewarm` server, and records these stage timings for each trial:

- `docker_run_ms`: detached `docker run` command duration
- `wait_tcp_ms`: wait time until the published host port accepts TCP connections
- `mcp_handshake_ms`: MCP client handshake time via `list_tools`
- `interface_test_ms`: one low-risk smoke tool call when available
- `total_ms`: end-to-end time from cold start to the final successful stage

The generated Markdown report also separates milestone-style cumulative timings into a dedicated `Milestones` section:

- `tcp_ready_elapsed_ms`: elapsed time from trial start until the TCP port becomes reachable
- `handshake_elapsed_ms`: elapsed time from trial start until the MCP handshake succeeds
- `interface_test_elapsed_ms`: elapsed time from trial start until the smoke call completes

For each server, the profiler runs 10 trials by default and reports average, minimum, and maximum timings. Each server section in `report.md` now includes `Metric Stats`, `Milestones`, and `Trial Results`.

## Files

- [laplace/mcp_server_profile/profile_mcp_servers.py](profile_mcp_servers.py): main profiler
- [laplace/mcp_server_profile/run_profile.sh](run_profile.sh): default one-click runner
- [laplace/mcp_server_profile/runs](runs): timestamped run outputs, each under `yyyyMMdd_hhmmss/`

## Prerequisites

- Docker CLI installed and Docker daemon running
- All manifest images already built or pullable on the local machine
- API-backed servers still require their corresponding API keys and environment variables

The profiler now auto-bootstraps the missing local backend dependencies for these heavy servers by default:

- Neo4j Cypher: starts a local Neo4j container on port 7687 when needed
- Milvus MCP: starts a local Milvus standalone backend on port 19530 when needed

The Milvus backend bootstrap command is declared directly in [src/agentscope/mcp/server_config/laplace_mcp_manifest.json](../../src/agentscope/mcp/server_config/laplace_mcp_manifest.json) under the Milvus MCP entry via `profile_dependencies`, so the MCP server and its local backend dependency are described together.

The Milvus backend now defaults to a dedicated local tag so it is clearly separated from the locally built MCP server image:

```bash
docker tag milvusdb/milvus:v3.0-beta laplace/milvus-backend:official-v3.0-beta
```

- MCP server image: `laplace/mcp-server-milvus:local`
- Backend image: `laplace/milvus-backend:official-v3.0-beta`

Jupyter MCP still expects a reachable Jupyter server if you include it in the profile run.

If your environment cannot pull the default backend images directly, you can override them without editing the script:

```bash
PROFILE_NEO4J_IMAGE=neo4j:5 MILVUS_URI=http://host.docker.internal:19530 \
  bash laplace/mcp_server_profile/run_profile.sh --servers "Neo4j Cypher" "Milvus MCP"
```

## One-Click Execution

From the repository root:

```bash
bash laplace/mcp_server_profile/run_profile.sh
```

This will:

1. profile all manifest servers marked `ready_for_prewarm`
2. auto-start Neo4j and Milvus backends when they are missing locally
3. run 10 cold-start trials per server
4. create a timestamped output directory such as `laplace/mcp_server_profile/runs/20260604_104500/`
5. write raw results to `profile_results.json` in that run directory
6. write the Markdown summary to `report.md` in that run directory, including overview, summary table, per-server stage metrics, milestone timings, and trial-level results

No top-level temporary `json/md` result files are left in `laplace/mcp_server_profile` after the run; outputs are archived in the timestamped run directory instead.

## Common Options

Profile only a subset of servers:

```bash
bash laplace/mcp_server_profile/run_profile.sh --servers "Playwright" "Jupyter MCP"
```

Change the number of trials:

```bash
PROFILE_REPEATS=3 bash laplace/mcp_server_profile/run_profile.sh
```

Customize the output root or run id:

```bash
PROFILE_OUTPUT_ROOT=laplace/mcp_server_profile/runs PROFILE_RUN_ID=20260604_104500 \
  bash laplace/mcp_server_profile/run_profile.sh
```

Tune timeouts:

```bash
PROFILE_TIMEOUT=30 PROFILE_TCP_READY_TIMEOUT=180 PROFILE_STARTUP_INTERVAL=1 \
  bash laplace/mcp_server_profile/run_profile.sh
```

Disable the post-handshake smoke call:

```bash
bash laplace/mcp_server_profile/run_profile.sh --disable-smoke-call
```

Keep the last profiled MCP container for each server:

```bash
bash laplace/mcp_server_profile/run_profile.sh --keep-containers
```

Run the Python entrypoint directly:

```bash
python laplace/mcp_server_profile/profile_mcp_servers.py --help
```

Disable backend bootstrap for debugging:

```bash
bash laplace/mcp_server_profile/run_profile.sh --disable-dependency-bootstrap
```

Keep auto-started backends after profiling:

```bash
bash laplace/mcp_server_profile/run_profile.sh --keep-dependencies
```

## Notes

- The profiler force-removes the target container before every trial to measure cold-start behavior.
- It also removes the container after each trial so results are not polluted by warm state.
- Auto-started Neo4j and Milvus backends are stopped again after profiling unless `--keep-dependencies` is used.
- `run_profile.sh` archives each run under `laplace/mcp_server_profile/runs/yyyyMMdd_hhmmss/`, which keeps the top-level directory clean.
- If no low-risk smoke tool can be inferred for a server, the trial is marked `partial` and the report will note that the smoke stage was skipped.
- The script profiles whatever the current manifest contains. If the manifest has 32 `ready_for_prewarm` entries, all 32 will be included automatically.
