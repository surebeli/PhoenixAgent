#!/usr/bin/env python3
"""
ci-check-spec.py — PhoenixAgent 4 件套 + 规划治理文档 ID 闭环与交叉引用校验器

规则来源：
    docs/rules/documentation-rules.md §8
    docs/rules/spec-change-policy.md S-VER-*

本脚本校验：
    - Tier-0 4 件套（PRD / TRD / RnD / SPEC）版本号齐备（D-LLM-4）
    - 跨文档 ID 引用无悬空（D-REF-1/2）
    - SPEC 引用必须带版本号，且不得使用模糊占位版本（D-REF-2）
    - M*-plan §0 列出四件套基线版本（D-REF-3）
    - 4 件套未反向引用 M*-plan（D-REF-4）
    - rules/* 未反向引用 PRD/TRD（D-REF-5）
    - docs/ 根目录无散落 .md（D-DIR-2）
    - 变更日志章节存在（§5.3；告警）

用法:
    python tools/ci-check-spec.py [--root <repo_root>] [--strict] [--json]

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

TIER0 = {
    "PRD.md":          {"prefixes": [r"FR-\d{2}", r"NFR-\d{2}", r"OOS-\d{2}"]},
    "TRD.md":          {"prefixes": [r"D-[A-Z]{2}(?:-\d)?", r"SEC-\d{2}"]},
    "RnD-Analysis.md": {"prefixes": [r"R-[A-Z]{2}-\d", r"OP-\d{2}"]},
    "SPEC.md":         {"prefixes": [r"INV-[A-Z]{2}-\d"]},
}

# 每类 ID 的 "归属文档"：跨文档引用闭环检查时，ID 必须在其归属文档里"被定义"
ID_HOME: dict[str, str] = {
    "FR": "PRD.md", "NFR": "PRD.md", "OOS": "PRD.md",
    "D": "TRD.md", "SEC": "TRD.md",
    "R": "RnD-Analysis.md", "OP": "RnD-Analysis.md",
    "INV": "SPEC.md",
}

# 架构层代码：仅 TRD §4 八层 + RnD / SPEC 沿用
LAYER_CODES = r"(?:RT|ML|HR|PL|MM|EV|AR|TL)"

# ID 识别正则（用于扫描文档中的 ID 出现）
# 注意：D-[A-Z]{2} 限制为层代码，避免误吞 documentation-rules 自定义的 D-ID/D-REF/D-LLM/D-DIR 等
ID_PATTERN = re.compile(
    r"\b("
    rf"FR-\d{{2,3}}|NFR-\d{{2,3}}|OOS-\d{{2,3}}|"
    rf"D-{LAYER_CODES}(?:-\d)?|SEC-\d{{2}}|"
    rf"R-{LAYER_CODES}-\d|OP-\d{{2}}|"
    rf"INV-{LAYER_CODES}-\d"
    r")\b"
)

# 定义点识别（文档治理规则 v1.1）：
#   - 标题首词： "#### FR-01 xxx"
#   - 加粗首词： "**FR-01**" / "- **FR-01**"
#   - 列表首词： "- INV-EV-1：..."
#   - 表格首列： "| R-ML-1 | ... |"
# 其中表格首列需单独按行识别。
DEF_PATTERN = re.compile(
    rf"(?:^#{{2,4}}\s+|\*\*(?:决策\s+)?)("
    rf"FR-\d{{2,3}}|NFR-\d{{2,3}}|OOS-\d{{2,3}}|"
    rf"D-{LAYER_CODES}(?:-\d)?|SEC-\d{{2}}|"
    rf"R-{LAYER_CODES}-\d|OP-\d{{2}}|INV-{LAYER_CODES}-\d"
    r")",
    re.MULTILINE,
)
LIST_DEF_PATTERN = re.compile(
    rf"^\s*[-*]\s+(?:\*\*)?("
    rf"FR-\d{{2,3}}|NFR-\d{{2,3}}|OOS-\d{{2,3}}|"
    rf"D-{LAYER_CODES}(?:-\d)?|SEC-\d{{2}}|"
    rf"R-{LAYER_CODES}-\d|OP-\d{{2}}|INV-{LAYER_CODES}-\d"
    r")(?:\*\*)?(?:[:：]\s*|\s+)"
)
TABLE_ROW_DEF_PATTERN = re.compile(
    rf"^\|\s*("
    rf"FR-\d{{2,3}}|NFR-\d{{2,3}}|OOS-\d{{2,3}}|"
    rf"D-{LAYER_CODES}(?:-\d)?|SEC-\d{{2}}|"
    rf"R-{LAYER_CODES}-\d|OP-\d{{2}}|INV-{LAYER_CODES}-\d"
    r")\s*\|"
)

# "层组"引用：D-RT / R-MM / INV-EV 等不带 -N 后缀的裸层代码
GROUP_REF_RE = re.compile(rf"^(D|R|INV)-{LAYER_CODES}$")

# 文件树行：含 Unicode box-drawing 字符
TREE_LINE_CHARS = set("│├└─")

VERSION_HEADER_RE = re.compile(r"^-\s*版本：\s*v(\d+\.\d+(?:\.\d+)?)", re.MULTILINE)
SPEC_REF_WITH_VER_RE = re.compile(r"SPEC\s+v\d+\.\d+(?:\.\d+)?\s*§")
# SPEC 引用但没跟版本（"SPEC §5.2" 或 "见 SPEC 第 5 章"）
SPEC_REF_NO_VER_RE = re.compile(r"SPEC(?!\s*v\d|\.md)\s*(?:§|第)")
SPEC_REF_AMBIGUOUS_VER_RE = re.compile(
    r"SPEC\s+(?:v\d+\.x(?:\s*§)?|v\d+\.\d+\s*/\s*v\d+\.x)"
)

MILESTONE_PLAN_REF_RE = re.compile(r"M\d+-plan\.md|docs/milestones/M\d+-plan")
MILESTONE_PREFIX_IN_SEC0_RE = re.compile(
    r"##\s*0\.[^\n]*启动前提", re.MULTILINE
)

TIER1_DIRS = {"milestones", "adr", "migrations"}
TIER2_DIRS = {"rules", "quality"}
TIER3_DIR = "teaching"


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
    docs_scanned: int = 0
    ids_discovered: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


@dataclass
class DocInfo:
    path: Path
    relpath: str
    text: str
    version: str | None
    defined_ids: set[str] = field(default_factory=set)
    referenced_ids: dict[str, list[int]] = field(default_factory=dict)


# =====================================================================
# 校验器
# =====================================================================

class SpecChecker:
    def __init__(self, root: Path, strict: bool) -> None:
        self.root = root
        self.docs_dir = root / "docs"
        self.strict = strict
        self.report = Report()
        self.all_defined: dict[str, str] = {}  # id → first doc that defined it
        self.docs: dict[str, DocInfo] = {}     # relpath → DocInfo

    def _err(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("error", rule_id, file, msg, line))

    def _warn(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("warning", rule_id, file, msg, line))

    # -- 扫描 --

    def _iter_docs(self) -> list[Path]:
        out: list[Path] = []
        if not self.docs_dir.is_dir():
            return out
        for p in self.docs_dir.rglob("*.md"):
            rel = p.relative_to(self.root).parts
            # 跳过教学层（由 ci-check-teaching.py 管）
            if len(rel) >= 2 and rel[1] == TIER3_DIR:
                continue
            out.append(p)
        return sorted(out)

    def _relpath(self, p: Path) -> str:
        return str(p.relative_to(self.root)).replace(os.sep, "/")

    def _extract_version(self, text: str) -> str | None:
        m = VERSION_HEADER_RE.search(text[:1000])
        return "v" + m.group(1) if m else None

    def _collect_definitions(self, text: str) -> set[str]:
        defs = {m.group(1) for m in DEF_PATTERN.finditer(text)}
        in_fence = False
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = LIST_DEF_PATTERN.match(line)
            if m:
                defs.add(m.group(1))
                continue
            m = TABLE_ROW_DEF_PATTERN.match(line)
            if m:
                defs.add(m.group(1))
        return defs

    def _collect_references(self, text: str) -> dict[str, list[int]]:
        """按行扫描，跳过代码 fence / 文件树，收集所有 ID 引用位置。"""
        refs: dict[str, list[int]] = {}
        in_fence = False
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            # 跳过显式缩进代码块
            if line.startswith("    ") and not stripped.startswith("- "):
                continue
            # 跳过 ASCII / Unicode 文件树行
            if any(c in TREE_LINE_CHARS for c in line):
                continue
            for m in ID_PATTERN.finditer(line):
                refs.setdefault(m.group(1), []).append(i)
        return refs

    def pass1_parse(self) -> None:
        for p in self._iter_docs():
            rel = self._relpath(p)
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                self._err("D-IO", rel, f"读取失败：{e}")
                continue
            info = DocInfo(
                path=p,
                relpath=rel,
                text=text,
                version=self._extract_version(text),
                defined_ids=self._collect_definitions(text),
                referenced_ids=self._collect_references(text),
            )
            self.docs[rel] = info
            for i in info.defined_ids:
                self.all_defined.setdefault(i, rel)
            self.report.docs_scanned += 1
        self.report.ids_discovered = len(self.all_defined)

    # -- 各规则 --

    def check_tier0_versions(self) -> None:
        for name in TIER0:
            rel = f"docs/{name}"
            info = self.docs.get(rel)
            if not info:
                self._err("D-LLM-4", rel, "Tier-0 文档缺失")
                continue
            if not info.version:
                self._err("D-LLM-4", rel, "首部缺少 '- 版本：vX.Y' 行")

    def check_id_closure(self) -> None:
        """
        每个被引用的 ID 必须在 ID_HOME[prefix] 对应的归属文档中有定义。
        层组引用（D-RT / R-MM / INV-EV 等不带 -N 后缀）若该 layer 下有 ≥1 个具体 ID 定义即视为闭合。
        """
        for rel, info in self.docs.items():
            for rid, lines in info.referenced_ids.items():
                prefix = rid.split("-", 1)[0]
                home = ID_HOME.get(prefix)
                if not home:
                    continue
                home_rel = f"docs/{home}"
                home_info = self.docs.get(home_rel)
                if not home_info:
                    self._err("D-REF-1", rel,
                              f"引用 ID '{rid}' 的归属文档 '{home_rel}' 缺失")
                    continue

                # 层组引用：rid 形如 D-RT / R-MM / INV-EV；home 定义了 D-RT-1 即闭合
                if GROUP_REF_RE.match(rid):
                    if any(d.startswith(rid + "-") for d in home_info.defined_ids):
                        continue

                if rid in home_info.defined_ids:
                    continue

                mentioned_in_home = rid in home_info.referenced_ids
                ln = lines[0] if lines else None
                if mentioned_in_home:
                    self._warn("D-REF-1", rel,
                               f"'{rid}' 在 {home_rel} 中仅以引用形式出现，"
                               f"未检测到定义（heading 或加粗首词）；若是新 ID 请补齐定义点",
                               line=ln)
                else:
                    self._err("D-REF-1", rel,
                              f"'{rid}' 在归属文档 {home_rel} 中不存在",
                              line=ln)

    def check_spec_ref_versioned(self) -> None:
        """SPEC 引用必须带版本号（D-REF-2），但：
           - SPEC.md 自身不检查
           - 允许 "SPEC.md" / "docs/SPEC.md" 这种纯文件路径引用
           - ADR / docs/README.md / 变更日志中的历史版本叙述可保留
        """
        for rel, info in self.docs.items():
            if rel == "docs/SPEC.md":
                continue
            if rel == "docs/README.md" or rel.startswith("docs/adr/"):
                continue
            in_fence = False
            in_changelog = False
            for i, line in enumerate(info.text.splitlines(), start=1):
                stripped = line.lstrip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if stripped.startswith("## "):
                    in_changelog = "变更日志" in stripped
                if in_changelog:
                    continue
                if SPEC_REF_AMBIGUOUS_VER_RE.search(line):
                    self._err("D-REF-2", rel,
                              f"引用 SPEC 使用模糊版本号：'{line.strip()[:80]}'",
                              line=i)
                    continue
                if SPEC_REF_NO_VER_RE.search(line):
                    # 若本行同时也有 "SPEC v1.2 §" 这类精确引用则跳过
                    if SPEC_REF_WITH_VER_RE.search(line):
                        continue
                    # 排除引用代码示例
                    if line.startswith("    "):
                        continue
                    self._err("D-REF-2", rel,
                              f"引用 SPEC 未带版本号：'{line.strip()[:80]}'",
                              line=i)

    def check_milestone_plan_section0(self) -> None:
        """M*-plan.md §0 启动前提必须列出四件套基线版本（D-REF-3）。"""
        for rel, info in self.docs.items():
            if not rel.startswith("docs/milestones/M") or not rel.endswith("-plan.md"):
                continue
            m = MILESTONE_PREFIX_IN_SEC0_RE.search(info.text)
            if not m:
                if rel == "docs/milestones/M0-plan.md":
                    continue
                self._warn("D-REF-3", rel,
                           "未找到 '## 0. ... 启动前提' 章节；"
                           "首个 Milestone（M0）可豁免，M1 起应显式列出")
                continue
            # 截取 §0 到下一 ## 之前
            start = m.start()
            end_m = re.search(r"\n## \d", info.text[start + 1:])
            section = info.text[start: start + 1 + (end_m.start() if end_m else len(info.text))]
            missing = []
            # 允许方式：§0 内含 "SPEC v1.1" / "PRD v1.0" / "TRD v1.0" 这类显式版本
            # 或含 "上位文档：PRD.md ..." 且首部 §0 之上已声明
            for tier0 in ["SPEC", "PRD", "TRD"]:
                if not re.search(rf"{tier0}\s+v\d+\.\d+", section):
                    # 作为宽松兜底，允许 §0 外的顶部元信息（文件首 10 行）提及 vX.Y
                    head = "\n".join(info.text.splitlines()[:15])
                    if not re.search(rf"{tier0}(?:\.md)?\s+v\d+\.\d+", head):
                        missing.append(tier0)
            if missing:
                self._warn("D-REF-3", rel,
                           f"§0 启动前提未显式冻结版本号：缺少 {missing}")

    def check_tier0_not_ref_milestone(self) -> None:
        """4 件套 PRD/TRD/RnD/SPEC 不得引用 M*-plan（D-REF-4）。

        排除：代码 fence 内 / 文件树行 / 目录清单列表项中单纯提及文件名。
        真违规：正文段落中跨引 M*-plan 的章节或任务。
        """
        for name in TIER0:
            rel = f"docs/{name}"
            info = self.docs.get(rel)
            if not info:
                continue
            in_fence = False
            for i, line in enumerate(info.text.splitlines(), start=1):
                stripped = line.lstrip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if any(c in TREE_LINE_CHARS for c in line):
                    continue
                if not MILESTONE_PLAN_REF_RE.search(line):
                    continue
                # 若是"目录清单列表项只提文件名"（无章节 §X / Step N 引用），降级告警
                if re.search(r"§\d|Step\s+\d", line):
                    self._err("D-REF-4", rel,
                              f"Tier-0 文档反向引用 M*-plan 章节：'{line.strip()[:80]}'",
                              line=i)
                else:
                    self._warn("D-REF-4", rel,
                               f"Tier-0 文档提及 M*-plan 文件名（未跨引章节）："
                               f"'{line.strip()[:80]}'",
                               line=i)

    def check_rules_not_ref_prd_trd(self) -> None:
        """rules/*.md 不得反向引用 PRD/TRD（D-REF-5）。

        判定：正文中（非"上位依据"行）出现 'PRD §' / 'TRD §' 视为违规。
        允许：
            - "上位依据/下位依据" 行的文件级提及
            - 代码 fence 内
            - 行内代码 `...` 内（例如规则举例 `TRD §5`）
            - 规则定义行（以 `- **D-` 或 `**D-` 开头，用于举例）
        """
        inline_code_re = re.compile(r"`[^`]*`")
        for rel, info in self.docs.items():
            if not rel.startswith("docs/rules/"):
                continue
            in_fence = False
            for i, line in enumerate(info.text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if stripped.startswith("- 上位依据") or stripped.startswith("- 下位依据"):
                    continue
                # 规则定义示例行：以 - **D-...**: 开头的行，内部可能引用 `TRD §X` 作为示例
                if re.match(r"^-?\s*\*\*D-[A-Z]+-\d+\*\*", stripped):
                    continue
                # 剥掉行内代码后再判断
                line_no_code = inline_code_re.sub("", line)
                if re.search(r"\bPRD\s+§|\bTRD\s+§", line_no_code):
                    self._err("D-REF-5", rel,
                              f"rules 反向引用 PRD/TRD 章节：'{stripped[:80]}'",
                              line=i)

    def check_docs_root_no_stray(self) -> None:
        """docs/ 根目录只允许 4 件套 + README.md + `documentation-rules §7` 明列的
        A-1/A-2 根级治理文档。其他散落 .md 违规（D-DIR-2）。
        """
        if not self.docs_dir.is_dir():
            return
        allowed = set(TIER0.keys()) | {"README.md", "roadmap.md", "risk-register.md"}
        for p in self.docs_dir.iterdir():
            if not p.is_file():
                continue
            if p.suffix != ".md":
                continue
            if p.name not in allowed:
                self._err("D-DIR-2", self._relpath(p),
                          f"docs/ 根目录散落 .md：'{p.name}'；必须归入子目录")

    def check_changelog_sections(self) -> None:
        """Tier-0/1/2 文档末尾应含 '变更日志' 章节（§5.3；告警）。"""
        targets = [rel for rel in self.docs
                   if rel.startswith("docs/") and (
                       rel in {f"docs/{n}" for n in TIER0}
                       or rel.startswith("docs/rules/")
                       or rel.startswith("docs/quality/")
                       or rel.startswith("docs/milestones/")
                   )]
        for rel in targets:
            info = self.docs[rel]
            if "变更日志" not in info.text and "## 变更日志" not in info.text:
                self._warn("D-CHANGELOG", rel, "缺少 '变更日志' 章节")

    # -- 主入口 --

    def run(self) -> Report:
        if not self.docs_dir.is_dir():
            self._err("D-DIR", "docs/", "docs/ 目录不存在")
            return self.report
        self.pass1_parse()
        self.check_tier0_versions()
        self.check_id_closure()
        self.check_spec_ref_versioned()
        self.check_milestone_plan_section0()
        self.check_tier0_not_ref_milestone()
        self.check_rules_not_ref_prd_trd()
        self.check_docs_root_no_stray()
        self.check_changelog_sections()
        return self.report


# =====================================================================
# CLI
# =====================================================================

def format_human(rep: Report) -> str:
    lines: list[str] = [
        f"扫描文档: {rep.docs_scanned}",
        f"发现 ID 定义: {rep.ids_discovered}",
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
        "docs_scanned": rep.docs_scanned,
        "ids_discovered": rep.ids_discovered,
        "errors": [v.to_dict() for v in rep.errors()],
        "warnings": [v.to_dict() for v in rep.warnings()],
    }, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="PhoenixAgent 4 件套 + 规划治理文档校验器"
    )
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--strict", action="store_true", help="严格模式：warning 升级为失败")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: --root {root} 不存在\n")
        return 1

    checker = SpecChecker(root=root, strict=args.strict)
    rep = checker.run()
    print(format_json(rep) if args.json else format_human(rep))

    if rep.errors():
        return 2
    if args.strict and rep.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
