#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sitecustomize  # noqa: F401

from swebench import run_evaluation
from swebench.harness.constants import KEY_INSTANCE_ID, RUN_EVALUATION_LOG_DIR
from swebench.harness.utils import get_predictions_from_file


DOCKER_RESOURCE_BIN = Path(r"C:\Program Files\Docker\Docker\resources\bin")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def materialize_predictions(args: argparse.Namespace, report_dir: Path) -> str:
    if args.predictions_path != "gold":
        return args.predictions_path

    selected_ids = set(args.instance_ids)
    predictions = get_predictions_from_file("gold", args.dataset_name, args.split)
    filtered = [prediction for prediction in predictions if prediction[KEY_INSTANCE_ID] in selected_ids]
    if len(filtered) != len(selected_ids):
        found_ids = {prediction[KEY_INSTANCE_ID] for prediction in filtered}
        missing = sorted(selected_ids - found_ids)
        raise ValueError(f"Missing gold predictions for: {', '.join(missing)}")

    out_path = report_dir / f"{args.run_id}.predictions.json"
    out_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return str(out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal local SWE-bench evaluation for M0 Step 8.")
    parser.add_argument("--dataset-name", default="SWE-bench/SWE-bench_Verified")
    parser.add_argument("--split", default="test")
    parser.add_argument("--instance-id", action="append", dest="instance_ids", required=True)
    parser.add_argument("--predictions-path", default="gold")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--report-dir", default=str(ROOT / "artifacts" / "M0" / "swebench-first-run"))
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--cache-level", default="env", choices=["none", "base", "env", "instance"])
    parser.add_argument("--open-file-limit", type=int, default=4096)
    parser.add_argument("--namespace", default="swebench")
    parser.add_argument("--instance-image-tag", default="latest")
    parser.add_argument("--env-image-tag", default="latest")
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--rewrite-reports", action="store_true")
    parser.add_argument("--modal", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    ensure_windows_docker_path()
    predictions_path = materialize_predictions(args, report_dir)
    started = time.perf_counter()

    with force_lf_writes():
        report_path = run_evaluation(
            dataset_name=args.dataset_name,
            split=args.split,
            instance_ids=args.instance_ids,
            predictions_path=predictions_path,
            max_workers=args.max_workers,
            force_rebuild=args.force_rebuild,
            cache_level=args.cache_level,
            clean=args.clean,
            open_file_limit=args.open_file_limit,
            run_id=args.run_id,
            timeout=args.timeout,
            namespace=args.namespace,
            rewrite_reports=args.rewrite_reports,
            modal=args.modal,
            instance_image_tag=args.instance_image_tag,
            env_image_tag=args.env_image_tag,
            report_dir=str(report_dir),
        )
    duration_s = round(time.perf_counter() - started, 2)

    report_file = Path(report_path) if report_path is not None else None
    archived_report = None
    if report_file is not None and report_file.exists():
        archived_report = report_dir / report_file.name
        if report_file.resolve() != archived_report.resolve():
            shutil.move(str(report_file), archived_report)

    summary = {
        "generated_at": now_iso(),
        "dataset_name": args.dataset_name,
        "split": args.split,
        "instance_ids": args.instance_ids,
        "predictions_path": predictions_path,
        "run_id": args.run_id,
        "duration_s": duration_s,
        "report_file": str(archived_report) if archived_report is not None else None,
        "log_dir": str(RUN_EVALUATION_LOG_DIR / args.run_id),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())