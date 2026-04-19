#!/usr/bin/env python3
"""
ci-check-adr.py — PhoenixAgent ADR 体系结构与 frontmatter 校验器（占位实现）

规则来源：
    docs/adr/README.md §3 / §4 / §6 / §7
    docs/adr/ADR-0000-adopt-adr.md §8 follow-up "C-9"

本脚本校验：
    - docs/adr/ 目录只允许 README.md / ADR-TEMPLATE.md / ADR-NNNN-<slug>.md
    - 文件名 ADR-NNNN-<slug>.md 合法（NNNN 四位零填充；slug kebab-case ≤60 字符；a-z0-9-）
    - frontmatter 必填字段齐备（id / title / status / date / authors）
    - id 与文件名一致
    - 编号无重复
    - status ∈ {Proposed, Accepted, Rejected, Superseded, Deprecated}
    - Superseded 状态必须带 superseded_by 字段
    - date 为 YYYY-MM-DD
    - ADR-TEMPLATE.md 未被误用（id 仍为 ADR-NNNN 字面量；告警）

用法:
    python tools/ci-check-adr.py [--root <repo_root>] [--strict] [--json]

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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# =====================================================================
# 常量
# =====================================================================

ADR_DIR_REL = "docs/adr"

FILENAME_RE = re.compile(r"^ADR-(\d{4})-([a-z0-9][a-z0-9-]*)\.md$")
SLUG_MAX_LEN = 60

ALLOWED_STATUS = {"Proposed", "Accepted", "Rejected", "Superseded", "Deprecated"}
REQUIRED_FIELDS = ("id", "title", "status", "date", "authors")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^ADR-(\d{4}|NNNN)$")


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
    adrs_scanned: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


# =====================================================================
# 极简 YAML frontmatter 解析（仅支持 ADR frontmatter 里用到的标量 / 行内列表 / null）
# =====================================================================

def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s.lower() == "null" or s == "~":
        return None
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(",")]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    body = m.group(1)
    out: dict[str, Any] = {}
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        # 丢弃行内注释（# 在字符串外视为注释，这里简化为首个 " #" 之前截断）
        if " #" in value:
            value = value.split(" #", 1)[0]
        out[key.strip()] = _parse_scalar(value)
    return out


# =====================================================================
# 校验器
# =====================================================================

class AdrChecker:
    def __init__(self, root: Path, strict: bool) -> None:
        self.root = root
        self.adr_dir = root / ADR_DIR_REL
        self.strict = strict
        self.report = Report()

    def _err(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("error", rule_id, file, msg, line))

    def _warn(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("warning", rule_id, file, msg, line))

    def _relpath(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace(os.sep, "/")

    # -- 目录与命名 --

    def scan_directory(self) -> list[Path]:
        if not self.adr_dir.is_dir():
            self._err("ADR-DIR", ADR_DIR_REL, "ADR 目录不存在")
            return []
        adrs: list[Path] = []
        allowed_sidecar = {"README.md", "ADR-TEMPLATE.md"}
        for p in sorted(self.adr_dir.iterdir()):
            if not p.is_file():
                continue
            rel = self._relpath(p)
            name = p.name
            if p.suffix != ".md":
                self._err("ADR-DIR-1", rel, f"ADR 目录内存在非 .md 文件：'{name}'")
                continue
            if name in allowed_sidecar:
                continue
            if not FILENAME_RE.match(name):
                self._err("ADR-NAME-1", rel,
                          f"文件名不符合 'ADR-NNNN-<slug>.md' 约束（NNNN 四位，slug kebab-case）")
                continue
            slug = FILENAME_RE.match(name).group(2)
            if len(slug) > SLUG_MAX_LEN:
                self._err("ADR-NAME-2", rel,
                          f"slug 长度 {len(slug)} 超过上限 {SLUG_MAX_LEN}")
            adrs.append(p)
        return adrs

    # -- frontmatter 与主体 --

    def check_adr(self, path: Path) -> None:
        rel = self._relpath(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            self._err("ADR-IO", rel, f"读取失败：{e}")
            return

        fm = parse_frontmatter(text)
        if fm is None:
            self._err("ADR-FM-1", rel, "缺少 YAML frontmatter 块（--- ... ---）")
            return

        for key in REQUIRED_FIELDS:
            if key not in fm or fm[key] in (None, "", []):
                self._err("ADR-FM-2", rel, f"frontmatter 缺少必填字段 '{key}'")

        # id 与文件名匹配
        fid = fm.get("id")
        fname = path.name
        m = FILENAME_RE.match(fname)
        if fid and isinstance(fid, str):
            if not ID_RE.match(fid):
                self._err("ADR-FM-3", rel, f"id '{fid}' 非法；应为 'ADR-NNNN'")
            elif m:
                expect = f"ADR-{m.group(1)}"
                if fid != expect:
                    self._err("ADR-FM-3", rel,
                              f"frontmatter id '{fid}' 与文件名编号 '{expect}' 不一致")

        # status 合法
        status = fm.get("status")
        if status and status not in ALLOWED_STATUS:
            self._err("ADR-FM-4", rel,
                      f"status '{status}' 非法；允许值：{sorted(ALLOWED_STATUS)}")

        # Superseded 必须带 superseded_by
        if status == "Superseded":
            sb = fm.get("superseded_by")
            if not sb or sb in (None, "null"):
                self._err("ADR-FM-5", rel,
                          "status=Superseded 必须填 superseded_by 字段")

        # date 格式
        d = fm.get("date")
        if isinstance(d, str) and not DATE_RE.match(d):
            self._err("ADR-FM-6", rel, f"date '{d}' 非 YYYY-MM-DD 格式")

    # -- 编号唯一 --

    def check_unique_numbers(self, adrs: list[Path]) -> None:
        seen: dict[str, str] = {}
        for p in adrs:
            m = FILENAME_RE.match(p.name)
            if not m:
                continue
            num = m.group(1)
            rel = self._relpath(p)
            if num in seen:
                self._err("ADR-NUM-1", rel,
                          f"ADR 编号 {num} 与 '{seen[num]}' 重复")
            else:
                seen[num] = rel

    # -- 模板未被误用 --

    def check_template_not_used(self) -> None:
        tpl = self.adr_dir / "ADR-TEMPLATE.md"
        if not tpl.is_file():
            return
        try:
            text = tpl.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        fm = parse_frontmatter(text) or {}
        if fm.get("id") != "ADR-NNNN":
            self._warn("ADR-TPL-1", self._relpath(tpl),
                       "ADR-TEMPLATE.md 的 frontmatter.id 应保持字面量 'ADR-NNNN'（未被误改）")

    # -- 主入口 --

    def run(self) -> Report:
        adrs = self.scan_directory()
        self.report.adrs_scanned = len(adrs)
        for p in adrs:
            self.check_adr(p)
        self.check_unique_numbers(adrs)
        self.check_template_not_used()
        return self.report


# =====================================================================
# CLI
# =====================================================================

def format_human(rep: Report) -> str:
    lines: list[str] = [
        f"扫描 ADR: {rep.adrs_scanned}",
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
        "adrs_scanned": rep.adrs_scanned,
        "errors": [v.to_dict() for v in rep.errors()],
        "warnings": [v.to_dict() for v in rep.warnings()],
    }, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PhoenixAgent ADR 校验器")
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--strict", action="store_true", help="严格模式：warning 升级为失败")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: --root {root} 不存在\n")
        return 1

    checker = AdrChecker(root=root, strict=args.strict)
    rep = checker.run()
    print(format_json(rep) if args.json else format_human(rep))

    if rep.errors():
        return 2
    if args.strict and rep.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
