---
id: ADR-NNNN
title: <一句话标题，例如：采用 Moonshot 标准 API 而非 Kimi Coding 专用端点>
status: Proposed
date: YYYY-MM-DD
authors: [dy]
related_spec: null         # 或 v1.0；SPEC 变更类 ADR 必填到 Minor 粒度
related_dod: []            # 例如 [DoD-M1-6]；无则空数组
related_risk: []           # 例如 [R-ML-1]
related_flag: []           # 例如 [s03]
superseded_by: null        # 或 ADR-NNNN
---

# ADR-NNNN：<标题与 frontmatter 一致>

- 状态：Proposed
- 日期：YYYY-MM-DD
- 作者：dy
- 摘要：一句话描述本 ADR 决定了什么（≤ 3 行；给后来者 5 秒内看懂）。

> 使用说明：复制本文件为 `docs/adr/ADR-NNNN-<slug>.md` 后按顺序填写以下 8 个章节。每节都不得留空；若某节确实不适用，写 "N/A — <原因>"。

---

## 1. 背景（Context）

描述触发本决策的客观事实、约束、以及它发生在哪个 Milestone / Step。
- 现状：...
- 触发事件：...
- 既有规则 / 文档指向：...

## 2. 问题（Problem）

把"背景"精炼成一句可判定的问题，以"如果不决策会怎样"结尾。
- 核心问题：...
- 不决策的代价：...

## 3. 候选方案（Options）

**至少列 2 个候选**（包括"维持现状"）；任何"只有一个方案"的 ADR 都要在本节写"为什么只有一个"。

### 3.1 方案 A：<名字>
- 描述：...
- 优点：...
- 缺点：...
- 成本 / 复杂度：...

### 3.2 方案 B：<名字>
- 描述：...
- 优点：...
- 缺点：...
- 成本 / 复杂度：...

（可追加 C/D/...）

## 4. 决策（Decision）

- 采用方案：A / B / ...
- 判定依据（按重要性列 2-5 条证据）：
  1. ...
  2. ...
- 放弃候选的关键原因：...

决策必须能被 6 个月后的自己复读后理解，无需外部对话上下文。

## 5. 影响面（Consequences）

列出本决策带来的所有可预见影响，**好坏都写**。

- 代码影响：`src/phoenix/<path>` 需要 ...（若本 ADR 在 SPEC 变更前写，此处可列"预期影响"）
- SPEC 影响：`SPEC vX.Y.Z` 的 §... 将 ...
- DoD / KPI 影响：DoD-M<N>-<K> 从 ... 调整为 ...（若不调整也明说）
- 教学 artifact 影响：F-<idx> / M-<slug> 需要新增 / 降 tier
- 风险影响：`R-*` 新增 / 升降状态
- 其他 ADR 影响：将 supersede / deprecate 哪些既有 ADR

## 6. 迁移与回滚（Migration & Rollback）

- 迁移步骤（有序）：
  1. ...
  2. ...
- 回滚预案：如果事后证明本决策错，如何回退？窗口期多长？
- 若决策不可回滚，写"不可回滚"，并说明为什么（通常涉及数据迁移 / Milestone 冻结）。

## 7. 证据与参考（Evidence）

决策所引用的外部信号，**全给可追资源**（不给"口口相传"）。

- 基准 / 评测报告：`docs/teaching/M<N>/experiments/<slug>/experiment-report.md`
- 代码引用：commit sha / PR 号
- 外部资料：URL
- 相关 ADR：ADR-NNNN

## 8. 后续行动（Follow-ups）

本 ADR 合入后必须完成的后置动作清单（作为 PR 的验收条目）：

- [ ] ...
- [ ] ...

---

## 修订记录

> 本节默认留空；后续以追加方式记录修订。禁止覆盖式修改上述 8 节内容。

| 日期 | 状态变化 | 修订说明 |
|---|---|---|
| YYYY-MM-DD | Proposed → Accepted | 合入 |
