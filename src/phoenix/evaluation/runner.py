from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from phoenix.memory import AKLLMWikiBackend, IngestSource, MemoryBackend
from phoenix.runtime.base import utcnow

from .swebench import SwebenchRunResult, run_verified_subset


@dataclass(frozen=True)
class VerifyResult:
    resolved: bool
    pass_at_1: float
    tests_passed: int
    tests_failed: int
    human_edit_distance: float | None = None
    long_horizon: dict[str, float] | None = None


@dataclass(frozen=True)
class CostBreakdown:
    execution_usd: float
    evaluation_usd: float
    research_usd: float
    total_usd: float


@dataclass(frozen=True)
class BenchmarkReport:
    runtime: str
    model_profile: str
    family: str
    tasks_total: int
    resolved: int
    cost: CostBreakdown
    tokens_in: int
    tokens_out: int
    per_task: list[tuple[str, VerifyResult]]
    generated_at: datetime

    @property
    def cost_usd(self) -> float:
        return self.cost.total_usd


@runtime_checkable
class EvaluationRunner(Protocol):
    def run(
        self,
        family: str,
        *,
        subset: int | None = None,
        runtime: str,
        model_profile: str,
        seed: int = 0,
    ) -> BenchmarkReport: ...

    def export_report(self, report: BenchmarkReport, out: Path) -> Path: ...


class DefaultEvaluationRunner:
    def __init__(
        self,
        workspace: Path,
        *,
        memory: MemoryBackend | None = None,
        metrics_db: Path | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.memory = memory or AKLLMWikiBackend()
        self.metrics_db = metrics_db or self.workspace / "artifacts" / "phoenix_metrics.sqlite3"
        self._last_run: SwebenchRunResult | None = None

    def run(
        self,
        family: str,
        *,
        subset: int | None = None,
        runtime: str,
        model_profile: str,
        seed: int = 0,
    ) -> BenchmarkReport:
        if family != "swe-bench-verified":
            raise ValueError(f"Unsupported benchmark family: {family}")

        run_result = run_verified_subset(
            self.workspace,
            subset=subset or 1,
            seed=seed,
        )
        self._last_run = run_result

        per_task: list[tuple[str, VerifyResult]] = []
        resolved = 0
        for task_id in run_result.instance_ids:
            outcome = run_result.per_task.get(task_id)
            if outcome is None:
                verify = VerifyResult(
                    resolved=False,
                    pass_at_1=0.0,
                    tests_passed=0,
                    tests_failed=0,
                )
            else:
                verify = VerifyResult(
                    resolved=outcome.resolved,
                    pass_at_1=1.0 if outcome.resolved else 0.0,
                    tests_passed=outcome.tests_passed,
                    tests_failed=outcome.tests_failed,
                )
            per_task.append((task_id, verify))
            if verify.resolved:
                resolved += 1

        return BenchmarkReport(
            runtime=runtime,
            model_profile=model_profile,
            family=family,
            tasks_total=len(run_result.instance_ids),
            resolved=resolved,
            cost=CostBreakdown(
                execution_usd=0.0,
                evaluation_usd=0.0,
                research_usd=0.0,
                total_usd=0.0,
            ),
            tokens_in=0,
            tokens_out=0,
            per_task=per_task,
            generated_at=utcnow(),
        )

    def export_report(self, report: BenchmarkReport, out: Path) -> Path:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = self._report_payload(report)
        if self._last_run is not None:
            payload["swebench"] = {
                "dataset_name": self._last_run.dataset_name,
                "split": self._last_run.split,
                "run_id": self._last_run.run_id,
                "duration_s": self._last_run.duration_s,
                "predictions_path": self._last_run.predictions_path,
                "report_file": str(self._last_run.report_file) if self._last_run.report_file is not None else None,
                "log_dir": str(self._last_run.log_dir),
                "instance_ids": self._last_run.instance_ids,
                "model_label": self._last_run.model_label,
            }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        markdown_path = out.with_suffix(".md")
        markdown_path.write_text(self._render_markdown(report, out), encoding="utf-8", newline="\n")

        self._write_metrics(report)
        self.memory.ingest(
            IngestSource(
                path=markdown_path,
                title=markdown_path.stem,
                namespace="evaluation",
            )
        )
        return out

    def _report_payload(self, report: BenchmarkReport) -> dict[str, object]:
        return {
            "runtime": report.runtime,
            "model_profile": report.model_profile,
            "family": report.family,
            "tasks_total": report.tasks_total,
            "resolved": report.resolved,
            "cost": {
                "execution_usd": report.cost.execution_usd,
                "evaluation_usd": report.cost.evaluation_usd,
                "research_usd": report.cost.research_usd,
                "total_usd": report.cost.total_usd,
            },
            "cost_usd": report.cost_usd,
            "tokens_in": report.tokens_in,
            "tokens_out": report.tokens_out,
            "generated_at": report.generated_at.isoformat(),
            "per_task": [
                {
                    "task_id": task_id,
                    "verify": {
                        "resolved": verify.resolved,
                        "pass_at_1": verify.pass_at_1,
                        "tests_passed": verify.tests_passed,
                        "tests_failed": verify.tests_failed,
                        "human_edit_distance": verify.human_edit_distance,
                    },
                }
                for task_id, verify in report.per_task
            ],
        }

    def _render_markdown(self, report: BenchmarkReport, json_path: Path) -> str:
        lines = [
            f"# BenchmarkReport {report.family}",
            "",
            "## Summary",
            f"- Runtime: {report.runtime}",
            f"- Model Profile: {report.model_profile}",
            f"- Family: {report.family}",
            f"- Tasks Total: {report.tasks_total}",
            f"- Resolved: {report.resolved}",
            f"- Generated At: {report.generated_at.isoformat()}",
            f"- JSON Artifact: {json_path}",
        ]
        if self._last_run is not None:
            lines.extend(
                [
                    f"- SWE-bench Run ID: {self._last_run.run_id}",
                    f"- SWE-bench Duration (s): {self._last_run.duration_s}",
                    f"- SWE-bench Predictions: {self._last_run.predictions_path}",
                    f"- SWE-bench Summary File: {self._last_run.report_file}",
                    f"- SWE-bench Log Dir: {self._last_run.log_dir}",
                ]
            )
        lines.extend(["", "## Per Task", "", "| Task | Resolved | pass@1 | Tests Passed | Tests Failed |", "|---|---:|---:|---:|---:|"])
        for task_id, verify in report.per_task:
            lines.append(
                f"| {task_id} | {int(verify.resolved)} | {verify.pass_at_1:.2f} | {verify.tests_passed} | {verify.tests_failed} |"
            )
        return "\n".join(lines) + "\n"

    def _write_metrics(self, report: BenchmarkReport) -> None:
        self.metrics_db.parent.mkdir(parents=True, exist_ok=True)
        session_id = self._last_run.run_id if self._last_run is not None else f"eval-{report.generated_at.strftime('%Y%m%d%H%M%S')}"
        with sqlite3.connect(self.metrics_db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phoenix_metrics (
                    ts TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT NOT NULL
                )
                """
            )
            base_tags = {
                "family": report.family,
                "runtime": report.runtime,
                "model_profile": report.model_profile,
            }
            ts = report.generated_at.isoformat()
            for task_id, verify in report.per_task:
                conn.execute(
                    "INSERT INTO phoenix_metrics (ts, session_id, task_id, metric, value, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    (ts, session_id, task_id, "benchmark_resolved", float(verify.resolved), json.dumps(base_tags, ensure_ascii=False)),
                )
            conn.execute(
                "INSERT INTO phoenix_metrics (ts, session_id, task_id, metric, value, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (ts, session_id, report.family, "cost_usd", report.cost_usd, json.dumps(base_tags, ensure_ascii=False)),
            )


__all__ = [
    "BenchmarkReport",
    "CostBreakdown",
    "DefaultEvaluationRunner",
    "EvaluationRunner",
    "VerifyResult",
]