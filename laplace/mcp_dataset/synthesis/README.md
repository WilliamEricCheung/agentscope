# Synthesis Overview

This directory is now split by contribution boundary instead of keeping all synthesis logic in one flat package.

## Layout

- `prompt2task/`: Contribution 1 pipeline that synthesizes MCP-Bench style tasks and exports single-runner or multi-runner datasets for the router model.
- `context2sdg/`: Contribution 2 pipeline that synthesizes SDG-oriented prompts and execution traces for graph construction, Markov transition estimation, and predictive prewarming.
- top-level `_*.py` modules: shared internal helpers used by both subpackages, such as DashScope access, manifest loading, and generic merge utilities.

## Why This Split

- `prompt2task` is responsible for task synthesis for router-model style training artifacts.
- `context2sdg` is responsible for SDG prompt and trace synthesis.
- `context2sdg` may consume runner-format task files as input data, but it is no longer organized as part of the `task_synthesis.py` workflow and should be treated as a separate pipeline.

## Entrypoints

### Contribution 1

See `prompt2task/README.md` for:

- server validation
- single-server and multi-server task synthesis
- runner-format merging
- whitelist and self-heal workflow

### Contribution 2

See `context2sdg/README.md` for:

- generic SDG prompt generation
- task-conditioned SDG prompt generation
- SDG trace synthesis
- server-level and state-level Markov transition matrix construction
