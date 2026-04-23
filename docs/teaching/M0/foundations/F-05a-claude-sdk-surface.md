---
id: F-05a
slug: claude-sdk-surface
name: Claude Agent SDK 表面、主循环边界与 Permission Hook 入口
milestone: M0
step: 3
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§2.1", "§5.2", "§12", "§13.1"]
related_fr: ["FR-01", "FR-03", "FR-08"]
related_inv: []
related_nodes: [F-01, F-02]
replaces: null
ingested: true
ingested_at: 2026-04-23T01:15:43.3758159+08:00
readers: [llm, human]
---

# Claude Agent SDK 表面、主循环边界与 Permission Hook 入口

## 动机（Why）

M0 Step 1 留下了一个悬念：Claude Agent SDK 的主循环，如何对应 ReAct 的 Reasoning / Action / Observation 三段？这个问题不回答，后面就很难判断 PhoenixAgent 到底应该在哪一层“借 SDK”，又该在哪一层保留自己的 Runtime / Harness 边界。尤其是 Step 3 以后项目会同时面对 Claude、Codex、自研 Runtime，如果把 Claude SDK 的 transport 包装误认成“完整 runtime 抽象”，后面的多 runtime 设计就会天然偏向单一 provider。

因此 F-05a 的目标不是“读懂所有 SDK 细节”，而是先把三件事钉牢：**Python SDK 自己做了什么、真正的主循环大概在哪一层、Permission Hook 与 tool_use 分发从哪里穿过来。**

## 核心内容

### 1. `query()` 只是薄包装；主循环不在 Python 文件里

`claude_agent_sdk/query.py` 几乎是一个极薄的入口。`query(...)` 先接收 `prompt` 与 `ClaudeAgentOptions`，然后创建 `InternalClient()`，再把调用转发到 `client.process_query(...)`。继续往下看 `client.py` 与 `_internal/client.py`，可以发现 Python SDK 主要做的是：

- 构造 `ClaudeAgentOptions`
- 选择 transport
- 把 CLI 流式 JSON 消息解析成 typed message
- 在需要时把 hook / permission callback 结果再回送给 CLI

真正“模型思考 → 决定是否调用工具 → 等工具结果 → 继续下一轮”的 ReAct 主循环，并不写在 Python SDK 里，而是**运行在 Claude Code CLI 进程内部**。Python 这一层更准确的定位，是 transport + typed adapter + callback bridge。

### 2. Python SDK 与 Claude Code CLI 的边界在 `SubprocessCLITransport`

`_internal/transport/subprocess_cli.py` 是这一层的关键文件。它会：

1. 决定用哪个 `claude` 可执行；
2. 组装命令行参数；
3. 以子进程方式启动 Claude Code CLI；
4. 强制使用 `--output-format stream-json --verbose --input-format stream-json`；
5. 把 stdout 当作结构化事件流来读。

这段代码还暴露了一个很有实际意义的实现细节：SDK 默认先找**bundled CLI**，找不到才回退到 `shutil.which("claude")`。这也是为什么本次 Step 3 在排查时，先看到了 SDK init 事件里的 `claude_code_version=2.1.114`，而系统里直接 `claude --version` 却是 `2.1.117`。所以在 `scripts/smoketest-claude.py` 里显式传 `cli_path=shutil.which("claude")` 是合理的，至少能避免“脚本跑的是另一份 CLI”这种调试噪音。

### 3. `tool_use` / `tool_result` 的 typed surface 在 parser 层出现

`_internal/message_parser.py` 明确把 stream-json 中的 assistant content block 解析为 `TextBlock`、`ThinkingBlock`、`ToolUseBlock`、`ToolResultBlock`。这一步非常关键：它说明 Python SDK 看见的“主循环阶段”不是黑盒字符串，而是已经被拆好的结构化块。

因此 Step 1 的悬念现在可以初步闭合为：

- **Reasoning**：assistant 的 `text` / `thinking` block
- **Action**：assistant 的 `tool_use` block
- **Observation**：随后历史里出现的 `tool_result` block

也就是说，ReAct 三段在 Python SDK 的可观测面上是**存在对应物的**；只是“谁来驱动下一轮循环”不在 Python，而在 CLI 内部。

### 4. Permission Hook 与 tool dispatch 的入口在 callback bridge

`types.py` 给出了 Hook 输入的标准形态：`PreToolUseHookInput`、`PostToolUseHookInput`、`PostToolUseFailureHookInput`、`PermissionRequestHookInput` 等都明文包含 `tool_name`、`tool_input`、`tool_use_id` 之类字段。进一步看 `_internal/query.py`，当收到 `subtype == "can_use_tool"` 的控制请求时，SDK 会构造 `ToolPermissionContext`，然后调用 `self.can_use_tool(...)`；如果是 `subtype == "hook_callback"`，则会把 CLI 发来的 hook 请求转到 Python 侧 callback，再把结果编码回 CLI 期望的字段。

这回答了 Step 3 的第二个问题：**“主循环 → tool_use 分发 → Permission Hook”三者并不都在 Python 一层。**

- 主循环：主要在 Claude Code CLI 内部
- tool_use 分发：CLI 产生 `tool_use`，Python 侧 parser/transport 负责把它转成 typed message
- Permission Hook：CLI 在真正执行工具前，向 Python SDK 发 `can_use_tool` / `hook_callback` 控制请求，Python 再返回 allow / deny / ask / updatedInput

从 PhoenixAgent 的角度看，这很像“外部 runtime 提供 Action 候选，Harness 决定是否放行”。

### 5. Step 3 实测进一步证明：Python SDK 更像观测与桥接层

本次 smoke log `logs/m0-step3-20260423-010259-2f2d0554.jsonl` 很适合作为反证。Claude 端并没有真正完成 `hello phoenix`，因为 provider 月限额用尽；但即便如此，日志里仍然完整出现了：

- `system.init`
- 多次 `system.api_retry`
- `assistant`
- `result`
- `sdk.epilogue_error`

这说明 Python SDK 的职责重点确实是**把 CLI 里的运行过程流式暴露出来**，并在必要时承担 hook / permission callback 通道，而不是自己实现一个独立的模型循环。换句话说，Claude Agent SDK 提供的是“可编排的 Claude Code surface”，不是 PhoenixAgent 最终要持有的 Runtime 主权。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §2.1` 的 `AgentRuntime` 在 Phoenix 侧仍然应该是主抽象；Claude Agent SDK 更适合作为 `ClaudeRuntime` 的下层适配器，而不是顶层运行时接口本身。
- `SPEC v1.2 §5.2` 的 5 步验证链可以自然挂在 SDK 暴露出来的 Action 边界上：`tool_use` 一出现，就进入 input validation / PreToolUse Hook / permission / worktree enforcement。
- `SPEC v1.2 §12` 的 Hook 协议与 Claude SDK 的 callback surface 高度同构。也正因为如此，Phoenix 没必要复制 Claude 的字段名，而应抽成自己统一的 Hook event，再在 provider 适配层做映射。
- `SPEC v1.2 §13.1` 的 JSONL 日志要求和 Claude SDK 非常契合：SDK 天然就是事件流，适合作为 StructuredLogger 的上游数据源。

## 失败模式（若适用）

第一种失败模式是**误把 Python SDK 当成完整主循环所在层**。这样会在设计 Phoenix Runtime 时重复造 transport、消息 parser、hook callback，而忽略真正需要自持的是统一 Runtime 抽象与 Harness 策略。

第二种失败模式是**不显式固定 `cli_path`**。SDK 默认优先 bundled CLI，这意味着系统 `claude` 版本升级后，脚本仍可能偷偷跑旧的 bundled 版本，调试体验会很差。

第三种失败模式是**只看最终 assistant 文本，不看系统事件**。Step 3 的 429 案例已经证明，如果不记录 `system.api_retry` 与 `result`，就无法分辨“模型真的回答了 hello”还是“CLI 帮你包了一层错误文本”。

## 延伸与争议

F-05a 只回答“Claude Agent SDK 表面长什么样、主循环边界在哪里”，并没有回答“Phoenix 是否应该长期绑定 Claude Code CLI 作为唯一 runtime”。这件事在 M1 以后仍有争议。一个方向是：把 Claude SDK 只当成 `ClaudeRuntime` 的适配器，同时保留自研 `PhoenixCoreRuntime`；另一个方向是：把 Claude SDK 当成早期默认 runtime，加速把 Harness / Memory / Evaluation 挂上去。当前更稳妥的路线仍是前者，因为它更符合 `FR-01` 的运行时可切换目标。

另外，F-05a 也没有展开 file checkpointing、MCP message 分发、sub-agent lifecycle 等更深的 surface。这些都已经在类型里露出了头，但超出 M0 Step 3 的最小问题边界，留给 F-05b 或 Step 4 再补。

## 参考

- Claude Agent SDK overview（official）：https://code.claude.com/docs/en/agent-sdk/overview
- `C:/Python314/Lib/site-packages/claude_agent_sdk/query.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/client.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/_internal/client.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/_internal/transport/subprocess_cli.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/_internal/message_parser.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/_internal/query.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/types.py`
- `logs/m0-step3-20260423-010259-2f2d0554.jsonl`
