---
id: F-05b
slug: runtime-abstraction
name: 为什么 PhoenixAgent 要自研 Runtime Protocol 而不是继承单家 SDK
milestone: M0
step: 4
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§2.1", "§2.3", "§12", "§13.1"]
related_fr: ["FR-01", "FR-03", "FR-08"]
related_inv: ["INV-RT-1"]
related_nodes: [F-02, F-05a]
replaces: null
ingested: true
ingested_at: 2026-04-23T01:40:08.1939869+08:00
readers: [llm, human]
---

# 为什么 PhoenixAgent 要自研 Runtime Protocol 而不是继承单家 SDK

## 动机（Why）

Step 3 已经回答了一个局部问题：Claude Agent SDK 的可观测表面，怎样对应 ReAct 的 Reasoning / Action / Observation 三段。但到了 Step 4，问题变了：**PhoenixAgent 到底该把哪一层视为“自己的 Runtime 抽象”，又该把哪一层视为第三方实现细节？** 这不是架构洁癖，而是后续 M1/M2 是否还能切换 Runtime、比较成本、统一 Harness、复用 Teaching 的分水岭。

如果直接继承某一家 SDK，早期确实省事，但会立刻遇到三类锁定。第一，Session 语义会被 provider 绑定：Claude 把会话放在 CLI / SDK 流里，OpenAI Agents SDK 有显式 `Session` Protocol 与 compaction-aware session，Google ADK 则把 `Session`、`State`、`Memory` 与 `SessionService` 绑定。第二，Tool 语义会被不同运行时的“执行边界”绑住：Claude 偏“agent-as-computer”，OpenAI 偏多 agent / handoff / hosted tools / sandbox，ADK 偏 workflow + function tools。第三，Hook / Guardrail 的挂载点并不一致：Claude 是 `PreToolUse` / `PostToolUse` 等回调，OpenAI 是 guardrails + tracing + HITL，ADK 是 callbacks around agent/model/tool。

所以 Step 4 的关键判断不是“哪家 SDK 更强”，而是：**PhoenixAgent 必须先定义自己的 `AgentRuntime` Protocol，再让三家 SDK 去适配它，而不能让 Phoenix 的顶层接口长成任意一家 SDK 的原生形状。**

## 核心内容

### 1. 三家 SDK 的 Session / Tool / Hook 抽象分别长什么样

先看 OpenAI Agents SDK。官方 `openai/openai-agents-python` README 直接把核心概念列成：**Agents、Tools、Guardrails、Sessions、Tracing**。源码里 `src/agents/memory/session.py` 又把 `Session` 写成一个明确的 `Protocol`，要求实现 `get_items / add_items / pop_item / clear_session`，并以 `session_id` 持有当前会话。也就是说，OpenAI 把 Session 视为**一级抽象**，不是顺手塞在 runner 里的附属状态。Tool 侧，`src/agents/tool.py` 的 `FunctionTool` dataclass 清楚给出了 `name / description / params_json_schema / on_invoke_tool`，还内置 `tool_input_guardrails`、`tool_output_guardrails` 与 `needs_approval`。Hook 侧，OpenAI 并不主推一个叫“Hook”的统一术语，而是把安全与拦截能力更多落在 **Guardrails**、approval、tracing 和 human-in-the-loop 上。

再看 Claude Agent SDK。`claude_agent_sdk.types.ClaudeAgentOptions` 里直接出现 `session_id`、`allowed_tools`、`permission_mode`、`can_use_tool`、`hooks`、`agents` 等字段，说明它把 Session、Tool 权限和 Hook 都压在一个“驱动 Claude Code CLI”的配置面上。更具体地，`types.py` 里的 `PreToolUseHookInput`、`PostToolUseHookInput`、`PostToolUseFailureHookInput`、`PermissionRequestHookInput` 把 Hook 的挂点定义得非常细：工具名前、工具后、失败后、权限请求时，都有不同输入结构。它的 Tool 抽象也更“运行时化”——`allowed_tools` / `disallowed_tools` / `can_use_tool` 决定的不是 schema-only function tool，而是 Claude Code 能不能真正访问 Bash、Read/Write/Edit、MCP server、subagent 等具备副作用的能力。

Google ADK 则是第三种形状。官方文档把上下文管理拆成 `Session`、`State`、`Memory` 三层，并由 `SessionService` / `MemoryService` 管理；`Session` 保存当前会话线程中的 `Events` 与临时 `State`。Tool 侧，ADK 官方文档把工具定义成“具备结构化输入输出的函数/方法/agent”，示例里直接使用 `from google.adk.tools import FunctionTool`。Hook 侧，ADK 不叫 hook，而叫 **Callbacks**：官方 callbacks 文档给出了 `Before Agent / After Agent / Before Model / After Model / Before Tool / After Tool` 等回调点，且强调这些 callback 可以 observe、customize、control agent behavior。

把三家并排看，会得到一个很重要的结论：**它们都有 Session / Tool / Hook 的对应物，但抽象层级并不一致。**

| 维度 | Claude Agent SDK | OpenAI Agents SDK | Google ADK |
|---|---|---|---|
| Session | `ClaudeAgentOptions.session_id` + CLI 会话流 | `Session` Protocol + session memory module | `Session` / `State` / `SessionService` |
| Tool | `allowed_tools` / `can_use_tool` / CLI tools / MCP | `FunctionTool` + hosted tools + MCP + handoffs | `FunctionTool` / built-in tools / agents-as-tools |
| Hook / Guardrail | `hooks` + `PreToolUse` / `PostToolUse` / permission callbacks | `Guardrails` / approval / tracing / HITL | `Callbacks`（Before/After Agent/Model/Tool） |

### 2. 为什么 Phoenix 必须先定义自研 Protocol

这正是 `SPEC v1.2 §2.1` 选择 `AgentRuntime` Protocol 的原因。Phoenix 顶层需要的是六个稳定动作：`start_session`、`run_task`、`register_tool`、`install_hook`、`stream_events`、`stop_session`。这六个动作不是任意一家 SDK 的原生 public API 原样照搬，而是 Phoenix 在三家异构实现之上抽出来的**最小共同母集**。

这么做的第一层原因是**切换权**。只要顶层代码面向 `AgentRuntime`，M0 可以先落 `ClaudeAgentSDKRuntime`，M1 再补 `PhoenixCoreRuntime`，M1/M2 再接 `OpenAIAgentsRuntime`，而不必把上游调用者一起重写。`SPEC v1.2 §2.3` 的 `RUNTIME_REGISTRY` + `make_runtime()` 正是这种切换权的机械落点。

第二层原因是**Harness 挂载权**。`INV-RT-1` 要求每一次 Tool 调用都必须经过验证链。若直接继承第三方 SDK，Phoenix 很容易退化成“在 SDK 外面包一层薄壳”，真正的 Action 边界却藏在 provider 内部。那样一来，验证链、PermissionRules、Hook 协议和日志就都会被 SDK 原生术语牵着走。自研 Protocol 的好处是：无论底层是 Claude 的 `PreToolUse`、OpenAI 的 `needs_approval`、还是 ADK 的 `Before Tool` callback，Phoenix 都先把它们映射成自己的 `install_hook` / `register_tool` / `stream_events` 语义，再去谈统一治理。

第三层原因是**Teaching 与 Evaluation 的可迁移性**。F-02、F-05a、F-05b 这些 teaching 节点并不是“某家 SDK 的教程”，而是 Phoenix 自己的架构知识。如果顶层接口直接继承 OpenAI Agent / Claude Session / ADK Runner 的命名，那么后面的教学节点、实验工件和成本对比会天然偏向一家 SDK，教学层就会失去“跨 Runtime 复用”的价值。

### 3. 最可能被 OpenAI Agents SDK 打破的假设是什么

最值得提前写下来的答案是：**“工具调用边界必然等于单个 provider 返回的一次 tool_use/tool_result 对”** 这个假设最容易在未来被打破。

在 Claude SDK 世界里，这个假设看起来最自然：assistant 发出 `tool_use`，外部回填 `tool_result`，Permission Hook 卡在工具前后。可一旦切到 OpenAI Agents SDK，情况立刻复杂起来。OpenAI 把多 agent handoff、session compaction、guardrails、approval、sandbox filesystem tools 放在同一框架里，Tool 可能不再只是“同步函数 + 一次返回”，而可能是：

1. 一个需要 approval 的 `FunctionTool`
2. 一个 hosted tool
3. 一个 sandbox agent 中的文件系统动作
4. 一个 agent-as-tool / handoff，背后又是另一轮 run

这会破坏 Phoenix 早期最容易偷懒的实现方式：把所有 Action 都想象成“拿到 tool call，执行函数，塞回结果”。真正稳妥的做法，是从现在开始就把 Runtime 抽象写成**能容纳不同 provider 对 Action 边界的切分方式**，而不是把 Claude 当前最顺手的形状误当成唯一真相。

换句话说，OpenAI Agents SDK 最有可能打破的，不是“有没有 Session”，也不是“有没有 Tool”，而是**谁拥有执行控制权、谁定义中断点、谁决定 Observation 何时回到主循环**。这也是为什么 Step 4 先冻结 `Protocol + Registry + Stub`，而不是急着在 `openai.py` 里承诺具体行为。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §2.1`：`AgentRuntime` Protocol 是三家 SDK 的统一上层接口，避免 provider 术语直接泄漏到 Phoenix 顶层。
- `SPEC v1.2 §2.3`：`RUNTIME_REGISTRY` + `make_runtime` 是 Runtime 可替换性的装配点；这一步已经在 Step 4 代码骨架里落下。
- `SPEC v1.2 §12`：Phoenix 的 Hook 协议需要接住 Claude hooks、OpenAI guardrails/HITL、ADK callbacks 这些不同来源的拦截面。
- `SPEC v1.2 §13.1`：不同 SDK 的 tracing / events / logs 最终都要收敛成 `logs/<session_id>.jsonl` 的统一 `AgentEvent` 流。
- `FR-01`：运行时抽象层的核心目的就是“统一 `AgentRuntime` 接口，封装 ReAct loop 与工具调度”；F-05b 解释了为什么“统一”必须先于“绑定单家 SDK”。

## 失败模式（若适用）

最直接的失败模式是**把 PhoenixRuntime 做成 ClaudeSDKRuntime 的别名**。这样短期虽然能跑，但 Step 5 以后切 OpenAI/Kimi 时，Session、Hook、Tool 三个抽象都会出现形状不兼容，迫使调用侧一起返工。

第二种失败模式是**把 Stub 写成空壳，却不冻结统一接口**。那会变成“文件都建了，但没有共同约束”，未来每家 runtime 还是各写各的，最后回到多套不兼容 surface。

第三种失败模式是**过早承诺 OpenAI/ADK 的具体行为细节**。Step 4 正确的粒度是先锁 Protocol 与 Factory；尚未真正接入的 Runtime 用 stub 明示边界，而不是写看似完整、实则未经验证的假实现。

## 延伸与争议

F-05b 并不主张“永远不要直接利用第三方 SDK 的高层能力”。相反，Claude SDK 的计算机访问面、OpenAI Agents SDK 的 sandbox / hosted tools、多 agent handoff，ADK 的 workflow agents 与 callbacks，未来都值得 Phoenix 适配。争议点不在“要不要用”，而在**Phoenix 顶层是否保留自己的语义主权**。当前项目的立场是：必须保留。

另一个未闭合问题是，`AgentRuntime` 是否最终还要拆成更细的 `SessionRuntime`、`ToolRuntime`、`TraceEmitter` 三层。M0 Step 4 先不拆，因为当前最重要的是锁住最小公共面；等 M1 自研 Runtime 真正接上 12 层 Harness 后，再看是否有必要二次分层。

## 参考

- PhoenixAgent `docs/SPEC.md` `SPEC v1.2 §2.1` / `§2.3` / `§12` / `§13.1` / `INV-RT-1`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/types.py`
- Claude Agent SDK overview（official）：https://code.claude.com/docs/en/agent-sdk/overview
- OpenAI Agents SDK README（official repo）：`https://github.com/openai/openai-agents-python`
- OpenAI Agents SDK `src/agents/memory/session.py`
- OpenAI Agents SDK `src/agents/tool.py`
- OpenAI Agents SDK `src/agents/guardrail.py`
- Google ADK docs（official）：https://google.github.io/adk-docs/
- Google ADK Agents / Sessions / Callbacks / Custom Tools：
  - https://google.github.io/adk-docs/agents/
  - https://google.github.io/adk-docs/sessions/
  - https://google.github.io/adk-docs/callbacks/
  - https://google.github.io/adk-docs/tools-custom/
- Composio 对比文：https://composio.dev/blog/claude-agents-sdk-vs-openai-agents-sdk-vs-google-adk/
