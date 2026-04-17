# -*- coding: utf-8 -*-
"""Tests for Laplace Docker MCP registration config loading."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from agentscope.mcp.server_config._laplace_mcp import (
    build_laplace_registration_config,
    load_laplace_registration_configs,
)


class LaplaceServerConfigTest(TestCase):
    """Test manifest-driven Laplace MCP registration config loading."""

    def test_build_single_ready_config(self) -> None:
        """A prewarm-ready manifest entry should become a registration config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "laplace_mcp_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "servers": {
                            "Wikipedia": {
                                "ready_for_prewarm": True,
                                "server_config": {
                                    "container_name": "laplace-wikipedia",
                                    "image": "laplace/wikipedia:local",
                                    "transport": "streamable_http",
                                    "url": "http://localhost:${TEST_WIKI_PORT:-9001}/mcp",
                                    "client_name": "laplace-wikipedia",
                                },
                                "docker_run_command": [
                                    "docker",
                                    "run",
                                    "laplace/wikipedia:local",
                                ],
                                "group_name": "laplace_wikipedia",
                                "group_description": "Wikipedia tools.",
                                "tool_names": ["search_wikipedia"],
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = build_laplace_registration_config(
                server_name="Wikipedia",
                manifest_path=str(manifest_path),
            )

        self.assertEqual(config.server_config.container_name, "laplace-wikipedia")
        self.assertEqual(config.server_config.transport, "streamable_http")
        self.assertEqual(config.group_name, "laplace_wikipedia")
        self.assertEqual(config.tool_names, ("search_wikipedia",))

    def test_skip_non_ready_entries_when_loading_all(self) -> None:
        """Bulk loading should ignore non-ready services by default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "laplace_mcp_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "servers": {
                            "Wikipedia": {
                                "ready_for_prewarm": True,
                                "server_config": {
                                    "container_name": "laplace-wikipedia",
                                    "image": "laplace/wikipedia:local",
                                    "transport": "streamable_http",
                                    "url": "http://localhost:9001/mcp",
                                    "client_name": "laplace-wikipedia",
                                },
                                "docker_run_command": [
                                    "docker",
                                    "run",
                                    "laplace/wikipedia:local",
                                ],
                                "group_name": "laplace_wikipedia",
                                "group_description": "Wikipedia tools.",
                            },
                            "Math MCP": {
                                "ready_for_prewarm": False,
                                "group_name": "laplace_math_mcp",
                                "group_description": "Math tools.",
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            configs = load_laplace_registration_configs(
                manifest_path=str(manifest_path),
            )

        self.assertEqual(list(configs.keys()), ["Wikipedia"])

    def test_missing_server_raises_key_error(self) -> None:
        """Requesting an absent server should raise KeyError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "laplace_mcp_manifest.json"
            manifest_path.write_text(
                json.dumps({"servers": {}}),
                encoding="utf-8",
            )
            with self.assertRaises(KeyError):
                build_laplace_registration_config(
                    server_name="Nonexistent",
                    manifest_path=str(manifest_path),
                )

    def test_not_ready_server_raises_value_error(self) -> None:
        """A server with ready_for_prewarm=false should raise ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "laplace_mcp_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "servers": {
                            "Math MCP": {
                                "ready_for_prewarm": False,
                                "server_config": {
                                    "container_name": "laplace-math-mcp",
                                    "image": "laplace/math-mcp:local",
                                    "transport": "streamable_http",
                                    "url": "http://localhost:8824/mcp",
                                    "client_name": "laplace-math-mcp",
                                },
                                "docker_run_command": [],
                                "group_name": "laplace_math_mcp",
                                "group_description": "Math tools.",
                            },
                        },
                    },
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_laplace_registration_config(
                    server_name="Math MCP",
                    manifest_path=str(manifest_path),
                )
