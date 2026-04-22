# PhoenixAgent 产品需求文档（PRD）

- 版本：v1.0（基于 grok-chat v0.3 合并整理）
- 日期：2026-04-18
- 作者：dy
- 语言：中文（面向大模型直接 ingest，禁止外部上下文依赖）
- 配套文档：TRD.md（技术白皮书）、RnD-Analysis.md（研发分析）、SPEC.md（模块接口契约）

---

## 1. 文档性质与读者

本 PRD 是 PhoenixAgent 本地研发计划的"单一真相源"（Single Source of Truth），服务两类读者：

- **大模型**（Claude Agent SDK、OpenAI Agents SDK / Codex SDK、Kimi K2.5 等）：作为研发 Agent 的需求上下文，直接 ingest 到 AK-llm-wiki，支撑 query 与 digest。
- **人类研发者**（项目作者 dy + 后续协作者）：作为研发决策、回顾、教学复盘的依据。

本文档只定义"做什么、为什么、验收什么"，不落具体代码；架构细节见 TRD，接口契约见 SPEC，排期与风险见 RnD-Analysis。

---

## 2. 项目愿景与一句话定位

**一句话定位**：PhoenixAgent 是一个兼顾"研发"与"学习"的自研编码 Agent 系统，从 Claude Agent SDK 骨架起步，经由自研 Agent Core + 插件化多场景，最终成为可在编码任务上对标甚至超越 Claude Agent SDK + Codex 基准的、全链路自主可控、可插拔 Harness、可切换模型、可量化验收的 Agent 平台。

**愿景关键词**（每一个都必须在设计里被显式承载）：
- **全链路自研可控**：最终运行时不强依赖任何闭源商业 SDK；Claude Agent SDK 仅作为初始骨架与教学对比参考保留。
- **可教学**：每个里程碑与子任务结束后，自动产出结构化教学 artifact（Notebook / README / 实验报告）并回灌记忆系统，形成复利。
- **可插拔**：Runtime（Claude SDK / 自研 Core / OpenAI Agents SDK）、场景（编程 / 研究 / 运维）、Memory Backend（wiki / agentmemory / hybrid RAG）均可热切换。
- **可验证**：所有改进必须通过客观基准（SWE-bench Verified 为主、SWE-EVO / SlopCodeBench 为辅）量化，杜绝主观改进。
- **平庸模型 + 强 Harness = 高性能**：通过工程纪律弥补模型能力，把高成本 Codex 仅用于调教与评测，执行主力逐步切换到低价 Kimi Coding Plan。

---

## 3. 背景与问题陈述

### 3.1 动机
1. 商业 Agent SDK（Claude Agent SDK、OpenAI Agents SDK）能跑通代码实现任务，但对用户而言是黑盒；无法内化"Harness Engineering"与"Agent 架构"知识。
2. 顶级模型（Claude Opus / Codex）每百万 token 成本昂贵，长期大量迭代不可持续。
3. 已有开源资料（sanbuphy/learn-coding-agent 的 12 层 Harness 拆解、Karpathy 的 LLM Wiki 与 Auto-Research 原概念、SWE-bench 的官方 Docker harness）证明"平庸模型 + 强 Harness"路线在 2026 年初已标准化。
4. 作者希望通过"边做边学"同时拿到三件东西：一个自研可用 Agent、一套 Harness Engineering 知识资产、一条可复利的长程研发工作流。

### 3.2 问题陈述（本项目要回答的核心问题）
- Q1：如何用 Claude Agent SDK + Codex API + Kimi Coding Plan 最短路径跑通编码场景？
- Q2：如何在同一套任务集上逐步把"Claude Agent SDK + Codex"替换为"自研 Agent Core + Kimi Coding Plan"而不掉点？
- Q3：如何构建一个"一次编译、复利工程"的记忆系统，让每一轮任务的结果自动沉淀并被下一轮复用？
- Q4：如何在开发全过程中持续产出教学 artifact，形成可被大模型 ingest 的学习闭环？
- Q5：如何用客观可复现的本地基准（SWE-bench Verified 等）取代主观判断，驱动 Auto-Research 自我迭代？

---

## 4. 利益相关者与角色

| 角色 | 职责 | 对 PhoenixAgent 的关注点 |
|---|---|---|
| 作者 dy | 研发 / 决策 / 教学内容作者 | 研发进度、知识沉淀质量、成本控制 |
| PhoenixAgent 自身 | 作为研发工具，被作者调用执行子任务 | 每个里程碑的工具能力是否足以承担下一阶段工作 |
| 大模型 Ingest 客户端（Claude SDK / Codex / Kimi） | 消费 PRD + Wiki，产出代码与分析 | 文档的结构化程度、可 query 度、是否自包含 |
| 未来协作者 / 读者 | 基于本项目学习 Harness Engineering | 每阶段教学 artifact 的完整度与可复现性 |

---

## 5. 核心价值主张

| 维度 | 价值 | 对比基准 |
|---|---|---|
| 研发 | 一个生产级、Harness 完备的自研编码 Agent | 仅使用 Claude Agent SDK 的黑盒调用 |
| 学习 | 每阶段教学 artifact + 记忆系统复利 | 读散落博客 / 看视频的碎片学习 |
| 成本 | 执行主力使用 Kimi Coding Plan，token 成本降低 ≥ 60% | 全程使用 Claude Opus / Codex |
| 可控 | 模型、Harness、插件、记忆四层均可替换 | 绑定单一 SDK 生态 |
| 可验证 | SWE-bench Verified 等客观基准驱动迭代 | 主观"感觉变好了"的改进 |

---

## 6. 范围与功能需求

### 6.1 In-Scope（本项目承诺实现）
FR-01 至 FR-08 标号供 TRD / SPEC / 验收清单交叉引用。

#### FR-01 运行时抽象层（AgentRuntime）
- 统一 `AgentRuntime` 接口，封装 ReAct Loop、Tool Dispatch、Permission Hook、Session 管理。
- 至少三个具体实现：`ClaudeAgentSDKRuntime`（M0 起始）、`PhoenixCoreRuntime`（M1 自研）、`OpenAIAgentsRuntime`（M1/M2，支持 Codex SDK）。
- 支持运行时秒级切换，命令行形如 `phoenix run --task "..." --runtime=self --model=kimi`。

#### FR-02 模型路由层（Model Routing）
- 统一 LLM 客户端，基于 LiteLLM 或等价封装，支持 Anthropic 兼容端点（Claude、Kimi）、OpenAI 兼容端点（Codex）。
- 两类职责：**调教 / 评测角色** 使用 Codex API；**执行角色** 使用 Kimi Coding Plan（`api.moonshot.ai/anthropic` 国际路由 + 自管 API Key）。
- 支持 `--model` / `--provider` / `base_url` / `api_key` 四元组显式传递；禁止 subprocess 隐式继承上层 API Key。
- 本地模型（Ollama / LM Studio / vLLM）通过 `ANTHROPIC_BASE_URL` 自定义端点零地域限制接入。

#### FR-03 自研 Harness 层（12 层机制）
参照 sanbuphy/learn-coding-agent，按需叠加实现如下 12 层：
- s01 主循环（ReAct loop）
- s02 工具调度（tool_use → executeTool 统一分发）
- s03 规划模式（Plan Mode + Todo Writer，先 Plan 再 Execute）
- s04 子代理（subagent via messages[] 独立上下文）
- s05 技能注入（Skill Tool，按需注入 system prompt）
- s06 上下文压缩（autoCompact + snipCompact + contextCollapse）
- s07 持久化任务（TaskCreate/Update + 状态存储）
- s08 后台任务（DreamTask，独立思考不污染主循环）
- s09 队协作（TeamCreate + InProcessTeamCraftTask）
- s10 队内协议（SendMessageTool）
- s11 自主调度（orchestrateMode）
- s12 工作树隔离（EnterWorktree via git worktree）
- 必须实现的强制验证链：`validateInput() → PreToolUse Hooks → checkPermissions() → executeTool() → mapToolResultToAPI()`。
- "永远不信任大模型输出"（Don't Trust LLM Output）作为硬约束。

#### FR-04 插件系统（场景化能力）
- `PluginRegistry` 运行时注册 / 热加载 / 版本化。
- 插件通过 MCP（Model Context Protocol）标准接口暴露工具；非 MCP 插件通过本地 entry-point 注册。
- 首个插件：**编程插件**，至少包含 `git-worktree`、`multi-file-edit`、`test-runner`、`harness-validator` 四个工具。
- 后续场景（研究 / 运维 / 文档生成）以同接口扩展，不改 Core。
- 插件必须声明独立的 memory slice，避免全局污染。

#### FR-05 记忆系统（一次编译、复利工程）
- 抽象：`MemoryBackend` 接口，强制实现 `ingest(source)`、`query(q)`、`digest(episode)`、`import(bulk)`、`graph()` 五个能力。
- 当前默认实现：AK-llm-wiki（GitHub: surebeli/AK-llm-wiki），基于 filesystem wiki + 核心命令 `wiki-ingest` / `wiki-query` / `wiki-lint` / `wiki-graph` / `wiki-import` / `wiki-tier`。
- 未来可替换为 agentmemory / qmd / hybrid RAG + Graph，接口不变。
- 必须形成闭环：每轮工具结果 → `digest` 回写 wiki → 下一轮 `query` 可命中。
- 支持三层记忆老化：active / archived / frozen。
- `wiki-import` 批量迁移 Obsidian / Notion / 现有知识库作为冷启动。

#### FR-06 检验框架（Evaluation Framework）
- 主基准：**SWE-bench Verified**（500 个真实 GitHub issue 子集），官方 Docker harness 本地运行。
- 长程补充：**SWE-EVO**（多 commit 软件演化）或 **SlopCodeBench**（迭代扩展任务）。
- 自定义任务集：作者维护的多文件重构 + 持久化任务链，覆盖"编程场景"特定验收点。
- 硬件要求：x86_64、120GB 磁盘、16GB RAM、8+ 核（M0 验证本地可跑）。
- 指标矩阵：
  - 执行质量：Resolved Rate、pass@1、补丁正确性、测试通过率、Human Edit Distance。
  - 长程质量：多步完成率、错误恢复率、任务持久性（中断后 resume）、架构决策稳定性。
  - 成本：单任务 token 消耗、$/Resolved。
- 每次迭代后自动运行基准 → Codex 作为 Evaluator 打分 → 自动保留或丢弃变更。

#### FR-07 Auto-Research 循环
- 采用 Generator（自研 Core）→ Evaluator（Codex API）→ Keep/Discard 的 GAN-style 循环。
- 每代迭代 5–15 次；每轮改动限定在 harness / 插件 / 记忆 digest 规则三类代码。
- 灵感来源：Karpathy gist（https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f）。
- 所有实验使用预构建 Docker 镜像 + `cache_level=env`，单机 1 小时内能跑完 Verified 子集。
- 输出：每轮 `experiment-report.md`（前后对比、token 消耗、Resolved Rate 变化）自动 ingest 到 wiki。

#### FR-08 教学层（Teaching Layer）
- 每个里程碑、每个子阶段强制产出一套教学 artifact：
  - `README-teaching.md`：本阶段 Harness / 插件 / 记忆为什么有效。
  - `walkthrough.ipynb`：代码走读 + 可复现实验。
  - `experiment-report.md`：量化数据（Resolved Rate、token、成本、成功率）。
- 所有 artifact 必须通过 `wiki-ingest` 自动入库，并与现有 wiki 节点建立 graph 链接。
- 每个阶段结束必须强制运行 `wiki-ingest` 与生成 Notebook，才允许进入下一阶段。

### 6.2 Out-of-Scope（本项目明确不做）
- OOS-01：面向非编码场景的通用 Agent 通用 UI；只保留 CLI + 可选的简单 TUI。
- OOS-02：商业发行 / 多租户 / 云端服务化；单机 / 自管环境。
- OOS-03：训练 / 微调底座模型；只做 Harness 与记忆层的工程优化。
- OOS-04：自研底层向量数据库；直接复用 AK-llm-wiki 或 qmd / 第三方 RAG。
- OOS-05：移动端 / 浏览器插件形态。

---

## 7. 用户场景与成功路径

### 7.1 场景 A：作者用 PhoenixAgent 完成一次多文件重构
1. 作者在 CLI 执行 `phoenix run --task "重构 module X 的 auth 逻辑" --runtime=self --model=kimi`。
2. PhoenixAgent 进入 Plan Mode（s03），输出结构化 JSON 计划；作者确认。
3. 执行阶段按计划分解子任务，必要时启用 subagent（s04）+ git worktree（s12）。
4. 每次工具调用前走 `validateInput` → `PreToolUse Hook` → `checkPermissions`；越权即拒。
5. 过程中上下文超阈值触发 `autoCompact`；长耗任务可被持久化（s07）并在后台 DreamTask（s08）思考下一步。
6. 任务完成后，结果 `digest` 到 AK-llm-wiki；生成 `experiment-report.md`；wiki-graph 自动补链接。

### 7.2 场景 B：Auto-Research 自我调教
1. 作者触发 `phoenix research --rounds=10 --benchmark=swe-bench-verified`。
2. Generator（自研 Core）提出 harness 或记忆 digest 改动；Evaluator（Codex）在 Verified 子集上打分。
3. 分数高的变更保留，低的丢弃；每轮自动生成 `experiment-report.md` 并入 wiki。
4. 10 轮后输出一份"本轮最佳配置"+ token 成本曲线 + Resolved Rate 曲线。

### 7.3 场景 C：学习路径
1. 作者打开 Milestone 1 结束时自动生成的 `walkthrough.ipynb`。
2. Notebook 内嵌每层 Harness 的代码片段 + 对比实验（开启 / 关闭该层的 Resolved Rate 差异）。
3. 作者对任意 Harness 机制有疑问时，通过 `wiki-query "Plan Mode 为什么能提升成功率"` 直接检索解答。

---

## 8. 非功能需求（NFR）

| 编号 | 类型 | 要求 |
|---|---|---|
| NFR-01 | 成本 | 全链路 token 成本相对 "Claude Opus + 纯 ReAct" 降低 ≥ 60% |
| NFR-02 | 可切换 | Runtime / Model 切换过程零中断、零记忆污染 |
| NFR-03 | 可复现 | 所有实验本地 Docker 运行，无需云端；种子 + 配置齐全时结果一致 |
| NFR-04 | 可观测 | 每次 Agent 运行产出结构化 log（JSONL）：task、plan、tool calls、token、耗时 |
| NFR-05 | 安全 | PreToolUse Hook 默认拒绝危险参数；worktree 隔离；不共享 API Key |
| NFR-06 | 合规 | API Key 自管，禁用订阅套利；香港网络下 Kimi 使用国际路由 |
| NFR-07 | 教学闭环 | 每阶段强制生成 artifact 并 wiki-ingest，否则 CI 视为阶段未完成 |
| NFR-08 | 文档自包含 | 所有关键文档（PRD / TRD / SPEC）不依赖外部链接可被大模型单独理解；外部资料必须标注明确 URL + 用途 |

---

## 9. 成功指标（量化 KPI）

### 9.1 里程碑级
- **Milestone 1（自研 Core + 编程插件 + MemoryBackend + 检验框架）**
  - M1-KPI-1：自研 Core 在 SWE-bench Verified 上 Resolved Rate ≥ Claude Agent SDK + Codex 基准的 85%。
  - M1-KPI-2：长程任务完成率 ≥ 80%（以 SWE-EVO 或自定义任务链为准）。
  - M1-KPI-3：每阶段教学 artifact 100% ingest 到 wiki。
- **Milestone 2（Kimi 接入与对齐）**
  - M2-KPI-1：自研 Core + Kimi 的 Resolved Rate 相对 M1 基准下降幅度 ≤ 5 个百分点。
  - M2-KPI-2：长程任务完成率 ≥ 75%。
  - M2-KPI-3a：Token 成本（执行口径）相对 Codex 基准下降 ≥ 60%。
  - M2-KPI-3b：端到端总成本（含执行+评测+Research）相对 M1 基准下降幅度达到验收目标（具体 X% 由 M1 baseline 设定）。
  - M2-KPI-4：Runtime / Model 热切换 100% 通过记忆一致性回归。

### 9.2 项目级
- 完成 ≥ 3 轮 Auto-Research 迭代，留存对 Resolved Rate 有显著正向贡献（统计显著 p<0.05）的 ≥ 2 项改动。
- AK-llm-wiki 节点 ≥ 200 个，graph 覆盖率（无孤立节点占比）≥ 95%。
- 教学 artifact：至少 1 份完整可公开的 `walkthrough.ipynb` 和 1 份完整的 12 层 Harness 走读报告。

---

## 10. 里程碑与教学环节

### Milestone 0（准备，1–2 周）
- **交付**：
  - 可运行的 Claude Agent SDK + Codex + Kimi base_url 测试环境。
  - `AgentRuntime` 接口原型 + 切换逻辑原型。
  - AK-llm-wiki 安装 + `wiki-import` 跑通一次。
  - SWE-bench Verified Docker Runner 搭好，能跑一个官方样例。
- **教学环节**：输出 `Runtime 切换原理 + Plugin/Memory 抽象设计 + 检验框架快速上手` 三份 Notebook，全部 ingest 到 wiki。

### Milestone 1（自研 Core + 切换 + 插件 + 记忆 + 检验，4–6 周）
- **交付**：
  - 并行开发自研 Agent Core（最小 ReAct + Plan + Compression + 验证链）。
  - 编程插件 + MemoryBackend（ingest-query-digest 全链路）。
  - Auto-Research 用 Codex 做 Evaluator（含切换对比实验）。
  - SWE-bench Verified 与自定义长程任务链集成到 Agent Core 的 CI。
- **教学环节**：每子阶段输出"本 harness / 插件 / 记忆为什么有效"+ 切换对比报告 + digest 示例，自动 ingest。
- **验收**：M1-KPI-1/2/3 全部达标。

### Milestone 2（Kimi 接入与对齐，3–5 周）
- **交付**：
  - 自研 Core 切换 Kimi Coding Plan + 插件 / 记忆压力测试。
  - Auto-Research 继续跑 Codex 评测，输出 Codex vs Kimi 对比报告。
  - Runtime 再次扩展：接入 OpenAI Agents SDK / Codex SDK 做三方对齐。
- **教学环节**：Codex vs Kimi 完整对比报告 + "模型切换后的 Harness 调整"教程 + "长程任务检验方法"教程。
- **验收**：M2-KPI-1/2/3/4 全部达标。

### 后续迭代（Milestone 3+）
- Milestone 1/2 模板交替执行，每轮新增插件 / 记忆 backend 测试。
- 每轮结束更新 wiki + 教学 artifact，形成复利。

---

## 11. 风险与开放问题（高层，细节见 RnD-Analysis.md）
- R-01：Kimi whitelist / User-Agent 校验可能挡掉 standalone CLI 调用 → 用自定义 headers 或 LiteLLM proxy 规避。
- R-02：自研 Core 初期能力不足以胜任调教任务 → 保留 Codex 作为 Teacher 长期兜底。
- R-03：长程任务评测方差大 → 用固定种子 + 多次取均值 + 统计显著性检验。
- R-04：记忆系统在任务量增长后检索质量衰退 → 启用 `wiki-lint` 定期清理 + 引入 qmd hybrid search。
- OP-01：是否在 M2 之后引入更多模型（GLM 4.7、MiniMax）作为备选执行层？决策点放在 M2 验收后。
- OP-02：教学 artifact 是否公开（GitHub 开源 / Blog）？默认先私有，在 ≥ 3 个 Milestone 完成后评估。

---

## 12. 学习资料与明确来源

以下是本项目所有外部知识来源，大模型在 query 时可根据主题直接取用；URL 在 grok-chat 里经作者 / Grok 交叉确认，未来若 404 请在 RnD-Analysis 更新。

| 主题 | URL | 用途 |
|---|---|---|
| Claude Agent SDK 官方文档 | https://code.claude.com/docs/en/agent-sdk/overview | 基础骨架与 Tool / Permission 机制 |
| Harness Engineering 12 层拆解（首选） | https://github.com/sanbuphy/learn-coding-agent | 自研 Harness 的蓝本 |
| Harness 工程风格教程 | https://github.com/walkinglabs/learn-harness-engineering | 官方风格 0→1 教程 |
| Harness 实用代码示例 | https://github.com/nexu-io/harness-engineering-guide | 代码级示例 |
| Harness Engineering 概念 | https://martinfowler.com/articles/harness-engineering.html | 概念 |
| Harness Engineering 实践 | https://humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents | 实践 |
| AK-llm-wiki | https://github.com/surebeli/AK-llm-wiki | 记忆系统默认实现 |
| Karpathy Auto-Research gist | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | Auto-Research 灵感原点 |
| Kimi Coding Plan | https://platform.moonshot.ai + `api.moonshot.ai/anthropic` | 执行模型来源（国际路由） |
| OpenAI Agents SDK / Codex SDK | https://openai.com/index/the-next-evolution-of-the-agents-sdk/ + https://developers.openai.com/codex/sdk | Runtime 横向对比 |
| Codex API 2026 Agentic Coding Trends | 查 Anthropic / OpenAI 2026 官方报告（RnD-Analysis 会给出具体链接） | 模型选型背景 |
| SWE-bench Verified | https://www.swebench.com/ + https://github.com/swe-bench/SWE-bench | 主基准（本地运行核心） |
| SWE-EVO | arXiv:2512.18470 | 长程扩展基准 |
| SlopCodeBench | 官方 GitHub（待 RnD-Analysis 锁定具体 repo） | 长程迭代任务基准 |
| 切换 / 插件实战 | https://composio.dev/content/claude-agents-sdk-vs-openai-agents-sdk-vs-google-adk | Runtime 对比案例 |
| Wiki vs RAG 对比 | https://mindstudio.ai/blog/llm-wiki-vs-rag-internal-codebase-memory | 记忆抽象设计依据 |
| LLM Wiki v2 扩展 | https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2 | Wiki 生命周期设计参考 |

> **学习闭环规则**：任何新的外部来源被引用到 PhoenixAgent 代码或文档中，都必须同步追加到本表，并通过 `wiki-ingest` 入库；禁止"隐式依赖"。

---

## 13. 文档配套与下一步

- 配套：TRD.md（分层架构 + 技术栈）、RnD-Analysis.md（可行性 + 风险 + 排期）、SPEC.md（模块接口契约）。
- 下一步：Fork 本 PRD 到 AK-llm-wiki → 执行 `wiki-import` + `digest`；运行 Milestone 0 环境搭建脚本；每阶段结束后重新 ingest 本文档更新版。

PhoenixAgent 项目启动，复利 + 检验闭环正式开启。

---

## 14. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；定义愿景、Milestone KPI、验收口径与外部知识来源。 |
