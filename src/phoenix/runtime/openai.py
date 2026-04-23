from __future__ import annotations

from typing import Iterator

from .base import AgentEvent, HookEvent, HookFn, RuntimeConfig, SessionHandle, Task, TaskResult, ToolSpec


class OpenAIAgentsRuntime:
    name = "openai"

    def start_session(self, cfg: RuntimeConfig, ctx: object) -> SessionHandle:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")

    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")

    def register_tool(self, handle: SessionHandle, tool: ToolSpec) -> None:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")

    def install_hook(self, handle: SessionHandle, event: HookEvent, fn: HookFn) -> None:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")

    def stream_events(self, handle: SessionHandle) -> Iterator[AgentEvent]:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")

    def stop_session(self, handle: SessionHandle) -> None:
        raise NotImplementedError("OpenAIAgentsRuntime arrives after the runtime abstraction is frozen.")


__all__ = ["OpenAIAgentsRuntime"]
