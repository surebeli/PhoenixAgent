# 通用 Definition of Done（DoD）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：PhoenixAgent 所有 Milestone 的 Step-level 与 Milestone-level 交付物。
- 上位依据：PRD §9（KPI）、`docs/milestones/M0-plan.md` §1（DoD-1~7）、`docs/milestones/M1-plan.md` §1（DoD-M1-1~10）、`docs/milestones/M2-plan.md` §1（DoD-M2-1~10）。
- 下位依据：`docs/quality/acceptance-checklist.md`（C-2，逐条对应本文件的 DoD 条款的可勾选版）、`docs/quality/test-strategy.md`（C-3，后续波次）、`docs/quality/code-review-checklist.md`（C-4，后续波次）。
- 相关规则：`docs/rules/spec-change-policy.md`、`docs/rules/learning-artifact-rules.md`、`docs/rules/documentation-rules.md`。

---

## 1. 本文件存在的理由（Why）

M0 / M1 / M2 三份 plan 各自定义了 `DoD-N`（M0）与 `DoD-M<N>-N`（M1/M2），但它们是**Milestone 级别**的完成定义。真正的质量控制瓶颈在于**每个 Step 的完成定义**：当作者自评"Step 做完了"时，怎么判定没有欠债？

PhoenixAgent 项目的特殊性决定 DoD 不能只看"代码可运行"：

- 学习资产是一等交付物（`feedback_plan_style` 学习内嵌规则）。
- 文档体系是单一真相源（`documentation-rules` D-LLM-1 自包含）。
- 记忆不变量（SPEC INV-MM-1/2/3）决定下一步是否可以叠加。

为此，本文件给出**三达标 DoD 模型**：工程达标 + 学习达标 + 记忆达标；每个 Step 必须同时满足三者，否则视为未完成。

---

## 2. 三达标 DoD 模型

```
╔════════════════════════════════════════════════╗
║  Step 完成 = 工程达标 ∧ 学习达标 ∧ 记忆达标      ║
╚════════════════════════════════════════════════╝
```

三类缺一不可。短板优先补齐，不得"工程先过、学习后补"——历史证明"后补"的学习节点质量永远低于内嵌撰写。

---

## 3. 工程达标（Engineering DoD）

### 3.1 通用工程 DoD（所有 Step 必须满足）

- **[auto] E-1 产物齐备**：Step 定义的所有"产物"文件 / 脚本 / 配置 / 接口存在于 git，且被对应的索引（`models.toml` / `PluginRegistry` / SQLite schema 等）注册。
- **[review] E-2 可运行**：Step 定义的验证命令（`phoenix run` / `phoenix eval` / `phoenix-doctor.sh` 等）能无人工干预地运行到终态，exit code 符合预期。
- **[review] E-3 验证链完整**：若本步引入新 Tool 或新 Runtime，`validateInput → PreToolUse Hook → checkPermissions → executeTool → mapToolResultToAPI` 5 步验证链全过（M1 Step 4 起硬性要求）。
- **[review] E-4 可观测**：本步引入的任何新行为有日志 / metric / JSONL 轨迹记录，且能与 `logs/` 下既有格式兼容。
- **[auto] E-5 错误路径**：本步引入的功能有至少一条"预期失败"的用例并能被验证（拒绝、超时、回滚、重试）。不是测试覆盖率要求，是"失败可解释"要求。
- **[auto] E-6 不破坏既有**：运行 `phoenix-doctor.sh --strict` + 前序 Step 的验证命令子集（"烟雾测试"），全部通过；不引入 regression。
- **[auto] E-7 幂等**：本步若涉及文件写、DB 写、wiki ingest，重复执行同一命令不产生重复状态或错误。特别是 `ingest` / `tier` / `migration` 脚本。

### 3.2 引入新 Tool 时的工程 DoD

当 Step 产出一个新的 `ToolSpec` 实现时，附加：

- **[review] E-T1** 有 JSON Schema 描述输入 / 输出。
- **[review] E-T2** 有 `requires_worktree` / `dangerous` 标志显式设定（非默认）。
- **[review] E-T3** 在 `permissions.toml` 默认规则中出现（至少一条 allow / ask / deny）。
- **[auto] E-T4** 至少 1 条 Hook 场景案例（即使是"无动作通过"）写入 `tools/hooks/` 或测试 fixture。

### 3.3 引入新 Runtime 时的工程 DoD

- **[review] E-R1** 实现 SPEC v1.1 §3 `AgentRuntime` 全部方法。
- **[review] E-R2** 至少 1 个相同任务可在 `--runtime=<new>` 与既有 Runtime 上产出可对比结果。
- **[review] E-R3** `Runtime.capabilities()` 显式登记能力差异（extended_thinking / parallel_tool_use 等）。
- **[review] E-R4** 记忆热切换回归（M2 DoD-M2-6 起强制）。

### 3.4 引入新 Model 时的工程 DoD

- **[review] E-M1** `ModelProfile` 新增，`phoenix-doctor.sh` 对应段 PASS。
- **[review] E-M2** 至少 1 次 smoke run（20 次最小任务，成功率 ≥ 95%）。
- **[review] E-M3** 国际路由 / 代理路径、API Key 管理与 `keys.env.template` 对齐。
- **[review] E-M4** 在基线 benchmark subset 上产出至少一份 report（即使是差的）。

### 3.5 引入新 Memory 操作 / 新 digest 规则时的工程 DoD

- **[review] E-MM1** 不变量 INV-MM-1/2/3 仍然成立（本地回归）。
- **[review] E-MM2** 与现有 namespace 隔离正确；跨 namespace 不泄漏。
- **[auto] E-MM3** `lint` / `tier` 在本次改动后仍可运行至终态。

---

## 4. 学习达标（Learning DoD）

### 4.1 通用学习 DoD（除显式标注"无新学习点"外，所有 Step 必须满足）

- **[auto] L-1 F-* 产出**：Step 定义的所有 `F-<idx>-<slug>.md` 文件存在，frontmatter 必填字段齐备（见 `learning-artifact-rules` §3）。
- **[review] L-2 字数区间**：每个 F-* 节点字数在 [400, 3000] 内（L-ART-7）。
- **[review] L-3 必答问题**：Step "内嵌学习" 段落列出的"要回答"问题，在 F-* 节点正文有直接回应（不可"回避"或"留待后续"）。
- **[review] L-4 资料可追**：必读资料以 URL / 文件路径 / 章节号形式出现在 F-* 的 `## 参考` 段。
- **[review] L-5 与 SPEC 对齐**：frontmatter `spec_version` 与当前 SPEC 一致；`related_spec` / `related_inv` 引用真实存在。
- **[auto] L-6 Ingest 完成**：`phoenix memory ingest` 已执行，`.ingested.json` 已更新，CI 通过（L-ING-4）。
- **[auto] L-7 可召回**：`phoenix memory query <关键问题>` 能召回本 F-* 节点（基本闭环测试，至少 1 个代表性 query 命中）。

### 4.2 纯机械 Step 的豁免

若 Step 显式标注"无新学习点"（例如 M0-plan 中某些辅助配置步骤），则 L-1 ~ L-7 豁免，但必须：

- **[review] L-0** 在 Step 的"内嵌学习"段落显式写"本步无新学习点，复用 Step X 的 F-Y"，不得留空。
- **[review] L-1'** `related_nodes` 语义明确，引用的 F-Y 为 `tier=active`。

### 4.3 Milestone 结尾的学习 DoD

每个 Milestone retrospective（M0 Step 12 / M1 Step 14 / M2 Step 12 对应位置）额外：

- **[review] L-M1** Milestone 内所有 F-* 节点 `ingested=true` 且 `ingested_at` ≥ 文件 mtime。
- **[review] L-M2** 对应的 `M-<slug>.md` Milestone Artifact 至少 1 份（walkthrough / playbook / report 任选），ingest 完成。
- **[review] L-M3** 上一个 Milestone 的节点降 tier 完成（learning-artifact-rules §6.2）。
- **[review] L-M4** 元反思节点 `F-<idx>-milestone-meta-reflection.md` 存在且直接回答"若重写会改哪 3 件事"（与"哪些结论被推翻"在 M2 起）。

---

## 5. 记忆达标（Memory DoD）

### 5.1 通用记忆 DoD

- **[review] M-1 INV-MM-1 成立**：跨 namespace digest 不重复（每个 Step 改动 Memory 后自检）。
- **[review] M-2 INV-MM-2 成立**：subagent digest 不污染主 agent（若本 Step 涉及 subagent）。
- **[review] M-3 INV-MM-3 成立**：新 ingest 必定更新 digest（ingest 后 query 可召回证实）。
- **[review] M-4 namespace 正确**：本步新增的 ingest 落在正确 namespace；本文件 §7 给出映射表。
- **[review] M-5 slug 唯一**：本步新增节点的 slug 在 `.ingested.json` 中不与既有条目冲突。
- **[hybrid] M-6 tier 与用途匹配**：`active` tier 的节点确实是"当前或近期 Milestone 主内容"，不滥用。

### 5.2 引入 Evaluator / Auto-Research 产出时的记忆 DoD

- **[review] M-E1** `experiment-report.md` 的 frontmatter `spec_version` 与开跑时 SPEC 一致，不跨 Major。
- **[review] M-E2** Kept 变更必须有后续 F-* 节点承接（否则该变更事实上脱离项目知识库）。
- **[review] M-E3** Discarded 变更仍然 ingest（失败是一等信息）。

### 5.3 Runtime / Model 热切换时的记忆 DoD（M2 起）

- **[review] M-H1** 切换点前后的 Memory 不变量回归 100% 通过（M2 Step 8）。
- **[review] M-H2** `digest_version` 字段存在且在冲突时走合并策略（R-MM-2 缓解）。

---

## 6. 门控与证据（Gate & Evidence）

### 6.1 "达标"的证据形式

任何 DoD 条款"已满足"必须有**可复核证据**，不接受"我检查过了"。允许形式：

| 证据类型 | 示例 |
|---|---|
| CI 绿灯 | `ci-check-teaching.py` / `ci-check-spec.py` PR 检查通过 |
| 命令输出快照 | `phoenix-doctor.sh --json > artifacts/...json`，入 git |
| Benchmark report | `artifacts/M<N>/bench/*.json` + 可读摘要 markdown |
| Query 命中日志 | `phoenix memory query` 输出 grep 到目标 slug |
| Git 状态 | `git log` / `git diff` 可见的文件与提交 |
| Screenshot / 录屏 | 仅限 CLI 无法捕获的交互行为（罕见） |

### 6.2 Step 级门控

- **[auto] G-1** 工程达标：产出命令输出 / CI 绿灯证据。
- **[review] G-2** 学习达标：`.ingested.json` diff + 至少一次召回证据。
- **[auto] G-3** 记忆达标：`phoenix memory lint` 运行输出无致命错误。
- **[review] G-4** 作者自评：在 Step 尾部的"进入下一步条件"下打勾确认。
- **[review] G-5**（可选，协作场景）PR reviewer 签字。

### 6.3 Milestone 级门控

- 全部 Step 的 G-1~G-4 通过。
- `DoD-M<N>-*`（M*-plan §1 定义）逐条核对，证据链接入 `M<N>-retrospective.md`。
- SPEC 冻结状态确认（`spec-change-policy` §7）。
- 上一 Milestone 节点降 tier 完成。

---

## 7. Namespace 映射表（Memory Layer）

| 产物 | namespace | tier |
|---|---|---|
| `docs/SPEC.md` | `spec` | active（历史版本 frozen） |
| `docs/PRD.md` / `TRD.md` / `RnD-Analysis.md` | `product` / `architecture` / `rnd` | active |
| `docs/rules/**` | `rules` | active |
| `docs/quality/**` | `quality` | active |
| `docs/milestones/M<N>-plan.md` | `milestone` | active（历史 Milestone archived） |
| `docs/milestones/M<N>-retrospective.md` | `retrospective` | active |
| `docs/teaching/M<N>/foundations/F-*.md` | `foundations` | 按 learning-artifact-rules §6 |
| `docs/teaching/M<N>/M-*.md` | `milestones` | 按上 |
| `docs/teaching/M<N>/experiments/*.md` | `experiments` | 按上 |
| `docs/teaching/M<N>/engineering/*.md` | `engineering` | 按上 |
| `docs/adr/**` | `adr` | active |
| `docs/migrations/**` | `migrations` | active |

---

## 8. 失败与退路（Failure Modes）

### 8.1 部分达标的处理

- 三达标中有一项未达 → Step 状态标记为 `partially_done`；不得进入下一 Step 的"进入下一步条件"判定。
- M*-plan §1 DoD-M<N>-N 未达 → 两种处理：
  - **硬退路**（M0/M1）：不放行 Milestone；继续工作直至达标。
  - **软退路**（M1 起）：若已暴露为结构性问题（如模型能力限制），允许在 retrospective 中调整 DoD 阈值并说明（M1 R-RT-1 已预留）。阈值变更进 ADR。

### 8.2 禁止的"假达标"

- **AN-1** 把"学习节点留空但写 'TODO: 后续补'"算作达标。
- **AN-2** 用 ingest 占位文件（frontmatter 齐全但正文少于 400 字）过学习达标。
- **AN-3** 通过跳过验证链（临时 disable Hook / Permission）让工程命令走通。
- **AN-4** 修改 DoD 原文以降低门槛而不走 ADR。
- **AN-5** 在 retrospective 中只记"通过"不记证据链接。

CI 与 reviewer 有义务识别并阻塞上述情况。

---

## 9. DoD 例外与 ADR

任一 DoD 条款豁免必须通过 ADR：

- 写 `docs/adr/ADR-NNNN-dod-exception-<slug>.md`。
- 必须含：豁免的条款 ID、影响范围（Step / Milestone / 全局）、补偿措施、回滚时机。
- retrospective 时逐条复核例外是否仍然成立。

---

## 10. 与其他文档的交叉引用

- `docs/rules/spec-change-policy.md`：DoD 条款涉及 SPEC 变更时遵循此策略。
- `docs/rules/learning-artifact-rules.md`：L-* 条款的具体 frontmatter / slug / ingest 规则。
- `docs/rules/documentation-rules.md`：DoD 中"文档达标"的引用规则来源。
- `docs/quality/acceptance-checklist.md`：本文件 DoD 条款的可勾选版；Step 验收时拉 checklist。
- `docs/quality/test-strategy.md`（C-3，待交付）：E-5 / E-6 的具体覆盖率与分层要求。
- `docs/quality/code-review-checklist.md`（C-4，待交付）：reviewer 识别 AN-* 假达标的清单。

---

## 11. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；定义三达标 DoD 模型，覆盖 Step / Milestone / Tool / Runtime / Model / Memory 五维度。 |
| v1.1 | 2026-04-22 | 全量条款补齐 `[auto]` / `[review]` / `[hybrid]` 标签（对应 T-P2-3 行动项 1）；`L-1` 补 `[auto]` 标签。reviewer checklist 的"内容充分度 / 错误路径证据"强化项挂 `docs/quality/code-review-checklist.md`（C-4 后续波次）。 |
