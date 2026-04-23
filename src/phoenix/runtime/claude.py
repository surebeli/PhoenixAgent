from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sqlite3
import tomllib
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from .base import (
    AgentEvent,
    Episode,
    HookEvent,
    HookFn,
    RuntimeConfig,
    SessionHandle,
    Task,
    TaskResult,
    ToolSpec,
    new_ulid,
    utcnow,
)


CONFIG_DIR = Path.home() / ".config" / "phoenix"
KEYS_ENV = CONFIG_DIR / "keys.env"
MODELS_TOML = CONFIG_DIR / "models.toml"
TASKS_DB = Path("artifacts") / "phoenix_tasks.sqlite3"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data.get("profiles", {})


def _usage_counter(usage: Any, *names: str) -> int:
    if usage is None:
        return 0
    for name in names:
        if isinstance(usage, dict):
            value = usage.get(name, 0)
        else:
            value = getattr(usage, name, 0)
        if value:
            return int(value)
    return 0


class _JsonlLogger:
    def __init__(self, path: Path, session_id: str) -> None:
        self._path = path
        self._session_id = session_id
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, task_id: str, kind: str, payload: dict[str, Any]) -> None:
        event = {
            "ts": utcnow().astimezone().isoformat(timespec="seconds"),
            "session_id": self._session_id,
            "task_id": task_id,
            "kind": kind,
            "payload": payload,
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=_json_default) + "\n")


def _summarize_blocks(content: list[Any]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    text_parts: list[str] = []
    tool_uses: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    for block in content:
        block_type = type(block).__name__
        if block_type == "TextBlock":
            text_parts.append(getattr(block, "text", ""))
        elif block_type == "ToolUseBlock":
            tool_uses.append(
                {
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", None),
                    "input": getattr(block, "input", None),
                }
            )
        elif block_type == "ToolResultBlock":
            tool_results.append(
                {
                    "tool_use_id": getattr(block, "tool_use_id", None),
                    "content": getattr(block, "content", None),
                    "is_error": getattr(block, "is_error", None),
                }
            )
    return "\n".join(part for part in text_parts if part).strip(), tool_uses, tool_results


@dataclass
class _SessionState:
    config: RuntimeConfig
    tools: list[ToolSpec] = field(default_factory=list)
    hooks: dict[HookEvent, list[HookFn]] = field(default_factory=dict)
    events: list[AgentEvent] = field(default_factory=list)


class ClaudeAgentSDKRuntime:
    name = "claude"

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionState] = {}

    def start_session(self, cfg: RuntimeConfig, ctx: Any) -> SessionHandle:
        handle = SessionHandle(
            id=new_ulid(),
            runtime_name=self.name,
            started_at=utcnow(),
            ctx=ctx,
        )
        self._sessions[handle.id] = _SessionState(config=cfg)
        return handle

    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult:
        state = self._require_session(handle)
        local_result = self._run_registered_tool_task(handle, task, state)
        if local_result is not None:
            return self._finalize_task_result(handle, task, state, local_result)
        result = asyncio.run(self._run_task_async(handle, task, state))
        return self._finalize_task_result(handle, task, state, result)

    def register_tool(self, handle: SessionHandle, tool: ToolSpec) -> None:
        self._require_session(handle).tools.append(tool)

    def install_hook(self, handle: SessionHandle, event: HookEvent, fn: HookFn) -> None:
        state = self._require_session(handle)
        state.hooks.setdefault(event, []).append(fn)

    def stream_events(self, handle: SessionHandle) -> Iterator[AgentEvent]:
        return iter(list(self._require_session(handle).events))

    def stop_session(self, handle: SessionHandle) -> None:
        self._sessions.pop(handle.id, None)

    def _require_session(self, handle: SessionHandle) -> _SessionState:
        try:
            return self._sessions[handle.id]
        except KeyError as exc:
            raise RuntimeError(f"unknown session: {handle.id}") from exc

    def _dispatch_hooks(
        self,
        state: _SessionState,
        handle: SessionHandle,
        event: HookEvent,
        payload: dict[str, Any],
    ) -> None:
        for hook in state.hooks.get(event, []):
            hook(payload, handle)

    def _run_registered_tool_task(
        self,
        handle: SessionHandle,
        task: Task,
        state: _SessionState,
    ) -> TaskResult | None:
        match = self._match_tool_call(task, state.tools)
        if match is None:
            return None

        tool, tool_args = match
        self._activate_tool_namespace(handle, tool)
        log_path = task.workspace / "logs" / f"{handle.id}.jsonl"
        logger = _JsonlLogger(log_path, handle.id)
        logger.write(task.id, "session.start", {"runtime": self.name, "model_profile": state.config.model_profile})

        start = perf_counter()
        tool_call = {
            "id": new_ulid(),
            "name": getattr(tool, "name", ""),
            "input": tool_args,
        }
        self._dispatch_hooks(state, handle, "PreToolUse", tool_call)

        run_events: list[AgentEvent] = [
            AgentEvent(kind="tool_invoked", payload=tool_call, ts=utcnow()),
        ]
        logger.write(
            task.id,
            "assistant",
            {
                "model": "local-tool-dispatch",
                "stop_reason": "tool_use",
                "text": "",
                "tool_uses": [tool_call],
                "tool_results": [],
                "usage": None,
            },
        )
        self._write_usage_observation(
            logger,
            task.id,
            message_kind="assistant",
            usage=None,
            source="local-tool-dispatch",
        )

        try:
            tool_result = self._execute_registered_tool(handle, tool_call, tool, tool_args)
        except Exception as exc:
            duration_s = perf_counter() - start
            error_text = str(exc)
            logger.write(task.id, "local.tool_error", {"tool": getattr(tool, "name", ""), "error": error_text})
            logger.write(
                task.id,
                "session.end",
                {"status": "failed", "stop_reason": "error", "duration_s": round(duration_s, 3)},
            )
            error_event = AgentEvent(kind="error", payload={"message": error_text}, ts=utcnow())
            run_events.append(error_event)
            state.events.extend(run_events)
            return TaskResult(
                task_id=task.id,
                status="failed",
                plan=None,
                artifacts=[log_path],
                events=run_events,
                duration_s=round(duration_s, 3),
                error=error_text,
            )

        tool_payload = self._tool_result_payload(tool_result)
        self._dispatch_hooks(state, handle, "PostToolUse", tool_payload)
        run_events.append(AgentEvent(kind="tool_completed", payload=tool_payload, ts=utcnow()))

        text = self._tool_result_text(tool_result)
        if text:
            run_events.append(AgentEvent(kind="message", payload={"text": text, "stop_reason": "stop"}, ts=utcnow()))
        logger.write(task.id, "local.tool_result", tool_payload)
        self._write_usage_observation(
            logger,
            task.id,
            message_kind="tool_result",
            usage=None,
            source="local-tool-dispatch",
        )

        status = "success" if bool(getattr(tool_result, "ok", False)) else "failed"
        duration_s = perf_counter() - start
        error = getattr(tool_result, "stderr", None)
        logger.write(
            task.id,
            "session.end",
            {"status": status, "stop_reason": "stop", "duration_s": round(duration_s, 3)},
        )
        state.events.extend(run_events)
        return TaskResult(
            task_id=task.id,
            status=status,
            plan=None,
            artifacts=[log_path],
            events=run_events,
            duration_s=round(duration_s, 3),
            error=error,
        )

    def _finalize_task_result(
        self,
        handle: SessionHandle,
        task: Task,
        state: _SessionState,
        result: TaskResult,
    ) -> TaskResult:
        if self._memory_digest_enabled(state.config):
            memory = getattr(handle.ctx, "memory", None)
            if memory is not None and hasattr(memory, "digest"):
                namespace = self._active_namespace(handle)
                digest_result = memory.digest(Episode(task=task, result=result, namespace=namespace))
                digest_event = AgentEvent(
                    kind="memory_digested",
                    payload={
                        "namespace": namespace,
                        "nodes_updated": digest_result.nodes_updated,
                        "new_facts": digest_result.new_facts,
                        "lint_warnings": digest_result.lint_warnings,
                    },
                    ts=utcnow(),
                )
                result.events.append(digest_event)
                state.events.append(digest_event)

        self._persist_task_result(task, result, handle.started_at)
        return result

    def _persist_task_result(self, task: Task, result: TaskResult, started_at: Any) -> None:
        db_path = task.workspace / TASKS_DB
        db_path.parent.mkdir(parents=True, exist_ok=True)
        events_jsonl_path: str | None = None
        if result.artifacts:
            events_jsonl_path = str(result.artifacts[0])

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phoenix_tasks (
                  id TEXT PRIMARY KEY,
                  prompt TEXT NOT NULL,
                  workspace TEXT NOT NULL,
                  status TEXT NOT NULL,
                  plan_json TEXT,
                  events_jsonl_path TEXT,
                  tokens_in INTEGER,
                  tokens_out INTEGER,
                  started_at TEXT,
                  finished_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON phoenix_tasks(status)")
            conn.execute(
                """
                INSERT OR REPLACE INTO phoenix_tasks (
                  id, prompt, workspace, status, plan_json, events_jsonl_path,
                  tokens_in, tokens_out, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.prompt,
                    str(task.workspace),
                    result.status,
                    json.dumps(result.plan, ensure_ascii=False, default=_json_default) if result.plan is not None else None,
                    events_jsonl_path,
                    result.tokens_in,
                    result.tokens_out,
                    started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at),
                    utcnow().isoformat(),
                ),
            )

    def _memory_digest_enabled(self, cfg: RuntimeConfig) -> bool:
        flags = cfg.harness_flags
        if flags is None:
            return True
        return bool(getattr(flags, "memory_digest_on_finish", True))

    def _activate_tool_namespace(self, handle: SessionHandle, tool: ToolSpec) -> None:
        registry = getattr(handle.ctx, "plugins", None)
        namespace = getattr(tool, "namespace", None) or getattr(tool, "plugin", None) or "default"
        if registry is not None and hasattr(registry, "activate_namespace"):
            registry.activate_namespace(str(namespace))

    def _active_namespace(self, handle: SessionHandle) -> str:
        registry = getattr(handle.ctx, "plugins", None)
        if registry is None:
            return "default"
        namespace = getattr(registry, "active_namespace", "default")
        return str(namespace or "default")

    def _match_tool_call(self, task: Task, tools: list[ToolSpec]) -> tuple[ToolSpec, dict[str, Any]] | None:
        requested_tool = task.constraints.get("tool_name")
        if isinstance(requested_tool, str):
            for tool in tools:
                if getattr(tool, "name", None) == requested_tool:
                    raw_args = task.constraints.get("tool_args", {})
                    return tool, raw_args if isinstance(raw_args, dict) else {}

        for tool in tools:
            tool_name = getattr(tool, "name", "")
            if not tool_name or tool_name not in task.prompt:
                continue
            return tool, self._extract_tool_args(tool_name, task.prompt, getattr(tool, "input_schema", {}))
        return None

    def _extract_tool_args(self, tool_name: str, prompt: str, input_schema: dict[str, Any]) -> dict[str, Any]:
        suffix = prompt.split(tool_name, 1)[1].strip()
        suffix = re.sub(r"^[\s:：,，]+", "", suffix)
        suffix = suffix.strip().strip("\"'`“”‘’").strip().rstrip("。.!！?")

        properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        if "message" in properties:
            return {"message": suffix or "hello"}

        if suffix and properties:
            first_key = next(iter(properties))
            return {first_key: suffix}
        return {}

    def _execute_registered_tool(
        self,
        handle: SessionHandle,
        tool_call: dict[str, Any],
        tool: ToolSpec,
        tool_args: dict[str, Any],
    ) -> Any:
        registry = getattr(handle.ctx, "plugins", None)
        if registry is not None and hasattr(registry, "execute"):
            from phoenix.plugins.registry import ToolCall

            return registry.execute(
                ToolCall(id=tool_call["id"], name=tool_call["name"], arguments=tool_args),
                handle.ctx,
            )

        handler = getattr(tool, "handler", None)
        if handler is None:
            raise RuntimeError(f"registered tool {getattr(tool, 'name', '<unknown>')} has no handler")
        return handler(tool_args, handle.ctx)

    def _tool_result_payload(self, tool_result: Any) -> dict[str, Any]:
        artifacts = []
        for artifact in getattr(tool_result, "artifacts", []) or []:
            artifacts.append(str(artifact))
        return {
            "ok": bool(getattr(tool_result, "ok", False)),
            "data": getattr(tool_result, "data", None),
            "artifacts": artifacts,
            "stderr": getattr(tool_result, "stderr", None),
            "tokens_consumed": int(getattr(tool_result, "tokens_consumed", 0) or 0),
        }

    def _tool_result_text(self, tool_result: Any) -> str:
        data = getattr(tool_result, "data", None)
        if isinstance(data, dict):
            for key in ("message", "text", "result"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(data, ensure_ascii=False)
        if data is None:
            return ""
        return str(data)

    async def _run_task_async(
        self,
        handle: SessionHandle,
        task: Task,
        state: _SessionState,
    ) -> TaskResult:
        from claude_agent_sdk import query as claude_query
        from claude_agent_sdk.types import AssistantMessage, ClaudeAgentOptions, ResultMessage, SystemMessage

        _load_env_file(KEYS_ENV)
        profiles = _load_profiles(MODELS_TOML)
        profile = profiles[state.config.model_profile]

        log_path = task.workspace / "logs" / f"{handle.id}.jsonl"
        logger = _JsonlLogger(log_path, handle.id)
        logger.write(task.id, "session.start", {"runtime": self.name, "model_profile": state.config.model_profile})

        assistant_text = ""
        stop_reason: str | None = None
        usage: Any = None
        run_events: list[AgentEvent] = []
        start = perf_counter()
        options = ClaudeAgentOptions(
            cwd=task.workspace,
            permission_mode="default",
            model=profile["model"],
            max_turns=int(state.config.extras.get("max_turns", 3)),
            cli_path=shutil.which("claude"),
        )

        try:
            async for message in claude_query(prompt=task.prompt, options=options):
                if isinstance(message, AssistantMessage):
                    text, tool_uses, tool_results = _summarize_blocks(message.content)
                    if text:
                        assistant_text = text
                        run_events.append(
                            AgentEvent(
                                kind="message",
                                payload={"text": text, "stop_reason": message.stop_reason},
                                ts=utcnow(),
                            )
                        )
                    for tool_use in tool_uses:
                        self._dispatch_hooks(state, handle, "PreToolUse", tool_use)
                        run_events.append(AgentEvent(kind="tool_invoked", payload=tool_use, ts=utcnow()))
                    for tool_result in tool_results:
                        run_events.append(AgentEvent(kind="tool_completed", payload=tool_result, ts=utcnow()))
                        self._dispatch_hooks(state, handle, "PostToolUse", tool_result)
                    stop_reason = message.stop_reason
                    usage = message.usage or usage
                    logger.write(
                        task.id,
                        "assistant",
                        {
                            "model": message.model,
                            "stop_reason": message.stop_reason,
                            "text": text,
                            "tool_uses": tool_uses,
                            "tool_results": tool_results,
                            "usage": message.usage,
                        },
                    )
                    self._write_usage_observation(
                        logger,
                        task.id,
                        message_kind="assistant",
                        usage=message.usage,
                        source="assistant",
                    )
                    for tool_result in tool_results:
                        self._write_usage_observation(
                            logger,
                            task.id,
                            message_kind="tool_result",
                            usage=message.usage,
                            source="assistant.tool_result",
                            tool_use_id=tool_result.get("tool_use_id"),
                        )
                elif isinstance(message, ResultMessage):
                    stop_reason = message.stop_reason or stop_reason
                    usage = message.usage or usage
                    logger.write(
                        task.id,
                        "result",
                        {
                            "subtype": message.subtype,
                            "stop_reason": message.stop_reason,
                            "usage": message.usage,
                            "model_usage": message.model_usage,
                            "duration_ms": message.duration_ms,
                            "duration_api_ms": message.duration_api_ms,
                            "result": message.result,
                            "total_cost_usd": message.total_cost_usd,
                        },
                    )
                elif isinstance(message, SystemMessage):
                    logger.write(task.id, f"system.{message.subtype}", message.data)
                else:
                    logger.write(task.id, type(message).__name__, _json_default(message))
        except Exception as exc:
            error_text = str(exc)
            if stop_reason and error_text.startswith("Command failed with exit code 1"):
                logger.write(task.id, "sdk.epilogue_error", {"error": error_text})
            else:
                raise

        duration_s = perf_counter() - start
        status: str = "success"
        error: str | None = None
        if assistant_text.startswith("API Error:") or "hit your limit" in assistant_text.lower():
            status = "failed"
            error = assistant_text
            run_events.append(AgentEvent(kind="error", payload={"message": assistant_text}, ts=utcnow()))
        elif not assistant_text and not stop_reason:
            status = "failed"
            error = "Claude runtime produced no assistant output."
            run_events.append(AgentEvent(kind="error", payload={"message": error}, ts=utcnow()))

        logger.write(
            task.id,
            "session.end",
            {
                "status": status,
                "stop_reason": stop_reason,
                "duration_s": round(duration_s, 3),
            },
        )
        state.events.extend(run_events)
        return TaskResult(
            task_id=task.id,
            status=status,
            plan=None,
            artifacts=[log_path],
            events=run_events,
            tokens_in=_usage_counter(usage, "input_tokens", "prompt_tokens"),
            tokens_out=_usage_counter(usage, "output_tokens", "completion_tokens"),
            duration_s=round(duration_s, 3),
            error=error,
        )

    def _write_usage_observation(
        self,
        logger: _JsonlLogger,
        task_id: str,
        *,
        message_kind: str,
        usage: Any,
        source: str,
        tool_use_id: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "message_kind": message_kind,
            "source": source,
            "prompt_tokens": _usage_counter(usage, "input_tokens", "prompt_tokens"),
            "completion_tokens": _usage_counter(usage, "output_tokens", "completion_tokens"),
            "cache_read": _usage_counter(usage, "cache_read_input_tokens", "cache_read_tokens"),
            "cache_creation": _usage_counter(usage, "cache_creation_input_tokens", "cache_creation_tokens"),
        }
        if tool_use_id:
            payload["tool_use_id"] = tool_use_id
        logger.write(task_id, "usage.observation", payload)


__all__ = ["ClaudeAgentSDKRuntime"]
