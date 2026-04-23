from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .registry import ToolResult, ToolSpec


def _echo_say(args: dict[str, Any], ctx: Any) -> ToolResult:
    message = str(args.get("message", "")).strip()
    if not message:
        raise RuntimeError("echo.say requires a non-empty message")
    return ToolResult(ok=True, data={"message": message, "plugin": "echo"})


@dataclass
class EchoPlugin:
    name: str = "echo"
    version: str = "0.1.0"
    tools: list[ToolSpec] = field(
        default_factory=lambda: [
            ToolSpec(
                name="echo.say",
                plugin="echo",
                description="Echo back the provided message without side effects.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to echo back to the caller.",
                        }
                    },
                    "required": ["message"],
                    "additionalProperties": False,
                },
                handler=_echo_say,
                side_effect="none",
                requires_worktree=False,
                namespace="default",
            )
        ]
    )

    def on_load(self, ctx: Any) -> None:
        return None

    def on_unload(self, ctx: Any) -> None:
        return None


__all__ = ["EchoPlugin"]
