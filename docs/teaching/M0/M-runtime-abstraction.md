---
id: M-runtime-abstraction
slug: runtime-abstraction
name: M0 Runtime Abstraction 串讲
milestone: M0
type: milestone
tier: active
spec_version: v1.2
covers_foundations: [F-02, F-03, F-05a, F-05b]
ingested: true
ingested_at: 2026-04-23T15:29:21.8831443+08:00
---

# M0 Runtime Abstraction 串讲

## 1. 本 Milestone 的学习主线

M0 在 Runtime 这一条线上做的事情，本质上是在回答一个简单但后续代价很高的问题：PhoenixAgent 是要“直接绑定 Claude SDK 的工作方式”，还是要“先抽象出一个自己可控的运行时接口，再让 Claude / OpenAI / 自研 Core 都挂到这个接口下面”。`F-02`、`F-05a`、`F-05b` 和 `F-03` 共同构成了这条主线。它们从协议层、SDK 表面、抽象边界和 MCP 兼容性四个角度，把 Step 3 到 Step 5 里的零散实现串成了同一个判断：M0 必须先冻结最小 Runtime contract，而不是把供应商 SDK 当作长期内核。

## 2. 路线串讲

`F-02-tool-use-protocol` 解决的是最底层的消息语义问题。它让我们先把 Anthropic 与 OpenAI 两侧的 tool use / tool result 协议对齐，知道“调用工具”在消息结构里到底是什么，而不是只在某个 SDK 里盲调方法。没有这一步，后面一切 Runtime 抽象都只是把供应商对象名换个壳。

`F-05a-claude-sdk-surface` 接着回答“Claude SDK 到底帮我们做了什么”。这里真正重要的不是 API 列表，而是确认 SDK 已经把一部分 ReAct 主循环、权限钩子和消息流隐藏进自己的运行时里。也正因为它做得多，Phoenix 才更需要在自己的边界处把 Session / Tool / Hook 重新命名清楚，否则后面想换 Runtime 时会发现上层逻辑早就和 Claude 的内部约定缠死了。

`F-05b-runtime-abstraction` 是这条线的转折点。它把“为什么要用自研 Protocol 包住三家 Runtime”说成了一个明确的架构判断，而不是偏好问题。到这里为止，M0 已经不是在比较 SDK 好不好用，而是在决定 Phoenix 的稳定依赖面应该是什么。`AgentRuntime`、`RuntimeConfig`、`SessionHandle` 这些名字之所以先于复杂能力落地，是因为它们定义了未来所有 runtime-specific 差异该落在哪一层。

`F-03-mcp-spec-digest` 则把视角再往外推了一层。Runtime 抽象不是孤立的内部接口，它最终要和 ToolSpec、PluginRegistry、MCP server 这些外部能力边界协同工作。MCP 的价值并不只是“多接一个工具协议”，而是提醒 Phoenix：工具发现、参数 schema、命名空间与运行时主循环是两条边界，不能在实现里混成一个对象树。M0 先把这些边界用最小骨架拆开，后面才能在 M1 里安全地往里面填功能。

## 3. 关键权衡

第一项权衡是：先保留 Claude SDK 的成熟主循环，还是立即自研 ReAct Core。M0 选的是前者，但不是简单依赖，而是通过 `AgentRuntime` Protocol 先把“调用方看到什么”冻结住。这比直接自研更保守，也比直接深绑 SDK 更可迁移。

第二项权衡是：Runtime 抽象应该贴着厂商 SDK 命名，还是贴着 Phoenix 自己的领域对象命名。M0 选后者，所以我们用 `Task`、`TaskResult`、`SessionHandle`、`RuntimeConfig` 这些中性名词，而不是把 Anthropic / OpenAI 的消息对象一路往上传。代价是初期要多做一层映射，但收益是后面切换 provider 时不会牵动所有上层调用点。

第三项权衡是：MCP 工具边界是否在 M0 就完全产品化。M0 没这么做，而是只在 `ToolSpec` + `PluginRegistry` 上先留出协议型接口，同时用 `F-03` 把 MCP 的概念依赖补齐。这让仓库在治理期保持窄实现，又不至于把未来的接入路径堵死。

## 4. 教训

最大的教训是，所谓“抽象”不能只在文档里存在。M0 前几步如果只写 `F-05b` 而不把 `src/phoenix/runtime/base.py` 和 `make_runtime()` 落出来，团队很快就会回到“先把功能跑通再说”的路径依赖，最后每个 runtime 都偷偷暴露自己的内部对象。

另一个教训是，Runtime 抽象的边界必须在工具协议之前就清楚，否则 `tool_use` 的消息结构、PluginRegistry 的执行语义和 Session 的生命周期会互相污染。表面上看像是三个模块，实际上如果边界错位，后面每加一个 provider 都会产生新的偶合点。

最后一个教训是，M0 不需要把每个未来能力都实现出来，但必须知道它们将来会从哪里长出来。`F-03` 与 `F-05b` 的价值，正是提前把这些增长方向固定到了正确的层，而不是等 M1 再靠重构救火。

## 5. 延伸阅读索引

- 本项目基础节点：`wiki-query "runtime abstraction" --namespace phoenix-docs`
- [docs/teaching/M0/foundations/F-02-tool-use-protocol.md](docs/teaching/M0/foundations/F-02-tool-use-protocol.md)
- [docs/teaching/M0/foundations/F-03-mcp-spec-digest.md](docs/teaching/M0/foundations/F-03-mcp-spec-digest.md)
- [docs/teaching/M0/foundations/F-05a-claude-sdk-surface.md](docs/teaching/M0/foundations/F-05a-claude-sdk-surface.md)
- [docs/teaching/M0/foundations/F-05b-runtime-abstraction.md](docs/teaching/M0/foundations/F-05b-runtime-abstraction.md)