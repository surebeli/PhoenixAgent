from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from phoenix.runtime.base import Episode


@dataclass(frozen=True)
class IngestSource:
    path: Path | None = None
    text: str | None = None
    url: str | None = None
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    namespace: str = "default"


@dataclass(frozen=True)
class IngestResult:
    node_id: str
    ingested_chunks: int
    created_links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryHit:
    node_id: str
    score: float
    excerpt: str
    path: Path | None = None


@dataclass(frozen=True)
class DigestResult:
    nodes_updated: int
    new_facts: int
    lint_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImportConfig:
    source_kind: Literal["obsidian", "notion", "markdown_dir", "url_list"]
    root: Path | None = None
    urls: list[str] = field(default_factory=list)
    namespace: str = "default"


@dataclass(frozen=True)
class ImportReport:
    imported_nodes: int = 0
    skipped_nodes: int = 0


@dataclass(frozen=True)
class MemoryGraph:
    nodes: int = 0
    edges: int = 0


@dataclass(frozen=True)
class LintReport:
    warnings: list[str] = field(default_factory=list)
    fixed: int = 0


@dataclass(frozen=True)
class TieringPolicy:
    name: str = "default"


@dataclass(frozen=True)
class TieringReport:
    moved_nodes: int = 0


@runtime_checkable
class MemoryBackend(Protocol):
    def ingest(self, source: IngestSource) -> IngestResult: ...

    def query(self, q: str, *, limit: int = 10, namespace: str | None = None) -> list[MemoryHit]: ...

    def digest(self, episode: Episode) -> DigestResult: ...

    def import_bulk(self, cfg: ImportConfig) -> ImportReport: ...

    def graph(self, *, scope: str | None = None) -> MemoryGraph: ...

    def lint(self, *, auto_fix: bool = False) -> LintReport: ...

    def tier(self, *, policy: TieringPolicy) -> TieringReport: ...


__all__ = [
    "DigestResult",
    "ImportConfig",
    "ImportReport",
    "IngestResult",
    "IngestSource",
    "LintReport",
    "MemoryBackend",
    "MemoryGraph",
    "MemoryHit",
    "TieringPolicy",
    "TieringReport",
]