# Milestone 1 — 执行顺序计划（Step-based，工程 × 学习同步）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 上位文档：PRD.md §10、TRD.md §4 / §6 / §7 / §8、RnD-Analysis.md §6.2、SPEC.md §5 / §6 / §7 / §8、M0-plan.md
- 总目标：实现 `PhoenixCoreRuntime`（最小 ReAct + Plan + Compression + 验证链）+ 编程插件 + MemoryBackend 完整闭环 + Evaluation Runner 全量 + Auto-Research v1；在 SWE-bench Verified 子集上 Resolved Rate ≥ "Claude Agent SDK + Codex" 基准的 85%，长程任务完成率 ≥ 80%。

---

## 0. 启动前提

- M0-plan.md 的 Step 12 已验收通过，DoD-1~DoD-7 全部成立。
- `AgentRuntime` / `MemoryBackend` / `ToolSpec` + `PluginRegistry` 三个硬接口已在 SPEC v1.0 / v1.x 冻结；进入 M1 后若需变更，走"SPEC 先行"流程。
- 学习节点 `F-01 ~ F-06 + F-mem-1/2 + F-05a/b + F-model-1`（M0 产出）已 `wiki-ingest` 并可被 `wiki-query` 召回。

---

## 1. 完成定义（DoD，状态驱动）

- **DoD-M1-1**：`phoenix run --task "..." --runtime=self --model=codex-base` 在 M0 的 echo 任务上返回 `status="success"`；`--runtime=self --model=kimi-worker` 同样成功。
- **DoD-M1-2**：12 层 Harness 中 s01 / s02 / s03 / s04 / s06 / s07 / s12 在自研 Core 中可运行；每层可通过 `HarnessFlags` 开关（SPEC v1.0 §5.1）。
- **DoD-M1-3**：5 步验证链（`validateInput → PreToolUse Hook → checkPermissions → executeTool → mapToolResultToAPI`）在 `PhoenixCoreRuntime.run_task` 内硬编码强制执行。
- **DoD-M1-4**：编程插件 `coding.git_worktree` / `coding.multi_file_edit` / `coding.test_runner` / `coding.harness_validator` 四个工具上线。
- **DoD-M1-5**：`MemoryBackend` 七动词（ingest / query / digest / import_bulk / graph / lint / tier）在 `AKLLMWikiBackend` 全部可用。
- **DoD-M1-6**：`phoenix eval --benchmark=swe-bench-verified --subset=50 --runtime=self --model=codex-base` 输出 Resolved Rate ≥ 对应 `--runtime=claude` 基线的 85%。
- **DoD-M1-7**：长程任务（SWE-EVO / SlopCodeBench 任一 + PhoenixAgent 自定义 ≥ 5 个）上的完成率 ≥ 80%。
- **DoD-M1-8**：Auto-Research 完成 ≥ 3 轮有效迭代；至少 2 项 Kept 变更在 wiki 留档（含 `experiment-report.md`）。
- **DoD-M1-9**：学习节点 `F-07 ~ F-22`（见 §4 索引）全部 `wiki-ingest` 并可召回。
- **DoD-M1-10**：M1 retrospective + interface-backlog 写入 wiki；进入 M2 前三个硬接口再次冻结。

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

### Step 1 — PhoenixCoreRuntime 最小 ReAct（s01 + s02） 〔量级：L〕

**工程任务**
- 在 `src/phoenix/runtime/core.py` 用自研逻辑实现 `run_task`：`messages[]` + `tools[]` 裸数组循环，通过 `ctx.model_profile.client.chat(...)` 调 Anthropic/OpenAI 兼容接口；`stop_reason` / `tool_use` 分发基本对齐 Claude SDK 语义。
- `src/phoenix/harness/loop.py`、`src/phoenix/harness/dispatch.py` 作为子模块承担 s01、s02 的纯函数部分（便于未来单测）。
- 打 log 与 token 计量复用 M0 Step 10 的观察点。

**内嵌学习（产出 F-07）**
- 必读：
  - sanbuphy/learn-coding-agent 的 s01 / s02 章节。
  - Claude Agent SDK GitHub 的主循环入口源码（对照 `messages[]` 结构的处理方式）。
- 要回答（写进 `F-07-react-self-vs-sdk.md`）：
  - 自研 ReAct 与 Claude SDK 的差异点：谁负责消息拼装 / tool_use 路由 / stop_reason 判定？
  - 若想要支持 `tool_choice` / `parallel_tool_use`，本实现的扩展点在哪？
  - 为什么 `mapToolResultToAPI` 必须独立出来？（对照 Anthropic vs OpenAI 的字段差异）

**产物**
- `src/phoenix/runtime/core.py`、`src/phoenix/harness/loop.py`、`src/phoenix/harness/dispatch.py`
- `docs/teaching/M1/foundations/F-07-react-self-vs-sdk.md`

**进入下一步条件**
- `phoenix run --task "hello" --runtime=self --model=codex-base` 成功；`logs/` 里可见完整 ReAct 轨迹。
- F-07 入库。

---

### Step 2 — Plan Mode（s03） 〔量级：M〕

**工程任务**
- `src/phoenix/harness/planning.py`：输入 Task，输出结构化 `Plan`（SPEC v1.0 §1 的 dataclass）；内部机制采用"专职 planner prompt + JSON schema 强制"。
- `HarnessFlags.s03_planning=True` 时，`core.run_task` 先调 `plan()` 再进入执行循环；`False` 时跳过。
- `coding.harness_validator` 的前身：在 Plan 缺失时拒绝破坏性 Tool 调用（只作最小检查，正式实现见 Step 6）。

**内嵌学习（产出 F-08）**
- 必读：
  - sanbuphy s03 章节 + Karpathy 关于 "先规划后执行" 的讨论段落。
  - Anthropic "Building Effective Agents" 中 Workflow vs Agent 的对比（Planner 模式对应 Workflow 的一种固化）。
- 要回答：
  - 为什么 Plan Mode 在"平庸模型"上提升更显著？
  - JSON schema 强制的利与弊（成功率 vs 表达力），如何在 PhoenixAgent 里权衡？
  - Plan 被执行途中发现不可行时，重规划（replanning）的触发条件？

**产物**
- `src/phoenix/harness/planning.py`（含结构化 `plan()` 接口）
- `docs/teaching/M1/foundations/F-08-plan-mode.md`

**进入下一步条件**
- 在一个"多文件读+小修改"的样例任务上，开启/关闭 s03 的 A/B run 均跑通；记录两次 `tokens_*` 与最终结果差异到 `docs/teaching/M1/engineering/M-plan-ablation.md`。
- F-08 入库。

---

### Step 3 — Context Compression（s06） 〔量级：M〕

**工程任务**
- `src/phoenix/harness/compression.py`：三种策略（SPEC v1.0 §5.5）：
  - `auto_compact`：messages tokens 超阈值时调用廉价模型（Haiku / local）总结旧消息。
  - `snip_compact`：单条 `tool_result` > 8KB 时裁剪保留头/尾 + 摘要。
  - `collapse`：多条重复 `tool_result` 折叠为"执行 N 次 X，结果一致"。
- `HarnessFlags.s06_compression` 开关。

**内嵌学习（产出 F-09）**
- 必读：
  - Anthropic Prompt Caching docs（复用 M0 F-04 读过的段落，补读 "incremental caching" 部分）。
  - sanbuphy s06 章节。
- 要回答：
  - 三种策略的触发时机 / 副作用 / 对 cache_read 的影响（尤其 `auto_compact` 会破坏 cache 前缀）？
  - `collapse` 风险：丢失细粒度时序信息的场景有哪些？
  - 未来想引入 hybrid RAG 做"按需召回历史片段"，与本策略如何配合？

**产物**
- `src/phoenix/harness/compression.py`
- `docs/teaching/M1/foundations/F-09-compression-tradeoffs.md`

**进入下一步条件**
- 在刻意构造的长会话（>100k token）上，三种策略均能稳定生效；token 曲线记入 `M-compression-profile.md`。
- F-09 入库。

---

### Step 4 — 5 步验证链 + PreToolUse Hook + Permission Rules 〔量级：L〕

**工程任务**
- `core.run_task` 内的每次 Tool 调用强制走 `_enforce_validation_chain`（SPEC v1.0 §5.2）：
  - `validateInput`（JSON Schema + 危险值 / 路径黑名单）
  - `PreToolUse Hook`（JSONL stdin/stdout 进程，SPEC v1.0 §12）
  - `checkPermissions`（`PermissionRules` 三层，SPEC v1.0 §11）
  - `executeTool`（经 `PluginRegistry.execute`）
  - `mapToolResultToAPI`（provider 对齐）
- 配置：
  - `~/.config/phoenix/permissions.toml`（按 SPEC v1.0 §11 起草）。
  - `tools/hooks/deny-rm-rf.sh`、`tools/hooks/worktree-enforce.sh` 两个默认 Hook。

**内嵌学习（产出 F-10 + F-11）**
- F-10 "Don't Trust LLM Output 原则"：
  - 必读：humanlayer 博客（harness engineering 实践段）、Anthropic safety guidance。
  - 要回答：五步验证链每一步拒绝哪类问题？为什么不能合并成一步？
- F-11 "Hook 与 Permission 体系"：
  - 必读：Claude Code 官方 Hook 文档 + sanbuphy s05 章节。
  - 要回答：`alwaysAllow / alwaysDeny / alwaysAsk` 的优先级？Hook 超时 / 崩溃的默认决策？

**产物**
- `src/phoenix/harness/validation.py`（验证链中枢）
- `src/phoenix/harness/hooks.py`（Hook runner，JSONL 协议）
- `src/phoenix/harness/permissions.py`（PermissionRules 加载）
- `~/.config/phoenix/permissions.toml`
- `tools/hooks/deny-rm-rf.sh`、`tools/hooks/worktree-enforce.sh`
- `docs/teaching/M1/foundations/F-10-dont-trust-llm.md`
- `docs/teaching/M1/foundations/F-11-hooks-permissions.md`

**进入下一步条件**
- 构造两个"会被 Hook / Permission 拦住"的任务样例，拦截与放行结果可复现；记入 `M-validation-chain-demo.md`。
- F-10 / F-11 入库。

---

### Step 5 — Worktree 隔离（s12）+ git 工具 〔量级：M〕

**工程任务**
- `src/phoenix/harness/worktree.py`：进入/退出 git worktree 的上下文管理器；与验证链第 4 步"`requires_worktree=True`"校验对接。
- `src/phoenix/plugins/coding/git_worktree.py` 作为 ToolSpec 暴露 `coding.git_worktree` 工具（create / list / remove）。
- 失败回滚：worktree 创建失败 / 执行中异常时强制清理临时分支。

**内嵌学习（产出 F-12）**
- 必读：
  - Git 官方文档 `git-worktree(1)`。
  - sanbuphy s12 章节。
- 要回答：
  - worktree 与 branch / stash 的关系？何时更合适用 stash？
  - 并发多个 Agent 共享同一 repo 时，worktree 如何避免冲突？
  - 回滚场景：`git worktree remove --force` 的风险点。

**产物**
- `src/phoenix/harness/worktree.py`
- `src/phoenix/plugins/coding/git_worktree.py`
- `docs/teaching/M1/foundations/F-12-worktree-safety.md`

**进入下一步条件**
- 示例任务在 worktree 内完成修改 → 原 repo 无脏状态。
- F-12 入库。

---

### Step 6 — 编程插件三件套：multi-file-edit / test-runner / harness-validator 〔量级：L〕

**工程任务**
- `src/phoenix/plugins/coding/multi_file_edit.py`：统一 diff 输入（unified diff 或"路径→全文"两种形式），dry-run + atomic apply；失败回滚。
- `src/phoenix/plugins/coding/test_runner.py`：自动发现 pytest / jest / go test；结构化返回 `passed` / `failed` / `skipped` / `duration_s`。
- `src/phoenix/plugins/coding/harness_validator.py`：对即将执行的 tool_use 列表做 lint（反模式：无 plan 直接破坏性写、同一文件并发写、worktree 外的写操作等）。

**内嵌学习（产出 F-13）**
- 必读：
  - nexu-io/harness-engineering-guide 的工具实现样例。
  - walkinglabs/learn-harness-engineering 后半章节（工具级 harness）。
- 要回答：
  - atomic apply 的边界情况（部分文件成功 + 部分失败）如何处理？
  - test-runner 对测试框架的自动探测策略，命中 / 失败时的 fallback？
  - harness-validator 检测"反模式"时，是 Deny 还是 Modify 更合适？

**产物**
- 三个 plugin 文件 + 注册进 `PluginRegistry`。
- `docs/teaching/M1/foundations/F-13-coding-plugin-design.md`

**进入下一步条件**
- 一个多文件重构样例任务完整跑通（plan → multi-file-edit → test-runner 验证），全部通过验证链。
- F-13 入库。

---

### Step 7 — Persistence（s07）与断点恢复 〔量级：M〕

**工程任务**
- `src/phoenix/harness/persistence.py` + SPEC v1.0 §5.4 的 SQLite schema（`phoenix_tasks`）。
- `phoenix execute --plan-id <ulid>` 从最后未完成 `PlanStep` 恢复；`phoenix tasks list|show|cancel`。
- `events_jsonl_path` 按 session 分文件，与 SQLite 索引对齐。

**内嵌学习（产出 F-14）**
- 必读：
  - sanbuphy s07 章节。
  - SQLite 官方 docs "WAL mode" + "busy_timeout" 相关段落。
- 要回答：
  - 为什么选 SQLite 而不是纯 JSON 文件？多 Agent 并发场景的冲突面？
  - 状态机设计：`pending / running / blocked / completed / failed / cancelled` 之间的转换图？
  - 恢复点粒度：PlanStep 级 vs tool_call 级的取舍？

**产物**
- `src/phoenix/harness/persistence.py`
- SQLite schema init 脚本（自动首次运行时创建）
- `docs/teaching/M1/foundations/F-14-persistence-state-machine.md`

**进入下一步条件**
- 中断 + `phoenix execute --plan-id` 恢复成功；恢复后 tokens 不重复计费（实际命中 cache）。
- F-14 入库。

---

### Step 8 — Subagent（s04） 〔量级：M〕

**工程任务**
- `src/phoenix/harness/subagent.py`：`spawn_subagent(task, ctx)` 在独立 `messages[]` 上下文里跑子任务，结果回填主循环。
- 与 Memory Layer 对接：subagent 的 digest namespace 独立（SPEC v1.0 §6.4 INV-MM-2）。
- 配合 `PluginRegistry.execute`，支持 "工具调用触发 subagent" 的模式（例如 `coding.test_runner` 在大型任务中拆 subagent 验证）。

**内嵌学习（产出 F-15）**
- 必读：
  - sanbuphy s04 章节。
  - Claude Agent SDK subagent/AgentTool 相关源码位置（只求理解接口，不照搬）。
- 要回答：
  - 为什么 subagent 必须独立上下文而不是共享？
  - 子 Agent 出错时的错误传播策略（隐藏细节 vs 透传完整轨迹）？
  - Subagent 与 Plan Mode 的关系：何时"规划 + subagent"、何时"单主 agent"？

**产物**
- `src/phoenix/harness/subagent.py`
- `docs/teaching/M1/foundations/F-15-subagent-contexts.md`

**进入下一步条件**
- 一个"主 agent 规划、子 agent 执行 3 个独立子任务"的样例跑通；主 agent 上下文未被子任务噪声污染。
- F-15 入库。

---

### Step 9 — MemoryBackend 七动词补全 〔量级：M〕

**工程任务**
- `src/phoenix/memory/akllmwiki.py` 补齐 `import_bulk` / `graph` / `lint` / `tier`（SPEC v1.0 §6.1）。
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

### Step 10 — EvaluationRunner 全量 + Codex Evaluator 〔量级：L〕

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

### Step 11 — 长程任务接入（SWE-EVO / SlopCodeBench + 自定义） 〔量级：L〕

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

### Step 12 — Auto-Research Loop v1 实现 〔量级：L〕

**工程任务**
- `src/phoenix/research/loop.py`：严格按 SPEC v1.0 §8.2 的 7 步流程实现；Generator 调用 `PhoenixCoreRuntime`，Evaluator 走 Step 10 的 Runner。
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
- 在 Step 10 的 Runner 上，`phoenix research --rounds=2 --benchmark=swe-bench-verified --subset=20` 完整跑完；无论 Keep / Discard，每轮都有 `experiment-report.md` 写 wiki。
- F-19 / F-20 入库。

---

### Step 13 — Auto-Research ≥ 3 轮实测与分析 〔量级：M〕

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

### Step 14 — M1 retrospective + 接口冻结 checkpoint 〔量级：S〕

**工程任务**
- 汇总 milestone-level artifact：
  - `docs/teaching/M1/M-harness-walkthrough.ipynb`（串起 s01 / s02 / s03 / s06 / s12 的代码走读）。
  - `docs/teaching/M1/M-autoresearch-lab.md`（从 Step 12 到 Step 13 的完整实验记录）。
  - `docs/teaching/M1/M-longhorizon-eval.md`（Step 11 的指标解读）。
- 交叉审阅接口变更：`AgentRuntime` / `MemoryBackend` / `ToolSpec` 及本阶段新增的 `HarnessFlags` / `PermissionRules` / `EvaluationRunner` 是否稳定；必要时升 SPEC v1.x。
- `phoenix-doctor.sh --json > artifacts/doctor-m1-final.json`；`wiki-lint --auto-fix`。
- `docs/milestones/M1-retrospective.md`：KPI 达标情况、意外发现、每个 F-* 的自测结果。

**内嵌学习（产出 F-22）**
- 无新资料阅读；本节点是"本阶段学到了什么"的元反思。要求写一段"若现在让我重写 M1，我会改哪 3 件事"。

**产物**
- 3 份 milestone artifact 全部入 wiki（`.ingested.json` marker 更新）。
- `docs/milestones/M1-retrospective.md`
- `artifacts/doctor-m1-final.json`
- 可能的 SPEC v1.x → 同步 `wiki-ingest`
- `docs/teaching/M1/foundations/F-22-milestone-meta-reflection.md`

**进入下一步条件**
- DoD-M1-1 ~ DoD-M1-10 全部成立。
- 三个硬接口（含 M1 新增）在 M2 Step 1 启动前不再破坏性变更。

---

## 4. 学习节点索引

| 节点 | 产自 Step | 主题 |
|---|---|---|
| F-07 | 1 | 自研 ReAct vs Claude SDK 主循环对比 |
| F-08 | 2 | Plan Mode 原理与 JSON schema 权衡 |
| F-09 | 3 | Context Compression 三策略 trade-off |
| F-10 | 4 | Don't Trust LLM Output 原则 |
| F-11 | 4 | Hook 协议 + Permission 三层模型 |
| F-12 | 5 | git worktree 隔离与并发 |
| F-13 | 6 | 编程插件三件套设计 |
| F-14 | 7 | Persistence 状态机与 SQLite |
| F-15 | 8 | Subagent 独立上下文 |
| F-16 | 9 | Memory 七动词语义 |
| F-17 | 10 | Evaluator Prompt 与 Injection 防御 |
| F-18 | 11 | 长程任务指标设计 |
| F-19 | 12 | GAN-style Generator-Evaluator |
| F-20 | 12 | LLM 实验显著性检验 |
| F-21 | 13 | Auto-Research 运维 |
| F-22 | 14 | M1 元反思 |

---

## 5. 风险预警（M1 阶段新增 / 升级）

| 编号 | 风险 | 触发步骤 | 缓解 |
|---|---|---|---|
| R-RT-1 | 自研 Core 初期 Resolved Rate 不达 85% | Step 10 | 延长 Step 12 / 13 专项调教；必要时 Step 14 把 DoD-M1-6 调成 "≥ 基线的 75%" 并在 retrospective 标注 |
| R-HR-2 | 验证链过严导致吞吐低 | Step 4 | Hook 性能预算 < 50ms；benchmark 模式允许临时关 `alwaysAsk` |
| R-EV-3 | Evaluator 打分不稳定 | Step 10 / 12 | 固定 seed + 固定 prompt + 多次均值；F-17 / F-20 记录具体检验方法 |
| R-AR-2 | Auto-Research 迭代收益递减累积成本 | Step 13 | `stop_on_n_noop_rounds=3` 自动终止；每轮预算上限硬编码 |
| R-MM-1 | wiki query 延迟随节点增长恶化 | Step 9 | `tier` 定期下沉；必要时引入 `qmd` hybrid search（延到 M2） |
| 新发现 | 任何未登记风险 | 随时 | Step 14 retrospective 新增 R-* 编号并同步 RnD-Analysis §4 |

---

## 6. 与 M2 的衔接

M2 的启动前提在 Step 14 完成后即满足：
- `PhoenixCoreRuntime` 可切换模型（显式 `--model` / `--provider`），Step 1 完成时已奠基。
- `EvaluationRunner` + Long-horizon 已具备"同基准对比 Kimi vs Codex"的能力（Step 10 / 11）。
- Auto-Research 已有第一轮 Kept 变更作为 M2 优化起点（Step 13）。

M2 的主线是"把执行主力切成 Kimi + 接入 OpenAI Agents SDK 做三方对齐"，学习节点 `F-*` 从 F-23 接续。起笔时机：M1 Step 14 验收通过且 `M1-retrospective.md` ingest 到 wiki 之后。
