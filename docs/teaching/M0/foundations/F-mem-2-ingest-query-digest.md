---
id: F-mem-2
slug: 2-ingest-query-digest
name: ingest、query、digest 为什么必须是三个分离的记忆动词
milestone: M0
step: 7
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§6.1", "§6.2", "§6.3", "§6.4", "§14"]
related_fr: ["FR-05", "FR-08"]
related_inv: ["INV-MM-1", "INV-MM-2", "INV-MM-3"]
related_nodes: [F-mem-1, F-03]
replaces: null
ingested: true
ingested_at: 2026-04-23T12:12:44.4380573+08:00
readers: [llm, human]
---

# ingest、query、digest 为什么必须是三个分离的记忆动词

## 动机（Why）

到了 M0 Step 7，PhoenixAgent 已经不再只是“能跑一个 runtime + 一个 dummy tool”的骨架，而是开始要求系统具备真正的记忆闭环：任务完成后，经验必须回写；下一次再问，系统必须能检索到刚才那次 run 沉淀下来的节点。如果这里把所有动作都混成一个宽泛的“记忆一下”，那么 Memory Layer 很快就会失去边界，最终又回到“谁都能直接写 wiki 文件、谁也说不清什么该进库”的状态。

因此，`SPEC v1.2 §6.1-§6.4` 把记忆层明确拆成 `ingest`、`query`、`digest` 等动词，不是为了接口看起来完整，而是为了把**输入来源、触发时机、语义责任**分离开。M0 的最小实现只把其中三者跑通，已经足够说明这套拆分为什么是必要的：文档入库不是运行时经验回写；运行时经验回写也不是查询接口；查询接口更不应该承担“顺手修库”的副作用。

## 核心内容

### 1. 为什么 `digest` 与 `ingest` 必须是两个动词

`ingest` 的输入是**外部已有内容**。它面对的是一个已经存在的 markdown 文件、一段整理好的文本、一个 URL，或者未来的批量导入目录。它做的事是把这个“现成知识源”编译进 wiki，并给它稳定的 namespace、slug 和索引位置。也就是说，`ingest` 解决的是“知识怎样进入系统”的问题。

`digest` 的输入则完全不同。它不是一篇现成文章，而是**一次运行刚结束时产生的 episode**：里面有 task prompt、`TaskResult.status`、tool 调用、失败恢复点、以及对下次最有价值的事件序列。这个输入天然是运行时对象，不是作者手工整理好的知识文件。所以 `digest` 解决的不是“导入哪份文档”，而是“怎样把一次动态执行压缩成可复用的记忆节点”。

如果把两者合并成一个动词，系统表面上好像更简单，实际上会把两个关键边界抹掉。第一，调用者会搞不清什么时候应该传文件、什么时候应该传 episode。第二，MemoryBackend 的实现会越来越依赖调用端的约定，例如“如果传了 text 且带 status 就当 digest”，这种隐式协议很快就会失控。把二者拆开后，调用侧就清晰了：文档、教学节点、实验报告走 `ingest`；任务 run 结束的经验回写走 `digest`。

这也是为什么 Step 7 的最小闭环不是“给 wiki 再加一个 query”，而是“在 `ClaudeAgentSDKRuntime.run_task` 收尾处触发 `ctx.memory.digest(...)`”。只有把运行时回写做成独立动词，Memory Layer 才真正和 Runtime Layer 建立了接口级闭环。

### 2. 为什么 `digest` 必须按 namespace 隔离

`SPEC v1.2 INV-MM-2` 与 `TRD.md` 的 `D-PL-3` 一起强调，记忆查询与记忆回写都不能忽略 namespace。原因很直接：PhoenixAgent 未来不是只有一个 `echo` 插件，也不是只有一个“编码场景”。如果不同插件、不同场景把经验都写进同一片全局 wiki 热面，那么 query 命中结果会迅速被污染。

举一个最小的污染例子。`echo.say` 这种 dummy tool 的 digest 节点里，频繁出现的是“echo”“message”“tool_invoked”“tool_completed”。如果不按 namespace 隔离，那么以后一个真正的 coding plugin 在查询“message formatting”“tool result contract”时，很可能先命中一堆 echo 试验节点，而不是代码修复或 benchmark 经验。这种污染不是搜索质量的随机噪声，而是接口设计没有表达“这份记忆属于谁”。

namespace 的价值，在于它把“知识内容”之前先加上“知识归属”。对于插件来说，它通常对应 `plugin.namespace`；对于后续 milestone / evaluation / retrospective，也可以对应不同知识域。这样 `query("echo", namespace="echo")` 与跨 namespace 的全局查询就是两种不同的意图，调用者必须显式选择，而不是被底层偷偷混在一起。

从工程角度看，这也保护了后续替换 backend 的自由。今天底层是 AK-llm-wiki，明天可以是 hybrid wiki + RAG，但“插件经验隔离”这件事不能因为底层实现变化而消失。所以 namespace 不是 AK-llm-wiki 的小细节，而是 Memory Layer 公开契约的一部分。

### 3. 为什么 `wiki-lint` 不是每次 `digest` 都跑

直觉上，很多人会觉得“既然 digest 可能引入脏数据，那每次 digest 后立刻 lint 最安全”。这个判断只对了一半。`wiki-lint` 的职责是**全局健康检查**：看断链、看孤点、看命名漂移、看过期结论。它天生更像 repo 级别的维护动作，而不是每个 episode 都必须同步执行的热路径。

如果把 lint 放到每次 digest 后强制执行，会带来三个问题。第一，运行时成本被放大。Step 7 的目标是让一次 `phoenix run` 结束后能立刻形成可 query 的节点；如果每次都做全库 lint，任务收尾延迟会随着节点数增长持续恶化。第二，失败域会被扩大。一次本来已经成功的 echo 任务，可能因为某个旧节点的孤立链接而在收尾阶段整单失败，这会让“运行时经验回写”被“全局知识维护”反向绑架。第三，职责会混乱。digest 负责压缩单次 run，lint 负责治理整个 wiki；把两者绑死会让调用者很难判断失败到底属于哪一层。

因此，更稳健的做法是：`digest` 只保证把本次 episode 写成一个最小可 query 节点；`wiki-lint` 则在更合适的时机跑，例如批量教学 artifact ingest 之后、Auto-Research 一轮结束之后、或者 CI / 定期维护任务里统一跑。这也是 `TRD.md` 中 `D-MM-3` 的合理落点：lint 是必要的，但不是每次最小 digest 的同步后置步骤。

M0 Step 7 的最小实现故意只把 `ingest/query/digest` 跑通，正好体现了这一点。系统先拿到“能写、能查、能复用”的闭环，再把 `lint/graph/tier/import` 作为下一阶段扩展能力补齐，而不是在第一天就把热路径做成笨重的全量维护任务。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §6.1`：`MemoryBackend` 把 `ingest/query/digest` 定义成不同签名，直接表达三种输入和责任的区别。
- `SPEC v1.2 §6.2`：AK-llm-wiki 适配通过 `wiki-ingest` / `wiki-query` 承接 Memory Layer，说明 Memory 不是直接读写文件，而是走显式接口。
- `SPEC v1.2 §6.3`：digest 的关注点是 episode 关键事件抽取与 namespace 回写，而不是全库维护。
- `SPEC v1.2 §6.4`：`INV-MM-1/2/3` 分别约束了任务结束必须 digest、query 必须带 namespace 语义、以及任何层都不能绕过 MemoryBackend 直写 wiki。
- `SPEC v1.2 §14`：CLI 最终会把这些动词暴露成统一的 `phoenix memory ...` 操作面。

## 失败模式（若适用）

如果把 `digest` 和 `ingest` 合并，最常见的失败模式是：调用端开始偷偷塞各种特殊字段，让同一个入口既处理文件导入又处理运行时回写，最后没有人能确定失败是“文件格式问题”还是“episode 摘要规则问题”。

如果取消 namespace 隔离，最先坏掉的不是底层存储，而是 query 的可解释性。调用者会看到“搜到了很多东西”，但无法回答“为什么搜到的是这个插件的记忆，而不是另一个插件的”。

如果每次 digest 都强制跑 lint，系统早期也许还能忍，节点一多后就会出现“任务本身成功，但全局维护导致收尾失败”的耦合问题。那时 Runtime Layer 与 Memory Layer 的边界会被再次打散。

## 延伸与争议

当前仍然有一个值得保留的问题：当节点规模继续增长后，是否需要把“轻量 lint”与“全量 lint”再进一步拆开，例如 digest 后只做 namespace 内局部检查，批处理阶段再做全局 lint。M0 不急着回答这个问题，因为先把最小闭环走通比提前复杂化维护策略更重要。

另一个后续争议是，namespace 是否应该只对应插件，还是也要覆盖 benchmark、teaching、retrospective 等更高层知识域。现阶段答案是“必须保留这个能力”，但具体命名体系可以等 M1b 的 Memory Layer 扩展时再冻结。

## 参考

- PhoenixAgent `docs/SPEC.md`：`SPEC v1.2 §6.1` / `§6.2` / `§6.3` / `§6.4` / `§14`
- PhoenixAgent `docs/TRD.md`：`D-PL-3` / `D-MM-3` / `D-MM-4`
- PhoenixAgent `docs/milestones/M0-plan.md` Step 7
- PhoenixAgent `docs/teaching/M0/foundations/F-mem-1-wiki-why.md`
- PhoenixAgent `src/phoenix/memory/backend.py`
- PhoenixAgent `src/phoenix/memory/akllmwiki.py`
- PhoenixAgent `src/phoenix/runtime/claude.py`