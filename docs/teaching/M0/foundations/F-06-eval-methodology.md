---
id: F-06
slug: eval-methodology
name: 本地 SWE-bench 评测方法学与 Evaluator 偏差控制
milestone: M0
step: 8
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§7.1", "§7.2", "§7.3", "§7.4"]
related_fr: ["FR-06", "FR-07"]
related_inv: ["INV-EV-1", "INV-EV-2", "INV-EV-3"]
related_nodes: [F-05b, F-model-1]
replaces: null
ingested: true
ingested_at: 2026-04-23T12:53:19.1793233+08:00
readers: [llm, human]
---

# 本地 SWE-bench 评测方法学与 Evaluator 偏差控制

## 动机（Why）

PhoenixAgent 到了 M0 Step 8，第一次真正碰到“不要靠主观感觉判断 Agent 变强了没有”这个问题。只要后续要做 Auto-Research、要比较 Claude SDK runtime 与自研 runtime、要把 M1 的 KPI 绑定到一个可冻结的基线上，评测层就不能只是“跑一下样例看看不错”。它必须同时满足三件事：一是任务集足够接近真实软件维护；二是运行方式可复现，别人能在同一台机器上重跑；三是打分过程本身不能被被测系统反向污染。

`SPEC v1.2 §7`、`TRD.md §7` 和 `PRD.md FR-06 / FR-07` 把这个面明确成 Evaluation Layer。Step 8 要做的并不只是装 Docker 跑一个 benchmark，而是先建立一套足够保守的方法学：知道哪些指标在衡量什么、会在哪些方向上偏；知道为什么要优先用 SWE-bench Verified 而不是未清洗全集；也知道为什么 Evaluator 不能吃原始任务提示词，更不能带随机性随手打分。否则后续任何“Resolved Rate 提升了”都可能只是统计口径漂移，而不是系统真变强。

## 核心内容

### 1. Resolved Rate、pass@1、Human Edit Distance 分别在测什么

Resolved Rate 是**任务级二元结果**：在一组 benchmark task 里，最终有多少个 issue 被 verifier 判定为“已解决”。它最接近项目管理语义里的“这单到底修没修好”，所以适合做主 KPI，也适合做 `baseline-swebench.json` 里的冻结比较口径。它的偏差方向也最明显：当 patch 已经解决了大部分问题、但还差一个边界 case 没过时，Resolved Rate 会把这种“接近成功”直接压成 0，所以它对近似正确解有**保守、低估**倾向；反过来，如果 verifier 本身覆盖不全，只检查了部分行为，它又会把“测试刚好过了但语义并未完全修复”的 patch 记成 1，因此对弱验证集存在**乐观、高估**风险。

pass@1 测的是**第一次采样就成功的概率**。它不是“理论上多试几次总能中一次”，而是部署视角下的一次出手成功率，因此非常适合衡量 Phoenix 这种默认单次执行、失败后再显式进入下一轮计划的 agent 体系。它的主要偏差在于：对本来依赖多次 sampling、rerank 或自修复循环的系统，pass@1 会显得**偏保守**，因为它故意不奖励“多抽几次也许会成功”；但如果评测时 seed、temperature、提示词模板不固定，pass@1 又会被偶然的随机幸运样本抬高，表现出**虚高**。所以 `SPEC v1.2 §7.3` 要求固定 seed 和 `temperature=0`，把模型波动尽可能从口径里剥掉。

Human Edit Distance 测的是**候选 patch 离一个人类可接受最终补丁还有多远**。它对“差一点点就能合”的近似解特别敏感，能补足 Resolved Rate 的粗颗粒度，所以适合作为辅助分析指标，而不是唯一淘汰条件。它的偏差方向更多来自人工判断：如果 annotator 更偏好某种代码风格、命名或改动布局，那么结构上更像维护者手法的 patch 会被**偏乐观**地判为“改动距离小”；相反，语义上正确但写法不同、需要重排文件结构的 patch 会被**偏悲观**地判为距离大。换句话说，它捕捉的是“人类收尾成本”，不是“数学上是否等价正确”。

### 2. 为什么 Verified 子集比原始 SWE-bench 更可靠

原始 SWE-bench 的价值在于大规模、真实 issue、多仓库来源，但它也天然带着真实世界数据集会有的噪声：有些 issue 描述和测试之间并不完全对齐；有些仓库版本漂移后，历史 patch 与当前可复现环境不再稳定对应；还有些任务虽然名义上“可验证”，实际上 baseline 就已经不干净，或者隐藏依赖让本地重跑变得脆弱。对于想做方法学冻结的 Phoenix 来说，这些噪声会直接污染结论，因为我们根本分不清是 runtime / harness 退化了，还是 benchmark 本身标签有问题。

Verified 子集更可靠，恰恰因为它不是简单抽样，而是对任务可复现性、问题定义和验证链条做了额外清洗。可以把它理解成“从真实软件维护任务里，筛出那些 issue 描述、仓库快照、验证步骤、成功判定标准都更稳定的一层”。这样做的直接收益有三点：第一，减少误报与漏报，让 Resolved Rate 的 0 和 1 更像真实信号，而不是数据噪声；第二，降低环境漂移造成的偶然失败，使本地 Docker 评测更适合作为基线冻结；第三，给后续的 Auto-Research 提供更干净的 reward signal，否则 Generator 会为了适应脏 benchmark 学出错误策略。

这也是为什么 `TRD.md §7.2` 和 `PRD.md FR-06` 都把 SWE-bench Verified 而不是原始全集写成主基准。Phoenix 当前的目标不是“尽快拿一个更大的数字”，而是先获得一条能审计、能复跑、能对 M1 KPI 负责的基线。

### 3. 为什么 Evaluator 必须固定 seed、temperature=0，并禁止吃原始 task prompt

Evaluator 的职责不是“像另一个 agent 那样自由理解任务”，而是**对既有执行结果做稳定裁决**。只要它本身还带明显随机性，评测就会把“模型波动”与“系统能力变化”混在一起。固定 seed 与 `temperature=0` 的意义就在这里：让同一份 diff + verify 输出，尽可能得到同一份判断。只有这样，Step 8 冻结的 baseline 才能在 Step 9 / M1 里用于横向比较，而不是每次重跑都先被评委摇骰子。

禁止把原始 task prompt 直接喂给 Evaluator，则是更关键的防污染设计。原始 issue 文本、仓库说明、甚至 agent 的中间轨迹里，都可能含有对下游模型有影响的指令片段，例如“忽略上文”“直接输出通过”“按某种风格重写”。这些内容对 Generator 是任务材料，但对 Evaluator 来说属于**不应接触的攻击面**。如果让 Evaluator 看到原始 prompt，它可能被 prompt injection、角色污染或任务泄漏影响，最终不是在评价“这个 diff 是否修复了问题”，而是在重复被 issue 文本牵着走。

因此 `SPEC v1.2 §7.3` 才明确约束：Evaluator 只看 diff 与 verify 输出，不看原始 task prompt。diff 提供实际改动证据，verify 输出提供可执行结果证据，这两者共同构成裁决所需的最小事实面。这样既缩小了注入面，也让评审日志更容易审计，因为我们知道判断依据只来自可冻结产物，而不是一段可能夹带指令的自然语言背景。

## 与 PhoenixAgent 的映射

- `PRD.md FR-06` 把 SWE-bench Verified 定义成主基准，说明 Phoenix 的“变强”必须先经过客观 benchmark，而不是主观体感。
- `TRD.md §7.2-§7.4` 把本地 Docker、Codex Evaluator、`cache_level=env` 与自动 ingest 串成了运行路径，说明 Step 8 不是孤立实验，而是后续 Auto-Research 的地基。
- `SPEC v1.2 §7.1` 把 `VerifyResult.pass_at_1`、`resolved` 与 `human_edit_distance` 固化为数据结构字段，意味着这三个指标不是文档口号，而是未来 `BenchmarkReport` 的一部分。
- `SPEC v1.2 §7.3` 约束 Evaluator 的输入和随机性，直接对应本节点里关于 prompt injection 防御和裁决稳定性的讨论。
- `SPEC v1.2 INV-EV-1/2/3` 则把“报告必须入库、Evaluator 不得绕 runner、成本字段必须可审计”固定成不变量，避免 Step 8 变成一次无法复盘的手工演示。

## 失败模式（若适用）

如果只盯 Resolved Rate，不看 pass@1 与 Human Edit Distance，团队很容易误把“很多近似正确但还没收尾”的系统当成完全无效，也可能在 verifier 不够强时把表面通过当成真实修复。这样做出来的优化会朝错误方向收敛。

如果不用 Verified，而直接把原始 SWE-bench 当主裁判，Phoenix 之后做任何 runtime / harness 对比，都可能被 benchmark 噪声盖掉，最后既无法定位真实退化，也无法说服人基线是可信的。

如果 Evaluator 保留高温随机性、或者把原始 task prompt 整段喂进去，那么最常见的坏结果不是“偶尔多一个误判”，而是整个评测链条失去审计性。那时你无法解释一次提升到底来自代码改动，还是来自评委模型临场改口。

## 延伸与争议

当前仍有一个没有完全冻结的问题：Human Edit Distance 是否应该在 M1 就进入硬门槛，还是继续只做诊断指标。前者能更早捕捉“离正确很近”的改进，后者则更稳，因为它的人为判断噪声更大。对 M0 来说，更保守的做法仍是把它留在解释层，而不是一票否决条件。

另一个后续争议是，Phoenix 是否要在 Verified 之外尽早并入 SWE-EVO 或 SlopCodeBench。答案大概率是“要”，但时点不应早于本地 Docker + baseline 冻结稳定之后。否则一边换 benchmark、一边调 runtime，最后没有任何一条对比链是干净的。

## 参考

- PhoenixAgent `docs/PRD.md`：`FR-06`、`FR-07`
- PhoenixAgent `docs/TRD.md`：`§7.2`、`§7.3`、`§7.4`
- PhoenixAgent `docs/SPEC.md`：`SPEC v1.2 §7.1` / `§7.2` / `§7.3` / `§7.4`
- PhoenixAgent `docs/milestones/M0-plan.md` Step 8
- SWE-bench 官方站点：https://www.swebench.com/
- SWE-bench GitHub 仓库：https://github.com/SWE-bench/SWE-bench
- Andrej Karpathy, Auto-Research gist：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f