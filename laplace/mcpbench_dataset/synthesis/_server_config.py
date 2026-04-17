"""Utilities for loading MCP-Bench-style local MCP server configs."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(slots=True)
class ServerConfig:
    """Normalized local MCP server configuration.

    Args:
        name (`str`):
            Human-readable server name.
        command (`str`):
            Executable used to start the server.
        args (`list[str]`):
            Command line arguments for the executable.
        env (`dict[str, str]`):
            Environment variables injected into the spawned server process.
        cwd (`str | None`):
            Working directory used to launch the server process.
        transport (`str`, optional):
            MCP transport type. Supported values are `stdio`, `streamable_http`
            and `sse`.
        port (`int | None`, optional):
            HTTP port when the transport is HTTP-based.
        endpoint (`str`, optional):
            HTTP endpoint path when the transport is HTTP-based.
        pre_warmed (`bool`, optional):
            Whether the server is already running (e.g. a pre-started
            Docker container).  When ``True``, tool discovery will skip
            the process-spawn step and connect directly.
    """

    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    cwd: str | None
    transport: str = "stdio"
    port: int | None = None
    endpoint: str = "/mcp"
    pre_warmed: bool = False


class MCPBenchCommandSource:
    """Load MCP-Bench server commands and related synthesis config.

    Args:
        commands_json_path (`str | None`, optional):
            Explicit path to MCP server command definitions.
        api_key_path (`str | None`, optional):
            Explicit path to the API key file.
        problematic_tools_path (`str | None`, optional):
            Explicit path to the MCP-Bench benchmark config file.
    """

    def __init__(
        self,
        commands_json_path: str | None = None,
        api_key_path: str | None = None,
        problematic_tools_path: str | None = None,
    ) -> None:
        """Initialize the command source.

        Args:
            commands_json_path (`str | None`, optional):
                Explicit path to MCP server command definitions.
            api_key_path (`str | None`, optional):
                Explicit path to the API key file.
            problematic_tools_path (`str | None`, optional):
                Explicit path to the MCP-Bench benchmark config file.
        """
        self.commands_json_path = Path(commands_json_path) if commands_json_path else self._resolve_default_commands_json()
        self.api_key_path = Path(api_key_path) if api_key_path else self._resolve_default_api_key_path()
        self.problematic_tools_path = (
            Path(problematic_tools_path)
            if problematic_tools_path
            else self._resolve_default_problematic_tools_path()
        )
        self.api_keys = self._load_api_keys()

    def load_server_configs(self) -> list[ServerConfig]:
        """Load all local MCP server configs from commands.json.

        Returns:
            `list[ServerConfig]`:
                All available normalized server configs.
        """
        with self.commands_json_path.open("r", encoding="utf-8") as file:
            raw_configs = json.load(file)

        configs: list[ServerConfig] = []
        for server_name, payload in raw_configs.items():
            command_tokens = self._parse_command_string(str(payload.get("cmd", "")).strip())
            if not command_tokens:
                continue

            required_envs = [str(item) for item in payload.get("env", [])]
            resolved_env = self._resolve_env(required_envs)
            cwd = self._resolve_cwd(payload.get("cwd"))
            transport = self._normalize_transport(str(payload.get("transport", "stdio")))
            port = payload.get("port")
            endpoint = str(payload.get("endpoint", "/mcp"))

            configs.append(
                ServerConfig(
                    name=server_name,
                    command=command_tokens[0],
                    args=command_tokens[1:],
                    env=resolved_env,
                    cwd=str(cwd) if cwd else None,
                    transport=transport,
                    port=int(port) if port is not None else None,
                    endpoint=endpoint,
                ),
            )

        return configs

    def load_server_names(self) -> list[str]:
        """Load all available server names.

        Returns:
            `list[str]`:
                Server names from commands.json.
        """
        return [config.name for config in self.load_server_configs()]

    def load_problematic_tools(self) -> list[str]:
        """Load MCP-Bench problematic tool names from benchmark config.

        Returns:
            `list[str]`:
                Known problematic tool names.
        """
        if not self.problematic_tools_path.exists():
            return []

        lines = self.problematic_tools_path.read_text(encoding="utf-8").splitlines()
        collected: list[str] = []
        in_block = False
        block_indent = 0

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue

            current_indent = len(raw_line) - len(raw_line.lstrip(" "))
            if stripped.startswith("problematic_tools:"):
                in_block = True
                block_indent = current_indent
                continue

            if not in_block:
                continue

            if current_indent <= block_indent and not stripped.startswith("-"):
                break

            if stripped.startswith("-"):
                value = stripped[1:].strip().strip('"').strip("'")
                if value:
                    collected.append(value)

        return collected

    def _resolve_default_commands_json(self) -> Path:
        """Resolve the default commands.json path.

        Returns:
            `Path`:
                Resolved commands file path.

        Raises:
            `FileNotFoundError`:
                Raised when no default commands.json can be located.
        """
        candidates = self._default_candidates("mcp_servers/commands.json")
        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError("Unable to locate MCP-Bench commands.json.")

    def _resolve_default_api_key_path(self) -> Path:
        """Resolve the default api_key path.

        Returns:
            `Path`:
                Resolved API key file path.
        """
        candidates = self._default_candidates("mcp_servers/api_key")
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    def _resolve_default_problematic_tools_path(self) -> Path:
        """Resolve the default benchmark config path.

        Returns:
            `Path`:
                Resolved benchmark config file path.
        """
        candidates = self._default_candidates("config/benchmark_config.yaml")
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[0]

    @staticmethod
    def _parse_command_string(command: str) -> list[str]:
        """Split one shell command string into tokens.

        Args:
            command (`str`):
                Original command string from commands.json.

        Returns:
            `list[str]`:
                Parsed command tokens.
        """
        if not command:
            return []
        return shlex.split(command, posix=False if os.name == "nt" else True)

    def _resolve_env(self, required_envs: list[str]) -> dict[str, str]:
        """Resolve required environment variables.

        Args:
            required_envs (`list[str]`):
                Environment variable names required by one server.

        Returns:
            `dict[str, str]`:
                Resolved environment variable mapping.
        """
        resolved: dict[str, str] = {}
        for env_name in required_envs:
            if env_name in os.environ:
                resolved[env_name] = os.environ[env_name]
            elif env_name in self.api_keys:
                resolved[env_name] = self.api_keys[env_name]
        return resolved

    def _resolve_cwd(self, raw_cwd: Any) -> Path | None:
        """Resolve one configured working directory.

        Args:
            raw_cwd (`Any`):
                Raw cwd field from commands.json.

        Returns:
            `Path | None`:
                Absolute working directory, or `None` if not configured.
        """
        if raw_cwd in [None, "", False]:
            return None

        cwd_path = Path(str(raw_cwd))
        if cwd_path.is_absolute():
            return cwd_path

        return (self.commands_json_path.parent / cwd_path).resolve()

    def _load_api_keys(self) -> dict[str, str]:
        """Load API keys from the optional key file.

        Returns:
            `dict[str, str]`:
                Parsed API key mapping.
        """
        if not self.api_key_path.exists():
            return {}

        parsed: dict[str, str] = {}
        for line in self.api_key_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", maxsplit=1)
            parsed[key.strip()] = value.strip()
        return parsed

    @staticmethod
    def _normalize_transport(transport: str) -> str:
        """Normalize transport names from MCP-Bench config.

        Args:
            transport (`str`):
                Raw transport string.

        Returns:
            `str`:
                Normalized transport value.
        """
        normalized = transport.strip().lower()
        if normalized in {"http", "streamable_http", "streamable-http"}:
            return "streamable_http"
        if normalized == "sse":
            return "sse"
        return "stdio"

    @staticmethod
    def _default_candidates(relative_path: str) -> list[Path]:
        """Build default path candidates shared by all config files.

        Args:
            relative_path (`str`):
                Relative path below the MCP-Bench repository root.

        Returns:
            `list[Path]`:
                Candidate paths ordered by preference.
        """
        repo_root = Path(__file__).resolve().parents[3]
        sibling_mcp_bench = repo_root.parent / "mcp-bench"
        local_bundle = repo_root / "laplace" / "mcpbench_dataset"
        return [
            local_bundle / relative_path,
            sibling_mcp_bench / relative_path,
        ]


class LaplaceMCPManifestSource:
    """Load server configs from the Laplace MCP manifest for synthesis.

    Each server entry is represented as a :class:`ServerConfig` backed by a
    foreground ``docker run`` command.  The ``-d`` (detached) flag is
    intentionally omitted so that the spawned process stays alive while the
    container is running, making it possible to detect container failures via
    ``process.poll()`` and to stop it cleanly via ``process.terminate()``.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to ``laplace_mcp_manifest.json``.  When omitted
            the default path
            ``<repo_root>/laplace/mcp_lifecycle/laplace_mcp_manifest.json``
            is used.
    """

    def __init__(self, manifest_path: str | None = None) -> None:
        """Initialize the manifest source.

        Args:
            manifest_path (`str | None`, optional):
                Explicit path to ``laplace_mcp_manifest.json``.
        """
        self.manifest_path = (
            Path(manifest_path)
            if manifest_path is not None
            else self._resolve_default_manifest_path()
        )
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"Laplace MCP manifest not found: {self.manifest_path}",
            )

    # ------------------------------------------------------------------
    # Public interface mirroring MCPBenchCommandSource
    # ------------------------------------------------------------------

    def load_server_configs(self) -> list[ServerConfig]:
        """Load all server configs from the manifest.

        Returns:
            `list[ServerConfig]`:
                One :class:`ServerConfig` per manifest entry, ordered by
                server name.
        """
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        configs: list[ServerConfig] = []
        for server_name, payload in manifest.get("servers", {}).items():
            if not bool(payload.get("ready_for_prewarm", False)):
                continue
            server_config_block = payload.get("server_config", {})
            raw_url = str(server_config_block.get("url", ""))
            resolved_url = _resolve_env_placeholders(raw_url)
            parsed = urlparse(resolved_url)
            port = parsed.port
            endpoint = parsed.path or "/mcp"
            transport = str(server_config_block.get("transport", "streamable_http"))

            raw_docker_cmd = [
                _resolve_env_placeholders(str(t))
                for t in payload.get("docker_run_command", [])
            ]
            docker_args = self._build_foreground_docker_args(raw_docker_cmd)

            # Set pre_warmed=True to skip container management (assume all servers are pre-started)
            configs.append(
                ServerConfig(
                    name=server_name,
                    command="docker",
                    args=docker_args,
                    env={},
                    cwd=None,
                    transport=transport,
                    port=port,
                    endpoint=endpoint,
                    pre_warmed=True,  # pre-warmed mode: do not spawn/stop containers, only send HTTP requests
                ),
            )
        return configs

    def load_server_names(self) -> list[str]:
        """Return all server names from the manifest.

        Returns:
            `list[str]`:
                Server names.
        """
        return [config.name for config in self.load_server_configs()]

    def load_problematic_tools(self) -> list[str]:
        """Return known problematic tool names.

        The Laplace manifest does not carry a problematic-tools list, so
        an empty list is returned.  Override or subclass to add filtering.

        Returns:
            `list[str]`:
                Empty list.
        """
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_foreground_docker_args(raw_command: list[Any]) -> list[str]:
        """Convert a manifest docker_run_command into foreground-mode args.

        Strips the leading ``docker`` token and removes the ``-d`` flag so
        that the spawned ``docker run`` process stays in the foreground.

        Args:
            raw_command (`list[Any]`):
                Full docker run command from the manifest, e.g.
                ``["docker", "run", "-d", "--rm", ...]``.

        Returns:
            `list[str]`:
                Argument list starting with ``run`` (without ``-d``).
        """
        tokens = [str(t) for t in raw_command]
        # Strip leading "docker" token if present
        if tokens and tokens[0] == "docker":
            tokens = tokens[1:]
        # Remove detach flag so the process stays alive in the foreground
        tokens = [t for t in tokens if t != "-d"]
        return tokens

    @staticmethod
    def _resolve_default_manifest_path() -> Path:
        """Resolve the default Laplace manifest path.

        Returns:
            `Path`:
                Path to ``laplace_mcp_manifest.json`` inside the
                agentscope repository.
        """
        # synthesis/_server_config.py is 4 levels below repo root
        repo_root = Path(__file__).resolve().parents[3]
        return (
            repo_root
            / "laplace"
            / "mcp_lifecycle"
            / "laplace_mcp_manifest.json"
        )


def _resolve_env_placeholders(value: str) -> str:
    """Resolve ``${VAR}`` and ``${VAR:-default}`` placeholders via env.

    Args:
        value (`str`):
            String that may contain shell-style variable placeholders.

    Returns:
        `str`:
            String with all placeholders substituted from the process
            environment (falling back to the ``:-default`` when defined).
    """
    output = value
    while "${" in output and "}" in output:
        start = output.index("${")
        end = output.index("}", start)
        token = output[start + 2 : end]
        if ":-" in token:
            key, default = token.split(":-", maxsplit=1)
            replacement = os.getenv(key, default)
        else:
            replacement = os.getenv(token, "")
        output = output[:start] + replacement + output[end + 1 :]
    return output