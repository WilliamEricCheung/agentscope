# -*- coding: utf-8 -*-
"""Standalone background daemon for AgentScope MCP lifecycle management."""

import argparse
import asyncio

from ._mcp_server_helper import (
    _run_mcp_lifecycle_daemon_forever,
    _run_mcp_lifecycle_daemon_once,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the MCP lifecycle daemon.

    Returns:
        `argparse.ArgumentParser`:
            The configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Run the AgentScope MCP lifecycle daemon.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one lifecycle management tick and exit.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Optional daemon poll interval in seconds.",
    )
    return parser


def main() -> None:
    """Run the AgentScope MCP lifecycle daemon CLI.

    Returns:
        `None`:
            The daemon loop is started.
    """
    args = _build_parser().parse_args()
    if args.once:
        asyncio.run(_run_mcp_lifecycle_daemon_once())
        return

    asyncio.run(
        _run_mcp_lifecycle_daemon_forever(
            poll_interval_seconds=args.poll_interval,
        ),
    )


if __name__ == "__main__":
    main()
