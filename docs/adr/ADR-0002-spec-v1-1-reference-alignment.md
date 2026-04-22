---
id: ADR-0002
title: 以治理补丁方式收口 SPEC v1.1 引用并清理 v1.0 / v1.x 漂移
status: Accepted
date: 2026-04-22
authors: [dy]
related_spec: v1.1
related_dod: []
related_risk: []
related_flag: []
superseded_by: null
---

# ADR-0002：以治理补丁方式收口 SPEC v1.1 引用并清理 v1.0 / v1.x 漂移

- 状态：Accepted
- 日期：2026-04-22
- 作者：dy
- 摘要：当前仓库权威 SPEC 基线已是 `v1.1`，但 Tier-0 / rules / milestone 文档中仍残留大量 `SPEC v1.0` 与 `SPEC v1.x` 漂移引用。本 ADR 先冻结治理策略，再由后续补丁任务分两步完成 ADR 前置与批量收口。

---

## 1. 背景（Context）

- 现状：
  - `docs/SPEC.md` 首部版本已是 `v1.1`，且 `§19 变更日志` 已记载 `v1.0 -> v1.1` 的升级来源为 `ADR-0001`。
  - `docs/milestones/M0-plan.md`、`M1-plan.md`、`M2-plan.md`、`TRD.md`、`roadmap.md` 与多份 `docs/rules/*.md` 仍存在 `SPEC v1.0 §...` 或 `SPEC v1.x` 的引用。
  - 设计审查修复清单最初把这项工作集中放在 `T-P1-1` 一条大任务中。
- 触发事件：
  - 2026-04-22 设计审查明确指出当前 `SPEC` 版本收口不完整，导致版本冻结与复现基线漂移。
  - 执行修复清单时发现：若直接执行原 `T-P1-1`，会同时牵动 `SPEC`、`PRD`、`TRD`、`RnD-Analysis`、`M0/M1/M2-plan` 与 `ci-check-spec.py`，超过单轮安全推进范围。
- 既有规则 / 文档指向：
  - `docs/rules/spec-change-policy.md §4.2 / §5`：SPEC Minor 变更必须先有 ADR。
  - `docs/adr/README.md §2`：SPEC Minor / Major 变更是 ADR 强制触发项。
  - `artifacts/reviews/2026-04-22-design-audit-tasklist.md`：原 `T-P1-1` 的任务入口。

## 2. 问题（Problem）

- **核心问题**：仓库已经事实性进入 `SPEC v1.1`，但引用面仍停留在 `v1.0 / v1.x` 混用状态；如果不先把治理边界和执行顺序冻结，后续批量替换既可能违反 ADR 前置规则，也可能在单轮里同时改坏过多 Tier-0 文档。
- **不决策的代价**：
  1. `ci-check-spec.py` 的版本引用噪声持续存在，机器审计可信度下降。
  2. 后续 M1 / M2 启动前提仍可能引用模糊版本，冻结基线失真。
  3. 执行层容易把“引用收口”“规则升级”“版本语义修订”混成一轮大改，增加 review 风险。

## 3. 候选方案（Options）

### 3.1 方案 A：维持原 `T-P1-1` 一次性执行

- 描述：不拆任务；直接在一轮中完成 ADR、`SPEC v1.0 -> v1.1` 批量替换、`v1.x` 清理、`ci-check-spec.py` 规则升级、最小 changelog 补齐。
- 优点：
  - 任务总轮次少。
  - 一次改完后表面上最“干净”。
- 缺点：
  - 单轮牵动文件过多，容易命中停表条件。
  - ADR 前置、任务拆分、批量替换混在一起，review 面过宽。
  - 若中途发现某些 `v1.0` 引用不是机械替换问题，而是语义漂移，回退成本高。
- 成本 / 复杂度：高。

### 3.2 方案 B：先建 ADR，再把原 `T-P1-1` 拆成前置与执行两步

- 描述：先建立 ADR，明确“本轮处理的是治理收口，不新增接口语义”；再把任务拆成 `T-P1-1a`（ADR 前置与任务拆分）和 `T-P1-1b`（执行收口）。
- 优点：
  - 满足 SPEC 变更必须先有 ADR 的仓库硬约束。
  - 将“决策冻结”和“批量改文”解耦，便于逐轮确认。
  - 后续 `T-P1-1b` 的 diff 清单可更聚焦，风险更可控。
- 缺点：
  - 任务数量增加。
  - tasklist 需要先做一次结构性更新。
- 成本 / 复杂度：中。

### 3.3 方案 C：只做 grep 清单，不写 ADR，暂缓所有收口

- 描述：把命中点整理出来，但暂不新增 ADR，也不拆任务，等待后续更大一轮治理补丁统一处理。
- 优点：
  - 当前改动最少。
  - 不会立即触碰 Tier-0 文档。
- 缺点：
  - 与仓库硬约束不一致，无法形成可执行闭环。
  - 只是把问题继续向后推，无法驱动 `T-P1-1` 进入稳定执行态。
- 成本 / 复杂度：低，但收益也低。

## 4. 决策（Decision）

- 采用方案：**B**。
- 判定依据（按重要性列）：
  1. `AGENTS.md` 与 `spec-change-policy.md` 已把“改 SPEC 必须先开 ADR”写成硬约束，不能在执行期绕过。
  2. 原 `T-P1-1` 同时涉及多份 Tier-0 与 milestone 文档，拆成两步更符合“每轮只推进一个任务”的执行纪律。
  3. 本轮的主要目标是冻结治理路径，而不是直接判定每一处 `v1.0` 引用都可以机械替换。
  4. 设计审查修复清单本身就是操作界面；先把清单结构修对，后续执行才稳定。
- 放弃 A：单轮面太宽，容易把 ADR 前置和批量改文搅在一起。
- 放弃 C：不能形成可执行闭环，只是延后问题。

## 5. 影响面（Consequences）

- 代码影响：无。当前轮次不触碰 `src/phoenix/**`。
- SPEC 影响：本 ADR 不直接修改 `docs/SPEC.md` 接口语义；后续 `T-P1-1b` 负责处理 `v1.1` 引用收口与必要声明。
- DoD / KPI 影响：无直接阈值变化；影响的是版本引用一致性与里程碑冻结表达。
- 教学 artifact 影响：无。
- 风险影响：
  - 降低“单轮改动过宽导致 review 漏检”的风险。
  - 降低“在未先确认 ADR 的情况下直接动 SPEC 相关文档”的流程风险。
- 其他 ADR 影响：无；本 ADR 不 supersede 既有 ADR。

## 6. 迁移与回滚（Migration & Rollback）

- 迁移步骤（有序）：
  1. 新增本 ADR（ADR-0002）。
  2. 在修复 tasklist 中把原 `T-P1-1` 拆成 `T-P1-1a / T-P1-1b`。
  3. 完成 `T-P1-1a` 的 CI 校验，确认 ADR 编号、frontmatter、命名均合法。
  4. 下一轮单独执行 `T-P1-1b`，再进入真正的版本引用收口。
- 回滚预案：
  - 若作者认为拆分后反而增加治理负担，可回滚为单一 `T-P1-1` 表述，但仍需保留本 ADR，或以新 ADR 说明为何恢复一体化执行。
  - 本轮改动主要是文档治理层，回滚成本低。

## 7. 证据与参考（Evidence）

- `docs/SPEC.md` 首部与 `§19 变更日志`（当前权威版本为 `v1.1`）。
- `docs/milestones/M0-plan.md` / `M1-plan.md` / `M2-plan.md` 中现存的 `SPEC v1.0` / `v1.x` 引用。
- `docs/TRD.md`、`docs/roadmap.md`、`docs/rules/*.md` 中现存的旧引用。
- `docs/rules/spec-change-policy.md §4.2 / §5`。
- `docs/adr/README.md §2`。
- `artifacts/reviews/2026-04-22-design-audit-tasklist.md` 原 `T-P1-1`。

## 8. 后续行动（Follow-ups）

- [x] 新建 `ADR-0002-spec-v1-1-reference-alignment.md`。
- [x] 在修复 tasklist 中将 `T-P1-1` 拆为 `T-P1-1a / T-P1-1b`。
- [x] 运行 `py -3 tools/ci-check-adr.py`，确认 ADR 命名、frontmatter、编号合法。
- [x] 执行 `T-P1-1b`：完成 `SPEC v1.1` 引用收口、`v1.x` 清理、`ci-check-spec.py` 规则升级、最小变更日志补齐。
- [ ] 在 `T-P1-1b` 完成后，回填 tasklist 证据与 CI 输出。

---

## 修订记录

| 日期 | 状态变化 | 修订说明 |
|---|---|---|
| 2026-04-22 | Proposed → Accepted | 作者同意先拆 `T-P1-1`，本 ADR 作为前置治理决策落盘。 |
