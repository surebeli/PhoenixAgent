#!/usr/bin/env python3
"""
ci-check-flags.py — HarnessFlags 治理一致性校验器（占位实现）

规则来源：
    docs/rules/harness-flags-policy.md §3 / §4 / §8
    docs/SPEC.md §5.1 HarnessFlags dataclass

本脚本校验：
    - SPEC §5.1 HarnessFlags 字段清单与 policy §3 表完全一致（字段齐、无遗漏、无多余）
    - 两侧 default 值一致（HF-ATOMIC-1）
    - Safety-Critical flag（s01 / s02 / s12）在 SPEC 与 policy 中默认值都为 True（HF-SEC-1）
    - HarnessFlags dataclass 在 SPEC 中声明为 frozen（HF-IMPL-1）

用法:
    python tools/ci-check-flags.py [--root <repo_root>] [--strict] [--json]

退出码:
    0  通过（允许 warning，除非 --strict）
    1  使用错误
    2  校验失败

依赖: 无（stdlib only）

限制（占位版）:
    - 不扫描非 phoenix.harness.* 模块对 HarnessFlags 的读取（HF-IMPL-2，未来静态检查补全）
    - 不验证 flag 翻转 PR 是否带 ADR / experiment-report（由 git-workflow + PR reviewer 承担）
    - 不解析 CLI 层 --harness-flag 行为（HF-IMPL-3，集成测试范围）
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# =====================================================================
# 常量
# =====================================================================

SPEC_REL = "docs/SPEC.md"
POLICY_REL = "docs/rules/harness-flags-policy.md"

SAFETY_CRITICAL = {"s01_main_loop", "s02_tool_dispatch", "s12_worktree"}

# SPEC §5.1 HarnessFlags dataclass 字段匹配：
#   s03_planning: bool = True
SPEC_FIELD_RE = re.compile(
    r"^\s*([a-z][a-z0-9_]*)\s*:\s*bool\s*=\s*(True|False)\s*$",
    re.MULTILINE,
)
# dataclass 装饰器（支持 @dataclass 与 @dataclass(frozen=True, ...)）
DATACLASS_DECO_RE = re.compile(r"@dataclass(?:\(([^)]*)\))?\s*\nclass\s+HarnessFlags\b")

# policy §3 表行匹配：
#   | `s03_planning` | True | M1 | Active | Non-Safety | ... |
POLICY_ROW_RE = re.compile(
    r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*(True|False)\s*\|",
    re.MULTILINE,
)


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
    spec_flags: int = 0
    policy_flags: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


# =====================================================================
# 校验器
# =====================================================================

class FlagsChecker:
    def __init__(self, root: Path, strict: bool) -> None:
        self.root = root
        self.strict = strict
        self.report = Report()

    def _err(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("error", rule_id, file, msg, line))

    def _warn(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("warning", rule_id, file, msg, line))

    def _relpath(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace(os.sep, "/")

    # -- 解析 SPEC --

    def parse_spec(self) -> tuple[dict[str, bool], bool] | None:
        """返回 (flags_dict, is_frozen)；若 SPEC 不存在 / 无 HarnessFlags 返回 None。"""
        path = self.root / SPEC_REL
        if not path.is_file():
            self._err("HF-IO", SPEC_REL, "SPEC.md 不存在")
            return None
        text = path.read_text(encoding="utf-8", errors="replace")

        m = DATACLASS_DECO_RE.search(text)
        if not m:
            self._err("HF-SPEC-1", SPEC_REL,
                      "未找到 `@dataclass ... class HarnessFlags` 定义")
            return None

        args = m.group(1) or ""
        is_frozen = bool(re.search(r"\bfrozen\s*=\s*True\b", args))
        if not is_frozen:
            self._err("HF-IMPL-1", SPEC_REL,
                      "HarnessFlags dataclass 必须声明 frozen=True（见 harness-flags-policy HF-IMPL-1）")

        # 取 HarnessFlags 类块（装饰器起、下一个空行或下一 class 结束前）
        start = m.start()
        end_m = re.search(r"\n```", text[start:])
        block = text[start: start + (end_m.start() if end_m else len(text))]

        flags: dict[str, bool] = {}
        for fm in SPEC_FIELD_RE.finditer(block):
            name = fm.group(1)
            val = fm.group(2) == "True"
            flags[name] = val

        self.report.spec_flags = len(flags)
        return flags, is_frozen

    # -- 解析 policy --

    def parse_policy(self) -> dict[str, bool] | None:
        path = self.root / POLICY_REL
        if not path.is_file():
            self._err("HF-IO", POLICY_REL, "harness-flags-policy.md 不存在")
            return None
        text = path.read_text(encoding="utf-8", errors="replace")

        flags: dict[str, bool] = {}
        for m in POLICY_ROW_RE.finditer(text):
            name = m.group(1)
            val = m.group(2) == "True"
            flags[name] = val

        if not flags:
            self._err("HF-POL-1", POLICY_REL, "§3 flag 表未解析到任何行；格式可能已变更")
            return None

        self.report.policy_flags = len(flags)
        return flags

    # -- 交叉一致性 --

    def cross_check(self, spec: dict[str, bool], policy: dict[str, bool]) -> None:
        spec_set = set(spec)
        pol_set = set(policy)

        for missing in sorted(pol_set - spec_set):
            self._err("HF-SYNC-1", SPEC_REL,
                      f"policy §3 列出的 '{missing}' 在 SPEC §5.1 HarnessFlags 中不存在")
        for extra in sorted(spec_set - pol_set):
            self._err("HF-SYNC-1", POLICY_REL,
                      f"SPEC §5.1 HarnessFlags 中的 '{extra}' 未出现在 policy §3 表")

        for name in sorted(spec_set & pol_set):
            if spec[name] != policy[name]:
                self._err("HF-SYNC-2", POLICY_REL,
                          f"'{name}' 的 default 不一致：SPEC={spec[name]} vs policy={policy[name]}")

    def check_safety_critical(self, spec: dict[str, bool], policy: dict[str, bool]) -> None:
        for name in sorted(SAFETY_CRITICAL):
            if name in spec and spec[name] is not True:
                self._err("HF-SEC-1", SPEC_REL,
                          f"Safety-Critical flag '{name}' 在 SPEC 中 default 非 True")
            if name in policy and policy[name] is not True:
                self._err("HF-SEC-1", POLICY_REL,
                          f"Safety-Critical flag '{name}' 在 policy 中 default 非 True")

    # -- 主入口 --

    def run(self) -> Report:
        spec_res = self.parse_spec()
        policy = self.parse_policy()
        if not spec_res or policy is None:
            return self.report
        spec, _frozen = spec_res
        self.cross_check(spec, policy)
        self.check_safety_critical(spec, policy)
        return self.report


# =====================================================================
# CLI
# =====================================================================

def format_human(rep: Report) -> str:
    lines: list[str] = [
        f"SPEC flags: {rep.spec_flags}   policy flags: {rep.policy_flags}",
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
        "spec_flags": rep.spec_flags,
        "policy_flags": rep.policy_flags,
        "errors": [v.to_dict() for v in rep.errors()],
        "warnings": [v.to_dict() for v in rep.warnings()],
    }, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PhoenixAgent HarnessFlags 一致性校验器")
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--strict", action="store_true", help="严格模式：warning 升级为失败")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: --root {root} 不存在\n")
        return 1

    checker = FlagsChecker(root=root, strict=args.strict)
    rep = checker.run()
    print(format_json(rep) if args.json else format_human(rep))

    if rep.errors():
        return 2
    if args.strict and rep.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
