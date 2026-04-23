---
id: M-evaluation-setup
slug: evaluation-setup
name: M0 Evaluation Setup 串讲
milestone: M0
type: milestone
tier: active
spec_version: v1.2
covers_foundations: [F-06]
ingested: true
ingested_at: 2026-04-23T15:29:21.8831443+08:00
---

# M0 Evaluation Setup 串讲

## 1. 本 Milestone 的学习主线

M0 在评测这一条线上，不是直接去追求更高 benchmark 分数，而是先把“什么叫可信的本地评测闭环”固定下来。`F-06` 给出方法学约束，Step 8 用本地 Docker harness 证明 SWE-bench Verified 能在当前 Windows 环境跑通，Step 9 再把这条手工路径包成 `EvaluationRunner` 和 `phoenix eval`。所以这条线的主线不是性能，而是可复现、可审计、可入库。

## 2. 路线串讲

`F-06-eval-methodology` 是起点。它先把 Resolved Rate、pass@1、Human Edit Distance 的统计意义说清楚，又把 Verified 子集为什么比原始 SWE-bench 更可靠解释成一套方法学判断。没有这一步，Step 8 跑出来的任何数字都只是“看起来像评测”，却缺少解释框架。

Step 8 的 [docs/milestones/M0-swebench-first-run.md](docs/milestones/M0-swebench-first-run.md) 把方法学第一次落成工程事实：Windows 11 + Docker Desktop 下，`pallets__flask-5014` 用 gold patch 成功跑通，相关镜像、耗时、容器日志、冻结基线都被记录下来。这一步的重要性不在于只跑了 1 个实例，而在于它把“本地 Verified Docker harness 可复现”这件事从口头假设变成了有路径、有日志、有 frozen artifact 的仓内证据。

Step 9 的 [docs/teaching/M0/engineering/M-eng-eval-runner-design.md](docs/teaching/M0/engineering/M-eng-eval-runner-design.md) 进一步把工程边界固定下来。它说明 `EvaluationRunner` 必须是 Protocol，而不是一个写死 swebench 行为的具体类。真正的收益在于：Step 8 的手工命令不再只是一段脚本经验，而是变成 `phoenix eval --benchmark=swe-bench-verified --subset=1 --runtime=claude` 这类可调用接口的一部分。

`src/phoenix/evaluation/swebench.py` 和 `src/phoenix/evaluation/runner.py` 则把这一判断具象化。前者封装数据集选择、predictions materialization、Windows 兼容写入和 harness 调用；后者负责把结果映射成 `BenchmarkReport`，写 JSON、落 SQLite `phoenix_metrics` 并 ingest 到 `namespace="evaluation"`。这意味着评测终于从“会跑命令”升级成“会产出标准化工件”。

最后，Step 10 的 [docs/milestones/M0-token-profile.md](docs/milestones/M0-token-profile.md) 虽然不直接属于 Evaluation Layer，但它补上了成本和观测的侧面证据：评测不仅要看 resolved，还要知道运行过程里的 token / cache 字段有没有被结构化记录下来。这样 M1/M2 才有条件把质量与成本放在同一张表里看。

## 3. 关键权衡

第一项权衡是：Step 8 是否要一开始就跑多实例、非 gold、接近真实 Phoenix runtime 的评测。M0 没这么做，而是先接受“单实例 + gold + 本地 Docker smoke”这个更保守的基线。代价是它不能代表最终 KPI；收益是方法学、环境和工具链先闭环，后面再扩规模时不会混淆环境问题与模型问题。

第二项权衡是：Step 9 要不要等完整 MetricsSink、完整 Evaluator prompt 和多 benchmark family 都到位后再写。M0 也没这么做，而是先实现最小 `swe-bench-verified` 路径，让 `BenchmarkReport`、SQLite 指标和 wiki ingest 都有最小闭环。这样做保住了接口连续性，也避免 Step 8 的经验继续散落在脚本和人工命令里。

第三项权衡是：评测运行证据应该更偏向 frozen artifact，还是更偏向本地瞬时状态。M0 的选择是前者，所以保留 `baseline-swebench.json`、first-run 记录和标准化 report artifact，同时把本地 SQLite 视为 runtime state，而不是默认提交物。这样仓库里留下的是可审计证据，而不是环境偶然状态。

## 4. 教训

最大的教训是，评测路径一旦跨平台，就不能假设上游 harness 在本机天然可用。Step 8 里的 Docker helper path、CRLF shell 脚本和 Unix-only `resource` 模块问题说明：环境兼容本身就是评测方法学的一部分。

另一个教训是，`gold` predictions 虽然非常适合做 smoke test，但不能在叙述上冒充最终性能基线。M0 必须把这一点写清楚，否则后面任何人都可能把“单实例 gold smoke”误读成“Phoenix runtime 的真实基线”。

最后一个教训是，EvaluationRunner 的价值不只是跑 benchmark，而是把评测结果沉淀成统一工件。如果没有 JSON、wiki ingest 和 SQLite 指标三条出口，后续 Auto-Research 根本无法稳定消费这些结果。

## 5. 延伸阅读索引

- 本项目基础节点：`wiki-query "eval methodology" --namespace phoenix-docs`
- [docs/teaching/M0/foundations/F-06-eval-methodology.md](docs/teaching/M0/foundations/F-06-eval-methodology.md)
- [docs/milestones/M0-swebench-first-run.md](docs/milestones/M0-swebench-first-run.md)
- [docs/teaching/M0/engineering/M-eng-eval-runner-design.md](docs/teaching/M0/engineering/M-eng-eval-runner-design.md)
- [docs/milestones/M0-token-profile.md](docs/milestones/M0-token-profile.md)