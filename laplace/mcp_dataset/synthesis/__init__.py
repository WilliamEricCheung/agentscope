"""DashScope-based MCP-Bench synthesis toolkit for AgentScope.

This package ports the MCP-Bench task synthesis workflow into the
AgentScope repository while keeping the generated dataset format compatible
with the existing fastText semantic router training scripts.
"""

from .benchmark_generator import BenchmarkTaskGenerator
from .task_synthesis import TaskSynthesizer, TaskQualityEvaluator

__all__ = [
    "BenchmarkTaskGenerator",
    "TaskSynthesizer",
    "TaskQualityEvaluator",
]