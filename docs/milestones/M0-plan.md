# Milestone 0 — 执行顺序计划（Step-based，工程 × 学习同步）

- 版本：v2.1（2026-04-19 修订 Step 1：F-01 ingest 移交 Step 2，避免 Step 1 物理上无 wiki 仍要求入库的自相矛盾）
- 作者：dy
- 上位文档：RnD-Analysis.md §6.1（任务清单）、TRD.md §11（技术栈）、SPEC.md §16（最小可运行骨架）、PRD.md §12（学习资料）
- 总目标：跑通所有依赖，搭好最小 `AgentRuntime` 抽象 + 基线评测环境 + 记忆入口；同步沉淀 Agent / Harness 工程的基础知识。

---

## 0. 规划原则

- **按顺序，不按时间**：每一步以**依赖关系**排位，不安排日历日期。完成当前 Step 的"进入下一步条件"才能启动下一 Step。时间粒度仅作"小 / 中 / 大"的粗略量级标注（见每步右上角），不承诺具体天数。
- **学习内嵌**：每个 Step 同时包含**工程任务**、**内嵌学习**、**产物**、**进入下一步条件**。学习节点与工程产物一起 `wiki-ingest`。
- **产物命名约定**：
  - 学习节点：`F-NN-<topic>.md`（Foundations 系列）或 `M-NN-<topic>.md`（Milestone artifact）。
  - 路径：学习节点进 `docs/teaching/M0/foundations/`；工程笔记进 `docs/teaching/M0/engineering/`。
  - 每份节点 front-matter 必须含 `milestone: M0`、`step: <N>`、`related_nodes: [...]`、`related_code: [...]`。
- **单一真相源**：任何与本计划冲突的表述以本文件为准；若涉及接口改动，先改 SPEC.md（版本 +1）再回本文件同步。

---

## 1. 完成定义（DoD，状态驱动，与时间无关）

- **DoD-1**：`bash tools/phoenix-doctor.sh` 输出 `FAIL=0`；核心条目（Python≥3.11、git、docker daemon、docs 四件套、anthropic/openai/moonshot 三端点可达）全部 PASS。
- **DoD-2**：`phoenix run --task "hello" --runtime=claude` 返回 `status="success"` 的 `TaskResult`。
- **DoD-3**：AK-llm-wiki 中 `phoenix-docs` namespace 已收录 PRD/TRD/RnD/SPEC；`wiki-query "PhoenixAgent 愿景"` 命中 PRD §2。
- **DoD-4**：SWE-bench Verified 官方 Docker harness 本地跑通 ≥ 1 个 instance 的完整流程（patch → 容器内测试 → 报告）。
- **DoD-5**：学习 artifact `F-01 ~ F-06` 全部入库（内容见 §3 各 Step 内嵌学习小节）。
- **DoD-6**：工程 artifact `M-runtime-abstraction` / `M-evaluation-setup` / `M-walkthrough` 三份汇总 artifact 入库，`docs/teaching/M0/` 存在 `.ingested.json` marker。
- **DoD-7**：三个硬接口（`AgentRuntime` / `MemoryBackend` / `ToolSpec` + `PluginRegistry`）在 SPEC v1.1 的签名下稳定冻结，进入 M1 前无再次破坏性变更。

---

## 2. 整体依赖图（Step 间顺序）

```
Step 1 (env)  ──────────────▶ Step 2 (wiki)
     │                              │
     ▼                              ▼
Step 3 (claude hello)          (wiki 支撑后续所有学习节点入库)
     │
     ▼
Step 4 (AgentRuntime abstraction)  ─▶ Step 5 (model layer)
                                         │
                                         ▼
                             Step 6 (plugin registry + dummy tool)
                                         │
                                         ▼
                             Step 7 (memory adapter + digest 闭环)
                                         │
                                         ▼
Step 8 (swebench docker, 可与 Step 3–7 并行但不先于 Step 1)
     │
     ▼
Step 9 (evaluation runner stub)
     │
     ▼
Step 10 (context/token observability)
     │
     ▼
Step 11 (teaching artifacts 汇总)
     │
     ▼
Step 12 (interface freeze checkpoint → 进入 M1)
```

虚线并行：Step 8（SWE-bench Docker）与 Step 3–7 的代码线可并行推进，但硬依赖 Step 1 的环境与 Step 2 的 wiki。

---

## 3. Step 清单（顺序推进，每步自闭环）

> 每步右上角的"量级"仅为主观粗估（S/M/L），用于提醒负担；非时间承诺。

### Step 1 — 环境预检 · Agent 与 ReAct 范式入门 〔量级：S〕

**工程任务**
- 跑 `bash tools/phoenix-doctor.sh --json > artifacts/doctor-m0-baseline.json` 归档基线。
- 按 FAIL 列表补齐依赖：`py -3 -m pip install anthropic openai litellm claude_agent_sdk`；Docker Desktop / WSL2；配置 `~/.config/phoenix/keys.env`（权限 0600）。
- 排查 `api.anthropic.com` / `api.openai.com` / `api.moonshot.ai` 三端点不可达（网络出口 / 代理 / DNS 任一环节）。

**内嵌学习（产出 F-01）**
- 必读：
  - ReAct 原论文（arXiv:2210.03629）— 阅读 Abstract + §3 Method + §5 Discussion。
  - Anthropic "Building Effective Agents"（官方 blog）— 抓三个概念：Augmented LLM、Workflow、Agent。
- 要回答（写进 `F-01-react-paradigm.md`）：
  - ReAct = Reasoning + Acting，循环结构最小形式是什么？
  - 为什么说"先 Reason 再 Action 再 Observation"比"纯 CoT"更适合工具调用？
  - Claude Agent SDK 的主循环在哪一层对应 ReAct？（此问题留到 Step 3 闭合）

**产物**
- `artifacts/doctor-m0-baseline.json`（工程）
- `docs/teaching/M0/foundations/F-01-react-paradigm.md`（学习；frontmatter `ingested:false` 占位，留待 Step 2 wiki 安装后入库）
- `docs/milestones/M0-doctor-baseline.md`（FAIL 登记或 PASS 确认）

> **Ingest 顺序说明（v2.1 修订）**：F-01 的 wiki ingest 不在本 Step 完成——AK-llm-wiki 安装本身是 Step 2 的工程任务。本 Step 只要求 F-01 物理落盘 + frontmatter 合规；ingest 由 Step 2 统一执行（覆盖本 Step 的 F-01 与 Step 2 自身的 F-mem-1）。`ci-check-teaching.py` 对 `ingested:false` 占位降级为 warning（L-ING-2），合并 PR 前由 PR template 勾选项强制翻 true。

**进入下一步条件**
- DoD-1 成立或 FAIL 条目在 `docs/milestones/M0-doctor-baseline.md` 显式记录为"已知偏差 + 缓解方案"（例如"docker 暂缓安装，Step 8 前补齐"）。
- F-01 物理落盘且 `ci-check-teaching.py` 0 error（warning 允许，含 ingest 占位）。

---

### Step 2 — AK-llm-wiki 记忆入口 · 一次编译/复利工程 〔量级：S〕

**工程任务**
- 安装 AK-llm-wiki（按 https://github.com/surebeli/AK-llm-wiki 的 README）；设定 wiki 根目录。
- `wiki-import --source markdown_dir --root docs/ --namespace phoenix-docs`，将 `PRD.md` / `TRD.md` / `RnD-Analysis.md` / `SPEC.md` 全部导入。
- 验证：`wiki-query "PhoenixAgent 愿景"`、`wiki-query "12 层 Harness"`、`wiki-query "SWE-bench"` 各抽 1 次，命中率 ≥ 1。
- 把 Step 1 产出的 F-01 `wiki-ingest`（v2.1 起 Step 1 不再尝试入库；本 Step 必须执行），并把 frontmatter `ingested` 翻 true、写入 `ingested_at`。

**内嵌学习（产出 F-mem-1）**
- 必读：
  - mindstudio "LLM Wiki vs RAG"（https://mindstudio.ai/blog/llm-wiki-vs-rag-internal-codebase-memory）。
  - LLM Wiki v2 gist（https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2）。
  - Karpathy LLM Wiki 概念（AK-llm-wiki README 内引用段落）。
- 要回答：
  - 为什么"一次编译、复利工程"比纯向量 RAG 更适合本项目？
  - ingest → query → digest → import → graph → lint → tier 七动词分别承担什么职责？

**产物**
- `docs/teaching/M0/foundations/F-mem-1-wiki-why.md`
- wiki namespace `phoenix-docs`（含 4 份核心文档 + F-01 + F-mem-1）。

**进入下一步条件**
- DoD-3 成立。
- `wiki-query` 抽样命中。

---

### Step 3 — Claude Agent SDK Hello · tool_use 协议内化 〔量级：M〕

**工程任务**
- `pip install claude-agent-sdk`；编写一段极简 demo：发一个 `"hello phoenix"` 任务，走 Claude Agent SDK 完整 ReAct 一圈；打印 assistant 文本 + tool_use 轨迹（即使此 demo 没有工具，也观察 stop_reason）。
- 同一个任务切到 Codex API（OpenAI function calling）跑一次；记录两次 tokens / 耗时，作为 M2 成本对比原点写入 `docs/milestones/M0-cost-baseline.md`。
- 日志输出到 `logs/<session_id>.jsonl`（SPEC v1.1 §13.1）。

**内嵌学习（产出 F-02 + F-05a）**
- 必读：
  - Anthropic API docs：Messages API、tool_use / tool_result 结构、cache_control、extended thinking。
  - Claude Agent SDK 官方 overview（https://code.claude.com/docs/en/agent-sdk/overview）+ 顺带浏览其 GitHub 源码的 ReAct 循环入口（只求"看见主循环在哪个文件"，不要求读懂全部实现）。
  - OpenAI function calling / tool_choice 文档（两种协议的映射点）。
- 要回答：
  - `role="tool"` 消息在 Anthropic 与 OpenAI 两边的字段差异？
  - Claude Agent SDK 的"主循环 → tool_use 分发 → Permission Hook"三个钩子大致在哪一层？
  - 此时能否回答 Step 1 留下的悬念："Claude SDK 的主循环如何对应 ReAct 的 Reasoning/Action/Observation 三段？"

**产物**
- `scripts/smoketest-claude.py`（可留根目录或 `examples/`，不进入 `src/phoenix/`）。
- `logs/` 下 ≥ 1 条完整 session JSONL。
- `docs/teaching/M0/foundations/F-02-tool-use-protocol.md`
- `docs/teaching/M0/foundations/F-05a-claude-sdk-surface.md`（F-05 的前半；F-05b 留给 Step 4 做 Runtime 抽象时继续补）
- `docs/milestones/M0-cost-baseline.md`

**进入下一步条件**
- DoD-2 初步成立（Claude 端 hello 跑通；Codex 端至少跑过一次）。
- F-02 入库；Step 1 悬念已在 F-02 或 F-05a 内闭合。

---

### Step 4 — AgentRuntime 抽象接口 · Strategy/Factory 模式落地 〔量级：M〕

**工程任务**
- 按 SPEC v1.1 §2.1 落 `src/phoenix/runtime/base.py`：`AgentRuntime` Protocol + 相关 dataclass（`RuntimeConfig`、`SessionHandle`）。
- 落 `src/phoenix/runtime/claude.py` 的最小可运行实现（把 Step 3 的 smoketest 收进来）。
- 落 `src/phoenix/runtime/core.py` 与 `openai.py` 的 stub（仅签名，`raise NotImplementedError`）。
- 落 `RUNTIME_REGISTRY` + `make_runtime`（SPEC v1.1 §2.3）。

**内嵌学习（产出 F-05b）**
- 必读：
  - Composio 的 "Claude Agents SDK vs OpenAI Agents SDK vs Google ADK" 对比文章。
  - OpenAI Agents SDK 2026-04-15 更新 blog（sandbox + Codex-like filesystem tools）。
- 要回答（写进 `F-05b-runtime-abstraction.md`）：
  - 三家 SDK 的 Session / Tool / Hook 三个抽象各自对应哪个字段或类？
  - 为什么本项目选择"用自研 Protocol 同时封装三家 Runtime"而不是"直接继承其中一家"？
  - 未来切换到 OpenAI Agents SDK 时，最有可能破坏的假设是哪一个？

**产物**
- `src/phoenix/runtime/base.py`（Protocol + dataclass，无算法）
- `src/phoenix/runtime/claude.py`（最小可运行）
- `src/phoenix/runtime/core.py`（stub）
- `src/phoenix/runtime/openai.py`（stub）
- `src/phoenix/runtime/__init__.py` 暴露 `RUNTIME_REGISTRY`
- `docs/teaching/M0/foundations/F-05b-runtime-abstraction.md`

**进入下一步条件**
- `python -c "from phoenix.runtime import make_runtime; make_runtime('claude')"` 成功返回实例。
- F-05b 入库。

---

### Step 5 — Model Layer · 多 Provider 路由与合规 〔量级：M〕

**工程任务**
- 创建 `~/.config/phoenix/models.toml`（按 SPEC v1.1 §4.1 三个 profile：`codex-base`、`kimi-worker`、`local-ollama`）。
- 落 `src/phoenix/model/client.py`：`LLMClient` Protocol + `ChatRequest/ChatResponse` dataclass；最小路由实现可基于 LiteLLM 或直调 SDK。
- `scripts/smoketest-model.py`：对 `codex-base` 与 `kimi-worker` 分别发一条 `chat`，打印 tokens / 耗时。
- 若 Kimi 报 `only available for Coding Agents`，在脚本里加 `User-Agent: Claude-Code`，记录能否穿透。
- 增加 `kimi-worker` whoami 级探针：记录 HTTP 码、延迟、直连/伪装 `User-Agent` 路径与结论到 `artifacts/M0/kimi-smoke.json`；失败不阻断 Step 5，但必须留档。
- 若直连失败，优先登记后续 HTTP 代理/兼容路由回退路径，不在本 Step 内强行实现。

**内嵌学习（产出 F-model-1）**
- 必读：
  - Moonshot Kimi Coding Plan 文档（国际路由 vs 中国路由差异）。
  - LiteLLM 统一路由 README（关注 `completion()` 与 `provider` 的映射）。
  - Anthropic 2026 初关于订阅套利的 TOS 声明（TRD §3.6 已标）。
- 要回答：
  - 为什么 subprocess 必须显式传 `--model` / `--provider` 而不能继承环境变量？（合规视角）
  - `ANTHROPIC_BASE_URL` 覆盖到 Kimi / 本地 Ollama 时，端点路径差异是什么？
  - "平庸模型 + 强 Harness"里，哪些角色归 Kimi，哪些归 Codex？

**产物**
- `~/.config/phoenix/models.toml`
- `src/phoenix/model/client.py`（Protocol + 最小 adapter stub）
- `src/phoenix/model/profiles.py`（加载 models.toml）
- `scripts/smoketest-model.py`
- `artifacts/M0/kimi-smoke.json`
- `docs/teaching/M0/foundations/F-model-1-routing-and-compliance.md`

**进入下一步条件**
- 两个 profile 至少有一个成功拿到响应；失败 profile 在 `F-model-1` 中记录诊断与后续补救时机。
- `artifacts/M0/kimi-smoke.json` 已产出；若 `kimi-worker` 失败，失败原因与回退路径已在工件和 `F-model-1` 中登记。

---

### Step 6 — Plugin Registry + dummy 工具 · MCP 协议内化 〔量级：M〕

**工程任务**
- 落 `src/phoenix/plugins/registry.py`（SPEC v1.1 §3.2）的最小实现：`register` / `list` / `tool_specs` / `execute`。
- 实现一个 dummy plugin：`echo`（`ToolSpec: echo.say`，`side_effect="none"`），手动在 `ClaudeAgentSDKRuntime` 里注册并触发。
- 落 `src/phoenix/cli.py` 的最小 `phoenix run --task ... --runtime=claude --model=<profile>` 命令。

**内嵌学习（产出 F-03）**
- 必读：
  - MCP 官方 spec（https://modelcontextprotocol.io）— 抓 `resources` / `tools` / `prompts` 三类能力 + stdio 协议栈。
  - Anthropic MCP blog / Claude Desktop 的 MCP 配置示例。
- 要回答（写进 `F-03-mcp-spec-digest.md`）：
  - MCP `tools/call` 请求与 Anthropic `tool_use` 消息的映射关系？
  - 为什么 PhoenixAgent 把 MCP 视为"第一公民"而非"可选扩展"？
  - 若未来把编程插件的 `git-worktree` 迁成 MCP server，`ToolSpec.handler` 需要如何重写？（不用真写代码，只用伪代码描述）

**产物**
- `src/phoenix/plugins/registry.py`
- `src/phoenix/plugins/echo.py`
- `src/phoenix/cli.py`（最小版本，只解析 `--task/--runtime/--model` 并调用 `make_runtime`）
- `docs/teaching/M0/foundations/F-03-mcp-spec-digest.md`

**进入下一步条件**
- `phoenix run --task "请调用 echo.say hello" --runtime=claude` 触发 tool_use 并返回 `status="success"`。
- F-03 入库。

---

### Step 7 — Memory Layer adapter · ingest/query/digest 闭环 〔量级：M〕

**工程任务**
- 落 `src/phoenix/memory/backend.py`（SPEC v1.1 §6.1 Protocol + dataclass）。
- 落 `src/phoenix/memory/akllmwiki.py`：subprocess 调用 `wiki` 命令的 adapter；只完成 `ingest` / `query` / `digest` 三个方法的最小可用版本；`import_bulk / graph / lint / tier` 留 stub。
- 在 `ClaudeAgentSDKRuntime.run_task` 末尾调用 `ctx.memory.digest(Episode(...))`（SPEC v1.1 §6.4 INV-MM-1）。
- 跑一次 Step 6 的 echo 任务，`wiki-query "echo"` 验证 digest 落盘。

**内嵌学习（产出 F-mem-2）**
- 必读：
  - AK-llm-wiki README 的"digest 规则"段落。
  - SPEC v1.1 §6.3 Digest Rules 的本项目约定。
- 要回答：
  - `digest` 与 `ingest` 为什么是两个动词？（输入来源与触发时机差异）
  - 为什么 `digest` 必须按 `namespace` 隔离？对比插件污染场景。
  - `wiki-lint` 通常在什么时机跑，为什么不是每次 digest 都跑？

**产物**
- `src/phoenix/memory/backend.py`
- `src/phoenix/memory/akllmwiki.py`（ingest/query/digest 三方法最小实现）
- 一个被 digest 产生的 wiki 节点（`namespace=echo`）
- `docs/teaching/M0/foundations/F-mem-2-ingest-query-digest.md`

**进入下一步条件**
- 一次 `phoenix run` 结束后，`wiki-query` 能命中对应 Episode 节点。
- F-mem-2 入库。

---

### Step 8 — SWE-bench Docker · 评测方法学 〔量级：L〕

> Step 8 在完成 Step 1 后即可与 Step 3–7 并行推进；但开始 Step 9 前必须先完成 Step 8。

**工程任务**
- `pip install swebench`；`docker pull swebench/sweb.eval.x86_64:latest`（或 epoch.ai 预构建镜像）。
- 选 Verified 中最小体量的一个 instance，准备一份"空 patch"或人工正确 patch。
- 调用 `swebench.harness.run_evaluation`，观察镜像启动 → 容器执行 → 报告产出；在 `docs/milestones/M0-swebench-first-run.md` 记录镜像大小、耗时、CPU/内存、产物结构。
- 冻结 `artifacts/M0/baseline-swebench.json`，至少包含：`task_ids[]`、`seed`、`runtime`、`model`、`harness_flags`、`resolved[]`、`cost.execution_usd`、`cost.evaluation_usd`、`git_sha`、`produced_at`。

**内嵌学习（产出 F-06）**
- 必读：
  - SWE-bench 原论文（NeurIPS 2023）+ Verified 技术报告（Anthropic / OpenAI 官方的验证说明）。
  - SWE-bench 官方 Setup Guide（https://www.swebench.com/）。
  - Karpathy Auto-Research gist 里关于"Evaluator 偏差"的段落。
- 要回答（写进 `F-06-eval-methodology.md`）：
  - Resolved Rate、pass@1、Human Edit Distance 三个指标各自的统计含义与偏差方向？
  - 为什么 Verified 子集比原始 SWE-bench 更可靠？
  - Codex 做 Evaluator 时为什么要固定 seed + temperature=0 + 禁止把原始 task prompt 直喂它？（Prompt Injection 防御视角）

**产物**
- `docs/milestones/M0-swebench-first-run.md`
- `docs/teaching/M0/foundations/F-06-eval-methodology.md`
- 一次成功的 SWE-bench 报告文件（路径归档进上条 md）
- `artifacts/M0/baseline-swebench.json`

**进入下一步条件**
- DoD-4 成立。
- F-06 入库。
- `artifacts/M0/baseline-swebench.json` 已冻结，且字段满足本 Step 的最小 schema。

---

### Step 9 — EvaluationRunner stub + BenchmarkReport 入 wiki 〔量级：M〕

**工程任务**
- 落 `src/phoenix/evaluation/runner.py`（SPEC v1.1 §7.2 最小形态）：只支持 `family="swe-bench-verified"` + `subset=N`；封装 Step 8 的手工流程。
- 扩展 `phoenix cli`：`phoenix eval --benchmark=swe-bench-verified --subset=1 --runtime=claude`。
- `BenchmarkReport` 写入 SQLite（`phoenix_metrics`）+ JSON 产物，同时 `wiki-ingest` 到 `namespace="evaluation"`（SPEC v1.1 §7.4 INV-EV-1）。

**内嵌学习**
- 无独立新学习节点；本步为 F-06 的代码化落地。要求在 `docs/teaching/M0/engineering/M-eng-eval-runner-design.md` 写一段"为什么 Runner 必须是 Protocol 而不是具体类"的短笔记，引用 F-05b 的 Strategy 讨论。

**产物**
- `src/phoenix/evaluation/runner.py`（最小）
- `src/phoenix/evaluation/swebench.py`（Step 8 手工流程的封装）
- SQLite 中第一条 `benchmark_resolved` 指标
- `docs/teaching/M0/engineering/M-eng-eval-runner-design.md`

**进入下一步条件**
- `phoenix eval --benchmark=swe-bench-verified --subset=1 --runtime=claude` 输出合法 `BenchmarkReport` 且入 wiki。

---

### Step 10 — Context Engineering 观察点 〔量级：S〕

**工程任务**
- 在 `ClaudeAgentSDKRuntime` 内增加轻量观察（不实现压缩算法）：每轮 assistant / tool_result 消息后，打印 `prompt_tokens` / `completion_tokens` / `cache_read` / `cache_creation` 四个字段，写入 `logs/` 下 JSONL。
- 基于最近 ≥ 3 次 run 的日志，画一张 token 画像（plain markdown 表或简单 ascii 图）。

**内嵌学习（产出 F-04）**
- 必读：
  - Anthropic Prompt Caching 官方 docs。
  - Anthropic Extended Thinking / Thinking Blocks docs。
  - sanbuphy/learn-coding-agent 关于 s06（压缩）的章节。
- 要回答（写进 `F-04-context-engineering.md`）：
  - Context 窗口的典型构成（system / few-shot / scratchpad / tool_result / thinking），哪些可以被 cache？
  - `cache_read` 与 `cache_creation` 的计费差异，对本项目成本目标（NFR-01，降 60%）贡献点在哪？
  - 为什么 PhoenixAgent 到了一定规模必须上 s06 压缩，而不是"加大上下文窗口"就够？

**产物**
- `docs/teaching/M0/foundations/F-04-context-engineering.md`
- `docs/milestones/M0-token-profile.md`（工程观察结果）

**进入下一步条件**
- F-04 入库。
- `M0-token-profile.md` 至少收录 3 次 run 的字段对比。

---

### Step 11 — 教学 artifact 汇总 〔量级：M〕

**工程任务**
- 生成三份 milestone-level artifact（把前面步骤里的 F-* 节点引用起来，形成可阅读的综合文本）：
  - `docs/teaching/M0/M-runtime-abstraction.md`：引用 F-05a / F-05b / F-02 / F-03。
  - `docs/teaching/M0/M-evaluation-setup.md`：引用 F-06 + Step 8/9 工程笔记。
  - `docs/teaching/M0/M-walkthrough.ipynb`：端到端 Notebook，串起 phoenix doctor → phoenix run → phoenix eval，穿插 F-01 / F-02 / F-04 的关键概念卡片。
- `wiki-ingest docs/teaching/M0/*`；在 `docs/teaching/M0/.ingested.json` 写入本步所有 artifact 的 ingest marker。

**内嵌学习**
- 无新学习节点；本步强迫进行一次"把分散学习节点连接成知识网"的图谱整理。使用 `wiki-graph --scope phoenix-docs --scope evaluation --scope foundations-M0` 产出可视化或文本报告，归档进 `docs/milestones/M0-memory-graph.md`。

**产物**
- 三份 M-* milestone artifact
- `docs/teaching/M0/.ingested.json`
- `docs/milestones/M0-memory-graph.md`

**进入下一步条件**
- DoD-5 + DoD-6 成立。
- `wiki-graph` 报告显示 F-* 与 M-* 节点之间无孤岛（至少两两之间有 ≥ 1 条链接）。

---

### Step 12 — 接口冻结 checkpoint · M0 收官 〔量级：S〕

**工程任务**
- 交叉审阅 `AgentRuntime`（SPEC v1.1 §2.1）、`MemoryBackend`（SPEC v1.1 §6.1）、`ToolSpec` + `PluginRegistry`（SPEC v1.1 §3.1–§3.2）三个接口：
  - 在 Step 3–9 里实际使用时是否出现过想加字段但为了 "M0 先不改" 而绕过的点？统一列出来。
  - 每条待改项决定：A. 本 Step 内同步更新 SPEC v1.1 + 代码；B. 确认延后到 M1 开头，记入 `docs/milestones/M0-interface-backlog.md`。
- 写 `docs/milestones/M0-retrospective.md`：完成项、未完成项、意外发现、每个 Step 的内嵌学习自评（"我现在能不能不看笔记回答该步的要回答问题？"）。
- `phoenix-doctor.sh --json > artifacts/doctor-m0-final.json` 作为最终基线归档。
- `wiki-lint --auto-fix` 清理孤立节点。

**内嵌学习**
- 无新学习节点；本步是学习复盘 + 接口稳定性反思。

**产物**
- `docs/milestones/M0-interface-backlog.md`
- `docs/milestones/M0-retrospective.md`
- `artifacts/doctor-m0-final.json`
- 如有 SPEC 变更：`docs/SPEC.md` 版本 +1 并 `wiki-ingest`

**进入下一步条件**
- DoD-1 ~ DoD-7 全部成立。
- 三个硬接口签名在接下来的 M1 Step 1 启动前不再破坏性变更。

---

## 4. 学习节点索引（便于反查）

| 节点 | 产自 Step | 主题 |
|---|---|---|
| F-01 | 1 | ReAct 范式 + Agent 定义 |
| F-mem-1 | 2 | Wiki vs RAG / 一次编译复利 |
| F-02 | 3 | Anthropic tool_use / tool_result 协议 + OpenAI 映射 |
| F-05a | 3 | Claude Agent SDK 表层机制 |
| F-05b | 4 | Runtime 抽象 / Strategy / 三家 SDK 对比 |
| F-model-1 | 5 | 多 Provider 路由 + 合规 |
| F-03 | 6 | MCP 协议核心 |
| F-mem-2 | 7 | ingest/query/digest 闭环 |
| F-06 | 8 | 评测方法学（pass@1 / Resolved Rate / Human Edit Distance） |
| F-04 | 10 | Context Engineering / Prompt Caching / Thinking Blocks |

---

## 5. 风险预警（M0 阶段可能触发）

| 编号 | 风险 | 触发步骤 | 当前阶段缓解 |
|---|---|---|---|
| R-ML-1 | Kimi whitelist 挡 CLI | Step 5 | 先走 `api.moonshot.ai/anthropic` 标准路径；必要时自定义 `User-Agent: Claude-Code`；写进 F-model-1 |
| R-EV-1 | Docker 跑 SWE-bench 慢 | Step 8 | 先跑最小 instance；超过主观可忍受的耗时就切 epoch.ai 预构建镜像；再不行租 Linux VPS |
| R-MM-2 | AK-llm-wiki CLI 不稳 | Step 2 / Step 7 | 记录到 `docs/milestones/M0-wiki-issues.md`；极端情况 digest 先降级为"直接追加 markdown 文件" |
| 新发现 | 任何未登记风险 | 随时 | 在 Step 12 retrospective 显式新增 R-* 编号并回写 RnD-Analysis §4 |

---

## 6. 与 M1 的衔接（硬接口清单）

以下三个接口在 Step 12 冻结后，M1 开始前不再破坏性变更：

1. `AgentRuntime` Protocol（SPEC v1.1 §2.1）
2. `MemoryBackend` Protocol（SPEC v1.1 §6.1）
3. `ToolSpec` + `PluginRegistry`（SPEC v1.1 §3.1–§3.2）

若 M0 执行过程中发现任何接口必须破坏性变更，必须先走"SPEC +1 → 本 M0 计划相应 Step 补丁"的流程，不允许"先改代码再补 SPEC"。

---

## 7. M1 / M2 计划的预告

M1 与 M2 将沿用同样的 Step-based + 学习内嵌结构。起笔时机：Step 12 验收通过且 `M0-retrospective.md` ingest 到 wiki 之后。学习节点 `F-*` 编号延续不重置（F-07 起从 M1 开始）。

---

## 7. 变更日志

- 2026-04-22：收口 Step 1 的官方 shell 基线为 Windows Git Bash（MSYS/MINGW）；`M0-doctor-baseline.md` 与 `tools/phoenix-doctor.sh` 统一按该基线对账。
