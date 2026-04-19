# PhoenixAgent 文档体系导览

- 版本：v1.0（2026-04-19）
- 作者：dy
- 适用范围：本目录（`docs/`）下全部文档；以及 repo 根的 `AGENTS.md` / `CLAUDE.md` 入口指针。
- 目的：作为 `docs/` 的入口，回答两类问题——"这堆文档**为什么**这样组织"以及"我现在想找 X，**该读哪份**"。

> 阅读时间：完整 8 分钟；只看 §9-10（导航 + 阅读路径）2 分钟。

---

## 1. 项目一句话

PhoenixAgent 是单作者 + LLM Agent 协同开发的"自研 Coding Agent"，按八层架构（Runtime / Model / Harness / Plugin / Memory / Evaluation / Auto-Research / Teaching）逐层叠加，并以"工程 ∧ 学习 ∧ 记忆"三达标交付。

当前阶段：**治理层完整、实现层为零**；M0 之前不写 `src/phoenix/**`。

---

## 2. 为什么单人项目还需要"治理层"

单人 + LLM Agent 代笔的开发模式有三种"失忆"：

1. **作者失忆**：6 个月后回看自己的代码 / 决策，忘记当时为什么这么选。
2. **Agent 失忆**：每次对话冷启动；Agent 看不到上一次会话的判断与权衡。
3. **跨工具失忆**：Claude Code、Codex、Cursor、未来的 PhoenixAgent 自身，需要"读同一份文档就能上手"。

治理层就是把这三种失忆"硬化"成可追、可读、可校验的文件。它不是流程洁癖，是**降低未来的"重新发现成本"**。

> 反直觉的代价：当前阶段所有产出都在 `docs/`，看起来"还没写代码就先写 N 份规则"。这是有意为之 —— 让 M1 起任一行代码都能被即时判定"是否合规"，反过来给实现层加速。

---

## 3. 治理层 vs 实现层

```
docs/                ← 治理层（当前所有产出都在这里）
src/phoenix/         ← 实现层（M1 起开始填）
tests/               ← 实现层验证（M1 起）
tools/               ← 治理 + 实现的边界（CI 脚本 + phoenix-doctor）
artifacts/           ← 运行时产物（doctor baseline / experiment 报告 / 测试日志）
```

| 层 | 管什么 | 谁修订 |
|---|---|---|
| 治理层 | "**应该如何**" | 作者（必要时 Agent 起草） |
| 实现层 | "**实际怎样**" | 作者 + Agent 协同 |
| `tools/` | 把治理规则机器化执行 | Agent 起草、作者审 |

---

## 4. Tier 分层：按稳定性与影响半径

`docs/rules/documentation-rules.md` 把所有文档分四档。改动成本与"为什么这样分"：

| Tier | 含义 | 改一行的代价 | 例子 |
|---|---|---|---|
| **Tier-0** | 单一真相源；项目存在的全部依据 | **极高**：走 `spec-change-policy`（ADR + 版本号 + 影响面扫描） | `PRD.md` / `TRD.md` / `RnD-Analysis.md` / `SPEC.md` |
| **Tier-1** | 执行编排；具体到何时做何事 | **中**：M\*-plan 冻结后改要 ADR | `milestones/M*-plan.md` / `adr/` / `roadmap.md` / `risk-register.md` / `migrations/` |
| **Tier-2** | 流程规则与达标定义；Tier-0 的 "how" | **中**：rules 改动可能等同 SPEC Minor | `rules/*.md` / `quality/*.md` |
| **Tier-3** | 学习与执行记录；append-only 多于修订 | **低**：走 tier 转换（active → archived → frozen），不直接删 | `teaching/M*/foundations/F-*.md` / `experiments/` |

**核心约束（D-REF-4 / D-REF-5）**：
- Tier-N 只能引用 Tier-N 或 Tier-(N-1)。
- Tier-0 不得引用 M\*-plan 的章节（只能提文件名）。
- `rules/*` 不得引用 PRD / TRD 的具体章节（避免反向耦合）。

`tools/ci-check-spec.py` 强制校验。

---

## 5. Rule / Quality / ADR 各管什么

四类文档经常被混淆，但回答的是不同问题：

| 类型 | 回答 | 时态 | 例子 |
|---|---|---|---|
| **Tier-0** | "**是什么**" | 静态契约 | `INV-RT-1` 主循环不变量；`HarnessFlags` 字段集 |
| **Rule（`rules/`）** | "**怎么做**才合规" | 长期适用 | `spec-change-policy` 改 SPEC 的 6 步；`git-workflow` 的 commit footer 规则 |
| **Quality（`quality/`）** | "**什么算达标**" | 长期适用 | `definition-of-done` E-5 错误路径；`test-strategy` 覆盖率门限 |
| **ADR** | "**为什么这样定**" | 一次性决策；不可静默撤销 | `ADR-0000` 为何采用 ADR；`ADR-0001` 为何 frozen=True |

**记忆口诀**：
- **Tier-0 + Rule + Quality** 共同回答"现在我们怎么做事"。
- **ADR** 回答"为什么我们决定这么做事" —— 它是 Tier-0 / Rule / Quality 任一变更的"配套小传"。

### 一个具体例子：HarnessFlags 加 frozen=True

| 文件 | 角色 | 写了什么 |
|---|---|---|
| `docs/adr/ADR-0001-harness-flags-frozen.md` | **ADR** | "为什么选 frozen 不选 runtime guard" + 3 候选方案 + 影响面 |
| `docs/SPEC.md` §5.1 | **Tier-0** | "现在 `HarnessFlags` 就是 frozen 的" |
| `docs/rules/harness-flags-policy.md` HF-IMPL-1 | **Rule** | "将来要消费它就必须 `dataclasses.replace()`" |
| `docs/quality/code-review-checklist.md` CR-F-1 | **Quality** | "reviewer 怎么验证你确实这么做" |
| `tools/ci-check-flags.py` | **CI** | "机器自动检测 SPEC ↔ policy 漂移" |

同一件事在五处各占一个角色，互不重复。

---

## 6. 三条贯穿原则

### 6.1 D-LLM-1：自包含 / 离线可读

任一文档读起来不需要外部 chat 历史、不需要 issue tracker、不需要 Slack。理由：Agent 冷启动；离线 ingest；6 个月后的自己。

### 6.2 D-REF-\*：闭环引用 + 显式版本号

- 跨文档引用走显式 ID：`FR-* / D-* / R-* / INV-* / DoD-* / ADR-NNNN / s<NN>`。
- SPEC 引用必须带版本号（`SPEC v1.1 §5.1`）。
- `tools/ci-check-spec.py` 强制校验闭环。

这让"改一处会影响哪里"是机器可算的。

### 6.3 决策的"为什么"与"是什么"物理分离

- **是什么** → Tier-0 / Rule / Quality（当前正确做法；可被覆盖式更新）。
- **为什么** → ADR（决策原貌；只能新 ADR supersede，不能改写历史）。

避免 SPEC 正文里塞一段"我们为什么不选方案 B"——SPEC 只说现在是什么，决策小传归 ADR。

---

## 7. 与"三达标"的关系

`docs/quality/definition-of-done.md` 把每一次交付定义为三档同时达标：

```
工程 ∧ 学习 ∧ 记忆
  ↑       ↑       ↑
 E-*     L-*     M-*
  ↑       ↑       ↑
test    teach   memory
strategy artifact ingest
```

每档都有专属的：Tier-0 不变量（`INV-*`）+ Rule（怎么做）+ Quality（什么算达标）+ Acceptance（怎么勾选）。这套结构让"质量"不再依赖作者主观判断，而是逐条可勾选。

---

## 8. 当前阶段的特殊性

**治理层完整 / 实现层为零**。这看似本末倒置，但有意为之：

- **正向收益**：M1 Step 1 一旦动笔，所有规则立刻生效；不会出现"代码先跑起来再补规则"的债。
- **风险**：`R-TL-2`（治理过载 / 永远准备）。继续堆治理不如进 M0 Step 1 —— 治理产物的价值必须靠被代码消费来验证；再不进入实现层，治理本身会变成新的失忆源。

---

## 9. 文档导航（按 Tier）

### Tier-0（4 件套；改动走 `spec-change-policy`）

| 文件 | 职责 | 当前版本 |
|---|---|---|
| `PRD.md` | WHY / WHAT；用户与功能需求 | v1.0 |
| `TRD.md` | HOW 架构；八层划分与决策（D-\*）+ 安全条款（SEC-\*） | v1.0 |
| `RnD-Analysis.md` | 风险（R-\*）+ 操作清单（OP-\*）+ 排期分析 | v1.0 |
| `SPEC.md` | 接口契约 + 不变量（INV-\*）+ HarnessFlags + 5 步验证链 | **v1.1** |

### Tier-1（执行编排）

| 文件 / 目录 | 职责 |
|---|---|
| `roadmap.md` | 跨 Milestone 总路线图 + KPI 横切 + 决策分支 D-ROAD-\* |
| `risk-register.md` | R-\* 风险的运行态登记（active / watch / mitigated / triggered / archived） |
| `milestones/M0-plan.md` / `M1-plan.md` / `M2-plan.md` | 各 Milestone 的 Step 清单 + DoD-M\<N\>-\* |
| `adr/README.md` | ADR 体系流程（命名 / 状态机 / 触发清单） |
| `adr/ADR-TEMPLATE.md` | 复制改名用的模板 |
| `adr/ADR-0000-adopt-adr.md` | 体系自证 ADR |
| `adr/ADR-0001-harness-flags-frozen.md` | 首个真实 ADR；SPEC v1.0 → v1.1 |
| `migrations/` | SPEC Major 变更的迁移指南（当前空） |

### Tier-2（流程规则 + 达标定义）

| 文件 | 职责 |
|---|---|
| `rules/documentation-rules.md` | Tier 分层 / D-DIR-\* / D-LLM-\* / D-REF-\* |
| `rules/spec-change-policy.md` | SPEC Patch / Minor / Major 流程；冻结期；S-REPRO-\* |
| `rules/git-workflow.md` | 分支 / commit / PR / worktree / tag 全流程 |
| `rules/harness-flags-policy.md` | 12 flag 治理状态 + Safety-Critical 零例外 + HF-\* |
| `rules/learning-artifact-rules.md` | 教学 artifact 命名 / frontmatter / tier 转换 |
| `quality/definition-of-done.md` | 三达标条款（E-\* / L-\* / M-\* / G-\* / AN-\*） |
| `quality/acceptance-checklist.md` | 执行者侧勾选清单（Step / Milestone / 特别场景） |
| `quality/test-strategy.md` | 四档金字塔 / 分层覆盖率 / INV 守护 / Flag 矩阵 |
| `quality/code-review-checklist.md` | reviewer 侧清单（CR-\* + 反假 CR-AN-\*） |

### Tier-3（学习记录；M1 起填）

```
teaching/
├── M0/
│   ├── foundations/F-01-react-paradigm.md  ← M0 Step 1 起
│   ├── walkthroughs/M-*.md
│   └── experiments/<slug>/experiment-report.md
├── M1/...
└── M2/...
```

### 工具链（`tools/`）

| 文件 | 职责 |
|---|---|
| `phoenix-doctor.sh` | 环境预检（依赖 / 网络 / API key 配置） |
| `ci-check-spec.py` | Tier-0 4 件套 + 跨文档 ID 引用 + SPEC 版本号 |
| `ci-check-adr.py` | ADR 命名 / frontmatter / 编号唯一 |
| `ci-check-flags.py` | SPEC v1.1 §5.1 ↔ harness-flags-policy §3 一致性 |
| `ci-check-teaching.py` | 教学 artifact 字数 / frontmatter / ingest |
| `ci-check-milestone-dod.py` | M\*-plan §1 DoD 条款 ↔ retrospective 勾选闭环 |

### Repo 根入口

| 文件 | 职责 |
|---|---|
| `AGENTS.md` | 通用 LLM agent 入口（任何工具都可读） |
| `CLAUDE.md` | Claude Code 专用入口（自动注入对话上下文） |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR 描述模板，承载 CR-\* checkbox |

---

## 10. 阅读路径建议

### 10.1 新读者（人类）

完整理解项目，按顺序读：

1. 本文件（你正在读的）
2. `PRD.md` §1-3（项目目标 + 用户场景）
3. `TRD.md` §1-4（八层架构 + 关键决策）
4. `roadmap.md` §2-5（Milestone 序列 + 冻结节律）
5. `SPEC.md` §0-1 + §5.1（接口约定 + HarnessFlags）
6. `quality/definition-of-done.md`（三达标）
7. `adr/README.md` + `ADR-0000` + `ADR-0001`（看一份完整 ADR 长什么样）

预计 60-90 分钟。

### 10.2 LLM Agent 冷启动

按以下顺序加载到上下文：

1. 本文件 §3-7（治理结构 + 三达标）
2. `AGENTS.md`（硬约束）
3. 当前任务相关的 1-2 个具体文档（如改 SPEC 则加载 `spec-change-policy.md`）

避免一次性吞下整个 `docs/`。

### 10.3 维护者（修改既有规则）

1. 先读对应的 Tier-2 文件本身。
2. 检查 `documentation-rules §7` 看自己的改动是否触发 ADR / 版本号变更。
3. 改完跑：
   ```
   py -3 tools/ci-check-spec.py
   py -3 tools/ci-check-adr.py
   py -3 tools/ci-check-flags.py
   ```
4. 按 `.github/PULL_REQUEST_TEMPLATE.md` 写 PR；按 `quality/code-review-checklist.md` 自审。

---

## 11. 与其他入口文件的关系

- `docs/README.md`（本文件）= **canonical 治理原理 + 文档导航**。
- `AGENTS.md`（repo 根）= **薄 agent 入口**，只放硬约束 + 跳转链接，**不复制本文件内容**。
- `CLAUDE.md`（repo 根）= **Claude Code 专用入口**，一行指向 `AGENTS.md` + Claude-specific 补充（hooks / slash command 等）。

任何概念性 / 结构性更新只改本文件；agent 入口同步更新跳转链接即可，不复制详文。这是 §6.1 D-LLM-1 自包含原则在 entry-point 层面的延伸。

---

## 12. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-19 | 首版；治理原理 + Tier / Rule / Quality / ADR 角色矩阵 + 三贯穿原则 + 文档导航 + 三类阅读路径；与 `AGENTS.md` / `CLAUDE.md` 协同；作为 `docs/` 入口。 |
