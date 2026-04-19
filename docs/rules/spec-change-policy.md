# SPEC 变更治理策略（SPEC Change Policy）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：`docs/SPEC.md`、`docs/PRD.md`、`docs/TRD.md`、`docs/RnD-Analysis.md` 以及所有被其直接引用的接口 / 数据结构 / 常量 / 不变量（INV-*）。
- 上位依据：PRD §7（愿景关键词"全链路自研可控 / 可插拔"）、TRD §4、SPEC v1.0 §1 ~ §14。
- 下位依据：`docs/rules/documentation-rules.md`、`docs/rules/learning-artifact-rules.md`、`docs/quality/definition-of-done.md`。

---

## 1. 本策略存在的理由（Why）

PhoenixAgent 是"自研编码 Agent + 教学资产"的双栈项目。如果 `SPEC.md` 的接口契约随意漂移，会同时污染：

- **代码层**：Runtime / Plugin / Memory / Evaluation 互相依赖 `AgentRuntime / ToolSpec / MemoryBackend / PhoenixContext` 等硬接口。任一接口无节制变更都会引发跨层级联重写。
- **教学层**：`docs/teaching/**` 下 `F-*`、`M-*` artifact 与具体 SPEC 条款锚定；SPEC 漂移会使已 ingest 的节点"静默过期"，破坏 wiki 召回质量。
- **评测层**：Evaluation / Auto-Research 的显著性推断依赖"同一 SPEC 版本下的多次实验"。中途变更会让前后轮次不可比。

因此本项目坚持一条铁律：**SPEC 先行、实现跟进、教学追认**。所有 SPEC 变更必须经过本策略定义的流程，禁止"改代码顺手改 SPEC"。

---

## 2. 术语

| 术语 | 定义 |
|---|---|
| **硬接口（Hard Interface）** | `AgentRuntime`、`MemoryBackend`、`ToolSpec + PluginRegistry`、`LLMClient + ModelProfile`、`EvaluationRunner`、`AutoResearchLoop`、`TeachingEmitter`、`PhoenixContext`、`HarnessFlags`、`PermissionRules` |
| **半硬接口（Soft Interface）** | `BenchmarkTask`、`BenchmarkReport`、`LongHorizonMetrics`、`Plan` / `PlanStep`、SQLite schema、Hook JSONL 协议 |
| **私有实现（Private Impl）** | `src/phoenix/**/*.py` 中非 `base.py` 的文件 |
| **破坏性变更（Breaking Change）** | 删除 / 重命名 / 收窄已有字段、改变已有行为语义、引入新必填参数、对既有 INV-* 添加更严格约束 |
| **兼容性变更（Additive Change）** | 新增可选字段、新增新接口、放宽约束（原有调用方无感知） |
| **冻结（Freeze）** | 在指定 Milestone 范围内禁止对目标接口做破坏性变更 |

---

## 3. SPEC 版本号

`SPEC.md` 采用语义化版本 `vX.Y.Z`：

- **X（主版本）**：任一硬接口发生破坏性变更时 +1；对齐 Milestone 粒度，Milestone 切换不自动升 X。
- **Y（次版本）**：硬接口兼容性变更 / 半硬接口破坏性变更 / 新增 INV-*。
- **Z（补丁）**：措辞澄清、typo、示例修正、内部交叉引用修补；不改变任何接口语义。

约束：

- **S-VER-1**：`SPEC.md` 文件首行的版本号与 wiki `namespace="spec"` 内对应节点的 `version` 字段必须一致。
- **S-VER-2**：PRD / TRD / RnD-Analysis 对 SPEC 的引用必须指向具体 `vX.Y`（至少到 Y），不得只写"见 SPEC"。
- **S-VER-3**：任一 Milestone 的 `M*-plan.md §0 启动前提` 必须冻结一个 SPEC 版本号作为基线。

---

## 4. 变更类别与触发条件

### 4.1 Patch 级（Z）

触发条件（任一）：
- 修改 typo / 语法 / 格式化。
- 补充示例或图示，但不改变字段、函数签名、INV-* 条款文字。
- 修正交叉引用编号（如 `§5.2` 误写成 `§5.1`）。

流程：直接改 → 本地校验（C-6 `ci-check-spec.py`）→ `wiki-ingest` → 提交。无需 ADR。

### 4.2 Minor 级（Y）

触发条件（任一）：
- 对硬接口新增可选字段 / 可选方法 / 可选枚举值。
- 半硬接口发生破坏性变更（例如 SQLite schema 新增必填列，需要 migration）。
- 新增 INV-* 条款、或放宽 / 细化已有 INV-* 条款但不与历史实现冲突。
- 新增一整类接口（如将来可能新增的 `ObservabilityBackend`）。

流程：ADR → SPEC 修订 → 实现跟进 → 教学追认。详见 §5。

### 4.3 Major 级（X）

触发条件（任一）：
- 删除 / 重命名 / 收窄硬接口的已有字段或方法。
- 改变任一硬接口已有方法的语义（返回含义、异常契约、幂等性、并发安全）。
- 删除或反向收紧已有 INV-*。
- 引入新必填参数导致既有调用方必须修改。

流程：ADR（强制评审）→ 迁移指引（Migration Guide）→ SPEC 修订 → 实现跟进 → 教学追认 → 旧版本 wiki 节点降 tier 至 `archived`。详见 §5 + §6。

---

## 5. 标准变更流程（Canonical Flow）

下述流程为 Minor / Major 统一流程。Major 在每一步加粗处有额外硬要求。

### Step 1 — 动机登记（Motivation）

- 在 `docs/adr/ADR-NNNN-<slug>.md` 新建或复用一条 ADR（见 A-3 占位；在 ADR 体系未建立前先登记到 `docs/milestones/M*-plan.md` 的对应 Step 内）。
- **Major 强制**：ADR 必须包含"不做此变更会产生什么问题"的具体代码 / 评测 / 教学证据，禁止仅"美学改进"。
- 动机登记完成后，变更才允许进入 Step 2。

### Step 2 — 影响面扫描（Impact Scan）

必查项：
1. **代码影响**：grep `src/phoenix/**` 中对该接口的引用；列出所有调用点与适配成本。
2. **教学影响**：`phoenix memory query <接口名> --namespace spec` + `--namespace foundations`；列出会失效的 F-* / M-* 节点。
3. **评测影响**：是否会令前序 Auto-Research 轮次的 `experiment-report.md` 不可复现？若是，必须在 §7 "复现性保护"小节说明。
4. **教学 artifact 的 ingested marker**：列出需要重新 ingest 的节点 slug。

产物：`docs/adr/ADR-NNNN-*.md` 的 `## 影响面` 章节；当变更范围跨越 2 个及以上 Milestone 时，同时更新 `docs/risk-register.md`。

### Step 3 — SPEC 修订（SPEC First）

**必须先改 SPEC，再改实现**。SPEC 修订 PR / commit 必须：
- 修改 `docs/SPEC.md` 文件首部的版本号（按 §3 递增）。
- 修改后通过 `tools/ci-check-spec.py`（C-6，占位，Milestone 后置交付）。
- 通过 `wiki-ingest --source docs/SPEC.md --namespace spec --tier active`。
- **Major 强制**：同 commit 包含 `docs/migrations/SPEC-vX.Y.Z-to-vX'.Y'.Z'.md` 迁移指引（§6）。

### Step 4 — 实现跟进（Impl Follows）

- 只有 Step 3 合入后才允许修改 `src/phoenix/**/*.py`。
- 实现 commit 的 commit message 首行必须包含对应 SPEC 版本号（例如 `feat(runtime): align with SPEC v1.3 AgentRuntime.run_task`）。
- **Major 强制**：实现侧必须在 CHANGELOG 或 retrospective 中记录"迁移清单执行情况"。

### Step 5 — 教学追认（Teaching Trails）

- 为此次变更新建 `docs/teaching/M<current>/foundations/F-<next>-<slug>.md`（命名规则见 B-2 `learning-artifact-rules.md`）。
- 节点内容必须覆盖：
  - 动机（不超过 3 行）。
  - 变更前后接口对比（代码片段 + 字段表）。
  - 对 INV-* 的影响。
  - 对既有教学节点的引用修订清单。
- `wiki-ingest` 后方可认定变更流程闭合。

### Step 6 — 老节点处置（Legacy Handling）

- **Minor**：受影响的 F-* 节点更新 `frontmatter.spec_version` 字段并追加 `updated_for: vX.Y`；保留在 `active` tier。
- **Major**：受影响的 F-* 节点若内容不再适用，降至 `archived` tier（但**不删除**）；其位置由新节点承接并在 `replaces:` frontmatter 指向旧 slug。

---

## 6. 迁移指引（Migration Guide）要求（仅 Major）

`docs/migrations/SPEC-vX.Y.Z-to-vX'.Y'.Z'.md` 模板：

```markdown
# 从 SPEC vA 迁移到 vB

- 变更级别：Major
- 触发 ADR：ADR-NNNN
- 受影响接口：<列表>

## 字段对照表
| 旧字段 | 新字段 | 迁移动作 |
|---|---|---|
| ... | ... | ... |

## 行为变更
<列出所有语义差异，逐条给出 before/after 伪代码>

## 必须执行的迁移步骤（按顺序）
1. ...
2. ...

## 验证点
- 构造一个最小复现脚本，分别在 vA 和 vB 下运行，展示差异。
- CI `ci-check-spec.py` 通过。
- Benchmark 回归：在 SWE-bench Verified subset=20 上，Resolved Rate 变化 ≤ 2 pp 或有可解释原因。

## 回滚预案
<回滚到 vA 的步骤；若不可回滚，说明冻结期窗口>
```

---

## 7. 冻结期与 Milestone 约束

| Milestone | 冻结时点 | 冻结范围 |
|---|---|---|
| M0 结束 | Step 12 验收通过 | `AgentRuntime` / `MemoryBackend` / `ToolSpec + PluginRegistry` 三个硬接口；进入 M1 前只允许 Patch |
| M1 结束 | Step 14 验收通过 | 上述三个 + 新增 `HarnessFlags` / `PermissionRules` / `EvaluationRunner`；进入 M2 前只允许 Patch 与预先批准的 Minor |
| M2 结束 | Step 12 验收通过 | 上述 + `AgentRuntime` / `LLMClient` / `ModelProfile` 再冻结一次 |
| 每个 Auto-Research 轮次 | 轮次开跑至轮次收尾 | 本轮 Generator-Evaluator 锁定的全部 SPEC 条款；途中仅允许 Patch |

约束：

- **S-FREEZE-1**：冻结期内任一提案 Minor / Major 变更必须延到下一 Milestone 的 Step 1 之后。
- **S-FREEZE-2**：若冻结期内发现 P0 级 bug（违反 INV-* 或造成数据损坏），允许破冻，但必须：
  1. 即时创建紧急 ADR。
  2. 在对应 `docs/milestones/M*-retrospective.md` 记录破冻事件与事后复盘。
  3. 自动触发受影响 Auto-Research 轮次作废重跑。

---

## 8. 复现性保护

Auto-Research / Benchmark 报告的可比性依赖 SPEC 稳定。为此：

- **S-REPRO-1**：每一份 `experiment-report.md` / `benchmark-report.json` frontmatter 必须记录生成时 `spec_version`。
- **S-REPRO-2**：CI `ci-check-spec.py`（C-6）应在 SPEC 版本跃迁时扫描最近 N=3 次 Auto-Research 报告的 `spec_version`，若跨越 Major 则在 PR 中要求显式 `--allow-spec-discontinuity` 标记并附原因。
- **S-REPRO-3**：禁止在"一个 Auto-Research 轮次的中途"合入任何 Minor / Major SPEC 变更（对应 §7 最后一行）。

---

## 9. 违规与检查

| 违规 | 检查点 | 后果 |
|---|---|---|
| 改实现但未改 SPEC | C-6 CI：对比 `git diff` 中 `src/phoenix/**` 对硬接口符号的变更 vs `SPEC.md` diff | 阻塞 PR |
| SPEC 改了但教学未追认 | C-5 CI：扫描本次 diff 的 SPEC 条款，要求 `docs/teaching/M*/foundations/` 有对应 F-* 节点 | 警告（非阻塞）；M*-retrospective 时必须清零 |
| 冻结期破冻 | Reviewer 人工检查 + `M*-retrospective.md` 自检清单 | PR 需额外 1 次 approve + 记录破冻 |
| 迁移指引缺失（Major） | C-6 CI 检查 `docs/migrations/SPEC-v*.md` 存在且被 SPEC 首部引用 | 阻塞 PR |

---

## 10. 与其他规则的交叉引用

- `docs/rules/learning-artifact-rules.md`：F-* / M-* frontmatter `spec_version` / `replaces:` 字段定义。
- `docs/rules/documentation-rules.md`：PRD/TRD/RnD/SPEC 交叉引用规则。
- `docs/quality/definition-of-done.md`：任一 Step 的 DoD 默认包含"SPEC 变更已按本策略闭环"。
- `docs/quality/acceptance-checklist.md`：验收 checklist 中的 "SPEC & 教学" 板块项逐条对应 §5 Step 1–6。

---

## 11. 变更日志（本文件自己的）

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；对齐 M0–M2 三份 plan 已隐含的 SPEC-first 约定。 |
