---
id: M-eng-eval-runner-design
slug: eval-runner-design
name: Step 9 为什么 EvaluationRunner 必须是 Protocol
milestone: M0
step: 9
type: engineering
tier: active
spec_version: v1.2
related_spec: ["§7.2", "§7.4"]
related_fr: ["FR-06", "FR-07"]
related_inv: ["INV-EV-1", "INV-EV-2", "INV-EV-3"]
related_nodes: [F-05b, F-06]
replaces: null
ingested: true
ingested_at: 2026-04-23T13:05:00+08:00
readers: [llm, human]
---

# Step 9 为什么 EvaluationRunner 必须是 Protocol

`EvaluationRunner` 在 Step 9 不能直接做成一个唯一具体类，原因和 `F-05b-runtime-abstraction.md` 里讲的 Runtime Strategy 是同一个：这里的变化轴不是一个，而是至少有三条。

第一条变化轴是 benchmark family。今天 M0 只支持 `swe-bench-verified`，但 `SPEC v1.2 §7.2` 已经把 `swe-evo`、`slopcodebench`、`phoenix-custom` 预留出来了。如果一开始就把 `run()` 的行为写死在一个具体类里，后面每加一种 benchmark 都会把 family-specific 解析、镜像准备、任务选择、验证结果映射继续塞回同一处，最后这个类会同时承担调度器、适配器和报告聚合器三个职责。

第二条变化轴是执行来源。M0 的 Step 9 还是对 Step 8 的手工流程做封装，本质上用的是 swebench harness + gold patch 路径；但到了 M1/M2，真正被比较的对象会是不同 Runtime 和不同 model profile。也就是说，Runner 的上层契约应该稳定，底层“任务怎么跑出来”必须可替换。Protocol 让 `phoenix eval` 依赖的是 `run()` / `export_report()` 这两个稳定方法，而不是依赖某个 swebench 细节实现。

第三条变化轴是副作用出口。`BenchmarkReport` 现在要同时写 JSON、落 SQLite `phoenix_metrics`、并 ingest 到 wiki `namespace="evaluation"`。这些副作用在本地开发阶段可以放进默认实现里，但它们不应该决定接口本身。否则未来要接远端 MetricsSink、对象存储、或批量评测 orchestrator 时，调用方就必须知道具体类有哪些额外行为，接口边界会被副作用反向污染。

因此本步采用的结构是：`EvaluationRunner` 只定义稳定契约，`DefaultEvaluationRunner` 负责当前 M0 需要的最小可运行路径。这样做和 Runtime Layer 一样，先把“调用方依赖什么”冻结，再让 family-specific 代码留在适配层扩张。