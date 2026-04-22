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
- `src/phoenix/harness/planning.py`：输入 Task，输出结构化 `Plan`（SPEC v1.1 §1 的 dataclass）；内部机制采用"专职 planner prompt + JSON schema 强制"。
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
- `src/phoenix/harness/compression.py`：三种策略（SPEC v1.1 §5.5）：
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
- `core.run_task` 内的每次 Tool 调用强制走 `_enforce_validation_chain`（SPEC v1.1 §5.2）：
  - `validateInput`（JSON Schema + 危险值 / 路径黑名单）
  - `PreToolUse Hook`（JSONL stdin/stdout 进程，SPEC v1.1 §12）
  - `checkPermissions`（`PermissionRules` 三层，SPEC v1.1 §11）
  - `executeTool`（经 `PluginRegistry.execute`）
  - `mapToolResultToAPI`（provider 对齐）
- 配置：
  - `~/.config/phoenix/permissions.toml`（按 SPEC v1.1 §11 起草）。
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
- `src/phoenix/harness/persistence.py` + SPEC v1.1 §5.4 的 SQLite schema（`phoenix_tasks`）。
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
- 与 Memory Layer 对接：subagent 的 digest namespace 独立（SPEC v1.1 §6.4 INV-MM-2）。
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

### Step 9 — M1a retrospective + 接口冻结 checkpoint 〔量级：S〕

**工程任务**
- 汇总 M1a milestone-level artifact
- 冻结 HarnessFlags / PermissionRules（部分）
- docs/milestones/M1a-retrospective.md

**进入下一步条件**
- DoD-M1a-1 ~ DoD-M1a-6 全部成立。
- 接口基线稳固，允许 M1b 启动。

---

## 4. 学习节点索引

按 M1 教学闭环“每能力块必有”规则，同属一类的节点在完结时可合并编写（如 `F-07` 和 `F-08` 可合并为一份“核心架构”产出）。

| 节点 | 产自 Step | 能力块主题 |
|---|---|---|
| F-07 | 1 | ReAct vs Claude SDK (核心架构) |
| F-08 | 2 | Plan Mode (核心架构) |
| F-09 | 3 | Context Compression (核心架构) |
| F-10 | 4 | Don't Trust LLM (验证与权限) |
| F-11 | 4 | Hook + Permission (验证与权限) |
| F-12 | 5 | git worktree (插件与工具) |
| F-13 | 6 | 编程插件三件套 (插件与工具) |
| F-14 | 7 | Persistence (记忆基础) |
| F-15 | 8 | Subagent (记忆基础) |

---

## 5. 风险预警

同 M1 计划，见 RnD-Analysis。

---

## 6. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-22 | 从 M1 拆分出 M1a（最小价值闭环）。 |
