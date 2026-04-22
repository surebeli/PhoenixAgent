#!/usr/bin/env python3
"""
ci-check-milestone-dod.py — Milestone DoD 闭合与验收 checklist 同步校验器

规则来源：
    docs/quality/definition-of-done.md
    docs/quality/acceptance-checklist.md §4
    docs/rules/spec-change-policy.md §7（冻结期破冻登记）

本脚本校验：
    - M<N>-plan.md §1 中声明的每条 DoD-(M<N>-)N，在对应 M<N>-retrospective.md
      中必须出现并有打勾状态
    - [x] 必须附带证据（→ / 证据: / 路径 / commit hash 之一）
    - [~] partially_done 不得泄漏出本 Milestone（必须转为 backlog 条目）
    - [-] N/A 必须附不适用原因
    - 破冻事件：retrospective 中若出现"破冻"/"emergency"，需引用 ADR-NNNN
    - Step 级"进入下一步条件"在 plan 中每个 Step 尾部可见（warning）

用法:
    python tools/ci-check-milestone-dod.py [--root <repo_root>] [--strict] [--json]

退出码:
    0  通过（允许 warning，除非 --strict）
    1  使用错误
    2  校验失败

依赖: 无（stdlib only）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# Windows 控制台默认 GBK，统一切 UTF-8 避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


# =====================================================================
# 常量
# =====================================================================

# 在 plan 中提取 DoD 定义：- **DoD-1**:  或  - **DoD-M1-1**:
PLAN_DOD_RE = re.compile(
    r"^-\s+\*\*(?P<id>DoD(?:-M\d+)?-\d+)\*\*\s*[:：]",
    re.MULTILINE,
)

# 在 retrospective 中提取 DoD 勾选项：- [x] DoD-M1-1 ...
RETRO_DOD_RE = re.compile(
    r"^\s*-\s*\[(?P<mark>[ xX~\-])\]\s+(?P<id>DoD(?:-M\d+)?-\d+)\b(?P<rest>.*)$",
    re.MULTILINE,
)

# Step heading：### Step N — <title>
PLAN_STEP_RE = re.compile(r"^###\s+Step\s+(?P<n>\d+)\s*[—\-]\s*(?P<title>.+)$", re.MULTILINE)

# 进入下一步条件标识
PLAN_NEXT_COND_RE = re.compile(r"\*\*进入下一步条件\*\*", re.MULTILINE)

# T-P0-2：M1 的 DoD-M1-6 必须指向具体 baseline 工件
M1_BASELINE_PATH_RE = re.compile(r"artifacts/M0/baseline-swebench\.json")

# 破冻事件关键词
FREEZE_BREAK_RE = re.compile(r"破冻|emergency\s*(?:ADR|break)", re.IGNORECASE)

# ADR 引用
ADR_REF_RE = re.compile(r"ADR-\d{4}")

# 证据识别：箭头 + 任意非空、"证据:"、commit 哈希、路径（.md/.py/.json/.log/.yaml 等）
EVIDENCE_TOKENS = [
    re.compile(r"→\s*\S"),
    re.compile(r"证据[:：]\s*\S"),
    re.compile(r"\bcommit\s+[0-9a-fA-F]{7,}"),
    re.compile(r"`[0-9a-fA-F]{7,40}`"),
    re.compile(r"\.(md|py|json|log|yaml|yml|ipynb|toml|sh|ts|rs|go)\b"),
    re.compile(r"https?://"),
]


# =====================================================================
# 数据结构
# =====================================================================

@dataclass
class Violation:
    severity: str
    rule_id: str
    file: str
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    violations: list[Violation] = field(default_factory=list)
    milestones_scanned: int = 0
    retrospectives_scanned: int = 0
    dods_total: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


@dataclass
class PlanInfo:
    path: Path
    relpath: str
    milestone: str            # "M0", "M1", ...
    text: str
    dods: dict[str, int]      # id → line
    steps: list[tuple[int, int, str]]  # (step_n, line, title)


@dataclass
class RetroInfo:
    path: Path
    relpath: str
    milestone: str
    text: str
    dods: dict[str, tuple[str, int, str]]  # id → (mark, line, rest-of-line)


# =====================================================================
# 校验器
# =====================================================================

class MilestoneChecker:
    def __init__(self, root: Path, strict: bool) -> None:
        self.root = root
        self.milestones_dir = root / "docs" / "milestones"
        self.strict = strict
        self.report = Report()
        self.plans: dict[str, PlanInfo] = {}
        self.retros: dict[str, RetroInfo] = {}

    def _err(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("error", rule_id, file, msg, line))

    def _warn(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("warning", rule_id, file, msg, line))

    def _relpath(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace(os.sep, "/")

    # -- 扫描 --

    def scan_plans(self) -> None:
        if not self.milestones_dir.is_dir():
            return
        for p in sorted(self.milestones_dir.glob("M*-plan.md")):
            m = re.match(r"^M(\d+)-plan\.md$", p.name)
            if not m:
                continue
            milestone = f"M{m.group(1)}"
            text = p.read_text(encoding="utf-8", errors="replace")

            dods: dict[str, int] = {}
            for mm in PLAN_DOD_RE.finditer(text):
                did = mm.group("id")
                line = text.count("\n", 0, mm.start()) + 1
                if did in dods:
                    self._err("D-DoD-DUP", self._relpath(p),
                              f"DoD '{did}' 在 plan 中重复定义", line=line)
                dods[did] = line

            steps = []
            for mm in PLAN_STEP_RE.finditer(text):
                line = text.count("\n", 0, mm.start()) + 1
                steps.append((int(mm.group("n")), line, mm.group("title").strip()))

            self.plans[milestone] = PlanInfo(
                path=p,
                relpath=self._relpath(p),
                milestone=milestone,
                text=text,
                dods=dods,
                steps=steps,
            )
            self.report.milestones_scanned += 1
            self.report.dods_total += len(dods)

    def scan_retrospectives(self) -> None:
        if not self.milestones_dir.is_dir():
            return
        for p in sorted(self.milestones_dir.glob("M*-retrospective.md")):
            m = re.match(r"^M(\d+)-retrospective\.md$", p.name)
            if not m:
                continue
            milestone = f"M{m.group(1)}"
            text = p.read_text(encoding="utf-8", errors="replace")

            dods: dict[str, tuple[str, int, str]] = {}
            for mm in RETRO_DOD_RE.finditer(text):
                did = mm.group("id")
                line = text.count("\n", 0, mm.start()) + 1
                mark = mm.group("mark").lower()
                rest = mm.group("rest")
                if did in dods:
                    self._err("D-DoD-DUP", self._relpath(p),
                              f"DoD '{did}' 在 retrospective 中重复出现", line=line)
                dods[did] = (mark, line, rest)

            self.retros[milestone] = RetroInfo(
                path=p,
                relpath=self._relpath(p),
                milestone=milestone,
                text=text,
                dods=dods,
            )
            self.report.retrospectives_scanned += 1

    # -- 规则 --

    def check_plan_has_dods(self) -> None:
        for m, plan in self.plans.items():
            if not plan.dods:
                self._err("D-DoD-EMPTY", plan.relpath,
                          f"{m}-plan.md §1 未检出任何 DoD（模式：`- **DoD-...**:`）")

    def check_step_has_next_conditions(self) -> None:
        for m, plan in self.plans.items():
            if not plan.steps:
                continue
            # 大致数量匹配：**进入下一步条件** 出现次数应接近 Step 数
            nexts = PLAN_NEXT_COND_RE.findall(plan.text)
            if len(nexts) < len(plan.steps) - 1:  # 最后一 Step 可以不要
                self._warn("D-STEP-NEXT", plan.relpath,
                           f"Step 数 {len(plan.steps)} 但 '**进入下一步条件**' "
                           f"出现 {len(nexts)} 次；可能某 Step 遗漏该小节")

    def check_m1_baseline_reference(self) -> None:
        """T-P0-2：M1 的 DoD-M1-6 必须引用冻结的 baseline 工件路径。"""
        plan = self.plans.get("M1")
        if plan is None:
            return
        line_no = plan.dods.get("DoD-M1-6")
        if line_no is None:
            return
        line = plan.text.splitlines()[line_no - 1]
        if not M1_BASELINE_PATH_RE.search(line):
            self._err("D-DoD-BASELINE", plan.relpath,
                      "DoD-M1-6 未引用 `artifacts/M0/baseline-swebench.json`；"
                      "无法将 resolved rate 阈值绑定到冻结基线",
                      line=line_no)

    def check_retro_closure(self) -> None:
        """每条 plan 的 DoD 必须在对应 retrospective 出现；未出现视为 error。"""
        for m, plan in self.plans.items():
            retro = self.retros.get(m)
            if retro is None:
                # 无 retrospective 时不强制（Milestone 未收尾）；仅 info
                continue
            plan_ids = set(plan.dods)
            retro_ids = set(retro.dods)

            missing = plan_ids - retro_ids
            extra = retro_ids - plan_ids

            for mid in sorted(missing):
                self._err("D-DoD-CLOSURE", retro.relpath,
                          f"retrospective 缺 '{mid}'（plan 中定义行 {plan.dods[mid]}）")
            for eid in sorted(extra):
                _, ln, _ = retro.dods[eid]
                self._err("D-DoD-CLOSURE", retro.relpath,
                          f"retrospective 出现未在 plan 中定义的 '{eid}'", line=ln)

            # 顺序检查（告警）：retro 中 DoD 出现顺序应与 plan 一致
            retro_order = [did for did in retro.dods if did in plan_ids]
            plan_order = [did for did in plan.dods if did in retro_ids]
            if retro_order != plan_order:
                self._warn("D-DoD-ORDER", retro.relpath,
                           "retrospective 中 DoD 出现顺序与 plan 不一致；"
                           "建议按 plan 顺序列出便于比对")

    def check_retro_marks(self) -> None:
        """勾选状态 + 证据链接校验。"""
        for m, retro in self.retros.items():
            for did, (mark, ln, rest) in retro.dods.items():
                rest_stripped = rest.strip()
                if mark == "x":
                    if not self._has_evidence(rest):
                        self._err("D-DoD-EVIDENCE", retro.relpath,
                                  f"'{did}' 勾选 [x] 但本行未见证据链接；"
                                  f"应含 '→'、'证据:'、commit 哈希或文件路径之一",
                                  line=ln)
                elif mark == " ":
                    self._err("D-DoD-UNCHECKED", retro.relpath,
                              f"'{did}' 未勾选；Milestone 验收禁止留空",
                              line=ln)
                elif mark == "~":
                    self._err("D-DoD-PARTIAL", retro.relpath,
                              f"'{did}' 标记 [~] partially_done；"
                              f"Milestone 验收前必须清零或转为下 Milestone backlog",
                              line=ln)
                elif mark == "-":
                    # N/A：必须附不适用原因（rest 非空）
                    if not rest_stripped:
                        self._err("D-DoD-NA", retro.relpath,
                                  f"'{did}' 标记 [-] N/A 但未附不适用原因",
                                  line=ln)
                    # 强 N/A 场景下，最好附 ADR
                    if not ADR_REF_RE.search(rest):
                        self._warn("D-DoD-NA-ADR", retro.relpath,
                                   f"'{did}' 标记 [-] 未引用 ADR；"
                                   f"若属 DoD 豁免应走 ADR 流程",
                                   line=ln)

    def _has_evidence(self, rest: str) -> bool:
        return any(pat.search(rest) for pat in EVIDENCE_TOKENS)

    def check_freeze_break(self) -> None:
        """破冻事件需在 retrospective 登记并引用 ADR。"""
        for m, retro in self.retros.items():
            breaks = list(FREEZE_BREAK_RE.finditer(retro.text))
            if not breaks:
                continue
            adrs_found = ADR_REF_RE.findall(retro.text)
            if not adrs_found:
                self._err("D-FREEZE-ADR", retro.relpath,
                          f"retrospective 出现破冻事件但未引用任何 ADR；"
                          f"按 spec-change-policy §7 S-FREEZE-2 必须附 ADR")
            else:
                self._warn("D-FREEZE-OK", retro.relpath,
                           f"retrospective 登记破冻事件并引用 ADR: "
                           f"{', '.join(sorted(set(adrs_found)))}（仅提示）")

    def check_retro_has_acceptance_header(self) -> None:
        """retrospective 应含 `Milestone M<N> 验收` 格式首行（来自 C-2 §4）。"""
        pat = re.compile(r"Milestone\s+M\d+\s+验收", re.IGNORECASE)
        for m, retro in self.retros.items():
            head = "\n".join(retro.text.splitlines()[:20])
            if not pat.search(head):
                self._warn("D-RETRO-HEADER", retro.relpath,
                           "首部 20 行未找到 'Milestone M<N> 验收' 标题；"
                           "建议按 C-2 §4 模板开头")

    # -- 主入口 --

    def run(self) -> Report:
        if not self.milestones_dir.is_dir():
            self._err("D-DIR", str(self.milestones_dir),
                      "docs/milestones/ 目录不存在")
            return self.report
        self.scan_plans()
        self.scan_retrospectives()
        self.check_plan_has_dods()
        self.check_step_has_next_conditions()
        self.check_m1_baseline_reference()
        self.check_retro_closure()
        self.check_retro_marks()
        self.check_freeze_break()
        self.check_retro_has_acceptance_header()
        return self.report


# =====================================================================
# CLI
# =====================================================================

def format_human(rep: Report) -> str:
    lines: list[str] = [
        f"扫描 plan: {rep.milestones_scanned}",
        f"扫描 retrospective: {rep.retrospectives_scanned}",
        f"DoD 总数: {rep.dods_total}",
        f"错误: {len(rep.errors())}   警告: {len(rep.warnings())}",
        "",
    ]
    if rep.errors():
        lines.append("=== ERRORS ===")
        for v in rep.errors():
            loc = f":{v.line}" if v.line else ""
            lines.append(f"  [ERR][{v.rule_id}] {v.file}{loc}: {v.message}")
        lines.append("")
    if rep.warnings():
        lines.append("=== WARNINGS ===")
        for v in rep.warnings():
            loc = f":{v.line}" if v.line else ""
            lines.append(f"  [WARN][{v.rule_id}] {v.file}{loc}: {v.message}")
        lines.append("")
    if not rep.errors() and not rep.warnings():
        lines.append("全部通过。")
    return "\n".join(lines)


def format_json(rep: Report) -> str:
    return json.dumps({
        "milestones_scanned": rep.milestones_scanned,
        "retrospectives_scanned": rep.retrospectives_scanned,
        "dods_total": rep.dods_total,
        "errors": [v.to_dict() for v in rep.errors()],
        "warnings": [v.to_dict() for v in rep.warnings()],
    }, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PhoenixAgent Milestone DoD 校验器")
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: --root {root} 不存在\n")
        return 1

    checker = MilestoneChecker(root=root, strict=args.strict)
    rep = checker.run()
    print(format_json(rep) if args.json else format_human(rep))

    if rep.errors():
        return 2
    if args.strict and rep.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
