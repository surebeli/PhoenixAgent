# Step / Milestone 验收 Checklist 模板

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：每个 Step 验收与每个 Milestone 收尾的勾选式清单；是 `docs/quality/definition-of-done.md` 的可操作对偶。
- 上位依据：`docs/quality/definition-of-done.md`（所有 E-* / L-* / M-* / G-* / AN-* 编号的定义源）。
- 下位依据：（无；本文件是最末端的执行物）。
- 相关规则：`docs/rules/spec-change-policy.md`、`docs/rules/learning-artifact-rules.md`、`docs/rules/documentation-rules.md`。

---

## 1. 使用说明（How to use）

### 1.1 复制到哪里

- **Step 验收**：把 §3 的"Step 验收 Checklist"整块复制到对应 PR 描述 / work log 末尾，逐条打勾。禁止"部分勾选就合并"。
- **Milestone 验收**：把 §4 的"Milestone 验收 Checklist"整块复制到 `docs/milestones/M<N>-retrospective.md` 内，逐条打勾并附证据链接。

### 1.2 勾选约定

- `[ ]` → 未完成 / 未验证。
- `[x]` → 已完成，证据链接在同行末尾或下一级子弹。
- `[~]` → 部分完成；必须附：差距描述 + 预定补齐时间 + 责任人（单人项目即作者本人）。
- `[-]` → 不适用（N/A）；必须附：一句话不适用原因。

### 1.3 证据链接格式

统一 `→ <描述>: <路径 / commit / URL>`。示例：

```
[x] E-2 可运行命令通过  → 日志: `artifacts/M1/step-03/run.log` (commit `abc1234`)
```

---

## 2. 通用准备清单（Pre-Acceptance Checklist）

在执行 Step / Milestone 验收前先过这份通用清单，确保环境就绪：

- [ ] `phoenix-doctor.sh --strict` 当前 PASS。
- [ ] 本地 git 工作区干净（`git status` 无未提交变更），所有产物已在 branch 上。
- [ ] 相关 SPEC 版本未在本 Step / Milestone 执行期间发生破坏性变更（否则先走 `spec-change-policy` §5）。
- [ ] `.ingested.json` 与 `docs/teaching/**` frontmatter 一致（L-ING-4）。
- [ ] 本 Step / Milestone 涉及的所有 `tier=archived` 节点未被新节点直接 `related_nodes` 引用（L-ART-5）。

---

## 3. Step 验收 Checklist（每个 Step 使用）

> 复制整块到 PR / work log，并在首行填写：
> `Step <编号> — <Step 名称>（Milestone: M<N>，量级: S/M/L）`

### 3.1 基本信息

- [ ] Step 编号与名称与 `docs/milestones/M<N>-plan.md` 一致。
- [ ] 对应的 `docs/milestones/M<N>-plan.md` Step 章节已列出全部"产物"清单。
- [ ] 本 Step 依赖的前序 Step 状态为 `completed` / `acceptance passed`（依赖图遵守）。

### 3.2 工程达标（对应 DoD §3）

**通用工程 DoD（所有 Step 必勾）**

- [ ] **E-1 产物齐备**：Step 定义的全部产物文件存在 → `<commit>` 或 `git diff --name-only` 证据。
- [ ] **E-2 可运行**：Step 定义的验证命令成功执行到终态 → `<日志路径>`。
- [ ] **E-3 验证链完整**（若本步引入新 Tool / Runtime）：5 步验证链全过 → `<logs/tool-call.jsonl 片段>`。
- [ ] **E-4 可观测**：新行为有 log / metric / JSONL 轨迹 → `<artifact 路径>`。
- [ ] **E-5 错误路径**：至少一条"预期失败"用例被验证 → `<失败用例路径 + 拦截证据>`。
- [ ] **E-6 不破坏既有**：前序 Step 烟雾测试子集通过 → `<smoke-test.log>`。
- [ ] **E-7 幂等**：关键写操作重复执行幂等 → `<测试命令或证据>`。

**附加项：新 Tool（仅当适用时勾）**

- [ ] **E-T1** JSON Schema 输入 / 输出齐备。
- [ ] **E-T2** `requires_worktree` / `dangerous` 显式设置。
- [ ] **E-T3** `permissions.toml` 至少一条对应规则。
- [ ] **E-T4** 至少 1 条 Hook 场景案例。

**附加项：新 Runtime（仅当适用时勾）**

- [ ] **E-R1** `AgentRuntime` 全部方法实现。
- [ ] **E-R2** 同任务多 Runtime 可对比输出。
- [ ] **E-R3** `Runtime.capabilities()` 显式登记。
- [ ] **E-R4** 记忆热切换回归通过（M2 Step 8 起强制）。

**附加项：新 Model（仅当适用时勾）**

- [ ] **E-M1** `ModelProfile` 新增，`phoenix-doctor.sh` 对应段 PASS。
- [ ] **E-M2** smoke run 成功率 ≥ 95%（20 次最小任务）。
- [ ] **E-M3** Key 管理与 `keys.env.template` 对齐；路由 / 代理路径记录。
- [ ] **E-M4** 基线 benchmark subset 产出至少 1 份 report。

**附加项：新 Memory 操作 / digest 规则（仅当适用时勾）**

- [ ] **E-MM1** INV-MM-1/2/3 回归通过 → `<记录>`。
- [ ] **E-MM2** namespace 隔离验证 → `<测试记录>`。
- [ ] **E-MM3** `lint` / `tier` 可运行到终态。

### 3.3 学习达标（对应 DoD §4）

> 若 Step 显式声明"无新学习点"，跳过 L-1~L-7 并勾 L-0。

- [ ] **L-0（豁免）** 本步无新学习点，复用 `F-<existing>` → 引用位置: `<plan 中的文字>`。
- [ ] **L-1 F-* 产出**：产出文件存在且 frontmatter 齐备 → `<F-*.md 路径>`。
- [ ] **L-2 字数区间**：每个 F-* 在 [400, 3000] 内 → `wc -m` 或 CI 输出。
- [ ] **L-3 必答问题**：Step 的"要回答"问题在 F-* 正文有直接回应 → `<具体章节锚点>`。
- [ ] **L-4 资料可追**：`## 参考` 段资料有 URL / 文件路径 / 章节号。
- [ ] **L-5 与 SPEC 对齐**：`spec_version` 与当前 SPEC 一致；`related_spec` / `related_inv` 真实存在。
- [ ] **L-6 Ingest 完成**：`phoenix memory ingest` 已执行，`.ingested.json` 已更新 → `<git diff>`。
- [ ] **L-7 可召回**：`phoenix memory query "<代表性问题>"` 命中本节点 → `<命中输出>`。

### 3.4 记忆达标（对应 DoD §5）

- [ ] **M-1 INV-MM-1**：跨 namespace digest 不重复 → `<lint 输出>`。
- [ ] **M-2 INV-MM-2**（若涉及 subagent）：subagent digest 不污染主 agent。
- [ ] **M-3 INV-MM-3**：新 ingest 已更新 digest，`query` 可召回。
- [ ] **M-4 namespace 正确**：按 DoD §7 映射表落位。
- [ ] **M-5 slug 唯一**：`.ingested.json` 查重通过。
- [ ] **M-6 tier 与用途匹配**：新增 active 节点确为当前或近期主内容。

**附加项：Evaluator / Auto-Research 产出（仅当适用时勾）**

- [ ] **M-E1** `experiment-report.md` 的 `spec_version` 与开跑时一致，不跨 Major。
- [ ] **M-E2** Kept 变更有后续 F-* 节点承接。
- [ ] **M-E3** Discarded 变更也已 ingest。

**附加项：Runtime / Model 热切换（仅当适用时勾；M2 起）**

- [ ] **M-H1** 切换点前后记忆不变量回归 100% 通过 → `<回归日志>`。
- [ ] **M-H2** `digest_version` 与合并策略生效。

### 3.5 文档与规则（对应 documentation-rules）

- [ ] 引用 SPEC 时带版本号（D-REF-2）。
- [ ] M*-plan §0 基线版本号与实际环境一致（D-REF-3）。
- [ ] 本 Step 新增或修改的 rules / quality 文档通过 ingest。
- [ ] `docs/` 根目录未新增散落 `.md`（D-DIR-2）。

### 3.6 反假达标（对应 DoD §8.2）

reviewer（或作者自评）确认以下未发生：

- [ ] **AN-1** 未以"TODO: 后续补"代替学习节点正文。
- [ ] **AN-2** 未用占位文件充数（每个 F-* 字数 ≥ 400，内容实质）。
- [ ] **AN-3** 未通过临时 disable Hook / Permission 让命令走通。
- [ ] **AN-4** 未在未经 ADR 的情况下修改 DoD 条款文字。
- [ ] **AN-5** PR / work log 中每个"[x]"都有证据链接。

### 3.7 门控收口

- [ ] **G-1** 工程达标证据齐备。
- [ ] **G-2** 学习达标证据齐备。
- [ ] **G-3** 记忆达标证据齐备（`phoenix memory lint` 无致命错误）。
- [ ] **G-4** 作者自评确认进入下一步条件：`<plan 中原文>`。
- [ ] **G-5** （可选）协作 reviewer 签字。

> 若任一 G-* 未满足 → Step 标记为 `partially_done`；禁止进入下一 Step 的启动判定。

---

## 4. Milestone 验收 Checklist（每个 Milestone 收尾使用）

> 复制整块到 `docs/milestones/M<N>-retrospective.md`，并在首行填写：
> `Milestone M<N> 验收 — <日期> — 作者: dy`

### 4.1 前置

- [ ] 本 Milestone 所有 Step 的 3.7 门控 G-1~G-4 全部满足（G-5 按需）。
- [ ] 所有 Step 的状态为 `completed`（无 `partially_done`）。
- [ ] 本 Milestone 的 `docs/milestones/M<N>-plan.md` §1 DoD-M<N>-* 条款已逐条抽出到下方。

### 4.2 DoD-M<N>-* 逐条核对

> 从 `docs/milestones/M<N>-plan.md` §1 拷入本 Milestone 的全部 DoD 条款并逐条勾选：

```
- [ ] DoD-M<N>-1  <原文>          → 证据: <路径>
- [ ] DoD-M<N>-2  <原文>          → 证据: <路径>
- ...
- [ ] DoD-M<N>-N  <原文>          → 证据: <路径>
```

### 4.3 学习达标 Milestone 级（对应 DoD §4.3）

- [ ] **L-M1** 全部 F-* `ingested=true` 且 `ingested_at` ≥ 文件 mtime → `<CI 检查输出>`。
- [ ] **L-M2** 至少 1 份 `M-<slug>.md`（walkthrough / playbook / report）ingest 完成 → `<路径>`。
- [ ] **L-M3** 上一个 Milestone 节点降 tier 完成（`active→archived`）；上上个 `archived→frozen` → `<tier 执行日志>`。
- [ ] **L-M4** 元反思节点 `F-<idx>-milestone-meta-reflection.md` 存在，直接回答"若重写会改哪 3 件事" + "哪些结论被推翻（M2 起）" → `<节点路径>`。

### 4.4 SPEC 与接口冻结（对应 spec-change-policy §7）

- [ ] 本 Milestone 的 SPEC 基线版本号明确 → `SPEC v<X.Y.Z>`。
- [ ] 本 Milestone 期间的 SPEC 变更全部按 `spec-change-policy` §5 闭环（ADR / Migration Guide / 教学追认 / 老节点处置）→ `<ADR 列表>`。
- [ ] 冻结范围对齐：
  - M0 结尾：`AgentRuntime / MemoryBackend / ToolSpec+PluginRegistry`
  - M1 结尾：上述 + `HarnessFlags / PermissionRules / EvaluationRunner`
  - M2 结尾：上述 + `AgentRuntime / LLMClient / ModelProfile` 再冻结
- [ ] 如有破冻事件，紧急 ADR 已登记 → `<ADR 路径>`。

### 4.5 风险登记更新（对应 A-2 `risk-register.md` / RnD-Analysis §4）

- [ ] 本 Milestone 触发 / 缓解 / 关闭的 R-* 风险已更新 → `<risk-register.md diff 或 RnD-Analysis §4>`。
- [ ] 新发现风险以 R-* 编号登记，并同步 RnD-Analysis §4。

### 4.6 Milestone Artifact 与教学层

- [ ] 本 Milestone `docs/teaching/M<N>/foundations/F-*` 全量通过 C-5 CI（待交付；当前手工过 checklist 即可）。
- [ ] 本 Milestone `docs/teaching/M<N>/M-*` 全量通过 ingest。
- [ ] `docs/teaching/M<N>/experiments/` 下所有 experiment-report 结构符合 `learning-artifact-rules` §4.3。

### 4.7 评测与复现性

- [ ] 本 Milestone 产出的 benchmark / experiment report 均带 `spec_version` → 抽查 3 份。
- [ ] 报告可复现：给出的 `phoenix eval` / `phoenix research` 命令参数完整。
- [ ] 与上一 Milestone 的指标对比表存在（M1 起）→ `<路径>`。

### 4.8 退路与例外

- [ ] 本 Milestone 内所有 `[~]` 部分完成项已清零或转入下 Milestone backlog。
- [ ] 所有 DoD 豁免走过 ADR（DoD §9）→ `<ADR 列表>`。
- [ ] `docs/milestones/M<N>-retrospective.md` 包含：KPI 达成表、意外发现、F-* 自测结果、R-* 变化、下一 Milestone backlog。

### 4.9 接口与下阶段启动

- [ ] 下一 Milestone plan（`M<N+1>-plan.md`）的 §0 启动前提已能被当前状态满足（或已识别差距）。
- [ ] 下一 Milestone 的 SPEC 基线版本号锁定并通过 ingest。
- [ ] 下一 Milestone 的学习节点起编号确认（F-* 连续递增）。

### 4.10 Milestone 门控

- [ ] 上述 4.1 ~ 4.9 全部通过 → Milestone 状态置为 `accepted`。
- [ ] `artifacts/doctor-m<N>-final.json` 入 git → `<路径>`。
- [ ] `wiki-lint --auto-fix` 通过。
- [ ] 作者签字：`<日期> dy`

---

## 5. 特别场景清单

### 5.1 Auto-Research 轮次验收（每轮使用）

插入到 Step（如 M1 Step 13、M2 Step 10）的验收过程中：

- [ ] 本轮 SPEC 版本在开跑到收尾期间未跨 Major（S-REPRO-3）。
- [ ] Generator / Evaluator 模型配置已记录 → `experiment-report.md` frontmatter。
- [ ] 显著性检验结果已填入 `significance` 字段（Kept / Discarded 必须；Inconclusive 置 null 并说明）。
- [ ] Kept 变更有对应的 F-* 承接节点（否则延期 kept 结论）。
- [ ] Discarded 变更也已 ingest（失败是一等信息）。
- [ ] `allowed_change_globs` 实际变更未越界。
- [ ] 预算未超 → `token/$ 使用记录`。

### 5.2 SPEC 变更 PR 专项清单（每次 SPEC 修订 PR 使用）

- [ ] 已按 `spec-change-policy` §5 分级（Patch / Minor / Major）。
- [ ] 版本号按规则递增（§3）。
- [ ] ADR 已创建（Minor / Major 强制）。
- [ ] 影响面扫描结果写入 ADR。
- [ ] 实现 PR 的 commit message 引用对应 SPEC 版本（Step 4）。
- [ ] 教学追认节点已创建（Step 5）。
- [ ] 老节点处置完成（Step 6）。
- [ ] Major：Migration Guide 已创建 → `docs/migrations/SPEC-v*-to-v*.md`。
- [ ] Major：受影响的 Auto-Research 轮次已标记复现性中断。

### 5.3 新增教学节点专项清单（每次新建 F-* / M-* 使用）

- [ ] 编号连续（上一个节点 + 1，或合规补号 a/b）。
- [ ] slug 合规（§2.3 of learning-artifact-rules）。
- [ ] Frontmatter 全量填写。
- [ ] 字数 [400, 3000]（F-*）。
- [ ] `related_*` 字段不悬空。
- [ ] ingest 完成，`.ingested.json` 同步更新。
- [ ] 代表性 query 命中。

---

## 6. 与其他文档的交叉引用

- `docs/quality/definition-of-done.md`：条款编号（E-*/L-*/M-*/G-*/AN-*）的定义源。
- `docs/rules/spec-change-policy.md`：§5.2 清单的规则来源。
- `docs/rules/learning-artifact-rules.md`：§5.3 清单的规则来源。
- `docs/rules/documentation-rules.md`：§3.5 的引用规则来源。
- `docs/milestones/M<N>-plan.md`：Step / Milestone DoD 原文来源。
- `docs/quality/code-review-checklist.md`（C-4，后续）：reviewer 侧的独立清单；本文件是执行者侧清单。

---

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；Step / Milestone 两级清单 + Auto-Research / SPEC 变更 / 新教学节点三个特别场景。 |
