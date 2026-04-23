from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
SideEffect: TypeAlias = Literal["none", "read", "write", "network", "exec"]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, JSONValue]
    id: str | None = None


class ToolHandler(Protocol):
    def __call__(self, args: dict[str, JSONValue], ctx: Any) -> "ToolResult": ...


@dataclass
class ToolResult:
    ok: bool
    data: JSONValue
    artifacts: list[Path] = field(default_factory=list)
    stderr: str | None = None
    tokens_consumed: int = 0


@dataclass(frozen=True)
class ToolSpec:
    name: str
    plugin: str
    description: str
    input_schema: dict[str, JSONValue]
    handler: ToolHandler
    side_effect: SideEffect
    requires_worktree: bool = False
    namespace: str = "default"


@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str
    tools: list[ToolSpec]

    def on_load(self, ctx: Any) -> None: ...
    def on_unload(self, ctx: Any) -> None: ...


class PluginRegistry:
    def __init__(self, *, active_namespace: str = "default") -> None:
        self._plugins: dict[str, Plugin] = {}
        self._tool_index: dict[str, ToolSpec] = {}
        self._active_namespace = active_namespace

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise RuntimeError(f"plugin already registered: {plugin.name}")
        for tool in plugin.tools:
            if tool.name in self._tool_index:
                raise RuntimeError(f"tool already registered: {tool.name}")
        self._plugins[plugin.name] = plugin
        for tool in plugin.tools:
            self._tool_index[tool.name] = tool

    def unregister(self, name: str) -> None:
        plugin = self._plugins.pop(name)
        for tool in plugin.tools:
            self._tool_index.pop(tool.name, None)

    def list(self) -> list[Plugin]:
        return [self._plugins[name] for name in sorted(self._plugins)]

    def tool_specs(self) -> list[ToolSpec]:
        return [self._tool_index[name] for name in sorted(self._tool_index)]

    def execute(self, call: ToolCall, ctx: Any) -> ToolResult:
        try:
            tool = self._tool_index[call.name]
        except KeyError as exc:
            raise RuntimeError(f"unknown tool: {call.name}") from exc
        return tool.handler(call.arguments, ctx)

    def reload(self, name: str) -> None:
        if name not in self._plugins:
            raise RuntimeError(f"unknown plugin: {name}")
        raise NotImplementedError("plugin reload is not implemented for M0 Step 6")

    def activate_namespace(self, namespace: str) -> None:
        self._active_namespace = namespace

    @property
    def active_namespace(self) -> str:
        return self._active_namespace


__all__ = [
    "JSONValue",
    "Plugin",
    "PluginRegistry",
    "ToolCall",
    "ToolHandler",
    "ToolResult",
    "ToolSpec",
]
