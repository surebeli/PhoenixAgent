# M0 Interface Backlog — Step 12 冻结复核

- 版本：v0.1（2026-04-23）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` §Step 12、`docs/SPEC.md`（当前基线 `SPEC v1.2`）、`docs/rules/spec-change-policy.md` §7
- 目的：记录 M0 Step 12 对 `AgentRuntime`、`MemoryBackend`、`ToolSpec + PluginRegistry` 的交叉复核结果，明确哪些问题已在本 Step 收口，哪些确认延后到 M1。

---

## 1. 复核范围与结论

- 复核对象：`AgentRuntime`、`MemoryBackend`、`ToolSpec + PluginRegistry` 三个硬接口，以及它们在 Step 3 ~ Step 9 中的实际调用面。
- 复核方法：对照 `SPEC v1.2` 当前文本、`src/phoenix/**` 的 M0 落地代码、以及 `docs/milestones/M1a-plan.md` / `docs/milestones/M1b-plan.md` 中已声明的后续交付边界。
- 结论：Step 3 ~ Step 9 的实际使用没有暴露“必须现在新增字段或改签名才能继续”的需求。M0 冻结前需要处理的是实现缺口，而不是接口字段扩张。
- 冻结判断：M0 结束时冻结的是三个接口的字段与职责边界；明确已经排入 M1a / M1b 的能力补齐，不在本 Step 提前拔高为 M0 必做项。

## 2. A 类事项：本 Step 内已同步收口

### A-1 `AgentRuntime` 结果持久化补齐

- 观察：Step 12 复核时发现 `ClaudeAgentSDKRuntime.run_task()` 已产出 `TaskResult` 与 JSONL 日志，但未落盘到 `SPEC v1.2 §2.5 INV-RT-2` 要求的 SQLite `phoenix_tasks` 表。
- 决策：A，本 Step 内直接补实现，不改接口签名。
- 处理：`src/phoenix/runtime/claude.py` 已在 `TaskResult` 完成收口后写入 `artifacts/phoenix_tasks.sqlite3`，表名为 `phoenix_tasks`，并记录 `task_id / prompt / workspace / status / plan_json / events_jsonl_path / tokens / timestamps`。
- 验证：本地 `echo.say` 任务已成功写入一条 `status="success"` 记录，说明 M0 当前运行时已经满足持久化不变量。
- 影响：无 `AgentRuntime` 字段变化，无 `TaskResult` 结构变化；M0 freeze 仍保持原签名。

## 3. B 类事项：确认延后到 M1

### B-1 `MemoryBackend.tier()`

- 观察：M0 实际闭环只依赖 `ingest / query / digest`；`tier()` 目前仍是 stub。
- 原因：M0 Step 7 明确只要求三动词最小可用版本；`tier` 在 `docs/milestones/M1a-plan.md` 的 `DoD-M1-5a` 才进入必做范围。
- 决策：B，延后到 M1a；M0 不为此改签名。

### B-2 `MemoryBackend.import_bulk() / graph() / lint()`

- 观察：`AKLLMWikiBackend` 这三项仍是 stub；Step 11 的 memory graph 已采用 frontmatter fallback 生成报告。
- 环境事实：当前机器上的 `wiki` CLI 只有 `wiki` 主命令，未暴露 `wiki-lint`；因此 Step 12 不能把 CLI 级 `lint` 当作现成能力调用。
- 原因：`docs/milestones/M0-plan.md` Step 7 已把这三项定义为 stub；`docs/milestones/M1b-plan.md` `DoD-M1-5b` 明确要求在 M1b 全量补齐。
- 决策：B，延后到 M1b；M0 仅冻结七动词职责边界，不提前承诺 M1b 的实现成熟度。

### B-3 `PluginRegistry.reload()`

- 观察：`PluginRegistry.reload()` 当前直接抛 `NotImplementedError`，M0 没有任何调用点依赖热重载。
- 原因：M0 的插件面只需要“注册 / 列表 / 执行 / namespace 激活”最小闭环；热重载更接近 M1a harness / plugin lifecycle 扩展的工作面。
- 决策：B，延后到 M1a soft-freeze 窗口内实现；M0 不扩字段、不改方法名。

### B-4 运行时占位实现的可选中状态

- 观察：CLI 已允许 `--runtime=self` 与 `--runtime=openai`，但 `src/phoenix/runtime/core.py` 与 `src/phoenix/runtime/openai.py` 仍是占位实现。
- 原因：这不是 `AgentRuntime` 协议字段缺失，而是后续 Runtime provider 尚未到交付 Milestone；`self` 在 M1a 落地，`openai` 在更后阶段落地。
- 决策：B，保留现有协议与 provider 名称，后续在对应 Milestone 完成真实实现或更明确的 capability gate。

## 4. 冻结结论

- M0 Step 12 不需要为三大硬接口做破坏性变更。
- 本 Step 需要立即处理的唯一实际偏差，是 `AgentRuntime` 的结果持久化缺口；该项已通过实现补齐解决。
- 其余待办均属于“实现补齐”而非“签名扩张”，因此统一纳入 M1 backlog，不在 M0 freeze 前改 `SPEC v1.2` 的接口字段。
- M1 Step 1 启动前，应先重读本文件，并把 B-1 ~ B-4 映射到当期 Step 的实际工程入口，避免 soft-freeze 窗口内重复讨论同一问题。

## 5. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | 初版创建：记录 Step 12 对三大硬接口的 A/B 决策，并确认 M1 backlog 归宿。 |