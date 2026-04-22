---
id: ADR-0003
title: 以 SPEC v1.2 Minor 变更方式引入 CostBreakdown 双口径成本
status: Accepted
date: 2026-04-22
authors: [dy]
related_spec: v1.1 -> v1.2
related_dod: [DoD-M2-4, M2-KPI-3a, M2-KPI-3b]
related_risk: []
related_flag: []
superseded_by: null
---

# ADR-0003：以 SPEC v1.2 Minor 变更方式引入 CostBreakdown 双口径成本

- 状态：Accepted
- 日期：2026-04-22
- 作者：dy
- 摘要：承接 `T-P1-2`（决策 D-4 = C，双口径并记）。当前 `SPEC v1.1 §7.1 BenchmarkReport.cost_usd` 只能记录单一总成本，无法区分执行成本、评测成本、研究成本。为了让 `M2-KPI-3a` 与 `M2-KPI-3b` 可审计，SPEC 走一次 Minor 变更（`v1.1 -> v1.2`）新增 `CostBreakdown` 数据结构，并把 `BenchmarkReport.cost_usd` 替换为 `BenchmarkReport.cost: CostBreakdown`（保留 `cost_usd` 的 property 别名以保证向后兼容）。

---

## 1. 背景（Context）

- 现状：
  - `docs/PRD.md` 已将 `M2-KPI-3` 拆为 `M2-KPI-3a`（执行成本下降 ≥ 60%）+ `M2-KPI-3b`（端到端成本下降 ≥ X%）。
  - `docs/milestones/M2-plan.md DoD-M2-4` 已按双口径改写。
  - 但 `SPEC v1.1 §7.1 BenchmarkReport.cost_usd` 仍为单字段，`docs/rules/learning-artifact-rules.md §3.3` 的 `experiment-report` frontmatter 也只列了 `result / significance / subset / seed / model_*` 等，不包含双曲线成本。
  - `docs/rules/spec-change-policy.md §4.2 / §5`：SPEC 新增字段属 Minor；必须先开 ADR。
- 触发事件：
  - 2026-04-22 设计审查 `P1-2`：成本口径不闭合。
  - 第一轮修复（R1）错把本任务记为"已完成"，但 SPEC 实际未改，经 R2 审计暴露。

## 2. 问题（Problem）

- **核心问题**：`BenchmarkReport.cost_usd` 是单字段，违反"双口径并记"策略；`experiment-report` 模板缺少 `CostBreakdown` 字段，导致 Auto-Research 的历史记录无法回溯"执行 vs 端到端"的成本分布。
- **不决策的代价**：
  1. `M2-KPI-3a / 3b` 名义上拆开，实际无法落在可复核字段上。
  2. 未来补字段的时机若不在 M1 启动前，会触发 M1 跑出来的 Auto-Research 报告全部缺字段，治理债务累积。

## 3. 候选方案（Options）

### 3.1 方案 A：Patch 级字段增补，不升 SPEC 版本号

- 描述：只在 §7.1 追加 `CostBreakdown` 定义，`BenchmarkReport` 保持 `cost_usd` 不变，CostBreakdown 作为可选旁路字段。
- 优点：影响面极小，无需升版。
- 缺点：违反 `spec-change-policy.md`（字段新增就是 Minor）；`cost_usd` 单字段语义未解决，`INV-EV-3` 的交叉校验仍模糊。

### 3.2 方案 B：Minor 变更 v1.1 -> v1.2，新增 CostBreakdown，保留 cost_usd 作为 total_usd 别名（采用）

- 描述：升版 v1.1 -> v1.2；§7.1 新增 `CostBreakdown`；`BenchmarkReport.cost: CostBreakdown` 字段成为权威；`cost_usd` 保留为 `cost.total_usd` 的 property 别名（实现时在 Python 侧写 `@property`）。`INV-EV-3` 改为对 `cost` 所有子字段与 MetricsSink 交叉校验。
- 优点：符合 `spec-change-policy`；语义完整；向后兼容；未来再升 Major 时一次性能拆掉 `cost_usd` 别名。
- 缺点：触发 ADR 与 SPEC 引用 §x 不变但 `SPEC v1.1` 字样需要同步更新（Tier-0 文档 + rules 一次小改）。

### 3.3 方案 C：Major 变更 v1.1 -> v2.0，彻底重做 §7

- 描述：不保留 `cost_usd`；`BenchmarkReport` 重写；同时把 Evaluator 配置也合并进此次变更。
- 优点：一步到位。
- 缺点：在 M0 中期触发 Major 变更代价远高于收益；M0/M1 前序的所有教学节点需要追认。

---

## 4. 决策（Decision）

**采用方案 B**：走 Minor 变更 `SPEC v1.1 -> v1.2`，新增 `CostBreakdown`，`BenchmarkReport.cost` 为权威字段，`cost_usd` 作为 `cost.total_usd` 的向后兼容别名。

理由：

- 符合 `spec-change-policy §4.2` 的 Minor 判定；
- 不打破任何现存的代码或文档（无代码还未落地，文档层仅新增语义，不删旧字段）；
- 把后续 `M2-KPI-3a / 3b` 与 `experiment-report` 的证据字段钉到 `CostBreakdown` 子字段上，机器可审计。

---

## 5. 后果（Consequences）

### 5.1 立即变更

- `docs/SPEC.md` §7.1 新增 `CostBreakdown`；修改 `BenchmarkReport` 采用 `cost: CostBreakdown`；修改 `INV-EV-3`；`§19 变更日志` 追加 `v1.2` 条目。
- `docs/SPEC.md` 版本号 `v1.1 -> v1.2`；首部 `版本：v1.2`。
- `docs/rules/learning-artifact-rules.md §3.3` `experiment-report` frontmatter 增加 `cost.execution_usd / cost.evaluation_usd / cost.research_usd / cost.total_usd` 必填；变更日志追加 `v1.1` 条目。
- `docs/milestones/M1a-plan.md §0` / `M1b-plan.md §0` 将启动冻结版本写为 `SPEC v1.2`（其他 Tier-0 / M-plan 中的 `SPEC v1.1` 引用**按章节号不变原则**可保留，不做批量替换，见 §5.3）。

### 5.2 向后兼容保证

- `BenchmarkReport.cost_usd` 通过 `@property` 等价于 `cost.total_usd`；现存的 M2-KPI-3 单口径消费者不会立即断裂。
- 在 M1a Step 6（Evaluation Runner 最小能力）实现时统一落实双字段。

### 5.3 引用面约束（避免 v1.1 -> v1.2 再触发一次 T-P1-1b）

- Tier-0 / rules / milestone 文档中既存的 `SPEC v1.1 §<num>` 引用**保持不变**：`§7` 节号未漂移，`§5.1` / `§6.1` 等无关章节语义未动。
- 只有**直接引用 `BenchmarkReport.cost_usd` 字段**或**新增 experiment-report 成本字段**的两处改写。
- `tools/ci-check-spec.py` 的 `SPEC v1\.x` 规则仍然生效，无需放宽。

### 5.4 对齐的下游

- `M2-plan.md DoD-M2-4`（已双口径）继续成立。
- `experiment-report` 新模板的 CI 校验由 `ci-check-teaching.py` 后续波次吸收（T-P2-2 续）。

---

## 6. 回滚条件

- 若 `BenchmarkReport.cost_usd` 别名在实现时出现序列化冲突（例如多个消费者期望字段存在而不认 property），允许在 M1a Step 6 之前降级为"cost + cost_usd 双写字段"；无需 Major 回滚。

---

## 7. 交叉引用

- `docs/rules/spec-change-policy.md`
- `docs/SPEC.md §7 / §19`
- `docs/PRD.md M2-KPI-3a / 3b`
- `docs/milestones/M2-plan.md DoD-M2-4`
- `docs/rules/learning-artifact-rules.md §3.3`
- `artifacts/reviews/2026-04-22-design-audit-tasklist.md T-P1-2`
