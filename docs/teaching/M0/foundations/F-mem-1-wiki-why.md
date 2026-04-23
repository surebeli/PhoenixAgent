---
id: F-mem-1
slug: 1-wiki-why
name: 为什么 PhoenixAgent 先做 LLM Wiki 而不是纯向量 RAG
milestone: M0
step: 2
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§6.1", "§6.2", "§14"]
related_fr: ["FR-05", "FR-08"]
related_inv: ["INV-MM-2", "INV-MM-3"]
related_nodes: [F-01]
replaces: null
ingested: true
ingested_at: 2026-04-23T00:37:13.4263729+08:00
readers: [llm, human]
---

# 为什么 PhoenixAgent 先做 LLM Wiki 而不是纯向量 RAG

## 动机（Why）

PhoenixAgent 在 M0 阶段还没有大规模代码仓，而是一个**治理层先行**的项目：PRD / TRD / RnD / SPEC、规则、ADR、教学节点才是当前最重要的“工作记忆”。这类知识的价值不在“找到语义接近的一段话”，而在**保留稳定术语、引用链、决策上下文和跨文档约束**。因此，项目需要的不是“每次提问都重新检索一批 chunk”，而是把高价值知识先编译成可持续维护的中间层；这正是 Karpathy 所说的 LLM Wiki。

对 PhoenixAgent 来说，“一次编译、复利工程”有两个直接收益。第一，作者和 Agent 共享同一份人类可读的记忆层，后续任何会话都能从已经整理好的节点起步，而不是反复从原始文档中二次发现。第二，学习节点、运行日志、评测报告可以继续回灌到同一套 wiki 中，形成 Memory Layer 与 Teaching Layer 的闭环，符合 `FR-05` 与 `FR-08` 的同时达标。

## 核心内容

### 1. 为什么这里优先 LLM Wiki，而不是纯向量 RAG

纯向量 RAG 的强项是大规模、弱结构、跨语义召回；但 PhoenixAgent 当前最稀缺的不是“海量文档检索能力”，而是**把少量高约束文档编译成稳定语义面**。PRD、TRD、SPEC、规则与 ADR 之间存在大量显式 ID、版本号、章节引用和不变量。若只用 RAG，Agent 每次都要重新切块、重组、解释这些关系；一旦 chunk 边界切坏，或相邻约束落在不同片段里，就会把“闭环规则”退化成“命中几段相关文本”。

LLM Wiki 的优势在于它把“关系”前置固化：哪些页面互相引用、哪些结论已经被整理、哪些矛盾需要 lint 暴露，都不是在 query 时临时拼出来的，而是 ingest 之后就成为结构的一部分。对 PhoenixAgent 这种重视 Harness 纪律、文档版本和验收证据的项目，这比黑盒检索更可审计，也更接近 `MemoryBackend` 的设计目标：让 `query()` 回答的不是“相似文本”，而是“已经编译过的项目知识”。

### 2. 七个动词各自承担什么职责

`ingest` 是**单源编译**：把一篇文章、一份教学节点、一次实验结果变成可引用的 wiki 节点，并补齐链接与摘要。`query` 是**带引用的读取面**：从已编译节点里回答问题，并把高价值回答继续沉淀。`digest` 是**运行时回写**：把一次任务或一轮 episode 压缩成可复用的经验，而不是把经验留在聊天历史里。

`import` 是**冷启动迁移**：当项目已有成批 markdown 时，把它们一次性纳入统一 namespace，避免 Memory Layer 从零开始。`graph` 是**结构发现**：把“哪几个节点相互依赖、谁是桥、谁是孤点”显式化，帮助 Agent 做跨页面推理。`lint` 是**一致性与健康检查**：发现断链、陈旧结论、悬空术语和 schema 漂移，让 wiki 不至于越用越脏。`tier` 是**记忆老化与热面管理**：把 active / archived / frozen 分开，让 query 默认看热知识，但旧知识不会丢失。

这七个动词放在一起，才构成“复利工程”。只有 `query` 而没有 `digest`，记忆会变成只读索引；只有 `ingest` 而没有 `lint` / `tier`，知识会持续膨胀却不整理；只有 `import` 而没有 `graph`，冷启动资料只是堆在一起，不能形成结构。

### 3. Wiki 与未来混合方案的边界

这并不等于 PhoenixAgent 永远拒绝 RAG。MindStudio 的比较和 LLM Wiki v2 的扩展都指出：当节点数继续增长、查询开始偏向“模糊搜索实现位置”时，混合方案会更合理，例如 wiki 负责架构、约束、决策与教学节点，qmd / 向量检索负责大规模代码检索。关键点不在于“只准一种技术”，而在于**先把 MemoryBackend 的语义面定义成编译后的知识层**，再决定底层是否引入检索加速。

## 与 PhoenixAgent 的映射

- `PRD v1.0 FR-05` 明确要求 `MemoryBackend` 至少具备 `ingest / query / digest / import / graph` 五种能力，并以 AK-llm-wiki 作为默认实现；F-mem-1 解释了为什么这个默认值首先服务于“编译后的知识层”，而不是“运行时临时检索”。
- `SPEC v1.2 §6.1-§6.2` 把 AK-llm-wiki 适配定义为 subprocess CLI 边界，要求用 `wiki-ingest` / `wiki-query` / `wiki-import` 等命令承接 Memory Layer；这说明七动词不是口号，而是接口表面。
- `SPEC v1.2 §14` 又把这些能力抬升为 `phoenix memory ingest|query|digest|import|graph|lint|tier` 的 CLI 契约；换言之，未来 Phoenix CLI 只是把同一套记忆语义重新封装，并不会改变“先编译、再查询”的路线。
- `INV-MM-2` 与 `INV-MM-3` 说明 query 必须带 namespace，且任何层都不得绕过接口直接读写 wiki 文件。这正是 wiki 作为“中间知识层”的价值：它既可读，又必须通过显式入口维护，避免无约束地读原始文件。

## 失败模式（若适用）

如果把 PhoenixAgent 的记忆层直接做成纯向量 RAG，最容易出现的失败模式是：同一条问题每次得到不同拼接结果，引用链断裂，版本上下文丢失，Agent 很难解释“为什么这次命中了这几段”。这对于需要审阅 SPEC、ADR、规则和教学节点的一体化工程非常危险，因为看起来像“能答”，实际上答复没有编译后的稳定语义面。

反过来，如果只建 wiki、不做 lint / tier / graph，也会失败：节点越积越多，旧结论与新结论并存却不标记，最终又退化成“有目录的文档堆”。所以 PhoenixAgent 选择 LLM Wiki，不是选择“更多 markdown”，而是选择**用七动词治理知识生命周期**。

## 延伸与争议

本节点的立场是：M0 优先用 wiki 建 Memory Layer 的语义骨架，M1b 以后再评估 qmd、hybrid RAG 或 agentmemory 作为加速与扩展手段。争议点在于规模阈值到底在哪里：是几百节点后再上检索，还是更早就做混合。当前项目仍处于治理层与教学层主导阶段，因此先把 wiki 做对，比提前引入复杂检索基础设施更重要。

另一个争议是“tier 是否应该写入 frontmatter”。LLM Wiki v2 倾向于把老化策略做成生命周期系统，而 AK-llm-wiki 与 PhoenixAgent 当前更偏向**通过 tier 操作与策略计算维护热面**。这部分会在 M1b 的 `MemoryBackend` 七动词补全时继续复核。

## 参考

- Andrej Karpathy, *LLM Wiki*（idea file）. https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Rohit Goyal, *LLM Wiki v2 — extending Karpathy's LLM Wiki pattern with lessons from building agentmemory*. https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2
- MindStudio, *Two Different Bets on How Agents Should Remember Code*. https://mindstudio.ai/blog/llm-wiki-vs-rag-internal-codebase-memory
- PhoenixAgent PRD v1.0 `FR-05` / `FR-08`；`docs/PRD.md`
- PhoenixAgent SPEC v1.2 `§6.1` / `§6.2` / `§14` / `INV-MM-2` / `INV-MM-3`；`docs/SPEC.md`
