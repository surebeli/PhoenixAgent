---
id: F-03
slug: mcp-spec-digest
name: MCP 为什么是 PhoenixAgent 的第一公民接口
milestone: M0
step: 6
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§3.2", "§3.4", "§5.2", "§12", "§14"]
related_fr: ["FR-03", "FR-08"]
related_inv: ["INV-PL-1", "INV-PL-2"]
related_nodes: [F-02, F-05b]
replaces: null
ingested: true
ingested_at: 2026-04-23T11:25:38.3823442+08:00
readers: [llm, human]
---

# MCP 为什么是 PhoenixAgent 的第一公民接口

## 动机（Why）

到了 Step 6，PhoenixAgent 已经有了 Runtime 抽象和最小 Model Layer，接下来真正要解决的问题是：**工具能力到底怎样被系统性地接进来，而不是继续靠某一家 SDK 的私有扩展面零散挂接。** 如果这一步处理不好，后面的 git-worktree、test runner、browser、Playwright、memory adapter 都会沦为“对某个 runtime 生效、换一家就失灵”的局部胶水。

MCP 的意义正好在这里。Anthropic 对它的描述很直白：MCP 像 AI 应用的 USB-C。它不是某个 provider 独占的插件格式，而是一个把外部系统、工具与工作流接进模型宿主的开放协议。对 PhoenixAgent 来说，这件事的价值不在“可以多连几个 server”，而在于：**Plugin Layer 终于有了一个可迁移、可审计、可独立演进的标准边界。** 这也是为什么 `SPEC v1.2 §3.4` 明确把 MCP 适配写成 Plugin Layer 的一等职责，而不是“以后有空再做的可选扩展”。

## 核心内容

### 1. MCP `tools/call` 与 Anthropic `tool_use` 的真正对应关系

在 `F-02` 里，我们已经把 Anthropic / OpenAI 的 tool-use 协议压成了 Phoenix 关心的最小公共语义：Action、Observation、Finish。MCP 的 `tools/call` 正好落在同一层，但它不是 provider message，而是**宿主与工具服务器之间的协议调用**。

根据 MCP specification 2025-06-18，server 先通过 `tools/list` 向 client 暴露工具清单，每个工具都有 `name`、`description`、`inputSchema`，还可以带 `outputSchema`。真正调用时，host/client 发出：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "location": "New York"
    }
  }
}
```

返回则是 `result.content[]` 与可选 `structuredContent`，外加 `isError` 标记。把这层与 Anthropic `tool_use` 对照，会发现它们并不是竞争关系，而是上下游关系：

| Phoenix 视角 | Anthropic / Claude | MCP |
|---|---|---|
| Tool discovery | provider 不负责，宿主自己决定传哪些 tools | `tools/list` |
| Action request | assistant `tool_use{id,name,input}` | host/client 发 `tools/call{name,arguments}` |
| Observation | host 把 `tool_result{tool_use_id,content,is_error}` 回填给模型 | server 回 `content[]` / `structuredContent` / `isError` |
| Error split | provider 层 stop_reason + tool_result.is_error | JSON-RPC 协议错误 + `result.isError=true` |

所以，MCP `tools/call` 并不等于 Anthropic `tool_use` 本身。更准确地说，**Anthropic `tool_use` 是模型向宿主提出 Action 意图；MCP `tools/call` 是宿主把这个 Action 真正发给外部工具服务器的执行协议。** 它们之间应该由 Phoenix 的 Plugin Layer / Harness Layer 做桥接：

1. 模型先产生 `tool_use`
2. Runtime 把它翻译成统一 `ToolCall`
3. Plugin Layer 若该工具来自 MCP server，则发出 `tools/call`
4. 工具执行结果回到 Phoenix，映射成统一 `ToolResult`
5. Runtime 再把它包装成 provider 期望的 `tool_result`

这就是 Step 6 最重要的心智模型：**MCP 是 Phoenix 执行 Action 的标准外设协议，不是替代 Runtime 的消息协议。**

### 2. 为什么 Phoenix 必须把 MCP 当作第一公民，而不是“有的话就接一下”

MCP specification 把 server 能力明确分成三类：**Resources、Prompts、Tools**。Anthropic 的 MCP 概览也强调，MCP 可以连接数据源、工具和工作流，而不只是 function calling。对 PhoenixAgent，这个划分特别关键，因为它正好和后续八层架构咬合：

1. **Resources** 对应上下文面。以后 memory、repo state、benchmark metadata、worktree manifest 都可以被暴露成资源，而不必都伪装成工具。
2. **Prompts** 对应 workflow 面。后续 teaching、research 模板、审批模板、benchmark templates 都可能以 prompt asset 的形式被 server 提供。
3. **Tools** 才是 Action 面，对应 Plugin Layer 当前的 `ToolSpec.handler`。

如果 Phoenix 把 MCP 当成可选扩展，它就会继续陷在“本地 Python handler 和远端 stdio server 是两套体系”的老问题里；每接一个外部能力，都要重写一层私有 glue code。相反，把 MCP 视为第一公民有三层收益。

第一层是**可迁移性**。Claude Code、Claude Desktop、VS Code、Cursor、ChatGPT 等都在支持 MCP。Phoenix 如果自己也把 Plugin Layer 对齐到 MCP 语义，就不会把生态绑定到某一家 SDK 的私有 tools surface。

第二层是**治理一致性**。MCP specification 明确要求工具调用前做用户确认、输入验证、访问控制、超时和审计日志。它和 `SPEC v1.2 §5.2` 的五步验证链天然同向：Phoenix 不是为了“兼容 MCP”才做安全链，而是因为 MCP 这种任意数据访问 / 执行能力，本来就必须过安全链。

第三层是**能力边界更清楚**。如果以后把 git、browser、filesystem、database 都接成 MCP server，那么 Phoenix 顶层只要维护统一的 `ToolSpec`、PermissionRules 和日志格式，而不用在 Runtime 层知道每个工具背后到底是本地 Python 函数、stdio 子进程还是远端网关。

### 3. 若 `git-worktree` 迁成 MCP server，`ToolSpec.handler` 应该怎样改写

这正是 `SPEC v1.2 §3.4` 想表达的事：MCP tool 最终仍然应该收敛成 Phoenix 的 `ToolSpec`。变化的不是 `ToolSpec.name/description/input_schema/side_effect` 这些上层契约，而是 `handler` 的执行方式。

今天的本地 handler 大致长这样：

```python
def git_worktree_handler(args, ctx) -> ToolResult:
    branch = args["branch"]
    path = create_worktree(branch)
    return ToolResult(ok=True, data={"path": path})
```

若未来迁成 MCP server，Phoenix 不该让上层调用者直接学会 JSON-RPC，而应把 `handler` 改写成“Phoenix 内部 adapter”：

```python
def git_worktree_handler(args, ctx) -> ToolResult:
    mcp = ctx.plugins.get_mcp_session("coding")
    response = mcp.call_tool(
        name="git_worktree",
        arguments=args,
    )
    if response.is_error:
        return ToolResult(
            ok=False,
            data={"content": response.content},
            stderr="mcp tool execution failed",
        )
    return ToolResult(
        ok=True,
        data=_normalize_mcp_content(response),
        artifacts=_extract_artifacts(response),
    )
```

这里最重要的不是 JSON-RPC 细节，而是三条边界：

1. **上层仍只看 Phoenix `ToolSpec` / `ToolResult`**
2. **MCP server 细节被封在 handler adapter 里**
3. **Harness 仍在 handler 之前执行输入验证、权限判定、worktree 约束**

也就是说，MCP 化不是把 Plugin Layer 删掉，而是把 Plugin Layer 的执行后端标准化。

### 4. Step 6 当前最小实现如何对应这个方向

本步代码没有真正接 MCP server，而是先做了一个 `echo.say` dummy plugin 与最小 `PluginRegistry`。这一步的价值在于，Phoenix 现在已经有了：

- `PluginRegistry.register/list/tool_specs/execute`
- `ToolSpec` / `ToolCall` / `ToolResult`
- `phoenix run --task "请调用 echo.say hello" --runtime=claude`
- `ClaudeAgentSDKRuntime` 的本地 tool dispatch 路径

这看起来像是“先做本地插件”，其实是在给 MCP 做准备。因为从 Phoenix 顶层看，未来无论 `echo.say` 是本地 Python handler 还是 `mcp.echo.say`，都应该还是：

`ToolCall -> registry.execute(...) -> ToolResult`

这条调用链一旦稳定，MCP 就不再是“特殊插件类型”，而是 Plugin Layer 的一个标准后端。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §3.2`：Step 6 落下的 `PluginRegistry`、`ToolSpec`、`ToolResult` 是 Plugin Layer 的最小骨架。
- `SPEC v1.2 §3.4`：MCP server 最终要被映射成 `plugin="mcp.<server>"` 的 `ToolSpec`，而不是让 Runtime 直接耦合 JSON-RPC 细节。
- `SPEC v1.2 §5.2`：无论工具来自本地 handler 还是 MCP server，都必须先过输入校验、PreToolUse Hook、权限判定、worktree enforcement。
- `SPEC v1.2 §12`：Hook 协议是 Runtime 与 Plugin/MCP 的公共拦截面。
- `SPEC v1.2 §14`：`phoenix run` 是把这条统一工具调用链暴露给 CLI 的第一步。

## 失败模式（若适用）

最直接的失败模式是**把 MCP 视为 Runtime 的功能，而不是 Plugin Layer 的适配层**。那样一来，Claude Runtime 能用 MCP，OpenAI Runtime 又要另写一套，马上回到 provider-specific glue code。

第二种失败模式是**把 `tools/call` 直接暴露给上层业务代码**。这样每个工具调用方都要理解 JSON-RPC、`content[]`、`structuredContent`、`isError`，Phoenix 自己的 `ToolResult` 就失去存在价值了。

第三种失败模式是**只接 tools，不考虑 resources 和 prompts**。这会让 MCP 退化成“又一个 function calling 格式”，错过它真正提供的上下文与 workflow 能力，也解释不了为什么 `SPEC v1.2 §3.4` 要单列 MCP 适配。

第四种失败模式是**把 MCP server 当成可信边界**。MCP specification 明确提醒，tools 代表任意代码执行与任意数据访问，host 应该做用户确认、结果校验、超时和审计。Phoenix 不能因为某个能力是通过 MCP 接进来的，就跳过自己的 Harness 验证链。

## 延伸与争议

当前还没回答的一个问题是：Phoenix 未来到底应该直连 MCP stdio server，还是先统一挂 LiteLLM / 代理层后再接。Step 6 不急着定这个，因为现在最重要的是冻结 Phoenix 自己的 Tool surface，而不是过早绑定某种 transport 细节。

另一个值得保留的争议是，MCP prompts 与 Phoenix Teaching/Research 模板最终要不要收敛到同一种资产形态。MCP 已经把 prompts 视为 server 能力，而 Phoenix 又有 Teaching Layer 与 Auto-Research 的模板需求，这两者未来很可能会相遇。但在 M0，先把 Plugin Layer、CLI 和最小 tool path 走通，优先级高于 prompt asset 的统一设计。

## 参考

- PhoenixAgent `docs/SPEC.md`：`SPEC v1.2 §3.2` / `§3.4` / `§5.2` / `§12` / `§14`
- PhoenixAgent `docs/milestones/M0-plan.md` Step 6
- PhoenixAgent `src/phoenix/plugins/registry.py`
- PhoenixAgent `src/phoenix/plugins/echo.py`
- PhoenixAgent `src/phoenix/cli.py`
- PhoenixAgent `src/phoenix/runtime/claude.py`
- MCP specification 2025-06-18 — Tools: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP quickstart — user guide / Claude Desktop example: https://modelcontextprotocol.io/quickstart/user
- Anthropic MCP overview: https://docs.anthropic.com/en/docs/agents-and-tools/mcp
- Anthropic MCP announcement: https://www.anthropic.com/news/model-context-protocol
