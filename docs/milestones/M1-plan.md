# Milestone 1 — 入口与拆分索引（M1 = M1a + M1b）

- 版本：v1.1（2026-04-22）
- 作者：dy
- 目的：按 [`2026-04-22-design-audit-tasklist.md`](../../artifacts/reviews/2026-04-22-design-audit-tasklist.md) T-P1-5（D-3 = B）将原单体 M1 拆成两个子里程碑，降低单阶段交付面。本文件仅作索引，Step 清单与 DoD 分别落在 `M1a-plan.md` / `M1b-plan.md`。
- 上位文档：PRD.md §10、TRD.md §4 / §6 / §7 / §8、RnD-Analysis.md §6.2、SPEC.md §5 / §6 / §7 / §8、M0-plan.md
- 变更日志：

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版（单体 M1）；以 DoD-M1-1~10 覆盖 runtime / plan / memory / evaluation / auto-research / 长程任务全量 |
| v1.1 | 2026-04-22 | 按 T-P1-5 拆出 M1a（self runtime 最小价值闭环）与 M1b（长程任务 + Auto-Research + Memory 七动词全量），本文件降为索引；正文迁到 `M1a-plan.md` / `M1b-plan.md` |

---

## 0. 启动前提

M1 整体的启动前提由 M1a 承担（M1a-plan.md §0），进入 M1b 的前提由 M1b-plan.md §0 承担。本索引仅重申三条全局约束：

- M0-plan.md 的 Step 12 已验收通过，DoD-1~DoD-7 全部成立。
- `AgentRuntime` / `MemoryBackend` / `ToolSpec` + `PluginRegistry` 三个硬接口已按 `docs/rules/spec-change-policy.md S-FREEZE-0`（Soft-Freeze）进入 M1a；Step 7 起进入 hard-freeze，M1b 期间禁止 Patch 级改动。
- 启动冻结版本：`PRD v1.0` / `TRD v1.0` / `SPEC v1.2`（CostBreakdown 双口径落地后版本，ADR-0003）。

---

## 1. 完成定义（DoD 汇总，状态驱动）

本文件的 DoD 汇总自 M1a / M1b 两份子 plan，便于外部文档以"M1 DoD"单一入口引用。条款具体定义落在对应子文件。

- **DoD-M1-1**：见 `M1a-plan.md §1`（`--runtime=self` 在 `codex-base` / `kimi-worker` 上成功）。
- **DoD-M1-1a**：见 `M1a-plan.md §1`（kimi-worker 滚动成功率 ≥ 95%）。
- **DoD-M1-2**：见 `M1a-plan.md §1`（HarnessFlags s01/s02/s03/s04/s06/s07/s12 可开关）。
- **DoD-M1-3**：见 `M1a-plan.md §1`（5 步验证链硬编码）。
- **DoD-M1-4**：见 `M1a-plan.md §1`（编程插件四件套上线）。
- **DoD-M1-5a**：见 `M1a-plan.md §1`（`MemoryBackend` 基础四动词）。
- **DoD-M1-5b**：见 `M1b-plan.md §1`（`MemoryBackend` 七动词全量）。
- **DoD-M1-6**：见 `M1a-plan.md §1`；`phoenix eval --benchmark=swe-bench-verified --subset=50 --runtime=self --model=codex-base` 的 Resolved Rate 相对 `artifacts/M0/baseline-swebench.json` 中冻结基线的比例 ≥ 0.85。
- **DoD-M1-7**：见 `M1b-plan.md §1`（长程任务完成率 ≥ 80%）。
- **DoD-M1-8**：见 `M1b-plan.md §1`（Auto-Research ≥ 3 轮 + ≥ 2 项 Kept）。
- **DoD-M1-9a**：见 `M1a-plan.md §1`（F-07~F-15 ingest）。
- **DoD-M1-9b**：见 `M1b-plan.md §1`（F-16~F-22 ingest）。
- **DoD-M1-10a**：见 `M1a-plan.md §1`（M1a retrospective + soft→hard freeze 过渡）。
- **DoD-M1-10b**：见 `M1b-plan.md §1`（M1b retrospective + 进入 M2 前再次确认冻结无漂移）。

---

## 2. 为什么拆分

- 原单体 M1 同时承诺 runtime、plan、compression、validation chain、permission、hook、worktree、编程插件三件套、persistence、subagent、memory 七动词、evaluation 全量、长程任务集、Auto-Research 3–5 轮、`F-07~F-22` 全入库。
- RnD-Analysis §6.2 估算为 80–120h；单阶段风险集中。
- D-3=B 的决定：优先让"自研 Core 可用"（M1a）独立可证，再做"自我优化循环"（M1b）。
- 代价：DoD 分层后，M2 启动前提从"M1 Step 14 全部通过"改为"M1a + M1b 全部通过"；允许 M1b 与 M2 早期步骤并行（详见 `M2-plan.md` §0）。

---

## 3. 拆分总览

| 子里程碑 | 文件 | 北极星 | 硬 DoD |
|---|---|---|---|
| M1a | [M1a-plan.md](M1a-plan.md) | 证明自研 Core + 编程插件 + subset evaluation 可稳定运行 | DoD-M1-1 / 1a / 2 / 3 / 4 / 5a / 6 / 9a / 10a |
| M1b | [M1b-plan.md](M1b-plan.md) | 证明自我优化循环与长程任务可运作 | DoD-M1-5b / 7 / 8 / 9b / 10b |

注：原 `DoD-M1-5` 拆为 `5a`（M1a：基础四动词）+ `5b`（M1b：补齐三动词）；原 `DoD-M1-9` 拆为 `9a`（`F-07~F-15`）+ `9b`（`F-16~F-22`）；原 `DoD-M1-10` 拆为 `10a`（M1a retrospective + soft→hard freeze 过渡）+ `10b`（M1b retrospective + 进入 M2 前再次冻结确认）。

---

## 4. 下位依赖

- `M1a-plan.md`：详细 Step 清单、§4 学习节点索引（F-07~F-15）、§5 验证命令、§6 退路。
- `M1b-plan.md`：详细 Step 清单、§4 学习节点索引（F-16~F-22）、§5 验证命令、§6 退路。
- 进入 M2 前：见 `M2-plan.md §0`，要求 M1a + M1b 全部 DoD 成立。

---

## 5. 变更来源

- 本拆分由 T-P1-5 驱动，决策 D-3 = B（见 `artifacts/reviews/2026-04-22-design-audit-tasklist.md`）。
- 配套调整：
  - `docs/roadmap.md`、`docs/README.md`、`docs/SPEC.md` §18 目录、`docs/rules/documentation-rules.md` 目录结构图中对 `M1-plan.md` 的引用继续成立（本文件即入口）。
  - `docs/quality/definition-of-done.md`、`docs/milestones/M2-plan.md` 中对 `M1-plan.md §1` 的硬引用继续成立（M1a/M1b 合计语义）。
