# Milestone 1 — 执行顺序计划（Step-based，工程 × 学习同步）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 上位文档：PRD.md §10、TRD.md §4 / §6 / §7 / §8、RnD-Analysis.md §6.2、SPEC.md §5 / §6 / §7 / §8、M0-plan.md
- 总目标：实现 `PhoenixCoreRuntime`（最小 ReAct + Plan + Compression + 验证链）+ 编程插件 + MemoryBackend 完整闭环 + Evaluation Runner 全量 + Auto-Research v1；在 SWE-bench Verified 子集上 Resolved Rate ≥ "Claude Agent SDK + Codex" 基准的 85%，长程任务完成率 ≥ 80%。

---

## 0. 启动前提

- M0-plan.md 的 Step 12 已验收通过，DoD-1~DoD-7 全部成立。
- `AgentRuntime` / `MemoryBackend` / `ToolSpec` + `PluginRegistry` 三个硬接口已在 SPEC v1.1 冻结；进入 M1 后若需变更，走"SPEC 先行"流程。
- 学习节点 `F-01 ~ F-06 + F-mem-1/2 + F-05a/b + F-model-1`（M0 产出）已 `wiki-ingest` 并可被 `wiki-query` 召回。
- 启动冻结版本：`PRD v1.0` / `TRD v1.0` / `SPEC v1.1`。

---

## 1. 完成定义（DoD，状态驱动）

- **DoD-M1-1**：`phoenix run --task "..." --runtime=self --model=codex-base` 在 M0 的 echo 任务上返回 `status="success"`；`--runtime=self --model=kimi-worker` 同样成功。
- **DoD-M1-1a**：最近 20 次滚动运行中，`--runtime=self --model=kimi-worker` 成功率 ≥ 95%；若未达标，M1 不得关闭。
- **DoD-M1-2**：12 层 Harness 中 s01 / s02 / s03 / s04 / s06 / s07 / s12 在自研 Core 中可运行；每层可通过 `HarnessFlags` 开关（SPEC v1.1 §5.1）。
- **DoD-M1-3**：5 步验证链（`validateInput → PreToolUse Hook → checkPermissions → executeTool → mapToolResultToAPI`）在 `PhoenixCoreRuntime.run_task` 内硬编码强制执行。
- **DoD-M1-4**：编程插件 `coding.git_worktree` / `coding.multi_file_edit` / `coding.test_runner` / `coding.harness_validator` 四个工具上线。
- **DoD-M1-5**：`MemoryBackend` 七动词（ingest / query / digest / import_bulk / graph / lint / tier）在 `AKLLMWikiBackend` 全部可用。
- **DoD-M1-6**：`phoenix eval --benchmark=swe-bench-verified --subset=50 --runtime=self --model=codex-base` 的 Resolved Rate 相对 `artifacts/M0/baseline-swebench.json` 中冻结基线的比例 ≥ 0.85。
- **DoD-M1-7**：长程任务（SWE-EVO / SlopCodeBench 任一 + PhoenixAgent 自定义 ≥ 5 个）上的完成率 ≥ 80%。
- **DoD-M1-8**：Auto-Research 完成 ≥ 3 轮有效迭代；至少 2 项 Kept 变更在 wiki 留档（含 `experiment-report.md`）。
- **DoD-M1-9**：学习节点 `F-07 ~ F-22`（见 §4 索引）全部 `wiki-ingest` 并可召回。
- **DoD-M1-10**：M1b retrospective + interface-backlog 写入 wiki；进入 M2 前三个硬接口再次冻结。

---

## 2. 整体依赖图

```
Step 1 (Core ReAct s01+s02) ──▶ Step 2 (Plan s03) ──▶ Step 3 (Compression s06)
                                    │
                                    ▼
                              Step 4 (验证链 + Permission + Hook)
                                    │
                                    ▼
                              Step 5 (Worktree s12 + git 工具)
                                    │
                                    ▼
                              Step 6 (编程插件三件套)
                                    │
                                    ▼
Step 7 (Persistence s07) ──▶ Step 8 (Subagent s04)
                                    │
                                    ▼
                              Step 9 (Memory 七动词补全)
                                    │
                                    ▼
Step 10 (EvaluationRunner 全量) ──▶ Step 11 (长程任务接入)
                                    │
                                    ▼
Step 12 (Auto-Research Loop v1 实现)
                                    │
                                    ▼
Step 13 (Auto-Research 3–5 轮实测)
                                    │
                                    ▼
Step 14 (retrospective + interface freeze)
```

- Step 7 与 Step 8 可小范围并行（Subagent 在 Persistence 提供 task_id 后接线）。
- Step 10 与 Step 11 可并行，但 Step 12 必须等两者都完成。

---

## 3. Step 清单

### Step 1 — MemoryBackend 七动词补全 〔量级：M〕

**工程任务**
- `src/phoenix/memory/akllmwiki.py` 补齐 `import_bulk` / `graph` / `lint` / `tier`（SPEC v1.1 §6.1）。
- `phoenix memory` CLI 子命令上线（`ingest|query|digest|import|graph|lint|tier`）。
- 数据治理策略：
  - 每次 Auto-Research 迭代结束后自动 `lint(auto_fix=True)`。
  - 每完成一个 Milestone 跑 `tier`，把 M(N-1) 的节点降到 archived，M(N-2) 降到 frozen（除非显式保留）。

**内嵌学习（产出 F-16）**
- 必读：
  - AK-llm-wiki README 的 `tier` / `graph` / `import` 段落。
  - mindstudio wiki-vs-RAG 博文的"老化与清理"讨论。
- 要回答：
  - `import_bulk` 的冲突策略（同 slug 已存在时）？
  - `graph.scope` 与 `query.namespace` 的区别？
  - `tier` 的 active/archived/frozen 三层如何影响 `query` 权重？

**产物**
- `akllmwiki.py` 七动词完整实现（subprocess 包装）
- `src/phoenix/cli.py` 增加 `phoenix memory ...` 子命令
- `docs/teaching/M1/foundations/F-16-memory-seven-verbs.md`

**进入下一步条件**
- `phoenix memory import --source obsidian --root ~/vault --namespace personal-notes` 成功导入 ≥ 20 个节点；`lint` 无致命错误。
- F-16 入库。

---

### Step 2 — EvaluationRunner 全量 + Codex Evaluator 〔量级：L〕

**工程任务**
- `src/phoenix/evaluation/runner.py` 从 M0 的 subset=1 扩至 subset=N；集成 Codex 作为 Evaluator（`evaluation/prompts/evaluator.v1.md`）。
- `src/phoenix/evaluation/scoring.py`：Resolved Rate / pass@1 / Human Edit Distance / 成本估算（tokens × 价目）。
- 自动 `wiki-ingest` 到 `namespace="evaluation"`；metrics 落 SQLite `phoenix_metrics`。

**内嵌学习（产出 F-17）**
- 必读：
  - Anthropic Codex / Claude 作为 Evaluator 的官方指南（若无官方文档，则用 Karpathy gist + Prompt Injection 防御篇）。
  - SWE-bench 官方 benchmarking 模板。
- 要回答（写进 `F-17-evaluator-design.md`）：
  - Evaluator Prompt 固化的必要性，版本管理策略？
  - seed / temperature 控制与多次取平均的权衡？
  - Prompt Injection 防御清单（不喂原 task、不暴露 COT、输入字段白名单）？

**产物**
- `runner.py`、`scoring.py`、`evaluation/prompts/evaluator.v1.md`
- `docs/teaching/M1/foundations/F-17-evaluator-design.md`

**进入下一步条件**
- `phoenix eval --benchmark=swe-bench-verified --subset=50 --runtime=self --model=codex-base` 与 `--runtime=claude` 基线产出可对比的 BenchmarkReport。
- F-17 入库。

---

### Step 3 — 长程任务接入（SWE-EVO / SlopCodeBench + 自定义） 〔量级：L〕

**工程任务**
- `src/phoenix/evaluation/sweevo.py` 或 `slopcodebench.py`（择一优先）：加载官方数据集并转换为 `BenchmarkTask` 列表；多 commit / 多步任务由 Runner 串行驱动。
- `evaluation/tasks/phoenix-custom/*.yaml`：作者撰写 ≥ 5 个多文件重构 + 持久化任务（基于自己真实遇到的场景）。
- 长程指标：`LongHorizonMetrics`（completion rate / recovery rate / persistence / decision stability）。

**内嵌学习（产出 F-18）**
- 必读：
  - SWE-EVO 论文（arXiv:2512.18470）的数据集与 harness 设计章节。
  - SlopCodeBench 的 README / 论文。
- 要回答：
  - 长程任务的"成功"定义如何避免 reward hacking？
  - recovery rate / decision stability 的计算方式？
  - 自定义任务集如何保证"既像真实场景又可自动化验证"？

**产物**
- `src/phoenix/evaluation/{sweevo,slopcodebench}.py`（择一）
- ≥ 5 个 `phoenix-custom/*.yaml` 任务定义
- `docs/teaching/M1/foundations/F-18-longhorizon-metrics.md`

**进入下一步条件**
- 长程任务集上 `phoenix eval --benchmark=<family>` 输出合法 `LongHorizonMetrics`。
- F-18 入库。

---

### Step 4 — Auto-Research Loop v1 实现 〔量级：L〕

**工程任务**
- `src/phoenix/research/loop.py`：严格按 SPEC v1.1 §8.2 的 7 步流程实现；Generator 调用 `PhoenixCoreRuntime`，Evaluator 走 Step 2 的 Runner。
- `src/phoenix/research/patching.py`：git branch 管理 + `allowed_change_globs` 守门 + 显著性检验（proportion z-test / bootstrap）。
- `phoenix research --rounds=N --benchmark=...` CLI。

**内嵌学习（产出 F-19 + F-20）**
- F-19 "GAN-style Generator-Evaluator"：
  - 必读：Karpathy Auto-Research gist、Auto Agent 项目 README。
  - 要回答：为什么 Generator 与 Evaluator 必须是不同模型？自评偏差的具体形式？
- F-20 "显著性检验 for Agent 实验"：
  - 必读：Anthropic 或第三方关于 LLM A/B 统计检验的博客。
  - 要回答：proportion z-test vs bootstrap 各自适用场景？p<0.05 的实际风险？

**产物**
- `src/phoenix/research/loop.py`、`src/phoenix/research/patching.py`
- `docs/teaching/M1/foundations/F-19-generator-evaluator.md`
- `docs/teaching/M1/foundations/F-20-significance-testing.md`

**进入下一步条件**
- 在 Step 2 的 Runner 上，`phoenix research --rounds=2 --benchmark=swe-bench-verified --subset=20` 完整跑完；无论 Keep / Discard，每轮都有 `experiment-report.md` 写 wiki。
- F-19 / F-20 入库。

---

### Step 5 — Auto-Research ≥ 3 轮实测与分析 〔量级：M〕

**工程任务**
- 正式跑 ≥ 3 轮完整 Auto-Research（每轮 5–15 次迭代），变更范围限 `harness/ + plugins/ + memory/digest_rules/`。
- 每轮结束：整理 `experiment-report.md`（前后对比 / token 成本曲线 / Resolved Rate 变化 / 显著性结论）。
- 选 ≥ 2 项显著 Kept 变更，额外写一段"机理解读"：为什么这个 patch 有效？

**内嵌学习（产出 F-21）**
- 必读：重读 F-19 / F-20；翻一遍 Karpathy gist 的迭代日志风格。
- 要回答：
  - 噪声与 seed 的关系，多 seed 平均如何平衡成本与置信度？
  - "收益递减 3 轮自动终止"的具体阈值如何设计？
  - Kept 变更如何回灌到 `docs/teaching/M1/foundations/` 作为"本轮学习到的 Harness 改进"？

**产物**
- ≥ 3 份 `experiment-report.md` 存档并入 wiki
- ≥ 2 份 Kept 变更的"机理解读"笔记
- `docs/teaching/M1/foundations/F-21-autoresearch-ops.md`

**进入下一步条件**
- DoD-M1-8 成立。
- F-21 入库。

---

### Step 6 — M1b retrospective + 接口冻结 checkpoint 〔量级：S〕

**工程任务**
- 汇总 milestone-level artifact：
  - `docs/teaching/M1/M-harness-walkthrough.ipynb`（串起 s01 / s02 / s03 / s06 / s12 的代码走读）。
  - `docs/teaching/M1/M-autoresearch-lab.md`（从 Step 4 到 Step 5 的完整实验记录）。
  - `docs/teaching/M1/M-longhorizon-eval.md`（Step 3 的指标解读）。
- 交叉审阅接口变更：`AgentRuntime` / `MemoryBackend` / `ToolSpec` 及本阶段新增的 `HarnessFlags` / `PermissionRules` / `EvaluationRunner` 是否稳定；必要时按 `docs/rules/spec-change-policy.md` 递增 SPEC 版本号。
- `phoenix-doctor.sh --json > artifacts/doctor-m1-final.json`；`wiki-lint --auto-fix`。
- `docs/milestones/M1-retrospective.md`：KPI 达标情况、意外发现、每个 F-* 的自测结果。

**内嵌学习（产出 F-22）**
- 无新资料阅读；本节点是"本阶段学到了什么"的元反思。要求写一段"若现在让我重写 M1，我会改哪 3 件事"。

**产物**
- 3 份 milestone artifact 全部入 wiki（`.ingested.json` marker 更新）。
- `docs/milestones/M1-retrospective.md`
- `artifacts/doctor-m1-final.json`
- 可能的 SPEC 升版 → 同步 `wiki-ingest`
- `docs/teaching/M1/foundations/F-22-milestone-meta-reflection.md`

**进入下一步条件**
- DoD-M1-1 ~ DoD-M1-10 全部成立。
- 三个硬接口（含 M1 新增）在 M2 Step 1 启动前不再破坏性变更。

---

## 4. 学习节点索引

按 M1 教学闭环“每能力块必有”规则，同属一类的节点在完结时可合并编写（如 `F-16` 和 `F-17` 可合并为一份“评测基础”产出）。

| 节点 | 产自 Step | 能力块主题 |
|---|---|---|
| F-16 | 1 | Memory 七动词补全 (记忆进阶) |
| F-17 | 2 | Evaluator Prompt 与 Injection 防御 (评测基础) |
| F-18 | 3 | 长程扩展基准指标 (评测基础) |
| F-19 | 4 | GAN-style Generator-Evaluator (自研究循环) |
| F-20 | 4 | LLM 显著性检验 (自研究循环) |
| F-21 | 5 | Auto-Research 运作流 (自研究循环) |
| F-22 | 6 | M1b 回顾与反思 (里程碑总结) |

---

## 5. 风险预警（M1 阶段新增 / 升级）

| 编号 | 风险 | 触发步骤 | 缓解 |
|---|---|---|---|
| R-RT-1 | 自研 Core 初期 Resolved Rate 不达 85% | Step 2 | 延长 Step 4 / 13 专项调教；必要时 Step 6 把 DoD-M1-6 调成 "≥ 基线的 75%" 并在 retrospective 标注 |
| R-HR-2 | 验证链过严导致吞吐低 | Step 4 | Hook 性能预算 < 50ms；benchmark 模式允许临时关 `alwaysAsk` |
| R-EV-3 | Evaluator 打分不稳定 | Step 2 / 12 | 固定 seed + 固定 prompt + 多次均值；F-17 / F-20 记录具体检验方法 |
| R-AR-2 | Auto-Research 迭代收益递减累积成本 | Step 5 | `stop_on_n_noop_rounds=3` 自动终止；每轮预算上限硬编码 |
| R-MM-1 | wiki query 延迟随节点增长恶化 | Step 1 | `tier` 定期下沉；必要时引入 `qmd` hybrid search（延到 M2） |
| 新发现 | 任何未登记风险 | 随时 | Step 6 retrospective 新增 R-* 编号并同步 RnD-Analysis §4 |

---

## 6. 与 M2 的衔接

M2 的启动前提在 Step 6 完成后即满足：
- `PhoenixCoreRuntime` 可切换模型（显式 `--model` / `--provider`），Step 1 完成时已奠基。
- `EvaluationRunner` + Long-horizon 已具备"同基准对比 Kimi vs Codex"的能力（Step 2 / 11）。
- Auto-Research 已有第一轮 Kept 变更作为 M2 优化起点（Step 5）。

M2 的主线是"把执行主力切成 Kimi + 接入 OpenAI Agents SDK 做三方对齐"，学习节点 `F-*` 从 F-23 接续。起笔时机：M1 Step 6 验收通过且 `M1-retrospective.md` ingest 到 wiki 之后。


---

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；锁定自研 Core、编程插件、Evaluation 与 Auto-Research 的 Step 计划。 |
