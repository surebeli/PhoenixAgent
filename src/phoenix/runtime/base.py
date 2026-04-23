from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from secrets import randbits
from time import time_ns
from typing import Any, Callable, Iterator, Literal, Protocol, TypeAlias, runtime_checkable


ULID = str
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
PermissionDecision: TypeAlias = Literal["allow", "deny", "ask"]
HookEvent: TypeAlias = Literal[
    "PreToolUse",
    "PostToolUse",
    "PrePlan",
    "PostPlan",
    "PreSubagent",
    "PostSubagent",
    "OnError",
]

_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _encode_crockford(value: int, length: int) -> str:
    chars = ["0"] * length
    for idx in range(length - 1, -1, -1):
        chars[idx] = _CROCKFORD32[value & 0x1F]
        value >>= 5
    return "".join(chars)


def new_ulid() -> ULID:
    timestamp_ms = time_ns() // 1_000_000
    randomness = randbits(80)
    return f"{_encode_crockford(timestamp_ms, 10)}{_encode_crockford(randomness, 16)}"


@dataclass(frozen=True)
class Task:
    id: ULID
    prompt: str
    workspace: Path
    constraints: dict[str, JSONValue] = field(default_factory=dict)
    metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass
class PlanStep:
    id: ULID
    description: str
    tool: str | None
    tool_args: dict[str, JSONValue] = field(default_factory=dict)
    depends_on: list[ULID] = field(default_factory=list)
    subagent: bool = False


@dataclass
class Plan:
    id: ULID
    task_id: ULID
    steps: list[PlanStep]
    estimated_tokens: int
    model_profile: str


@dataclass
class AgentEvent:
    kind: Literal[
        "plan_proposed",
        "tool_invoked",
        "tool_completed",
        "hook_approved",
        "hook_denied",
        "message",
        "subagent_spawned",
        "memory_digested",
        "error",
    ]
    payload: dict[str, JSONValue]
    ts: datetime


@dataclass
class TaskResult:
    task_id: ULID
    status: Literal["success", "failed", "cancelled", "partial"]
    plan: Plan | None
    artifacts: list[Path] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    error: str | None = None


@dataclass
class Episode:
    task: Task
    result: TaskResult
    namespace: str
    extracted_facts: list[dict[str, JSONValue]] = field(default_factory=list)


@runtime_checkable
class ToolSpec(Protocol):
    name: str
    plugin: str
    description: str
    input_schema: dict[str, JSONValue]
    handler: Any
    side_effect: Literal["none", "read", "write", "network", "exec"]
    requires_worktree: bool
    namespace: str


@dataclass
class PermissionRule:
    pattern: str
    decision: PermissionDecision
    note: str = ""


@dataclass
class PermissionRules:
    allow: list[PermissionRule] = field(default_factory=list)
    deny: list[PermissionRule] = field(default_factory=list)
    ask: list[PermissionRule] = field(default_factory=list)

    def check(self, tool_name: str) -> PermissionDecision:
        for rule in self.deny:
            if fnmatch(tool_name, rule.pattern):
                return "deny"
        for rule in self.allow:
            if fnmatch(tool_name, rule.pattern):
                return "allow"
        for rule in self.ask:
            if fnmatch(tool_name, rule.pattern):
                return "ask"
        return "ask"


HookFn: TypeAlias = Callable[[dict[str, JSONValue], "SessionHandle"], None]


@dataclass(frozen=True)
class RuntimeConfig:
    name: Literal["claude", "self", "openai"]
    model_profile: str
    harness_flags: Any
    permissions: PermissionRules
    timeout_s: int = 1800
    extras: dict[str, JSONValue] = field(default_factory=dict)


@dataclass
class SessionHandle:
    id: ULID
    runtime_name: str
    started_at: datetime
    ctx: Any


@runtime_checkable
class AgentRuntime(Protocol):
    name: str

    def start_session(self, cfg: RuntimeConfig, ctx: Any) -> SessionHandle: ...
    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult: ...
    def register_tool(self, handle: SessionHandle, tool: ToolSpec) -> None: ...
    def install_hook(self, handle: SessionHandle, event: HookEvent, fn: HookFn) -> None: ...
    def stream_events(self, handle: SessionHandle) -> Iterator[AgentEvent]: ...
    def stop_session(self, handle: SessionHandle) -> None: ...


__all__ = [
    "AgentEvent",
    "AgentRuntime",
    "Episode",
    "HookEvent",
    "HookFn",
    "JSONValue",
    "PermissionRule",
    "PermissionRules",
    "Plan",
    "PlanStep",
    "RuntimeConfig",
    "SessionHandle",
    "Task",
    "TaskResult",
    "ToolSpec",
    "ULID",
    "new_ulid",
    "utcnow",
]
