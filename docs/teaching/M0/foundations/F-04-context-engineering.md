---
id: F-04
slug: context-engineering
name: Context Engineering、Prompt Caching 与 s06 压缩为什么必须一起设计
milestone: M0
step: 10
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§5.5", "§13.1", "§13.2"]
related_fr: ["FR-03"]
related_inv: []
related_nodes: [F-02, F-05a, F-05b]
replaces: null
ingested: true
ingested_at: 2026-04-23T13:23:25.2130126+08:00
readers: [llm, human]
---

# Context Engineering、Prompt Caching 与 s06 压缩为什么必须一起设计

## 动机（Why）

到 M0 Step 10，PhoenixAgent 的问题已经不再只是“能不能把 task 跑通”，而是“每一轮上下文到底在涨什么、哪些 token 是重复烧掉的、什么时候必须开始压缩”。如果没有这一层观察，后面讨论 `s06_compression` 是否值得做，就只能停留在感觉层面。对于 Phoenix 来说，Context Engineering 不是提示词修辞学，而是 Runtime、Harness 和成本目标之间的交汇点：消息怎样堆积、缓存命中在哪里发生、tool_result 会不会把上下文撑爆，这些都直接影响 `NFR-01` 的成本目标与 `NFR-04` 的可观测性目标。

`SPEC v1.2 §13.1 / §13.2` 已经把 JSONL 日志和 `phoenix_metrics` 指标表定义成基础设施，而 `SPEC v1.2 §5.5` 又明确给出了未来 s06 压缩的开口。因此 Step 10 的价值不是现在就实现压缩，而是先把“压缩前你在看什么”这件事固定下来。没有这一层观测，任何后续的 autoCompact、snipCompact 或 contextCollapse 都无法证明自己真的在降低成本，而不是单纯牺牲信息量。

## 核心内容

### 1. Context 窗口的典型构成，以及哪些部分天然适合被 cache

在 Phoenix 这类 coding agent 里，一次请求送进模型的上下文通常至少包含五段：system 指令、few-shot 示例、scratchpad 或 planning 痕迹、tool_result / observation、以及模型自己的 thinking 或 reasoning block。它们的变化频率并不相同。system 和大段固定 few-shot 往往是最稳定的；如果任务模板不变，这一块很适合 Prompt Caching。planning scaffold 也常常半稳定，比如同一类任务复用相同的执行框架。相反，tool_result 和 observation 几乎是每轮都在变的，它们最不适合 cache，却最容易把窗口撑大。

这也是为什么简单把“上下文窗口做大”不能替代 Context Engineering。窗口越大，并不代表可复用部分就会自动便宜；如果真正增长的是大量高波动的 tool_result，那么成本还是会跟着线性爬升。Context Engineering 的职责，就是先把这几块拆开看清楚，再分别决定：哪些该 cache，哪些该压缩，哪些必须原样保留。

### 2. `cache_read` 与 `cache_creation` 的计费差异，为什么它们会影响 NFR-01

Prompt Caching 的本质不是“让请求免费”，而是把高复用前缀的成本从“每次都完整重算”改成“第一次创建缓存、后续重复读取缓存”。因此 `cache_creation` 代表的是建立缓存时的一次性成本，而 `cache_read` 代表的是命中缓存时的读取成本。两者都不是零，但它们的边际含义完全不同：`cache_creation` 更像铺路成本，`cache_read` 更像复用收益是否发生。

对 Phoenix 的成本目标来说，真正重要的不是某一次请求是否出现了 cache，而是长期运行里高复用前缀的读写比。如果一直只看到 `cache_creation`，说明系统在不断制造新前缀，却没有得到稳定复用；这对 `NFR-01` 没有实质帮助。只有当同一类任务的 system / policy / 固定 scaffolding 被反复命中，`cache_read` 才会逐步稀释前缀成本。所以 Step 10 先把这两个字段做成结构化观测，是后面判断“缓存有没有真正帮我们降本”的必要前提。

### 3. 为什么 Phoenix 迟早必须上 s06 压缩，而不是只靠更大窗口

更大的窗口只能延后问题出现的时间，不能改变问题的形状。随着 Phoenix 接更多工具、更多工作轮次，增长最快的往往不是 system，而是 observation 和 tool_result。它们一方面是任务必要证据，另一方面又常常包含大量低信噪比的冗长文本，比如长日志、重复 traceback、或多轮读写文件片段。如果一直把这些原样堆回上下文，成本和注意力都会被“历史噪声”吃掉。

`SPEC v1.2 §5.5` 预留 s06 压缩，就是为了在这个阶段引入第二道治理：不是简单删上下文，而是把低价值历史折叠成更短、可继续引用的中间表示。这样做的意义有两层。第一层是成本层：减少重复注入的大块 observation。第二层是能力层：防止模型在超长历史里迷路，降低计划漂移和错误引用旧状态的概率。换句话说，压缩不是窗口的替代品，而是窗口增长后维持可控性的机制。

## 与 PhoenixAgent 的映射

- `PRD.md FR-03` 已经把 s06 上下文压缩列进 Harness 12 层机制，说明它不是可选优化，而是设计内生的一层。
- `PRD.md NFR-01` 与 `NFR-04` 共同要求 Phoenix 同时做到降成本和可观测，这正是 Step 10 记录 `prompt_tokens` / `completion_tokens` / `cache_read` / `cache_creation` 的原因。
- `SPEC v1.2 §13.1 / §13.2` 给了日志与指标的落点：JSONL 记录事件、SQLite 记录关键 metric，这使 Step 10 的观测不是临时打印，而是后续可比较的结构化数据。
- `SPEC v1.2 §5.5` 里的 s06 压缩开口解释了为什么本步先做观察，再在后续 Milestone 真正落压缩策略：先有画像，再谈压缩阈值与策略细节。

## 失败模式（若适用）

如果只盯 `tokens_in` / `tokens_out` 总数，而不拆 `cache_read` 与 `cache_creation`，团队很容易把“看起来有 cache”误判成“已经在降本”。实际上，如果每轮都在创建新缓存而几乎没有读命中，总成本并不会按预期下降。

如果完全不区分 system/few-shot 与高波动 tool_result，就会把所有上下文膨胀都怪到“模型太贵”上，结果不是去做结构治理，而是盲目缩短提示词或直接换模型，反而更容易伤到正确性。

如果等到窗口真的塞满才开始补 s06，往往已经来不及从日志里反推“到底是哪类消息在爆炸式增长”。那时压缩策略会退化成拍脑袋的全文截断，而不是可解释的分层折叠。

## 延伸与争议

一个真实争议是：Phoenix 该优先做 Prompt Caching，还是优先做 s06 压缩。更稳妥的答案通常不是二选一，而是先建立 Step 10 这种观测，再根据增长形状决定主攻方向。如果固定前缀特别长且高复用，缓存收益会先出现；如果主要问题是 observation 爆炸，压缩会更紧急。

另一个争议是 thinking blocks 是否应该完整保留进后续上下文。理论上它们对推理链连续性有帮助，但工程上它们也可能是高成本、低复用的一段。Phoenix 后面要做的，不是默认全保留或全删除，而是把 thinking 当成单独一类成本对象来观察。

## 参考

- Anthropic Prompt Caching docs
- Anthropic Extended Thinking / Thinking Blocks docs
- sanbuphy/learn-coding-agent 关于 s06 压缩章节
- PhoenixAgent `docs/PRD.md`：`FR-03`、`NFR-01`、`NFR-04`
- PhoenixAgent `docs/SPEC.md`：`SPEC v1.2 §5.5` / `§13.1` / `§13.2`