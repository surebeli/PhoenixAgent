from __future__ import annotations

from typing import Iterator

from .base import AgentEvent, HookEvent, HookFn, RuntimeConfig, SessionHandle, Task, TaskResult, ToolSpec


class PhoenixCoreRuntime:
    name = "self"

    def start_session(self, cfg: RuntimeConfig, ctx: object) -> SessionHandle:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")

    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")

    def register_tool(self, handle: SessionHandle, tool: ToolSpec) -> None:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")

    def install_hook(self, handle: SessionHandle, event: HookEvent, fn: HookFn) -> None:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")

    def stream_events(self, handle: SessionHandle) -> Iterator[AgentEvent]:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")

    def stop_session(self, handle: SessionHandle) -> None:
        raise NotImplementedError("PhoenixCoreRuntime arrives in M1.")


__all__ = ["PhoenixCoreRuntime"]
