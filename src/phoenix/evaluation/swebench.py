from __future__ import annotations

import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import sitecustomize  # noqa: F401

from phoenix.runtime.base import new_ulid


ROOT = Path(__file__).resolve().parents[3]
DOCKER_RESOURCE_BIN = Path(r"C:\Program Files\Docker\Docker\resources\bin")


@dataclass(frozen=True)
class SwebenchTaskOutcome:
    resolved: bool
    tests_passed: int
    tests_failed: int
    report_file: Path


@dataclass(frozen=True)
class SwebenchRunResult:
    family: str
    dataset_name: str
    split: str
    run_id: str
    model_label: str
    duration_s: float
    predictions_path: str
    report_file: Path | None
    log_dir: Path
    instance_ids: list[str]
    per_task: dict[str, SwebenchTaskOutcome]


def ensure_windows_docker_path() -> None:
    if sys.platform != "win32" or not DOCKER_RESOURCE_BIN.exists():
        return
    current = os.environ.get("PATH", "")
    entries = current.split(os.pathsep) if current else []
    resource_bin = str(DOCKER_RESOURCE_BIN)
    if resource_bin not in entries:
        os.environ["PATH"] = resource_bin + (os.pathsep + current if current else "")


@contextmanager
def force_lf_writes() -> Iterator[None]:
    if sys.platform != "win32":
        yield
        return

    original = Path.write_text

    def patched(self: Path, data: str, encoding=None, errors=None, newline=None) -> int:
        if newline is None and self.suffix in {".sh", ".diff"}:
            newline = "\n"
        return original(self, data, encoding=encoding, errors=errors, newline=newline)

    Path.write_text = patched
    try:
        yield
    finally:
        Path.write_text = original


def select_verified_instance_ids(
    workspace: Path,
    *,
    dataset_name: str,
    split: str,
    subset: int,
) -> list[str]:
    baseline_path = workspace / "artifacts" / "M0" / "baseline-swebench.json"
    ordered_ids: list[str] = []
    seen: set[str] = set()

    if baseline_path.exists():
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        for task_id in payload.get("task_ids") or []:
            if isinstance(task_id, str) and task_id and task_id not in seen:
                ordered_ids.append(task_id)
                seen.add(task_id)
                if len(ordered_ids) >= subset:
                    return ordered_ids

    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split=split)
    for item in dataset:
        task_id = item.get("instance_id")
        if not isinstance(task_id, str) or task_id in seen:
            continue
        ordered_ids.append(task_id)
        seen.add(task_id)
        if len(ordered_ids) >= subset:
            break

    return ordered_ids


def materialize_predictions(
    *,
    dataset_name: str,
    split: str,
    predictions_path: str,
    instance_ids: list[str],
    report_dir: Path,
    run_id: str,
) -> str:
    if predictions_path != "gold":
        return predictions_path

    from swebench.harness.constants import KEY_INSTANCE_ID
    from swebench.harness.utils import get_predictions_from_file

    selected_ids = set(instance_ids)
    predictions = get_predictions_from_file("gold", dataset_name, split)
    filtered = [prediction for prediction in predictions if prediction[KEY_INSTANCE_ID] in selected_ids]
    if len(filtered) != len(selected_ids):
        found_ids = {prediction[KEY_INSTANCE_ID] for prediction in filtered}
        missing = sorted(selected_ids - found_ids)
        raise ValueError(f"Missing gold predictions for: {', '.join(missing)}")

    out_path = report_dir / f"{run_id}.predictions.json"
    out_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return str(out_path)


def run_verified_subset(
    workspace: Path,
    *,
    subset: int,
    seed: int,
    predictions_path: str = "gold",
    dataset_name: str = "SWE-bench/SWE-bench_Verified",
    split: str = "test",
    report_dir: Path | None = None,
    max_workers: int = 1,
    timeout_s: int = 1800,
    cache_level: str = "env",
    namespace: str = "swebench",
    force_rebuild: bool = False,
    clean: bool = False,
) -> SwebenchRunResult:
    if subset < 1:
        raise ValueError("subset must be >= 1")

    instance_ids = select_verified_instance_ids(
        workspace,
        dataset_name=dataset_name,
        split=split,
        subset=subset,
    )
    if not instance_ids:
        raise ValueError("No SWE-bench Verified instance ids available for the requested subset")

    report_root = report_dir or workspace / "artifacts" / "M0" / "evaluation"
    report_root.mkdir(parents=True, exist_ok=True)

    run_id = f"eval-swe-bench-verified-{new_ulid().lower()}"
    resolved_predictions_path = materialize_predictions(
        dataset_name=dataset_name,
        split=split,
        predictions_path=predictions_path,
        instance_ids=instance_ids,
        report_dir=report_root,
        run_id=run_id,
    )

    ensure_windows_docker_path()

    from swebench import run_evaluation
    from swebench.harness.constants import RUN_EVALUATION_LOG_DIR

    started = time.perf_counter()
    with force_lf_writes():
        report_path = run_evaluation(
            dataset_name=dataset_name,
            split=split,
            instance_ids=instance_ids,
            predictions_path=resolved_predictions_path,
            max_workers=max_workers,
            force_rebuild=force_rebuild,
            cache_level=cache_level,
            clean=clean,
            open_file_limit=4096,
            run_id=run_id,
            timeout=timeout_s,
            namespace=namespace,
            rewrite_reports=False,
            modal=False,
            instance_image_tag="latest",
            env_image_tag="latest",
            report_dir=str(report_root),
        )
    duration_s = round(time.perf_counter() - started, 2)

    archived_report: Path | None = None
    if report_path is not None:
        candidate = Path(report_path)
        if candidate.exists():
            archived_report = report_root / candidate.name
            if candidate.resolve() != archived_report.resolve():
                shutil.move(str(candidate), archived_report)
            else:
                archived_report = candidate

    model_label = "gold"
    if archived_report is not None and "." in archived_report.name:
        model_label = archived_report.name.split(".", 1)[0]

    log_dir = RUN_EVALUATION_LOG_DIR / run_id
    per_task: dict[str, SwebenchTaskOutcome] = {}
    for task_id in instance_ids:
        task_report = log_dir / model_label / task_id / "report.json"
        if not task_report.exists():
            continue
        payload = json.loads(task_report.read_text(encoding="utf-8"))
        task_payload = payload.get(task_id) or {}
        tests_status = task_payload.get("tests_status") or {}
        tests_passed = 0
        tests_failed = 0
        for status in tests_status.values():
            if not isinstance(status, dict):
                continue
            tests_passed += len(status.get("success") or [])
            tests_failed += len(status.get("failure") or [])
        per_task[task_id] = SwebenchTaskOutcome(
            resolved=bool(task_payload.get("resolved")),
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            report_file=task_report,
        )

    return SwebenchRunResult(
        family="swe-bench-verified",
        dataset_name=dataset_name,
        split=split,
        run_id=run_id,
        model_label=model_label,
        duration_s=duration_s,
        predictions_path=resolved_predictions_path,
        report_file=archived_report,
        log_dir=log_dir,
        instance_ids=instance_ids,
        per_task=per_task,
    )


__all__ = [
    "SwebenchRunResult",
    "SwebenchTaskOutcome",
    "ensure_windows_docker_path",
    "force_lf_writes",
    "materialize_predictions",
    "run_verified_subset",
    "select_verified_instance_ids",
]