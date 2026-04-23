---
id: F-02
slug: tool-use-protocol
name: Anthropic 与 OpenAI 的 tool-use 协议映射
milestone: M0
step: 3
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§2.1", "§5.2", "§12", "§13.1", "§14"]
related_fr: ["FR-01", "FR-03", "FR-08"]
related_inv: []
related_nodes: [F-01]
replaces: null
ingested: true
ingested_at: 2026-04-23T01:15:43.3758159+08:00
readers: [llm, human]
---

# Anthropic 与 OpenAI 的 tool-use 协议映射

## 动机（Why）

PhoenixAgent 后续要同时挂 Claude Runtime、自研 Runtime 与 Codex/OpenAI Runtime。只要 Runtime 可以切换，就必须先把“工具调用协议的最小公共语义”讲清楚：**Action 在哪一条消息里出现，Observation 以什么字段写回，权限钩子应该截在什么地方，日志又该如何统一抽象。** 如果这一步没做，Step 5 以后就很容易把“某家 SDK 的消息格式”误当成 Phoenix 自己的抽象层，导致运行时切换时出现记忆污染和日志口径不一致。

M0 Step 3 的价值就在这里：哪怕 demo 只跑一个 `hello phoenix`，也要把 Anthropic / Claude Agent SDK 与 OpenAI function calling 的**字段边界**先摸清，再回答 Step 1 留下的问题——ReAct 的 Reasoning / Action / Observation 三段，到底分别落在协议哪一层。

## 核心内容

### 1. Anthropic 侧：`tool_use` / `tool_result` 是 content block，不是独立 role

从本机 `claude_agent_sdk` 的 `message_parser.py` 可以直接看到，Claude SDK 把 assistant / user 消息都解析成 content block 列表，其中 block 类型可以是 `text`、`thinking`、`tool_use`、`tool_result`。`tool_use` block 带 `id`、`name`、`input`；`tool_result` block 带 `tool_use_id`、`content`、`is_error`。也就是说，在 Anthropic 语义里，工具调用并不是“assistant 说完后，再冒出一个新的 role=tool 消息对象”，而是**消息内部的结构化片段**。

这对 ReAct 的映射非常直接：

- `text` / `thinking`：对应 Reasoning（显式或半显式推理表面）
- `tool_use`：对应 Action
- `tool_result`：对应 Observation

这里最容易误读的一点是：Anthropic 并不要求“Observation 一定长成独立角色消息”。在 SDK 的 typed surface 里，`UserMessage` 和 `AssistantMessage` 都可以携带 `tool_result` block，外层再靠 `parent_tool_use_id` / `tool_use_result` 把工具返回关联到前一个动作。这就是为什么 PhoenixAgent 的统一 Runtime 抽象不能死绑定到某一种“消息 role”。

### 2. OpenAI 侧：assistant 产出 `tool_calls`，调用方再补一条 `role="tool"`

OpenAI `openai==2.30.0` 的类型定义则更像两段式协议。`chat_completion.py` 明确写着：当模型调用工具时，`Choice.finish_reason` 可以是 `tool_calls`；`chat_completion_assistant_message_param.py` 又说明 assistant 消息可以有 `tool_calls`，而 `content` 在这种情况下可以为空。等调用方真正执行工具之后，再补一条 `ChatCompletionToolMessageParam`，其字段是：

- `role: "tool"`
- `tool_call_id`
- `content`

这回答了 Step 3 要求中的第一个问题：**OpenAI 侧有显式的 `role="tool"` 消息类型；Anthropic 侧没有等价的独立 role，而是把 `tool_result` 放在消息 content block 里。**

换句话说，OpenAI 把 Observation 建模成一条新消息；Anthropic 更像把 Observation 建模成“对上一个 tool_use 的结构化回填”。

### 3. 两边字段如何一一对齐

可以把两套协议压成下面这张对照表：

| ReAct 段 | Anthropic / Claude SDK | OpenAI / Chat Completions |
|---|---|---|
| Reasoning | `text` / `thinking` content block | `assistant.content`（若无工具） |
| Action | `tool_use{id,name,input}` | `assistant.tool_calls[].{id,function.name,function.arguments}` |
| Observation | `tool_result{tool_use_id,content,is_error}` | `role="tool"` + `tool_call_id` + `content` |
| 停止信号 | `stop_reason` | `finish_reason` |

真正可复用的抽象不是“有没有 role=tool”，而是：

1. 是否能拿到一个稳定的 **tool call id**
2. 是否能把 **tool output** 明确回绑到那个 id
3. 是否能在 Action 之前插 permission / validation
4. 是否能在 Observation 之后继续下一轮循环

PhoenixAgent 将来真正统一的，应当是这四个不变量，而不是某一家 SDK 的字段名字。

### 4. Step 3 实测告诉我们的另一件事：停止原因必须与错误面一起解释

本次 Step 3 的真实日志 `logs/m0-step3-20260423-010259-2f2d0554.jsonl` 恰好给了一个反例。Claude 侧因为 provider 月限额被打满，连续出现 `system.api_retry`，最终 assistant 落出的文本是 synthetic error，`ResultMessage.stop_reason` 却仍然是 `stop_sequence`。而 OpenAI / Codex 侧则自然结束，`finish_reason="stop"`，没有 `tool_calls`。

这说明协议映射除了“字段怎么长”，还必须回答“**什么时候一个 stop 算成功，什么时候只是 transport 正常结束但任务本身失败**”。因此 PhoenixAgent 的日志层必须把 stop / finish、tool trace、error text 和 retry 历史一起保留下来，不能只保留最后一条 assistant 文本。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §2.1` 的 `AgentRuntime` 不能暴露 Anthropic/OpenAI 私有字段，而应把两者统一抽象成“reasoning payload / tool request / tool observation / finish reason”四元组。
- `SPEC v1.2 §5.2` 的 5 步验证链必须挂在 **Action 出口** 上，而不是挂在 provider 的原始消息结构上。无论 Anthropic 用 `tool_use` block，还是 OpenAI 用 `tool_calls`，Phoenix 都应该先做输入校验、PreToolUse Hook、权限判定，再允许真正执行工具。
- `SPEC v1.2 §12` 的 Hook 协议恰好是这种跨 provider 抽象层：Hook 不关心你来自 Anthropic 还是 OpenAI，只关心“这是 PreToolUse 还是 PostToolUse”。
- `SPEC v1.2 §13.1` 的 JSONL 事件是观测底座。只有把 `tool_use` / `tool_result` / `role="tool"` 的差异压成统一事件，后面的成本分析和回放才成立。
- `SPEC v1.2 §14` 又要求未来 CLI 能把这套统一抽象暴露成 `phoenix run` / `phoenix memory` / `phoenix eval` 等命令，而不是让调用方直接依赖 provider SDK。

## 失败模式（若适用）

最常见的失败模式有四个。

第一，**把 Anthropic 的 `tool_result` 当成 OpenAI 式独立消息**。这样会在适配层里无端造一个“tool role”，导致历史结构和原 provider 不一致，排查问题时很难一一映射。

第二，**把 OpenAI 的 `function_call` 当成主路径**。在 `openai==2.30.0` 里它已经是 deprecated 字段，真正应优先处理的是 `tool_calls`；继续围绕 `function_call` 写适配，只会把未来 surface 越绑越旧。

第三，**只看 `stop_reason` / `finish_reason`，不看 payload**。本次 Claude 429 案例已经证明，transport 可以“正常结束”，但业务任务并没有成功完成。

第四，**不校验 arguments JSON 就直接执行工具**。OpenAI 类型注释已经明确提醒：模型生成的 arguments 不一定是合法 JSON，也可能 hallucinate 未定义参数。这个风险在 Anthropic / OpenAI 两边都存在，只是字段名字不同而已。

## 延伸与争议

本节点暂不把“thinking”与 OpenAI 的 reasoning token surface 强行画等号。Anthropic 的 `thinking` content block、Claude extended thinking 开关，以及 OpenAI 的 `reasoning_effort` / reasoning traces，并不是一一同构的对象；它们更像“Reasoning 可见度与预算控制”的不同实现。PhoenixAgent 在 Runtime 抽象上更稳妥的做法，是先统一 **Action / Observation / Finish** 三件事，再决定是否把 provider 私有 reasoning surface 暴露成调试能力。

另一个争议点是 parallel tool calls。OpenAI 已把 `parallel_tool_calls` 暴露到请求层；Anthropic / Claude Code 也可能在单条 assistant 消息里给出多个 tool_use。M0 先把**单步单回合**协议吃透，不在此节点里承诺并发调度策略；并行分发应留到 M1 Harness 实装阶段再落。

## 参考

- Anthropic Messages API（official）：https://docs.anthropic.com/en/api/messages
- Anthropic tool use overview（official）：https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- Anthropic extended thinking（official）：https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- Claude Agent SDK overview（official）：https://code.claude.com/docs/en/agent-sdk/overview
- `C:/Python314/Lib/site-packages/claude_agent_sdk/_internal/message_parser.py`
- `C:/Python314/Lib/site-packages/claude_agent_sdk/types.py`
- `C:/Python314/Lib/site-packages/openai/types/chat/chat_completion.py`
- `C:/Python314/Lib/site-packages/openai/types/chat/chat_completion_assistant_message_param.py`
- `C:/Python314/Lib/site-packages/openai/types/chat/chat_completion_tool_message_param.py`
- `logs/m0-step3-20260423-010259-2f2d0554.jsonl`
