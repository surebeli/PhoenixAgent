from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from phoenix.runtime.base import Episode

from .backend import (
    DigestResult,
    ImportConfig,
    ImportReport,
    IngestResult,
    IngestSource,
    LintReport,
    MemoryGraph,
    MemoryHit,
    TieringPolicy,
    TieringReport,
)


class MemoryBackendError(RuntimeError):
    pass


class AKLLMWikiBackend:
    def __init__(self, wiki_root: Path | None = None, cli: str = "wiki") -> None:
        self.wiki_root = Path(wiki_root).resolve() if wiki_root is not None else None
        self.cli = cli

    def ingest(self, source: IngestSource) -> IngestResult:
        slug = self._slug_for_source(source)
        cleanup_path: Path | None = None
        if source.path is not None:
            source_arg = str(source.path)
        elif source.text is not None:
            cleanup_path = self._write_temp_source(source, slug)
            source_arg = str(cleanup_path)
        elif source.url is not None:
            source_arg = source.url
        else:
            raise ValueError("ingest requires one of path, text, or url")

        args = self._command("ingest")
        args.extend([source_arg, "--namespace", source.namespace, "--slug", slug, "--tier", "active", "--json"])
        if self.wiki_root is not None:
            args.extend(["--path", str(self.wiki_root)])

        try:
            payload = self._run_json(args)
        finally:
            if cleanup_path is not None:
                cleanup_path.unlink(missing_ok=True)

        node_id = str(payload.get("node_id") or payload.get("slug") or f"{source.namespace}:{slug}")
        chunks = int(payload.get("ingested_chunks") or 1)
        raw_links = payload.get("created_links") or []
        created_links = [str(link) for link in raw_links] if isinstance(raw_links, list) else []
        return IngestResult(node_id=node_id, ingested_chunks=chunks, created_links=created_links)

    def query(self, q: str, *, limit: int = 10, namespace: str | None = None) -> list[MemoryHit]:
        args = self._command("query")
        args.extend([q, "--limit", str(limit), "--json"])
        if namespace is not None:
            args.extend(["--namespace", namespace])
        if self.wiki_root is not None:
            args.extend(["--path", str(self.wiki_root)])

        payload = self._run_json(args)
        hits: list[MemoryHit] = []
        for item in payload.get("hits") or []:
            if not isinstance(item, dict):
                continue
            source_path = item.get("source_path") or item.get("path")
            hits.append(
                MemoryHit(
                    node_id=str(item.get("node_id") or item.get("stored_path") or item.get("title") or "unknown"),
                    score=float(item.get("score") or 0.0),
                    excerpt=str(item.get("excerpt") or ""),
                    path=Path(source_path) if isinstance(source_path, str) and source_path else None,
                )
            )
        return hits

    def digest(self, episode: Episode) -> DigestResult:
        summary = self._render_episode_markdown(episode)
        ingest_result = self.ingest(
            IngestSource(
                text=summary,
                title=f"episode-{episode.task.id.lower()}",
                tags=["episode", episode.namespace, episode.result.status],
                namespace=episode.namespace,
            )
        )
        return DigestResult(
            nodes_updated=1 if ingest_result.node_id else 0,
            new_facts=max(1, len(episode.extracted_facts) + self._event_fact_count(episode)),
            lint_warnings=[],
        )

    def import_bulk(self, cfg: ImportConfig) -> ImportReport:
        raise NotImplementedError("wiki import is not implemented for M0 Step 7")

    def graph(self, *, scope: str | None = None) -> MemoryGraph:
        raise NotImplementedError("wiki graph is not implemented for M0 Step 7")

    def lint(self, *, auto_fix: bool = False) -> LintReport:
        raise NotImplementedError("wiki lint is not implemented for M0 Step 7")

    def tier(self, *, policy: TieringPolicy) -> TieringReport:
        raise NotImplementedError("wiki tier is not implemented for M0 Step 7")

    def _command(self, subcommand: str) -> list[str]:
        wrapper = shutil.which(f"wiki-{subcommand}")
        if wrapper:
            return [wrapper]
        if self.cli == "wiki":
            return [self.cli, subcommand]
        return [self.cli]

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        run_args = self._process_args(args)
        proc = subprocess.run(
            run_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            message = proc.stderr.strip() or proc.stdout.strip() or "wiki command failed"
            raise MemoryBackendError(message)
        return self._parse_json(proc.stdout)

    def _process_args(self, args: list[str]) -> list[str]:
        if os.name != "nt":
            return args

        executable = args[0]
        if shutil.which(executable):
            return args

        git_bash = self._git_bash_path()
        if git_bash is None:
            return args

        command = " ".join(shlex.quote(part) for part in args)
        return [str(git_bash), "-lc", command]

    def _git_bash_path(self) -> Path | None:
        configured = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
        candidates = [
            configured,
            r"D:\Program Files\Git\bin\bash.exe",
            r"D:\Program Files\Git\git-bash.exe",
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\git-bash.exe",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def _parse_json(self, stdout: str) -> dict[str, Any]:
        text = stdout.strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            items = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
            if len(items) == 1 and isinstance(items[0], dict):
                return items[0]
            return {"items": items}
        if not isinstance(payload, dict):
            return {"value": payload}
        return payload

    def _slug_for_source(self, source: IngestSource) -> str:
        if source.title:
            return self._slugify(source.title)
        if source.path is not None:
            return self._slugify(source.path.stem)
        if source.url:
            return self._slugify(source.url.rsplit("/", 1)[-1])
        return "episode-node"

    def _slugify(self, value: str) -> str:
        words: list[str] = []
        current: list[str] = []
        for ch in value.lower():
            if ch.isalnum():
                current.append(ch)
                continue
            if current:
                words.append("".join(current))
                current.clear()
        if current:
            words.append("".join(current))
        return "-".join(word for word in words if word) or "episode-node"

    def _write_temp_source(self, source: IngestSource, slug: str) -> Path:
        title = source.title or slug
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
            tmp.write(f"# {title}\n\n{source.text or ''}\n")
            return Path(tmp.name)

    def _event_fact_count(self, episode: Episode) -> int:
        return sum(1 for event in episode.result.events if event.kind in {"tool_invoked", "tool_completed", "message"})

    def _render_episode_markdown(self, episode: Episode) -> str:
        lines = [
            f"# Episode {episode.task.id}",
            "",
            "## Summary",
            f"- Namespace: {episode.namespace}",
            f"- Task Prompt: {episode.task.prompt}",
            f"- Status: {episode.result.status}",
            f"- Duration (s): {episode.result.duration_s}",
            f"- Tokens In: {episode.result.tokens_in}",
            f"- Tokens Out: {episode.result.tokens_out}",
        ]
        if episode.result.error:
            lines.append(f"- Error: {episode.result.error}")
        lines.extend(["", "## Key Events"])
        if episode.result.events:
            for event in episode.result.events:
                lines.append(f"- {event.kind}: {self._event_summary(event.payload)}")
        else:
            lines.append("- No events recorded.")
        if episode.extracted_facts:
            lines.extend(["", "## Extracted Facts"])
            for fact in episode.extracted_facts:
                lines.append(f"- {self._event_summary(fact)}")
        return "\n".join(lines) + "\n"

    def _event_summary(self, payload: Any) -> str:
        if isinstance(payload, dict):
            parts = []
            for key in sorted(payload):
                value = payload[key]
                if value in (None, "", [], {}):
                    continue
                parts.append(f"{key}={value}")
            return ", ".join(parts) if parts else "{}"
        return str(payload)


__all__ = ["AKLLMWikiBackend", "MemoryBackendError"]