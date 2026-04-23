#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.model import ChatRequest, ModelRequestError, make_client


KIMI_ARTIFACT = ROOT / "artifacts" / "M0" / "kimi-smoke.json"
DEFAULT_PROMPT = "Reply with only: hello phoenix"
WHOAMI_PROMPT = "Reply with only: whoami-ok"
DEFAULT_USER_AGENT = "PhoenixAgent/0.1"
CLAUDE_CODE_USER_AGENT = "Claude-Code"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def contains_coding_agents_hint(summary: dict[str, Any]) -> bool:
    haystacks = [
        str(summary.get("error", "")),
        str(summary.get("response_text", "")),
        json.dumps(summary.get("response_json"), ensure_ascii=False) if summary.get("response_json") else "",
    ]
    return any("only available for coding agents" in text.lower() for text in haystacks)


def summarize_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, ModelRequestError):
        return exc.as_dict()
    return {"type": type(exc).__name__, "message": str(exc)}


def run_chat_attempt(profile_name: str, prompt: str, *, user_agent: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        client = make_client(profile_name, user_agent=user_agent)
        response = client.chat(
            ChatRequest(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=64,
            )
        )
    except Exception as exc:
        return {
            "ok": False,
            "profile": profile_name,
            "prompt": prompt,
            "user_agent": user_agent,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            **summarize_exception(exc),
        }

    return {
        "ok": True,
        "profile": profile_name,
        "prompt": prompt,
        "user_agent": user_agent,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "finish_reason": response.finish_reason,
        "text": response.text,
        "tool_calls": response.tool_calls,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "raw_model": response.raw.get("model"),
    }


def run_kimi_sequence(prompt: str) -> dict[str, Any]:
    direct_probe = run_chat_attempt("kimi-worker", WHOAMI_PROMPT, user_agent=DEFAULT_USER_AGENT)
    disguised_probe = run_chat_attempt("kimi-worker", WHOAMI_PROMPT, user_agent=CLAUDE_CODE_USER_AGENT)

    attempts = [run_chat_attempt("kimi-worker", prompt, user_agent=DEFAULT_USER_AGENT)]
    final_attempt = attempts[-1]
    if not final_attempt["ok"] and contains_coding_agents_hint(final_attempt):
        attempts.append(run_chat_attempt("kimi-worker", prompt, user_agent=CLAUDE_CODE_USER_AGENT))
        final_attempt = attempts[-1]

    if final_attempt["ok"]:
        conclusion = "kimi-worker returned a chat response."
        next_step = "No Step 5 fallback is required for kimi-worker."
    else:
        conclusion = "kimi-worker did not return a successful chat response."
        if disguised_probe["ok"]:
            next_step = "Preserve the Claude-Code User-Agent workaround as a documented compatibility path; do not hard-wire a proxy fallback in Step 5."
        else:
            next_step = "Record the failure and keep HTTP proxy or anthropic-compatible rerouting as a later follow-up, per Step 5."

    return {
        "profile": "kimi-worker",
        "whoami_prompt": WHOAMI_PROMPT,
        "probes": {
            "direct": direct_probe,
            "claude_code_user_agent": disguised_probe,
        },
        "chat_attempts": attempts,
        "final": final_attempt,
        "conclusion": conclusion,
        "next_step": next_step,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Step 5 multi-provider model smoke test.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--kimi-artifact", default=str(KIMI_ARTIFACT))
    args = parser.parse_args()

    codex = run_chat_attempt("codex-base", args.prompt, user_agent=DEFAULT_USER_AGENT)
    kimi = run_kimi_sequence(args.prompt)

    summary = {
        "generated_at": now_iso(),
        "prompt": args.prompt,
        "profiles": {
            "codex-base": codex,
            "kimi-worker": kimi,
        },
    }
    artifact_path = Path(args.kimi_artifact)
    write_json(artifact_path, summary)

    print(json.dumps({"artifact": artifact_path, **summary}, ensure_ascii=False, indent=2, default=json_default))

    if codex["ok"] or kimi["final"]["ok"]:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
