#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import time
import tomllib
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import query as claude_query
from claude_agent_sdk.types import AssistantMessage, ClaudeAgentOptions, ResultMessage, SystemMessage
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path.home() / ".config" / "phoenix"
KEYS_ENV = CONFIG_DIR / "keys.env"
MODELS_TOML = CONFIG_DIR / "models.toml"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data.get("profiles", {})


def ensure_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


class JsonlLogger:
    def __init__(self, path: Path, session_id: str) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id

    def write(self, task_id: str, kind: str, payload: dict[str, Any]) -> None:
        event = {
            "ts": now_iso(),
            "session_id": self.session_id,
            "task_id": task_id,
            "kind": kind,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=json_default) + "\n")


def summarize_claude_blocks(content: list[Any]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
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


async def run_claude(task: str, logger: JsonlLogger, profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = "claude-hello"
    profile = profiles["claude-worker"]
    summary: dict[str, Any] = {
        "provider": "claude_agent_sdk",
        "model": profile["model"],
        "cli_path": shutil.which("claude"),
        "assistant_text": "",
        "assistant_stop_reason": None,
        "result_stop_reason": None,
        "tool_uses": [],
        "tool_results": [],
        "usage": None,
        "model_usage": None,
        "total_cost_usd": None,
        "duration_ms": None,
        "duration_api_ms": None,
        "session_id": None,
    }

    options = ClaudeAgentOptions(
        cwd=ROOT,
        permission_mode="default",
        model=profile["model"],
        max_turns=3,
        cli_path=summary["cli_path"],
    )

    start = time.perf_counter()
    try:
        async for message in claude_query(prompt=task, options=options):
            if isinstance(message, AssistantMessage):
                text, tool_uses, tool_results = summarize_claude_blocks(message.content)
                if text:
                    summary["assistant_text"] = text
                if tool_uses:
                    summary["tool_uses"] = tool_uses
                if tool_results:
                    summary["tool_results"] = tool_results
                summary["assistant_stop_reason"] = message.stop_reason
                summary["usage"] = message.usage
                summary["session_id"] = message.session_id or summary["session_id"]
                logger.write(
                    task_id,
                    "assistant",
                    {
                        "model": message.model,
                        "stop_reason": message.stop_reason,
                        "usage": message.usage,
                        "text": text,
                        "tool_uses": tool_uses,
                        "tool_results": tool_results,
                    },
                )
            elif isinstance(message, ResultMessage):
                summary["result_stop_reason"] = message.stop_reason
                summary["total_cost_usd"] = message.total_cost_usd
                summary["usage"] = message.usage or summary["usage"]
                summary["model_usage"] = message.model_usage
                summary["duration_ms"] = message.duration_ms
                summary["duration_api_ms"] = message.duration_api_ms
                summary["session_id"] = message.session_id or summary["session_id"]
                logger.write(
                    task_id,
                    "result",
                    {
                        "subtype": message.subtype,
                        "stop_reason": message.stop_reason,
                        "usage": message.usage,
                        "model_usage": message.model_usage,
                        "duration_ms": message.duration_ms,
                        "duration_api_ms": message.duration_api_ms,
                        "num_turns": message.num_turns,
                        "total_cost_usd": message.total_cost_usd,
                        "result": message.result,
                    },
                )
            elif isinstance(message, SystemMessage):
                logger.write(task_id, f"system.{message.subtype}", message.data)
            else:
                logger.write(task_id, type(message).__name__, json_default(message))
    except Exception as exc:
        error_text = str(exc)
        if summary["result_stop_reason"] and error_text.startswith("Command failed with exit code 1"):
            logger.write(task_id, "sdk.epilogue_error", {"error": error_text})
        else:
            raise

    summary["wall_clock_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return summary


def execute_openai_tool(tool_call: Any) -> str:
    arguments = json.loads(tool_call.function.arguments or "{}")
    return json.dumps(
        {
            "status": "hello-phoenix",
            "echo": arguments.get("message", ""),
            "provider": "codex-openai",
        },
        ensure_ascii=False,
    )


def run_codex(task: str, logger: JsonlLogger, profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = "codex-hello"
    profile = profiles["codex-base"]
    base_url = ensure_openai_base_url(profile["base_url"])
    api_key = os.environ[profile["api_key_env"]]
    client = OpenAI(api_key=api_key, base_url=base_url)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "echo_status",
                "description": "Return a fixed hello-phoenix status for smoke-testing function calling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "The greeting to echo back."}
                    },
                    "required": ["message"],
                },
            },
        }
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
    summary: dict[str, Any] = {
        "provider": "openai_chat_completions",
        "model": profile["model"],
        "assistant_text": "",
        "finish_reason": None,
        "final_finish_reason": None,
        "tool_calls": [],
        "usage": None,
        "tool_role_message": None,
    }

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=profile["model"],
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0,
    )
    choice = response.choices[0]
    summary["finish_reason"] = choice.finish_reason
    summary["usage"] = response.usage.model_dump() if response.usage else None
    assistant_message = choice.message
    tool_calls = []
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            tool_calls.append(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                }
            )
    summary["tool_calls"] = tool_calls
    if assistant_message.content:
        summary["assistant_text"] = assistant_message.content
    logger.write(
        task_id,
        "openai.response",
        {
            "finish_reason": choice.finish_reason,
            "usage": summary["usage"],
            "message": assistant_message.model_dump(),
        },
    )

    if tool_calls:
        messages.append(assistant_message.model_dump(exclude_none=True))
        for tool_call in assistant_message.tool_calls or []:
            tool_output = execute_openai_tool(tool_call)
            summary["tool_role_message"] = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_output,
            }
            logger.write(
                task_id,
                "openai.tool_call",
                {
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                    "tool_result": tool_output,
                },
            )
            messages.append(summary["tool_role_message"])

        follow_up = client.chat.completions.create(
            model=profile["model"],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )
        follow_choice = follow_up.choices[0]
        summary["final_finish_reason"] = follow_choice.finish_reason
        if follow_choice.message.content:
            summary["assistant_text"] = follow_choice.message.content
        if follow_up.usage:
            summary["followup_usage"] = follow_up.usage.model_dump()
        logger.write(
            task_id,
            "openai.followup",
            {
                "finish_reason": follow_choice.finish_reason,
                "usage": follow_up.usage.model_dump() if follow_up.usage else None,
                "message": follow_choice.message.model_dump(),
            },
        )
    else:
        summary["final_finish_reason"] = choice.finish_reason

    summary["wall_clock_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return summary


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run Step 3 Claude/Codex smoke tests.")
    parser.add_argument("--task", default="hello phoenix")
    parser.add_argument("--providers", choices=["all", "claude", "codex"], default="all")
    args = parser.parse_args()

    load_env_file(KEYS_ENV)
    profiles = load_profiles(MODELS_TOML)

    session_id = f"m0-step3-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    log_path = ROOT / "logs" / f"{session_id}.jsonl"
    logger = JsonlLogger(log_path, session_id)

    logger.write("session", "session.start", {"task": args.task, "providers": args.providers})

    summaries: dict[str, Any] = {
        "session_id": session_id,
        "log_path": str(log_path.relative_to(ROOT)),
        "task": args.task,
        "providers": {},
    }

    if args.providers in {"all", "claude"}:
        summaries["providers"]["claude"] = await run_claude(args.task, logger, profiles)
    if args.providers in {"all", "codex"}:
        summaries["providers"]["codex"] = run_codex(args.task, logger, profiles)

    logger.write("session", "session.end", {"providers": list(summaries["providers"].keys())})
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
