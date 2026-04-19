---
id: ADR-0000
title: 采用 ADR（Architecture Decision Records）作为项目决策唯一载体
status: Accepted
date: 2026-04-18
authors: [dy]
related_spec: v1.0
related_dod: []
related_risk: []
related_flag: []
superseded_by: null
---

# ADR-0000：采用 ADR 作为项目决策唯一载体

- 状态：Accepted
- 日期：2026-04-18
- 作者：dy
- 摘要：本项目引入 `docs/adr/` 作为所有"可解释决策"的单一载体；SPEC 变更、DoD 豁免、风险触发、路线图决策、HarnessFlags 翻转全部归入此处。本 ADR 自证 ADR 体系本身。

---

## 1. 背景（Context）

在本 ADR 写入之前：

- `spec-change-policy.md §5 Step 1` 要求 SPEC Minor/Major 变更"登记 ADR"，但 ADR 目录为空且流程未定义。
- `definition-of-done.md §9` 要求 DoD 豁免走 ADR，同样悬空。
- `risk-register.md §3 R-2`、`roadmap.md §6`、`harness-flags-policy.md §5`（规划中）都把"走 ADR"当作默认流程。
- 作者（dy）为单人开发，口头 / commit message / Slack 等渠道的决策记录会随时间失忆。

因此先建立 ADR 体系本身，才能让上述规则可执行。

## 2. 问题（Problem）

- **核心问题**：多份治理文件都指向"走 ADR"，但 ADR 没有载体、没有命名规则、没有触发清单、没有状态机；这些规则就**全部成空转**。
- **不决策的代价**：SPEC / DoD / 风险 / 路线图的"为什么"只能靠翻 git log 和 chat 历史，随时间指数级劣化；项目 6 个月后自己读自己的决策将不可行，违反 `documentation-rules` D-LLM-13。

## 3. 候选方案（Options）

### 3.1 方案 A：`docs/adr/` 目录 + Markdown + 本 README 定义的最小流程

- 描述：采用行业通行的 MADR / Nygard 风格，文件级 ADR，frontmatter 机读，README 承载流程。
- 优点：离线可读、git 友好、与 Tier-0 文档风格一致、被 `documentation-rules` D-DIR-1 直接锁定。
- 缺点：需要作者自律写；无 Web UI。
- 成本：极低；一次建立 README + TEMPLATE + 本 ADR 即落位。

### 3.2 方案 B：用 GitHub Issues / Discussions 代替 ADR

- 描述：把"决策"写在 issue/discussion 里。
- 优点：评论流方便；搜索好。
- 缺点：违反 `documentation-rules` D-LLM-12（禁止外部上下文依赖、离线不可读）；不进 wiki ingest；git blame 不可追；issue 会随平台变。
- 成本：中（需要 label 规约 + 导出脚本）。

### 3.3 方案 C：把决策内容嵌入 `docs/milestones/M*-plan.md` 的 Step 里

- 描述：没有独立 ADR 目录，决策就写在 Step 注释里。
- 优点：与执行计划物理靠近。
- 缺点：M\*-plan 一旦冻结就不允许改；而"为什么"可能在后来才被推翻 / 修订；且 Step 级粒度承载不下跨 Milestone 的决策；违反 "Tier-0 稳定性" 原则。
- 成本：低但技术债高。

## 4. 决策（Decision）

- 采用方案：**A**（独立 `docs/adr/` 目录 + Markdown + README 流程）。
- 判定依据：
  1. 与 `documentation-rules` D-LLM-1 / D-LLM-12 一致（自包含、离线可读）。
  2. `spec-change-policy` / `definition-of-done` / `risk-register` / `roadmap` 四处已写明"走 ADR"，有独立目录才成立。
  3. git 原生版本追溯，无需额外工具，与现有 `wiki-ingest` 流程零冲突。
  4. 作者为单人开发，最轻量方案即可解决问题，不引入额外平台依赖。
- 放弃 B：外部上下文依赖违规。
- 放弃 C：与 Tier-0 / Tier-1 的职责划分冲突，且粒度不适配跨 Milestone 决策。

## 5. 影响面（Consequences）

- **代码影响**：无（治理层变更）。
- **SPEC 影响**：无直接 SPEC 条款变更；本 ADR 是 SPEC v1.0 的补充治理载体。
- **DoD / KPI 影响**：`definition-of-done §9` 中"必须通过 ADR"从悬空变为可执行。
- **文档体系影响**：`documentation-rules §7` 已将 `docs/adr/` 作为受管目录；本 ADR 合入后 README + TEMPLATE + ADR-0000 三文件即为 A-3 体系最小形态。
- **风险影响**：无新增；`RnD-Analysis §4` 未识别"决策失忆"为独立风险，但 `R-TL-2`（artifact 质量参差）在精神上相关。
- **其他 ADR 影响**：无前置被取代；本 ADR 作为编号 0 的 meta-ADR，供所有后续 ADR 引用。

## 6. 迁移与回滚（Migration & Rollback）

- 迁移步骤：
  1. 创建 `docs/adr/README.md`、`docs/adr/ADR-TEMPLATE.md`、本文件（本 ADR 提交即完成）。
  2. `documentation-rules §7` 目录结构已提前包含 `docs/adr/`，无需再改。
  3. 未来 PR 触发器：SPEC Minor/Major、DoD 豁免、风险 `triggered`、路线图决策、HarnessFlags 默认翻转、冻结期破冻。
- 回滚预案：若证明 ADR 体系过重（例如作者长时间未产出任何 ADR 且流程沦为形式），可由新 ADR 将本 ADR 转为 `Superseded`，同时在 `documentation-rules §7` 目录结构中删除 `docs/adr/`。本 ADR 不可"静默撤销"。

## 7. 证据与参考（Evidence）

- `docs/rules/spec-change-policy.md §5 Step 1`
- `docs/quality/definition-of-done.md §9`
- `docs/risk-register.md §3 R-2`
- `docs/roadmap.md §6`
- 外部参考：MADR、Michael Nygard "Documenting Architecture Decisions"（格式灵感来源，不作为强制范式）

## 8. 后续行动（Follow-ups）

- [x] 创建 `docs/adr/README.md`
- [x] 创建 `docs/adr/ADR-TEMPLATE.md`
- [x] 本 ADR-0000 合入
- [x] C-9（`tools/ci-check-adr.py`）占位实现：校验 ADR 命名 / frontmatter / 编号无重复
- [ ] 首次"真实" ADR（ADR-0001）出现在 M1 Step 1 前后（`self-runtime` 首次 SPEC 变更）

---

## 修订记录

| 日期 | 状态变化 | 修订说明 |
|---|---|---|
| 2026-04-18 | Proposed → Accepted | ADR 体系自证立项，与 README / TEMPLATE 同批合入。 |
