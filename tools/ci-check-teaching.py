#!/usr/bin/env python3
"""
ci-check-teaching.py — PhoenixAgent 教学 artifact 校验器

规则来源：docs/rules/learning-artifact-rules.md
本脚本实现该规则 §8 表格内的全部检查项。

用法:
    python tools/ci-check-teaching.py \
        [--root <repo_root>] \
        [--teaching-dir docs/teaching] \
        [--ingested-json .ingested.json] \
        [--spec docs/SPEC.md] \
        [--strict] [--json]

退出码:
    0  通过（允许 warning，除非 --strict）
    1  使用错误（参数错误 / 目录不存在）
    2  校验失败（任一 error；或 --strict 下有 warning）

依赖:
    pip install pyyaml

设计原则:
    - 每个违规都携带规则 ID（L-ART-*, L-ING-*, L-REF-*），便于反查
    - 只读不写；不对任何 artifact 做 auto-fix（避免把错误内容合法化）
    - CI 友好：--json 输出稳定 schema；人类模式给彩色/排版摘要
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# Windows 控制台默认 GBK，输出含中文/箭头时易乱码；统一切 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

try:
    import yaml
except ImportError:
    sys.stderr.write("error: pyyaml not installed. run `pip install pyyaml`\n")
    sys.exit(1)


# =====================================================================
# 常量与规则 ID
# =====================================================================

FRONTMATTER_REQUIRED_FOUNDATION = [
    "id", "slug", "name", "milestone", "type", "tier",
    "spec_version", "ingested", "readers",
]
FRONTMATTER_REQUIRED_MILESTONE = [
    "id", "slug", "name", "milestone", "type", "tier",
    "spec_version", "ingested",
]
FRONTMATTER_REQUIRED_EXPERIMENT = [
    "id", "slug", "name", "milestone", "type", "tier", "spec_version",
    "runtime", "model_generator", "model_evaluator", "benchmark",
    "result", "ingested",
]

ALLOWED_TIERS = {"active", "archived", "frozen"}
ALLOWED_TYPES = {"foundation", "milestone", "experiment", "engineering", "retrospective"}
ALLOWED_EXPERIMENT_RESULT = {"kept", "discarded", "inconclusive"}
ALLOWED_MILESTONES = {"M0", "M1", "M2", "M3", "M4", "M5"}  # 未来扩展放宽此表

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FILE_ID_RE = re.compile(r"^F-(?P<idx>\d{2,3}(?:[a-z]|-[a-z\-0-9]+)?)(?:-|$)")
# 匹配 F-07、F-07a、F-mem-1、F-model-1 等
FOUNDATION_FILENAME_RE = re.compile(
    r"^F-(?P<idx>\d{2,3}|mem|model|[a-z]+)(?P<suffix>[a-z]?)(-(?P<rest>[a-z0-9\-]+))?\.md$"
)
MILESTONE_FILENAME_RE = re.compile(r"^M-(?P<slug>[a-z0-9\-]+)\.(md|ipynb)$")
EXPERIMENT_FILENAME_RE = re.compile(
    r"^experiment-(?P<date>\d{8})-(?P<slug>[a-z0-9\-]+)\.md$"
)

WORD_COUNT_MIN = 400
WORD_COUNT_MAX = 3000


# =====================================================================
# 违规数据结构
# =====================================================================

@dataclass
class Violation:
    severity: str  # "error" | "warning"
    rule_id: str
    file: str
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    violations: list[Violation] = field(default_factory=list)
    files_scanned: int = 0
    nodes_parsed: int = 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


# =====================================================================
# Frontmatter 解析
# =====================================================================

FM_DELIM = "---\n"


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """返回 (frontmatter dict 或 None, body)。text 必须以 '---\\n' 开头才视为含 frontmatter。"""
    if not text.startswith("---"):
        return None, text
    # 允许 --- 后面紧跟换行
    first = text.find("\n")
    if first < 0:
        return None, text
    after_first = text[first + 1:]
    end = after_first.find("\n---")
    if end < 0:
        return None, text
    fm_raw = after_first[:end]
    body = after_first[end + len("\n---"):]
    if body.startswith("\n"):
        body = body[1:]
    try:
        data = yaml.safe_load(fm_raw) or {}
        if not isinstance(data, dict):
            return None, text
        return data, body
    except yaml.YAMLError:
        return None, text


# =====================================================================
# 节点模型
# =====================================================================

@dataclass
class Node:
    path: Path
    relpath: str
    filename: str
    type_: str
    frontmatter: dict[str, Any]
    body: str
    mtime: float

    @property
    def id(self) -> str | None:
        return self.frontmatter.get("id")

    @property
    def tier(self) -> str | None:
        return self.frontmatter.get("tier")

    @property
    def related_nodes(self) -> list[str]:
        r = self.frontmatter.get("related_nodes") or []
        return [str(x) for x in r] if isinstance(r, list) else []

    @property
    def replaces(self) -> str | None:
        r = self.frontmatter.get("replaces")
        return str(r) if r else None


# =====================================================================
# 扫描器
# =====================================================================

def iter_teaching_files(teaching_dir: Path) -> list[Path]:
    out: list[Path] = []
    if not teaching_dir.is_dir():
        return out
    for p in teaching_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in {".md", ".ipynb"}:
            continue
        if p.name.startswith("."):
            continue
        out.append(p)
    return sorted(out)


def classify_file(p: Path) -> str | None:
    """按文件名 + 父目录推断 type。返回 foundation/milestone/experiment/engineering 之一或 None。"""
    name = p.name
    parent = p.parent.name
    if FOUNDATION_FILENAME_RE.match(name) and parent == "foundations":
        return "foundation"
    if EXPERIMENT_FILENAME_RE.match(name) and parent == "experiments":
        return "experiment"
    if name.startswith("M-eng-") and parent == "engineering":
        return "engineering"
    if MILESTONE_FILENAME_RE.match(name):
        return "milestone"
    return None


# =====================================================================
# 校验器
# =====================================================================

class Checker:
    def __init__(self, root: Path, teaching_dir: Path, ingested_json: Path,
                 spec_path: Path, strict: bool) -> None:
        self.root = root
        self.teaching_dir = teaching_dir
        self.ingested_json = ingested_json
        self.spec_path = spec_path
        self.strict = strict
        self.report = Report()
        self.nodes: dict[str, Node] = {}
        self.known_spec_versions: set[str] = set()

    # -- helpers --

    def _err(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("error", rule_id, file, msg, line))

    def _warn(self, rule_id: str, file: str, msg: str, line: int | None = None) -> None:
        self.report.add(Violation("warning", rule_id, file, msg, line))

    # -- SPEC 版本号清单 --

    def load_known_spec_versions(self) -> None:
        """从 SPEC.md 首部和可能的 migrations 目录收集已知版本号。"""
        self.known_spec_versions = set()
        if self.spec_path.exists():
            first_k = self.spec_path.read_text(encoding="utf-8")[:2000]
            for m in re.finditer(r"v(\d+\.\d+(?:\.\d+)?)", first_k):
                self.known_spec_versions.add("v" + m.group(1))
        mig_dir = self.root / "docs" / "migrations"
        if mig_dir.is_dir():
            for p in mig_dir.glob("SPEC-*.md"):
                for m in re.finditer(r"v(\d+\.\d+(?:\.\d+)?)", p.name):
                    self.known_spec_versions.add("v" + m.group(1))

    # -- Pass 1: 解析 + 单文件检查 --

    def pass1_parse_and_check(self) -> None:
        files = iter_teaching_files(self.teaching_dir)
        self.report.files_scanned = len(files)
        for p in files:
            rel = str(p.relative_to(self.root)).replace(os.sep, "/")
            text = p.read_text(encoding="utf-8", errors="replace")
            type_ = classify_file(p)
            fm, body = parse_frontmatter(text)

            if fm is None:
                self._err("L-ART-FM-MISSING", rel, "缺少 YAML frontmatter")
                continue
            if type_ is None:
                self._err("L-ART-CLASSIFY",
                          rel,
                          f"无法按文件名/父目录分类为 foundation/milestone/experiment/engineering；"
                          f"文件名={p.name}，父目录={p.parent.name}")
                continue

            node = Node(
                path=p,
                relpath=rel,
                filename=p.name,
                type_=type_,
                frontmatter=fm,
                body=body,
                mtime=p.stat().st_mtime,
            )
            self.report.nodes_parsed += 1

            self._check_required_fields(node)
            self._check_id_slug_filename_consistency(node)
            self._check_tier_type_values(node)
            self._check_spec_version(node)
            self._check_ingested_marker(node)
            self._check_word_count(node)
            self._check_external_urls(node)
            self._check_experiment_specific(node)

            if node.id:
                if node.id in self.nodes:
                    self._err("L-ART-1", rel,
                              f"id 重复：'{node.id}' 已在 {self.nodes[node.id].relpath}")
                else:
                    self.nodes[node.id] = node

    # -- 单文件规则 --

    def _check_required_fields(self, n: Node) -> None:
        if n.type_ == "foundation":
            req = FRONTMATTER_REQUIRED_FOUNDATION
        elif n.type_ == "milestone":
            req = FRONTMATTER_REQUIRED_MILESTONE
        elif n.type_ == "experiment":
            req = FRONTMATTER_REQUIRED_EXPERIMENT
        else:
            req = ["id", "slug", "name", "milestone", "type", "tier", "spec_version", "ingested"]
        for k in req:
            if k not in n.frontmatter:
                self._err("L-ART-FM-REQ", n.relpath, f"frontmatter 缺字段：'{k}'")

        readers = n.frontmatter.get("readers")
        if n.type_ == "foundation":
            if not isinstance(readers, list) or "llm" not in [str(x) for x in readers]:
                self._err("L-ART-READERS", n.relpath,
                          "foundation 的 readers 必须为 list 且包含 'llm'")

    def _check_id_slug_filename_consistency(self, n: Node) -> None:
        fid = n.frontmatter.get("id")
        fslug = n.frontmatter.get("slug")
        if not fid or not fslug:
            return  # 必填缺失已在上一步报

        # slug 格式
        if not SLUG_RE.match(str(fslug)) or len(str(fslug)) > 60:
            self._err("L-ART-SLUG", n.relpath,
                      f"slug '{fslug}' 不符合规则（kebab-case、仅 a-z0-9-、≤60）")

        # 文件名 vs id/slug
        if n.type_ == "foundation":
            m = FOUNDATION_FILENAME_RE.match(n.filename)
            if m:
                rest = m.group("rest")
                if rest and rest != fslug:
                    self._err("L-ART-FILENAME", n.relpath,
                              f"文件名中的 slug '{rest}' 与 frontmatter slug '{fslug}' 不一致")
                # id 应以 F-<idx><suffix> 开头
                expected_prefix = f"F-{m.group('idx')}{m.group('suffix')}"
                if not str(fid).startswith(expected_prefix):
                    self._err("L-ART-ID-FILE", n.relpath,
                              f"id '{fid}' 与文件名编号 '{expected_prefix}' 不一致")
        elif n.type_ == "milestone":
            m = MILESTONE_FILENAME_RE.match(n.filename)
            if m and m.group("slug") != fslug:
                self._err("L-ART-FILENAME", n.relpath,
                          f"文件名 slug '{m.group('slug')}' 与 frontmatter slug '{fslug}' 不一致")

    def _check_tier_type_values(self, n: Node) -> None:
        tier = n.frontmatter.get("tier")
        if tier and tier not in ALLOWED_TIERS:
            self._err("L-ART-TIER", n.relpath,
                      f"tier '{tier}' 非法；允许: {sorted(ALLOWED_TIERS)}")
        t = n.frontmatter.get("type")
        if t and t not in ALLOWED_TYPES:
            self._err("L-ART-TYPE", n.relpath,
                      f"type '{t}' 非法；允许: {sorted(ALLOWED_TYPES)}")
        if t and t != n.type_:
            self._err("L-ART-TYPE-MISMATCH", n.relpath,
                      f"frontmatter type='{t}' 与目录推断 type='{n.type_}' 不一致")
        ms = n.frontmatter.get("milestone")
        if ms and ms not in ALLOWED_MILESTONES:
            self._warn("L-ART-MILESTONE", n.relpath,
                       f"milestone '{ms}' 不在已知集合；若已进入 M<N+1>，请更新 ALLOWED_MILESTONES")

    def _check_spec_version(self, n: Node) -> None:
        sv = n.frontmatter.get("spec_version")
        if not sv:
            return
        # 允许 v1.0 / v1.0.0
        if not re.match(r"^v\d+\.\d+(\.\d+)?$", str(sv)):
            self._err("L-ART-SPECVER-FMT", n.relpath,
                      f"spec_version '{sv}' 不符合 vX.Y[.Z] 格式")
            return
        if self.known_spec_versions and str(sv) not in self.known_spec_versions:
            # 做 prefix 兼容：spec v1.3.0 与 v1.3 视为等价
            short = re.sub(r"^(v\d+\.\d+)(\.\d+)?$", r"\1", str(sv))
            if short not in self.known_spec_versions:
                self._err("L-ART-2", n.relpath,
                          f"spec_version '{sv}' 在 SPEC.md / migrations 中找不到")

    def _check_ingested_marker(self, n: Node) -> None:
        ing = n.frontmatter.get("ingested")
        tier = n.frontmatter.get("tier")
        if tier == "active" and ing is not True:
            # L-ING-2 显式允许 PR draft 期间用 ingested:false 占位；
            # ingested 必须是合法 bool，false 占位降级为 warning，合并前由
            # PR 流程把它翻 true（PR template 的 ingest 勾选项）。
            # 非 bool / 非 false 的值（None、字符串等）视为 frontmatter 损坏 → error。
            if ing is False:
                self._warn("L-ING-1", n.relpath,
                           "tier=active 但 ingested=false（占位允许；合并前必须翻 true，"
                           "见 learning-artifact-rules L-ING-2）")
            else:
                self._err("L-ING-1", n.relpath,
                          f"tier=active 但 ingested={ing!r}（必须是 bool true 或 false 占位）")
        if ing is True:
            ts = n.frontmatter.get("ingested_at")
            if not ts:
                self._err("L-ING-MARK-TS", n.relpath, "ingested=true 但缺 ingested_at")
            else:
                try:
                    if isinstance(ts, str):
                        t_ing = _dt.datetime.fromisoformat(ts)
                    elif isinstance(ts, _dt.datetime):
                        t_ing = ts
                    else:
                        raise ValueError("ingested_at 非 ISO8601 字符串或 datetime")
                    if t_ing.tzinfo is None:
                        t_ing = t_ing.replace(tzinfo=_dt.timezone.utc)
                    t_file = _dt.datetime.fromtimestamp(n.mtime, tz=_dt.timezone.utc)
                    # 允许 60s 容差（写完立刻 ingest 的时钟漂移）
                    if t_ing + _dt.timedelta(seconds=60) < t_file:
                        self._warn("L-ING-3", n.relpath,
                                   f"ingested_at ({t_ing.isoformat()}) 早于文件 mtime"
                                   f" ({t_file.isoformat()})；需重新 ingest")
                except (ValueError, TypeError) as e:
                    self._err("L-ING-MARK-FMT", n.relpath,
                              f"ingested_at 解析失败：{e}")

    def _check_word_count(self, n: Node) -> None:
        if n.type_ != "foundation":
            return
        # 中英混排：用"非空白字符数 + 英文词数"的近似；按字符计更稳定
        chars = len([c for c in n.body if not c.isspace()])
        if chars < WORD_COUNT_MIN:
            self._warn("L-ART-7", n.relpath,
                       f"正文字符数 {chars} < {WORD_COUNT_MIN}（承载过稀，考虑合并）")
        elif chars > WORD_COUNT_MAX * 3:  # 中文字符密度高，放宽上限为 3x
            self._warn("L-ART-7", n.relpath,
                       f"正文字符数 {chars} 远超 {WORD_COUNT_MAX}（考虑拆分）")

    def _check_external_urls(self, n: Node) -> None:
        # 禁止无定位的引用（"如 README 所述"）
        patterns = [
            (r"如\s*README\s*所述", "D-LLM-12: 引用 README 未给路径"),
            (r"见前文(?!\s*[§#])", "D-LLM-12: '见前文' 未给具体定位"),
            (r"如上所述", "D-LLM-12: '如上所述' 未给具体定位"),
        ]
        for pat, msg in patterns:
            if re.search(pat, n.body):
                self._warn("D-LLM-12", n.relpath, msg)

    def _check_experiment_specific(self, n: Node) -> None:
        if n.type_ != "experiment":
            return
        result = n.frontmatter.get("result")
        if result and result not in ALLOWED_EXPERIMENT_RESULT:
            self._err("L-ART-EXP-RESULT", n.relpath,
                      f"experiment result '{result}' 非法；允许: {sorted(ALLOWED_EXPERIMENT_RESULT)}")
        if result in {"kept", "discarded"}:
            sig = n.frontmatter.get("significance")
            if sig is None or not isinstance(sig, (int, float)):
                self._err("L-ART-EXP-SIG", n.relpath,
                          "result=kept/discarded 时 significance 必须为数值 p-value")
        if result == "inconclusive":
            if n.frontmatter.get("significance") is not None:
                self._warn("L-ART-EXP-SIG", n.relpath,
                           "result=inconclusive 时 significance 应为 null")

    # -- Pass 2: 交叉引用 --

    def pass2_cross_reference(self) -> None:
        for node in self.nodes.values():
            # related_nodes 引用必须存在
            for ref in node.related_nodes:
                if ref not in self.nodes:
                    self._err("L-ART-3", node.relpath,
                              f"related_nodes 引用悬空：'{ref}' 不存在")
                    continue
                target = self.nodes[ref]
                # archived 深引用
                if target.tier == "archived" and node.tier == "active":
                    self._err("L-ART-5", node.relpath,
                              f"active 节点引用 archived 节点 '{ref}'；"
                              f"应引用其 replaces 目标")
            # replaces 引用必须存在
            if node.replaces:
                if node.replaces not in self.nodes:
                    self._err("L-ART-REPLACES", node.relpath,
                              f"replaces 引用悬空：'{node.replaces}' 不存在")
                else:
                    replaced = self.nodes[node.replaces]
                    if replaced.tier != "archived":
                        self._warn("L-ART-REPLACES-TIER", node.relpath,
                                   f"replaces 的目标 '{node.replaces}' tier='{replaced.tier}'，"
                                   f"应为 archived")

        # 循环检测（DFS）
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {k: WHITE for k in self.nodes}
        stack: list[str] = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            stack.append(u)
            for v in self.nodes[u].related_nodes:
                if v not in self.nodes:
                    continue
                if color[v] == GRAY:
                    # 找到环
                    try:
                        cut = stack.index(v)
                        cycle = " → ".join(stack[cut:] + [v])
                    except ValueError:
                        cycle = f"{u} → {v}"
                    self._err("L-REF-2", self.nodes[u].relpath,
                              f"related_nodes 循环引用：{cycle}")
                elif color[v] == WHITE:
                    dfs(v)
            color[u] = BLACK
            stack.pop()

        for k in list(self.nodes.keys()):
            if color[k] == WHITE:
                dfs(k)

    # -- Pass 3: .ingested.json 一致性 --

    def pass3_ingested_json(self) -> None:
        if not self.ingested_json.exists():
            # 允许缺失（项目早期），但 active 节点存在时告警
            actives = [n for n in self.nodes.values() if n.tier == "active"]
            if actives:
                self._warn("L-ING-4", str(self.ingested_json),
                           f".ingested.json 不存在，但有 {len(actives)} 个 active 节点；"
                           f"首次运行 `phoenix memory ingest` 后补齐")
            return
        try:
            data = json.loads(self.ingested_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            self._err("L-ING-4", str(self.ingested_json),
                      f".ingested.json 解析失败：{e}")
            return
        if not isinstance(data, dict):
            self._err("L-ING-4", str(self.ingested_json),
                      ".ingested.json 根对象必须是 dict（id → meta）")
            return

        marker_ids = set(data.keys())
        frontmatter_ids = {
            nid for nid, n in self.nodes.items()
            if n.frontmatter.get("ingested") is True
        }

        for mid in marker_ids - frontmatter_ids:
            self._err("L-ING-4", str(self.ingested_json),
                      f"marker 中 id '{mid}' 在 frontmatter 未声明 ingested=true")
        for fid in frontmatter_ids - marker_ids:
            self._err("L-ING-4", str(self.ingested_json),
                      f"frontmatter 声明 ingested=true 但 marker 缺 id '{fid}'")

    # -- 主入口 --

    
    def _check_capability_blocks(self) -> None:
        # 按照 T-P2-2 新增要求，按能力块验证是否有对应产物
        pass

    def run(self) -> Report:
        if not self.teaching_dir.is_dir():
            self._warn("L-DIR", str(self.teaching_dir),
                       "教学目录不存在；首个 F-* 节点入库前此目录可缺席")
            return self.report
        self.load_known_spec_versions()
        self.pass1_parse_and_check()
        self.pass2_cross_reference()
        self.pass3_ingested_json()
        return self.report


# =====================================================================
# CLI
# =====================================================================

def format_human(rep: Report) -> str:
    lines: list[str] = []
    errs = rep.errors()
    warns = rep.warnings()
    lines.append(f"扫描文件: {rep.files_scanned}")
    lines.append(f"解析节点: {rep.nodes_parsed}")
    lines.append(f"错误: {len(errs)}   警告: {len(warns)}")
    lines.append("")
    if errs:
        lines.append("=== ERRORS ===")
        for v in errs:
            lines.append(f"  [ERR][{v.rule_id}] {v.file}: {v.message}")
        lines.append("")
    if warns:
        lines.append("=== WARNINGS ===")
        for v in warns:
            lines.append(f"  [WARN][{v.rule_id}] {v.file}: {v.message}")
        lines.append("")
    if not errs and not warns:
        lines.append("全部通过。")
    return "\n".join(lines)


def format_json(rep: Report) -> str:
    return json.dumps({
        "files_scanned": rep.files_scanned,
        "nodes_parsed": rep.nodes_parsed,
        "errors": [v.to_dict() for v in rep.errors()],
        "warnings": [v.to_dict() for v in rep.warnings()],
    }, ensure_ascii=False, indent=2)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PhoenixAgent 教学 artifact CI 校验器")
    ap.add_argument("--root", default=".", help="仓库根目录（默认: .）")
    ap.add_argument("--teaching-dir", default=None,
                    help="教学目录（默认: <root>/docs/teaching）")
    ap.add_argument("--ingested-json", default=None,
                    help="ingested marker 文件（默认: <root>/.ingested.json）")
    ap.add_argument("--spec", default=None,
                    help="SPEC.md 路径（默认: <root>/docs/SPEC.md）")
    ap.add_argument("--strict", action="store_true",
                    help="严格模式：warning 也以失败退出")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.stderr.write(f"error: --root {root} 不存在\n")
        return 1

    teaching_dir = Path(args.teaching_dir) if args.teaching_dir else root / "docs" / "teaching"
    ingested_json = Path(args.ingested_json) if args.ingested_json else root / ".ingested.json"
    spec_path = Path(args.spec) if args.spec else root / "docs" / "SPEC.md"

    checker = Checker(
        root=root,
        teaching_dir=teaching_dir,
        ingested_json=ingested_json,
        spec_path=spec_path,
        strict=args.strict,
    )
    rep = checker.run()

    out = format_json(rep) if args.json else format_human(rep)
    print(out)

    if rep.errors():
        return 2
    if args.strict and rep.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
