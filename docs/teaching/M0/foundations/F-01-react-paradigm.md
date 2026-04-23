---
id: F-01
slug: react-paradigm
name: ReAct 范式与 Agent 定义
milestone: M0
step: 1
type: foundation
tier: active
spec_version: v1.1
related_spec: ["§2.1", "§5.1"]
related_fr: ["FR-01"]
related_inv: ["INV-RT-1"]
related_nodes: []
replaces: null
ingested: true
ingested_at: 2026-04-23T00:32:22.0654938+08:00
readers: [llm, human]
---

# ReAct 范式与 Agent 定义

## 动机（Why）

PhoenixAgent 的全部 8 层架构都站在一个最小循环之上：让 LLM **先想（Reason）再做（Act）再看（Observe）**，并把结果反馈给下一轮思考。这个循环就是 ReAct。理解它是 M0 阶段最早需要内化的范式，因为 SPEC v1.1 §2.1 的 `AgentRuntime.run_task` 和 §5.1 的 `HarnessFlags.s01`（主循环开关）都直接落在它上面。如果一开始就把"工具调用"误读成"函数调用 + return"，后面 12 层 Harness、Permission Hook、记忆 digest 就都没有挂载点。

## 核心内容

### 1. ReAct 的最小循环形式

ReAct 论文（Yao et al., 2022, arXiv:2210.03629）把单步定义为一个三元组：

```
Thought  → Action  → Observation
（推理）   （动作）    （观测）
```

主循环结构：

```
loop:
  thought      = LLM.reason(history)            # 内部链式思考
  action       = LLM.choose_tool(thought)       # 选择工具及参数（可为"finish"）
  if action == finish: break
  observation  = environment.execute(action)    # 外部世界返回结果
  history.append(thought, action, observation)
```

终止条件由模型自己提出（`finish`）或外层施加（步数 / token / 预算上限）。**这一点与"纯 CoT 一次推理出答案"的核心差异：循环中每一步都允许把**外界返回的事实**纳入下一步推理**。

### 2. 为什么"Reason → Action → Observation"比纯 CoT 更适合工具调用

- **CoT** 把整条思路写在一次回答里，没有"我现在去调用 X 然后等结果"的中断点。一旦中间需要外部信息（搜索、读文件、跑测试），CoT 只能 hallucinate。
- **ReAct** 把推理切分成步，每一步显式声明"接下来要让世界做什么"。LLM 不再被迫预测工具结果，而是把它**等回来**再继续推理；幻觉率因此在工具型任务上大幅下降（论文 §5 在 HotpotQA 与 Fever 上的对比）。
- 工程上还有一个关键收益：**Observation 是结构化的**（tool_result 消息），可以走权限校验、副作用回放、缓存复用。这正是 SPEC v1.1 §5 12 层 Harness 能"夹"进来的位置——每一次 Action 出口、每一次 Observation 入口都是验证链的天然钩子。

### 3. Agent = LLM + 循环 + 工具 + 记忆

借 Anthropic 的"Building Effective Agents"提出的三个区分：

- **Augmented LLM**：单次调用，可读取检索/工具但无循环。
- **Workflow**：人写好的固定流程（DAG），LLM 只在某些节点参与。
- **Agent**：LLM **自己决定**下一步是什么、什么时候停。

PhoenixAgent 落在第三类。ReAct 是它最简单的实现；Plan-and-Execute、Tree-of-Thought、Reflexion 都是 ReAct 的变体（多了规划层、并行展开或反思阶段），但骨架一致。

### 4. Claude Agent SDK 主循环 ↔ ReAct 的对应（留到 Step 3 闭合）

M0 Step 1 暂不打开 SDK 源码，先记下三个待回答问题，留给 Step 3 的 `F-05a-claude-sdk-surface.md` 完成：

- SDK 内部哪个函数是 ReAct 主循环的入口？
- `tool_use` / `tool_result` 消息如何映射到 Action / Observation？
- Permission Hook 截获的是 Action 出口还是 Observation 入口？

**本节点的临时假设**（由 Step 3 验证或推翻）：SDK 的 `query()` 主流程对应 `loop`；模型回复中的 `tool_use` block 对应 Action；调用方在拿到 `tool_use` 后执行工具并把 `tool_result` 写回历史，对应 Observation；Permission Hook 在 Action 出口截获。

## 与 PhoenixAgent 的映射

- **SPEC v1.1 §2.1 `AgentRuntime.run_task`**：本质就是把"一次任务"包装成一次 ReAct 循环；`TaskResult.finish_reason ∈ {"stop", "tool_use", "length", "error"}` 中前两者直接对应循环的两类退出。
- **SPEC v1.1 §5.1 `HarnessFlags.s01`（主循环）**：这是把 ReAct 整个循环本身作为可开关单元；`s01=False` 等价于退化到 Augmented LLM（只一次调用，不循环）。s01 是 Safety-Critical 三个之一，default 永远 True（HF-SEC-1 / ADR-0001），但在评测对照实验中允许 `dataclasses.replace(flags, s01=False)` 临时关闭。
- **INV-RT-1**：每一次 Action（Tool 调用）必须经过 `_enforce_validation_chain`。ReAct 在这里给了 12 层 Harness 唯一合法的"挂载位置"——Action 出口、Observation 入口。

## 失败模式

- **退化为 CoT**：模型在 Thought 里"假装调用了工具并猜结果"。表现：tool_use 计数为 0 但回答中出现"我已查询..."字样。缓解：在系统 prompt 里强约束"必须使用工具或显式 finish"，并在评测层校验工具使用率（M0 暂以日志肉眼检查，M1 起进 EvaluationRunner 指标）。
- **循环不收敛**：模型反复发起相同 Action。原因常是 Observation 的格式让模型读不出"已成功"。缓解：tool_result 必须返回结构化 `ok/err` 字段，Harness s07（终止判定）兜底。
- **Action 不带充分参数**：模型生成的 `tool_use` 缺字段，造成执行报错。缓解：ToolSpec.input_schema（JSON Schema）在 SDK 侧严格校验，不合法直接打回（不走外部世界）。
- **跨步信息丢失**：history 截断时把关键 Observation 截掉。缓解：s06（压缩）必须保留最近若干 Action/Observation 对，留到 F-04（Step 10）展开。

## 延伸与争议

- **Reflexion / Tree-of-Thought 是不是 ReAct 的真子集？** 学界有争议；本项目立场：把它们视为"在 ReAct 单步外再加一层 meta-loop"，在 SPEC 中通过 s10（Reflection）开关与 s09（多 Plan）独立控制。
- **是否所有任务都该用 ReAct？** 不。极短任务（单次问答）走 Augmented LLM 更省 token；这正是 NFR-01"成本降 60%"的依据之一——`s01` 可被针对性关闭以做对照。
- 本节点暂未触及"并行 Action"（同一步发起多个 tool_use），留到 M1 讨论 Harness 多分支时再补 F-* 节点。

## 参考

- Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629（2022-10）。https://arxiv.org/abs/2210.03629 — 阅读 Abstract、§3 Method、§5 Discussion。
- Anthropic. *Building Effective Agents*. 2024-12。https://www.anthropic.com/research/building-effective-agents — 抓 "Augmented LLM / Workflow / Agent" 三分。
- PhoenixAgent SPEC v1.1 §2.1（`AgentRuntime` Protocol）、§5.1（`HarnessFlags` 与 s01）、§5 12 层 Harness 总表 — 本仓 `docs/SPEC.md`。
- PhoenixAgent PRD §3 第 1 条（"统一 `AgentRuntime` 接口，封装 ReAct Loop..."） — 本仓 `docs/PRD.md`。
- ADR-0001（HarnessFlags frozen=True）— 本仓 `docs/adr/ADR-0001-harness-flags-frozen.md`，解释为什么 s01 等开关需 `dataclasses.replace()` 而非属性赋值。
