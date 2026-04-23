from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phoenix.plugins import EchoPlugin, PluginRegistry
from phoenix.runtime import PermissionRules, RuntimeConfig, Task, make_runtime
from phoenix.runtime.base import new_ulid


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CLIContext:
    workspace: Path
    model_profile: str
    runtime_name: str
    plugins: PluginRegistry


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _serialize_result(result: Any, runtime_name: str, model_profile: str) -> dict[str, Any]:
    return {
        "task_id": result.task_id,
        "status": result.status,
        "runtime": runtime_name,
        "model_profile": model_profile,
        "artifacts": [str(path) for path in result.artifacts],
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "duration_s": result.duration_s,
        "error": result.error,
        "events": result.events,
    }


def run_command(args: argparse.Namespace) -> int:
    registry = PluginRegistry()
    registry.register(EchoPlugin())

    ctx = CLIContext(
        workspace=ROOT,
        model_profile=args.model,
        runtime_name=args.runtime,
        plugins=registry,
    )
    for plugin in registry.list():
        plugin.on_load(ctx)

    runtime = make_runtime(args.runtime)
    cfg = RuntimeConfig(
        name=args.runtime,
        model_profile=args.model,
        harness_flags=None,
        permissions=PermissionRules(),
        extras={"max_turns": 3},
    )
    handle = runtime.start_session(cfg, ctx)
    for tool in registry.tool_specs():
        runtime.register_tool(handle, tool)

    task = Task(
        id=new_ulid(),
        prompt=args.task,
        workspace=ROOT,
        metadata={"entrypoint": "phoenix run"},
    )

    exit_code = 0
    try:
        result = runtime.run_task(handle, task)
    except Exception as exc:
        payload = {
            "status": "failed",
            "runtime": args.runtime,
            "model_profile": args.model,
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))
        else:
            print(f"status=failed runtime={args.runtime} model={args.model}")
            print(str(exc))
        return 1
    finally:
        runtime.stop_session(handle)
        for plugin in registry.list():
            plugin.on_unload(ctx)

    payload = _serialize_result(result, args.runtime, args.model)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))
    else:
        print(f"status={result.status} runtime={args.runtime} model={args.model}")
        if result.error:
            print(result.error)
        elif result.events:
            for event in result.events:
                if event.kind == "message":
                    text = event.payload.get("text")
                    if isinstance(text, str) and text:
                        print(text)
        if result.artifacts:
            print(f"log={result.artifacts[0]}")

    if result.status != "success":
        exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phoenix", description="PhoenixAgent minimal CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a task with the selected runtime.")
    p_run.add_argument("--task", required=True)
    p_run.add_argument("--runtime", choices=["claude", "self", "openai"], default="claude")
    p_run.add_argument("--model", default="claude-worker")
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=run_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
