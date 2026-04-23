from __future__ import annotations

from .base import (
    AgentEvent,
    AgentRuntime,
    PermissionRule,
    PermissionRules,
    Plan,
    PlanStep,
    RuntimeConfig,
    SessionHandle,
    Task,
    TaskResult,
)
from .claude import ClaudeAgentSDKRuntime
from .core import PhoenixCoreRuntime
from .openai import OpenAIAgentsRuntime


RUNTIME_REGISTRY: dict[str, type[AgentRuntime]] = {
    "claude": ClaudeAgentSDKRuntime,
    "self": PhoenixCoreRuntime,
    "openai": OpenAIAgentsRuntime,
}


def make_runtime(name: str) -> AgentRuntime:
    try:
        runtime_cls = RUNTIME_REGISTRY[name]
    except KeyError as exc:
        raise RuntimeError(f"unknown runtime: {name}") from exc
    return runtime_cls()


__all__ = [
    "AgentEvent",
    "AgentRuntime",
    "ClaudeAgentSDKRuntime",
    "OpenAIAgentsRuntime",
    "PermissionRule",
    "PermissionRules",
    "PhoenixCoreRuntime",
    "Plan",
    "PlanStep",
    "RUNTIME_REGISTRY",
    "RuntimeConfig",
    "SessionHandle",
    "Task",
    "TaskResult",
    "make_runtime",
]
