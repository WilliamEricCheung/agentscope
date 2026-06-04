"""Validate Laplace MCP Docker servers before task synthesis.

This CLI verifies whether each pre-warmed MCP server from
``laplace_mcp_manifest.json`` can actually serve MCP requests through the
same client path used by synthesis.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from laplace.util.server_config import (
    LaplaceMCPManifestSource,
    ServerConfig,
)

_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _DockerRuntimeInfo:
    """Runtime status extracted from ``docker ps``.

    Args:
        available (`bool`):
            Whether Docker CLI is callable.
        container_ports (`dict[str, str]`):
            Mapping from container name to its ports column string.
        error (`str | None`, optional):
            Error message when Docker info cannot be queried.
    """

    available: bool
    container_ports: dict[str, str]
    error: str | None = None


@dataclass(slots=True)
class _ServerValidationResult:
    """Validation result for one MCP server.

    Args:
        server_name (`str`):
            Human-readable server name.
        container_name (`str`):
            Container name declared in the manifest.
        url (`str`):
            MCP endpoint URL used for probing.
        transport (`str`):
            MCP transport type.
        container_running (`bool`):
            Whether the named container appears in ``docker ps``.
        port_mapping_ok (`bool`):
            Whether expected host port mapping is visible in ``docker ps``.
        tcp_connect_ok (`bool`):
            Whether TCP connection to ``127.0.0.1:port`` succeeds.
        list_tools_ok (`bool`):
            Whether ``list_tools`` call succeeds.
        tool_count (`int`):
            Number of discovered tools.
        smoke_call_attempted (`bool`):
            Whether an optional tool-call smoke check was attempted.
        smoke_call_ok (`bool | None`):
            Result of smoke check when attempted.
        status (`str`):
            Overall status, one of ``pass``, ``fail``, ``partial``.
        elapsed_ms (`int`):
            End-to-end validation time in milliseconds.
        diagnostics (`dict[str, Any]`):
            Extra diagnostic fields and errors.
    """

    server_name: str
    container_name: str
    url: str
    transport: str
    container_running: bool
    port_mapping_ok: bool
    tcp_connect_ok: bool
    list_tools_ok: bool
    tool_count: int
    smoke_call_attempted: bool
    smoke_call_ok: bool | None
    status: str
    elapsed_ms: int
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert result object to a JSON-serializable dictionary.

        Returns:
            `dict[str, Any]`:
                Dictionary form of the validation result.
        """

        return {
            "server_name": self.server_name,
            "container_name": self.container_name,
            "url": self.url,
            "transport": self.transport,
            "container_running": self.container_running,
            "port_mapping_ok": self.port_mapping_ok,
            "tcp_connect_ok": self.tcp_connect_ok,
            "list_tools_ok": self.list_tools_ok,
            "tool_count": self.tool_count,
            "smoke_call_attempted": self.smoke_call_attempted,
            "smoke_call_ok": self.smoke_call_ok,
            "status": self.status,
            "elapsed_ms": self.elapsed_ms,
            "diagnostics": self.diagnostics,
        }


class MCPServerValidator:
    """Validate all pre-warmed MCP servers from Laplace manifest.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to ``laplace_mcp_manifest.json``.
        request_timeout (`float`, optional):
            Timeout in seconds for TCP and MCP operations.
        concurrency (`int`, optional):
            Maximum number of servers validated concurrently.
        enable_smoke_call (`bool`, optional):
            Whether to perform optional tool-call smoke check.
    """

    def __init__(
        self,
        manifest_path: str | None = None,
        request_timeout: float = 20.0,
        concurrency: int = 8,
        enable_smoke_call: bool = False,
    ) -> None:
        """Initialize validator state.

        Args:
            manifest_path (`str | None`, optional):
                Explicit path to ``laplace_mcp_manifest.json``.
            request_timeout (`float`, optional):
                Timeout in seconds for network and MCP checks.
            concurrency (`int`, optional):
                Maximum concurrent server validations.
            enable_smoke_call (`bool`, optional):
                Whether to run an additional tool-call smoke check.
        """

        self.request_timeout = max(1.0, float(request_timeout))
        self.concurrency = max(1, int(concurrency))
        self.enable_smoke_call = enable_smoke_call

        self.source = LaplaceMCPManifestSource(manifest_path=manifest_path)
        self.server_configs = self.source.load_server_configs()

        manifest = json.loads(self.source.manifest_path.read_text(encoding="utf-8"))
        self._container_names: dict[str, str] = {}
        for server_name, payload in manifest.get("servers", {}).items():
            if not bool(payload.get("ready_for_prewarm", False)):
                continue
            block = payload.get("server_config", {})
            container_name = str(block.get("container_name", "")).strip()
            if container_name:
                self._container_names[server_name] = container_name

    async def validate(
        self,
        target_servers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Validate one or more servers and build a summary report.

        Args:
            target_servers (`list[str] | None`, optional):
                Optional server-name whitelist.

        Returns:
            `dict[str, Any]`:
                Validation report with summary and per-server results.
        """

        selected = self._select_servers(target_servers)
        docker_info = self._read_docker_runtime_info()
        _logger.info("[validate] selected %d server(s)", len(selected))

        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = [
            self._validate_one_server(config, docker_info, semaphore)
            for config in selected
        ]
        results = await asyncio.gather(*tasks)

        passed = sum(1 for item in results if item.status == "pass")
        failed = sum(1 for item in results if item.status == "fail")
        partial = sum(1 for item in results if item.status == "partial")

        report = {
            "summary": {
                "manifest_path": str(self.source.manifest_path),
                "total_servers": len(results),
                "passed": passed,
                "failed": failed,
                "partial": partial,
                "request_timeout": self.request_timeout,
                "concurrency": self.concurrency,
                "enable_smoke_call": self.enable_smoke_call,
                "docker_available": docker_info.available,
                "docker_error": docker_info.error,
            },
            "servers": [item.to_dict() for item in results],
        }
        return report

    def _select_servers(
        self,
        target_servers: list[str] | None,
    ) -> list[ServerConfig]:
        """Filter loaded server configs by optional whitelist.

        Args:
            target_servers (`list[str] | None`):
                Optional server-name whitelist.

        Returns:
            `list[ServerConfig]`:
                Selected server configurations.

        Raises:
            `ValueError`:
                Raised when unknown server names are provided.
        """

        if not target_servers:
            return list(self.server_configs)

        wanted = {name.strip() for name in target_servers if name.strip()}
        known = {config.name for config in self.server_configs}
        unknown = sorted(wanted - known)
        if unknown:
            raise ValueError(f"Unknown server name(s): {', '.join(unknown)}")

        return [config for config in self.server_configs if config.name in wanted]

    async def _validate_one_server(
        self,
        config: ServerConfig,
        docker_info: _DockerRuntimeInfo,
        semaphore: asyncio.Semaphore,
    ) -> _ServerValidationResult:
        """Validate one server with layered checks.

        Args:
            config (`ServerConfig`):
                Normalized server configuration.
            docker_info (`_DockerRuntimeInfo`):
                Runtime docker status snapshot.
            semaphore (`asyncio.Semaphore`):
                Concurrency limiter.

        Returns:
            `_ServerValidationResult`:
                Per-server validation result.
        """

        async with semaphore:
            started = time.perf_counter()
            diagnostics: dict[str, Any] = {}

            container_name = self._container_names.get(config.name, "")
            ports_spec = ""
            container_running = False
            port_mapping_ok = False

            if docker_info.available and container_name:
                ports_spec = docker_info.container_ports.get(container_name, "")
                container_running = bool(ports_spec)
                if config.port is not None:
                    port_mapping_ok = _is_port_mapping_present(ports_spec, config.port)

            if container_name:
                diagnostics["docker_container_name"] = container_name
            if ports_spec:
                diagnostics["docker_ports"] = ports_spec

            tcp_connect_ok = False
            if config.port is not None:
                tcp_connect_ok = await _tcp_probe(
                    host="127.0.0.1",
                    port=config.port,
                    timeout=self.request_timeout,
                )
            else:
                diagnostics["tcp_error"] = "No HTTP port parsed from server URL"

            list_tools_ok = False
            tool_count = 0
            smoke_attempted = False
            smoke_ok: bool | None = None

            url = _build_server_url(config)

            if tcp_connect_ok:
                try:
                    tools = await self._list_tools(config)
                    list_tools_ok = True
                    tool_count = len(tools)

                    if self.enable_smoke_call:
                        smoke_attempted = True
                        smoke_ok, smoke_note = await self._smoke_call(config, tools)
                        if smoke_note:
                            diagnostics["smoke_note"] = smoke_note
                except Exception as exc:  # noqa: BLE001
                    diagnostics["mcp_error"] = f"{type(exc).__name__}: {exc}"
            else:
                diagnostics["mcp_error"] = "Skipped MCP list_tools because TCP probe failed"

            status = _compute_overall_status(
                container_running=container_running,
                port_mapping_ok=port_mapping_ok,
                tcp_connect_ok=tcp_connect_ok,
                list_tools_ok=list_tools_ok,
                smoke_call_required=self.enable_smoke_call,
                smoke_call_ok=smoke_ok,
            )

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            result = _ServerValidationResult(
                server_name=config.name,
                container_name=container_name,
                url=url,
                transport=config.transport,
                container_running=container_running,
                port_mapping_ok=port_mapping_ok,
                tcp_connect_ok=tcp_connect_ok,
                list_tools_ok=list_tools_ok,
                tool_count=tool_count,
                smoke_call_attempted=smoke_attempted,
                smoke_call_ok=smoke_ok,
                status=status,
                elapsed_ms=elapsed_ms,
                diagnostics=diagnostics,
            )

            _logger.info(
                "[validate] %s -> %s (container=%s, port_map=%s, tcp=%s, list_tools=%s, tools=%d)",
                config.name,
                status,
                container_running,
                port_mapping_ok,
                tcp_connect_ok,
                list_tools_ok,
                tool_count,
            )
            return result

    async def _list_tools(self, config: ServerConfig) -> list[Any]:
        """List MCP tools using AgentScope's stateless HTTP client.

        Args:
            config (`ServerConfig`):
                One server configuration.

        Returns:
            `list[Any]`:
                Tool list returned by MCP server.
        """

        from laplace.util.mcp_tool_discovery import (
            HttpStatelessClient,
        )

        transport = "sse" if config.transport == "sse" else "streamable_http"
        client = HttpStatelessClient(
            name=config.name,
            transport=transport,
            url=_build_server_url(config),
            timeout=self.request_timeout,
        )
        return await asyncio.wait_for(
            client.list_tools(),
            timeout=self.request_timeout,
        )

    async def _smoke_call(
        self,
        config: ServerConfig,
        tools: list[Any],
    ) -> tuple[bool, str]:
        """Optionally call one safe tool with generated mock arguments.

        Args:
            config (`ServerConfig`):
                One server configuration.
            tools (`list[Any]`):
                Tool list already discovered from server.

        Returns:
            `tuple[bool, str]`:
                Pair of success flag and diagnostic note.
        """

        tool_specs = [
            {
                "name": getattr(tool, "name", ""),
                "input_schema": getattr(tool, "inputSchema", {}) or {},
            }
            for tool in tools
        ]
        selected, arguments, reason = _pick_smoke_tool_and_args(tool_specs)
        if selected is None:
            return True, f"Smoke call skipped: {reason}"

        from laplace.util.mcp_tool_discovery import (
            HttpStatelessClient,
        )

        transport = "sse" if config.transport == "sse" else "streamable_http"
        client = HttpStatelessClient(
            name=config.name,
            transport=transport,
            url=_build_server_url(config),
            timeout=self.request_timeout,
        )

        fn = await client.get_callable_function(
            func_name=str(selected["name"]),
            wrap_tool_result=True,
            execution_timeout=self.request_timeout,
        )
        await asyncio.wait_for(fn(**arguments), timeout=self.request_timeout)
        return True, f"Smoke tool called: {selected['name']}"

    @staticmethod
    def _read_docker_runtime_info() -> _DockerRuntimeInfo:
        """Read running container names and ports from Docker.

        Returns:
            `_DockerRuntimeInfo`:
                Parsed docker runtime snapshot.
        """

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except FileNotFoundError:
            return _DockerRuntimeInfo(
                available=False,
                container_ports={},
                error="Docker CLI is not available in PATH",
            )
        except Exception as exc:  # noqa: BLE001
            return _DockerRuntimeInfo(
                available=False,
                container_ports={},
                error=f"Failed to query docker ps: {type(exc).__name__}: {exc}",
            )

        if result.returncode != 0:
            return _DockerRuntimeInfo(
                available=False,
                container_ports={},
                error=(result.stderr or result.stdout).strip() or "docker ps failed",
            )

        parsed: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            name, _, ports = line.partition("\t")
            parsed[name.strip()] = ports.strip()

        return _DockerRuntimeInfo(
            available=True,
            container_ports=parsed,
            error=None,
        )


def _build_server_url(config: ServerConfig) -> str:
    """Build the MCP URL from one server configuration.

    Args:
        config (`ServerConfig`):
            One HTTP-based server config.

    Returns:
        `str`:
            Resolved local MCP endpoint URL.
    """

    endpoint = config.endpoint if config.endpoint.startswith("/") else f"/{config.endpoint}"
    return f"http://127.0.0.1:{config.port}{endpoint}"


def _is_port_mapping_present(ports_spec: str, host_port: int) -> bool:
    """Check whether a host port appears in Docker port mappings.

    Args:
        ports_spec (`str`):
            Raw ``docker ps`` ports column.
        host_port (`int`):
            Expected host-side port.

    Returns:
        `bool`:
            ``True`` when mapping like ``:8800->`` is found.
    """

    if not ports_spec:
        return False

    pattern = re.compile(rf":{int(host_port)}->")
    return bool(pattern.search(ports_spec))


async def _tcp_probe(host: str, port: int, timeout: float) -> bool:
    """Probe TCP connectivity to one host/port.

    Args:
        host (`str`):
            Target host.
        port (`int`):
            Target port.
        timeout (`float`):
            Probe timeout in seconds.

    Returns:
        `bool`:
            ``True`` if TCP connection succeeds.
    """

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)),
            timeout=timeout,
        )
        del reader
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:  # noqa: BLE001
        return False


def _pick_smoke_tool_and_args(
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any], str]:
    """Pick one low-risk tool and generate mock arguments.

    Args:
        tool_specs (`list[dict[str, Any]]`):
            List of dict entries with ``name`` and ``input_schema`` fields.

    Returns:
        `tuple[dict[str, Any] | None, dict[str, Any], str]`:
            Selected tool (or ``None``), generated arguments, and note.
    """

    if not tool_specs:
        return None, {}, "No tools available"

    preferred_names = [
        "echo",
        "echo_tool",
        "echo-message",
        "echo_message",
        "think",
        "ping",
        "health",
        "health_check",
        "get_current_time",
        "now",
    ]

    def _tool_score(item: dict[str, Any]) -> tuple[int, int]:
        name = str(item.get("name", "")).strip().lower()
        preferred = 0 if name in preferred_names else 1
        required_size = len(_extract_required_fields(item.get("input_schema", {})))
        return preferred, required_size

    sorted_tools = sorted(tool_specs, key=_tool_score)

    for item in sorted_tools:
        tool_name = str(item.get("name", ""))
        if not _is_low_risk_tool_name(tool_name):
            continue

        input_schema = item.get("input_schema", {}) or {}
        required = _extract_required_fields(input_schema)
        if len(required) > 4:
            continue

        arguments = _build_mock_arguments(input_schema)
        missing = [field for field in required if field not in arguments]
        if missing:
            continue
        return item, arguments, ""

    return None, {}, "No low-risk tool with satisfiable mock arguments"


def _extract_required_fields(input_schema: dict[str, Any]) -> list[str]:
    """Extract required fields from JSON schema.

    Args:
        input_schema (`dict[str, Any]`):
            Tool input schema.

    Returns:
        `list[str]`:
            Required field names.
    """

    required = input_schema.get("required", [])
    if isinstance(required, list):
        return [str(field) for field in required]
    return []


def _build_mock_arguments(input_schema: dict[str, Any]) -> dict[str, Any]:
    """Build minimal mock arguments from JSON schema.

    Args:
        input_schema (`dict[str, Any]`):
            Tool input schema.

    Returns:
        `dict[str, Any]`:
            Generated mock argument dictionary.
    """

    properties = input_schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}

    required = _extract_required_fields(input_schema)
    arguments: dict[str, Any] = {}
    for field in required:
        field_schema = properties.get(field, {})
        if not isinstance(field_schema, dict):
            continue
        value = _mock_value_from_schema(field_schema)
        if value is not None:
            arguments[field] = value
    return arguments


def _mock_value_from_schema(schema: dict[str, Any]) -> Any:
    """Generate one mock value from a simple JSON schema snippet.

    Args:
        schema (`dict[str, Any]`):
            Field schema fragment.

    Returns:
        `Any`:
            One mock value compatible with common primitive types.
    """

    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and any_of:
        for option in any_of:
            if isinstance(option, dict):
                value = _mock_value_from_schema(option)
                if value is not None:
                    return value

    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        types = [str(item) for item in raw_type]
        if "string" in types:
            return "health_check"
        if "integer" in types:
            return 0
        if "number" in types:
            return 0
        if "boolean" in types:
            return False
        if "array" in types:
            return []
        if "object" in types:
            return {}
        return None

    field_type = str(raw_type or "")
    if field_type == "string":
        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return enum_values[0]
        return "health_check"
    if field_type in {"integer", "number"}:
        return 0
    if field_type == "boolean":
        return False
    if field_type == "array":
        return []
    if field_type == "object":
        return {}
    return None


def _is_low_risk_tool_name(tool_name: str) -> bool:
    """Heuristically reject tools that look state-changing.

    Args:
        tool_name (`str`):
            Raw tool name.

    Returns:
        `bool`:
            ``True`` when the name appears read-only and safe.
    """

    lowered = tool_name.lower()
    blocked_keywords = [
        "delete",
        "remove",
        "drop",
        "write",
        "create",
        "insert",
        "update",
        "edit",
        "post",
        "send",
        "purchase",
        "order",
        "transfer",
        "cancel",
    ]
    return not any(keyword in lowered for keyword in blocked_keywords)


def _compute_overall_status(
    container_running: bool,
    port_mapping_ok: bool,
    tcp_connect_ok: bool,
    list_tools_ok: bool,
    smoke_call_required: bool,
    smoke_call_ok: bool | None,
) -> str:
    """Compute one status label from detailed check results.

    Args:
        container_running (`bool`):
            Container running check result.
        port_mapping_ok (`bool`):
            Port mapping check result.
        tcp_connect_ok (`bool`):
            TCP probe result.
        list_tools_ok (`bool`):
            MCP ``list_tools`` result.
        smoke_call_required (`bool`):
            Whether smoke call is required by CLI option.
        smoke_call_ok (`bool | None`):
            Smoke call result.

    Returns:
        `str`:
            ``pass``, ``fail`` or ``partial``.
    """

    mandatory_ok = container_running and port_mapping_ok and tcp_connect_ok and list_tools_ok
    if mandatory_ok and (not smoke_call_required or smoke_call_ok is True):
        return "pass"

    if not tcp_connect_ok or not list_tools_ok:
        return "fail"

    return "partial"


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        `argparse.Namespace`:
            Parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Validate all pre-warmed MCP servers in Laplace manifest.",
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        help="Optional path to laplace_mcp_manifest.json.",
    )
    parser.add_argument(
        "--servers",
        nargs="*",
        help="Optional server names to validate. Default validates all.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Timeout in seconds for TCP and MCP operations.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Maximum number of servers validated concurrently.",
    )
    parser.add_argument(
        "--enable-smoke-call",
        action="store_true",
        help="Enable optional one-tool smoke call after list_tools.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional output JSON path.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero code if any server is fail/partial.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level.",
    )
    return parser.parse_args()


async def _run() -> int:
    """Run CLI validation workflow.

    Returns:
        `int`:
            Process exit code.
    """

    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    validator = MCPServerValidator(
        manifest_path=args.manifest_path,
        request_timeout=args.timeout,
        concurrency=args.concurrency,
        enable_smoke_call=args.enable_smoke_call,
    )
    report = await validator.validate(target_servers=args.servers)

    summary = report["summary"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    output = args.output
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _logger.info("[validate] report written to %s", output_path)

    if args.fail_on_error and (summary["failed"] > 0 or summary["partial"] > 0):
        return 2
    return 0


def main() -> int:
    """Entrypoint for ``python -m`` execution.

    Returns:
        `int`:
            Process exit code.
    """

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
