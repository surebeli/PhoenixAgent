# PhoenixAgent 技术需求文档 / 技术白皮书（TRD）

- 版本：v1.0
- 日期：2026-04-18
- 作者：dy
- 本文档是 PRD 的技术化表达，定义"如何实现 PRD 所定义的功能与非功能需求"。接口级契约见 SPEC.md；排期、风险、资源评估见 RnD-Analysis.md。

---

## 1. 架构总览

PhoenixAgent 采用**八层可插拔架构**，每层之间通过显式接口解耦，允许逐层替换、AB 对比、热切换。所有层通过一个 `PhoenixContext` 运行时对象共享 session、日志、指标与记忆引用。

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        Teaching Layer（教学层）                           │
│  每阶段自动生成 README/Notebook/实验报告 → wiki-ingest                    │
├───────────────────────────────────────────────────────────────────────────┤
│                     Evaluation Layer（检验层）                            │
│  SWE-bench Runner + SWE-EVO/SlopCodeBench + Codex Evaluator + Dashboard   │
├───────────────────────────────────────────────────────────────────────────┤
│                  Auto-Research Layer（自研究层）                          │
│  Generator(self) → Evaluator(Codex) → Keep/Discard GAN-style loop         │
├───────────────────────────────────────────────────────────────────────────┤
│          Harness Layer（12 层：Plan/Compression/Subagent/…）              │
│  验证链：validateInput → PreToolUse Hooks → checkPermissions → execute    │
├───────────────────────────────────────────────────────────────────────────┤
│  Plugin Layer（插件层）       │      Memory Layer（记忆层）               │
│  PluginRegistry + MCP         │  MemoryBackend（ingest/query/digest/…）   │
│  首插件：编程                 │  默认实现：AK-llm-wiki                    │
├───────────────────────────────┼───────────────────────────────────────────┤
│                        Model Layer（模型层）                              │
│  LiteLLM 统一路由；Codex（基准/评测） + Kimi（执行） + 本地模型           │
├───────────────────────────────────────────────────────────────────────────┤
│                        Runtime Layer（运行时层）                          │
│  AgentRuntime 接口：ClaudeSDK / PhoenixCore（自研）/ OpenAIAgentsSDK      │
└───────────────────────────────────────────────────────────────────────────┘
```

**设计原则（硬约束）**：
1. 每一层只暴露接口；上层调用必须经过抽象，禁止绕过。
2. Runtime 决定"怎么跑"；Model 决定"用谁跑"；Harness 决定"跑得稳不稳"；Plugin 决定"能跑什么场景"；Memory 决定"能记什么"；Evaluation 决定"跑得好不好"；Auto-Research 决定"怎么变更更好"；Teaching 决定"怎么沉淀"。
3. "永远不信任大模型输出"：所有 LLM 输出在变成副作用前必须经过 `validateInput + PreToolUse Hooks + checkPermissions + executeTool + mapToolResultToAPI` 的五步验证链。

---

## 2. Runtime Layer（运行时层）

### 2.1 目标
以统一接口封装任意 Agent 运行时的 ReAct 循环、工具调度、权限钩子与会话生命周期，让"切换 Runtime"成为一个启动参数。

### 2.2 技术选型
- 语言：Python 3.11+（Claude Agent SDK、OpenAI Agents SDK 皆原生支持，生态齐全）。
- 依赖：
  - `anthropic` / `claude-agent-sdk`（Claude 运行时）
  - `openai-agents-sdk` / `codex-sdk`（OpenAI 运行时，2026-04-15 已开放 sandbox + Codex-like filesystem tools）
  - 自研运行时不引入额外 SDK，仅使用 httpx + anthropic-compatible 封装。
- 模式：Strategy Pattern + Factory Pattern + Runtime Registry（依赖注入）。

### 2.3 关键接口（完整签名见 SPEC v1.1 §2）
```python
class AgentRuntime(Protocol):
    def start_session(cfg: RuntimeConfig) -> SessionHandle: ...
    def run_task(handle: SessionHandle, task: Task) -> TaskResult: ...
    def register_tool(tool: ToolSpec) -> None: ...
    def install_hook(event: HookEvent, fn: HookFn) -> None: ...
    def stream_events(handle: SessionHandle) -> Iterator[AgentEvent]: ...
    def stop_session(handle: SessionHandle) -> None: ...
```

### 2.4 关键技术决策
- **决策 D-RT-1**：启动时通过 `--runtime=claude|self|openai` 或 `PHOENIX_RUNTIME` 环境变量决定具体实现；默认 `claude`（M0），M1 切 `self`，M2 加 `openai`。
- **决策 D-RT-2**：Runtime 不承担任何业务记忆；Memory Layer 独立管理，Runtime 仅在 Hook 中读写 `PhoenixContext.memory`。
- **决策 D-RT-3**：自研 Core 不复制 SDK 的 Session 抽象，直接 `messages[] + tools[]` 数组 + 持久化到 SQLite；最小化理解成本。
- **决策 D-RT-4**：OpenAI Agents SDK 的 sandbox + filesystem tools 视为第三方参考实现，用于 AB 测试自研 Core 的正确性。

---

## 3. Model Layer（模型层）

### 3.1 目标
在"评测 / 调教"与"执行"之间显式区分模型角色；允许同一 Task 内部不同环节使用不同模型。

### 3.2 角色划分
| 角色 | 典型模型 | 使用场景 |
|---|---|---|
| **Base / Evaluator** | Codex API（OpenAI 2026 版） | 基准打分、Auto-Research Evaluator、Teacher |
| **Worker** | Kimi K2.5 Coding Plan | 规划后的具体执行、子代理 |
| **Fallback** | GLM 4.7 Coding Plan、本地 Ollama/LM Studio | Kimi 限流 / 合规问题时兜底 |
| **Cheap** | Grok-3-mini、Claude Haiku、Qwen2.5 | 上下文压缩、批量 digest |

### 3.3 技术选型
- 统一客户端：LiteLLM（或等价 wrapper），支持 Anthropic 兼容端点（`/v1/messages`）与 OpenAI 兼容端点。
- 关键环境变量：
  - `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`：覆盖任意 Anthropic 兼容端点（Kimi / 本地 / 代理）。
  - `OPENAI_API_KEY` + `OPENAI_BASE_URL`：Codex API 接入。
  - `PHOENIX_MODEL_PROFILE`：如 `codex-base`、`kimi-worker`、`local-ollama`，映射到 `~/.config/phoenix/models.toml`。

### 3.4 典型 Provider 配置

Codex：
```bash
export OPENAI_API_KEY=sk-xxx
export PHOENIX_MODEL_PROFILE=codex-base
```

Kimi（国际路由，香港友好）：
```bash
export ANTHROPIC_BASE_URL="https://api.moonshot.ai/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-kimi-xxx"
export PHOENIX_MODEL_PROFILE=kimi-worker
```

本地 Ollama：
```bash
export ANTHROPIC_BASE_URL="http://localhost:11434"
export ANTHROPIC_AUTH_TOKEN="ollama"
```

### 3.5 关键技术决策
- **决策 D-ML-1**：禁止 subprocess 隐式继承 API Key；子进程必须显式收到 `--model` / `--provider` 参数并读取自管 Key（合规硬约束）。
- **决策 D-ML-2**：模型路由以"Profile"为单位，而非以单一 `--model` 字符串，避免散落在多处的硬编码。
- **决策 D-ML-3**：Model Layer 不负责上下文压缩；上下文压缩由 Harness Layer 的 s06 机制统一处理，Model Layer 只负责"把 messages 发送到对应端点"。

### 3.6 合规与地域约束
- Kimi For Coding API 使用 User-Agent / whitelist 校验。默认用国际路由 `api.moonshot.ai/anthropic`，必要时伪装 User-Agent 为 `Claude-Code` 或挂 LiteLLM proxy；**禁止**订阅套利（共享 Pro/Max 订阅喂多代理 Swarm），会违反 Anthropic 2026 初 TOS。
- 香港网络：Kimi 国际路由通畅；Codex / Claude / 本地模型无地域限制。

---

## 4. Harness Layer（自研 12 层机制）

### 4.1 目标
把"平庸模型也能跑出高成功率"的 12 层工程机制固化为可按需叠加的模块化代码，每一层可独立开关用于 AB 实验。

### 4.2 12 层清单（与 PRD FR-03 同步）

| 编号 | 机制名 | 核心作用 | 对平庸模型的帮助 | 成本/成功率提升 |
|---|---|---|---|---|
| s01 | 主循环（THE LOOP） | 最小 ReAct (while-true) 骨架 | 基础 | — |
| s02 | 工具调度（TOOL DISPATCH） | 统一 Tool 接口 + executeTool | 标准化 | — |
| s03 | 规划（PLANNING） | 先 Plan 再 Execute，Todo Writer | 最显著：上下文稳定，成功率跳变 | 成功率 ★★★ |
| s04 | 子代理（SUB-AGENT） | 独立 messages[] 的子 Agent | 拆分复杂任务、避免污染 | 成本 ↓ |
| s05 | 技能（KNOWLEDGE） | Skill Tool 按需注入 system prompt | 节省 tokens | 成本 ↓ |
| s06 | 上下文压缩（COMPRESSION） | autoCompact / snipCompact / contextCollapse | 关键补救手段 | 成本 ↓↓ |
| s07 | 持久化（TASKS） | TaskCreate/Update + 状态持久 + 断点恢复 | 长任务可恢复 | 成功率 ★ |
| s08 | 后台任务（BACKGROUND） | DreamTask（后台思考）→ LocalShellTask | 避免主循环污染 | 成本 ↓ |
| s09 | 团队（TEAM） | TeamCreate + InProcessTeamCraftTask | 多代理协作 | 成功率 ★ |
| s10 | 协议（PROTOCOLS） | SendMessageTool 跨代理消息 | 可观测可审计 | — |
| s11 | 自主调度（AUTONOMOUS） | orchestrateMode（自主规划多代理） | Swarm 模式的终极上限 | 最复杂层 |
| s12 | 工作树隔离（WORKTREES） | EnterWorktree via git worktree | 安全隔离、回滚 | 安全性 ★★ |

### 4.3 强制验证链
每一次 Tool 调用必须按顺序通过：
```
validateInput()         # 静态参数检查：schema、危险值、路径黑名单
  ↓
PreToolUse Hook         # 用户可注入 shell 脚本；可 approve/deny/modify
  ↓
checkPermissions()      # alwaysAllow / alwaysDeny / alwaysAsk 三层规则
  ↓
executeTool()           # 实际执行（沙箱 / worktree 隔离）
  ↓
mapToolResultToAPI()    # 标准化为 provider 期望格式回塞
```
该链条是"永远不信任大模型输出"原则的工程体现，是自研 Core 的核心优势。

### 4.4 关键技术决策
- **决策 D-HR-1**：按 s01 → s02 → s03 + s06 → s07 → s04 → s09~s11 → s08 顺序推进；PRD §10 的里程碑与此顺序对齐。
- **决策 D-HR-2**：每层通过 `PhoenixContext.harness_flags` 运行时启停，便于 Auto-Research 的 AB 实验。
- **决策 D-HR-3**：所有 Hook 以 JSONL stdin/stdout 协议实现，与 Claude Code 的 Hook 兼容；用户已有的 Hook 脚本可直接迁移。

---

## 5. Plugin Layer（插件层）

### 5.1 目标
把"场景化能力"与"Agent 核心逻辑"完全解耦；编程是首个插件，后续研究 / 运维 / 文档均以同接口扩展。

### 5.2 技术选型
- 插件注册：本地 entry-point（setuptools）+ PluginRegistry 热加载（watchdog 监听插件目录）。
- 工具接口：MCP（Model Context Protocol）为第一公民；非 MCP 工具通过 `ToolSpec` 本地适配。
- 隔离：每个插件独立 Memory slice + 独立 `harness_flags` 覆盖默认值。

### 5.3 编程插件（首个插件）
必须包含的工具集（与 PRD FR-04 对齐）：
- `git-worktree`：创建 / 切换 / 清理 worktree。
- `multi-file-edit`：批量编辑，带 dry-run + 原子提交。
- `test-runner`：自动发现并运行 pytest / jest / go test，返回结构化结果。
- `harness-validator`：在执行前对即将运行的工具调用做 lint（典型反模式识别，如"无 plan 直接改代码"）。

### 5.4 关键技术决策
- **决策 D-PL-1**：不引入庞大的插件元框架；保持 PluginRegistry 为最小必要实现（register、lookup、reload）。
- **决策 D-PL-2**：插件版本号必须跟 `wiki-graph` 的节点版本对齐，方便未来 Auto-Research 追溯"哪个版本的插件产生了哪类改进"。
- **决策 D-PL-3**：插件不允许直接写全局 memory；必须通过 `MemoryBackend.digest()` 的 namespace 参数隔离。

---

## 6. Memory Layer（记忆层）

### 6.1 目标
强制实现"一次编译、复利工程"的记忆闭环：`ingest → query → digest → import → graph`。

### 6.2 接口契约（SPEC v1.1 §5 有完整签名）
```python
class MemoryBackend(Protocol):
    def ingest(source: IngestSource) -> IngestResult: ...
    def query(q: str, *, limit: int = 10) -> list[MemoryHit]: ...
    def digest(episode: Episode, *, namespace: str) -> DigestResult: ...
    def import_bulk(cfg: ImportConfig) -> ImportReport: ...
    def graph(*, scope: str | None = None) -> MemoryGraph: ...
    def lint(*, auto_fix: bool = False) -> LintReport: ...
    def tier(*, policy: TieringPolicy) -> TieringReport: ...
```

### 6.3 默认实现：AK-llm-wiki
- 仓库：https://github.com/surebeli/AK-llm-wiki
- 核心命令：`wiki-ingest`、`wiki-query`、`wiki-lint`、`wiki-graph`、`wiki-import`、`wiki-tier`。
- 特性：filesystem-based wiki、支持 Obsidian / Notion 批量导入、三层老化（active/archived/frozen）。
- 集成方式：通过 subprocess 调用命令，标准化结果为 `MemoryBackend` 返回值；未来可切换为原生库调用。

### 6.4 关键技术决策
- **决策 D-MM-1**：当前阶段接入 AK-llm-wiki；保留 `qmd` / `agentmemory` / `hybrid RAG+wiki` 的未来替换可能，接口不变。
- **决策 D-MM-2**：每一次 `run_task` 返回后，必须调用 `digest(episode)`；缺失则 CI 视为任务不完整。
- **决策 D-MM-3**：`wiki-lint` 作为每轮 Auto-Research 后置步骤，消除孤立节点与过期条目。
- **决策 D-MM-4**：查询入口始终通过 Memory Layer；**禁止**任何层直接读 wiki 文件，否则接口抽象会瓦解。

---

## 7. Evaluation Layer（检验层）

### 7.1 目标
用客观可复现的本地基准替代主观判断，驱动 Auto-Research 并产出 PRD KPI 数据。

### 7.2 技术栈
- 主基准：SWE-bench Verified，官方 Docker harness（`swebench.harness.run_evaluation`）。
  - 硬件要求：x86_64、120GB 磁盘、16GB+ RAM、8+ 核。
  - 推荐：epoch.ai 的 SWE-bench-docker 预构建镜像，1 小时跑完 Verified 子集。
- 长程扩展：SWE-EVO（arXiv:2512.18470）或 SlopCodeBench；这两个都是 2026 Q1 标准化的长程任务集。
- 自定义任务集：PhoenixAgent 自身维护的多文件重构 + 持久化任务链，放在 `evaluation/tasks/phoenix-custom/`。
- Evaluator：Codex API 作为 Teacher 打分（pass@1 + Resolved Rate + 长程指标）。

### 7.3 指标体系
- 执行质量：
  - Resolved Rate（主基准）
  - pass@1
  - Human Edit Distance
  - 补丁正确性
- 长程质量：
  - 多步完成率（completion rate over steps）
  - 错误恢复率
  - 任务持久性（中断后 resume 成功率）
  - 架构决策稳定性（跨 run 决策一致性）
- 成本：
  - Token 消耗（输入 / 输出 / 缓存命中）
  - $/Resolved
  - 每秒 token 吞吐

### 7.4 关键技术决策
- **决策 D-EV-1**：所有实验本地 Docker 运行，禁用云端（可复现性 + 成本）。
- **决策 D-EV-2**：每次 Auto-Research 迭代结束自动触发 Evaluation → 生成 `experiment-report.md` → `wiki-ingest`。
- **决策 D-EV-3**：`cache_level=env` 用于 SWE-bench Docker，加速多次迭代。
- **决策 D-EV-4**：Codex 作为唯一 Evaluator，保证打分一致性；绝不让被评测的自研 Core 给自己打分。

---

## 8. Auto-Research Layer（自研究层）

### 8.1 目标
建立 Generator-Evaluator GAN-style 循环，让自研 Agent 自动调教自身的 Harness / 插件 / 记忆 digest 规则。

### 8.2 循环流程
```
Generator（PhoenixCoreRuntime） 
  → 提出改动（patch: harness code / plugin / memory digest rule）
    → 应用到代码 fork 分支
      → Evaluator（Codex）跑 SWE-bench Verified 子集 + 自定义长程任务
        → 与上一轮基线比较 Resolved Rate / Completion Rate / Token Cost
          → Keep/Discard（p<0.05 统计显著才 Keep）
            → wiki-ingest experiment-report.md → 进入下一轮
```

### 8.3 参数
- 每代 5–15 次迭代；迭代数由上一轮收益决定（收益递减则提前终止）。
- 变更范围硬限制：`harness/*` + `plugins/*` + `memory/digest_rules/*`；禁止修改 Model Layer 和 Runtime Layer。
- 每次迭代使用固定随机种子；多次跑均值化以压低方差。

### 8.4 可行性证据
- Karpathy gist 与 Auto Agent 项目已经在社区验证此模式；PhoenixAgent 只需把它接到自研 Core + SWE-bench Docker 上即可。

### 8.5 关键技术决策
- **决策 D-AR-1**：Generator / Evaluator 使用不同模型（Generator: self 或 Kimi；Evaluator: Codex），避免自评偏差。
- **决策 D-AR-2**：每轮产出的 patch 用 git branch 管理，便于回滚与审计。
- **决策 D-AR-3**：Playwright MCP（或等价的浏览器工具）作为可选子工具，用于需要"真实执行验证"的任务。

---

## 9. Teaching Layer（教学层）

### 9.1 目标
让每个开发阶段自动沉淀为"可教学 + 可复利"的知识资产，避免一次性消耗的隐形工作。

### 9.2 artifact 规范
- `README-teaching.md`：回答"本阶段 Harness / 插件 / 记忆为什么有效"。
- `walkthrough.ipynb`：Jupyter 或 Claude Code 风格的 Notebook，代码走读 + 可复现实验。
- `experiment-report.md`：前后对比 + token 消耗 + 成功率，附原始 JSONL 日志路径。

### 9.3 自动化
- `phoenix teach build --milestone=M1.2` 命令自动收集当前阶段数据，生成三种 artifact。
- artifact 生成后**强制**调用 `MemoryBackend.ingest()`，入库失败则 CI 红。
- 每个 artifact 在生成时写入 front matter：`stage`, `milestone`, `date`, `related_nodes`。

### 9.4 关键技术决策
- **决策 D-TL-1**：教学 artifact 生成不依赖外部服务（非纯本地的依赖，如 Claude Code UI，需明确标注）。
- **决策 D-TL-2**：artifact 不引入额外元数据格式；直接用 markdown front matter + jupyter notebook。
- **决策 D-TL-3**：长期目标是让任何新增代码必须伴随 artifact；Milestone 1 结束前先半强制（CI 警告），Milestone 2 后强制（CI 失败）。

---

## 10. 统一上下文对象 `PhoenixContext`

```python
@dataclass
class PhoenixContext:
    session_id: str
    runtime: AgentRuntime
    model_profile: ModelProfile
    memory: MemoryBackend
    plugins: PluginRegistry
    harness_flags: HarnessFlags          # 12 层机制启停
    evaluation: EvaluationRunner | None  # 只在 benchmark 模式下注入
    teaching: TeachingEmitter | None     # 只在 teach 模式下注入
    logger: StructuredLogger
    metrics: MetricsSink
```

所有层通过 `PhoenixContext` 相互协作；**禁止**任何模块直接 import 其他层的具体实现（依赖必须走抽象接口）。

---

## 11. 技术栈与依赖矩阵

| 类别 | 选型 | 依据 |
|---|---|---|
| 编程语言 | Python 3.11+ | Claude Agent SDK、OpenAI Agents SDK 原生；LiteLLM / Anthropic SDK 生态完整 |
| Runtime SDK | `claude-agent-sdk`（M0）、`openai-agents-sdk` / `codex-sdk`（M1+） | 官方支持、功能完备 |
| LLM 客户端 | LiteLLM（统一路由）+ `anthropic`、`openai` | 多 provider 路由成熟；Anthropic 兼容端点覆盖 Kimi / 本地 |
| 记忆 | AK-llm-wiki（文件系统 wiki）+ 未来 qmd / hybrid RAG | 原生匹配"一次编译、复利工程" |
| 插件 & MCP | MCP 标准 + 本地 entry-point | 2026 MCP 已成为事实标准 |
| 存储 | SQLite（session、任务状态）、JSONL（日志）、git（代码 & worktree） | 零依赖、可复制；SQLite 足以支持单机研发 |
| 评测 | SWE-bench Docker harness、SWE-EVO、SlopCodeBench | 本地完整容器化 |
| CI 与教学产物 | Jupyter + nbconvert + pre-commit | 与 Claude Code 风格兼容 |
| 可选本地模型 | Ollama、LM Studio、vLLM | 零地域限制；兼容 Anthropic `/v1/messages` |
| 代理（视情况） | LiteLLM Proxy / CLIProxyAPI | 绕开 Kimi whitelist 的备用手段 |

**禁止引入**：任何需要云端状态、只能在特定商业 SaaS 上跑的组件；任何会让合规风险变差的订阅套利工具。

---

## 12. 部署与运行环境

- 操作系统：Linux x86_64（Docker 友好），或 Windows + WSL2（作者当前环境 Windows 11，SWE-bench 运行走 WSL2 / 本地 Docker Desktop）。
- 硬件：≥ 16GB RAM，≥ 120GB 可用磁盘（SWE-bench 镜像大），GPU 非必需（本地模型可选）。
- 网络：香港直连 Codex / Kimi 国际路由 / GitHub / Hugging Face 均正常，无需额外 proxy；境内用户建议走 Kimi 新加坡路由。
- API Key 管理：`~/.config/phoenix/keys.env`，权限 `0600`；严禁 commit 到 git。

---

## 13. 安全与合规要求

| 编号 | 要求 | 实现 |
|---|---|---|
| SEC-01 | 所有工具执行前必经 5 步验证链 | Harness Layer 硬编码 |
| SEC-02 | 代码改动必须在 git worktree 内（s12） | 编程插件 `git-worktree` 工具 |
| SEC-03 | 不共享 API Key / 不继承到 subprocess | Model Layer D-ML-1 |
| SEC-04 | Kimi / Claude / Codex 使用必须符合各自 2026 TOS | 文档 + PreToolUse Hook 注释（禁止订阅套利） |
| SEC-05 | 教学 artifact 发布前需人工 review（避免泄露 API key / 个人信息） | `phoenix teach publish` 前置检查脚本 |
| SEC-06 | 日志脱敏 | StructuredLogger 自动 mask 常见 secret pattern |

---

## 14. 可行性技术证据（回答 PRD "方案是否可行"）

| 组件 | 成熟度 | 证据 |
|---|---|---|
| Claude Agent SDK | 生产可用 | 官方 docs + 多个社区项目 |
| OpenAI Agents SDK / Codex SDK | 2026-04-15 更新后已具备 sandbox + Codex-like filesystem tools | OpenAI 官方博客、Composio 对比报告 |
| Kimi K2.5 Coding Plan | 社区广泛使用，香港国际路由稳定 | Moonshot 官方 + 大量用户反馈 |
| AK-llm-wiki | 原生支持 Claude Code / Codex Plugin + bulk import | repo README + Karpathy 原概念 |
| SWE-bench Verified 本地 Docker | 官方完整容器化；1 小时跑完 Verified 子集 | epoch.ai SWE-bench-docker |
| Auto-Research 循环 | Karpathy 原型 + Auto Agent 项目已验证 | Karpathy gist + 社区实现 |

**结论**：八层中没有任何一层需要基础研究突破；所有层已有开源或官方成熟实现，工作集中在"集成 + 抽象 + 可切换 + 教学闭环"。可行性 ≥ 95%。

---

## 15. 技术风险与缓解（高层摘要，细节见 RnD-Analysis §4）

| 风险 | 影响面 | 缓解 |
|---|---|---|
| Kimi whitelist 挡掉自研 CLI | Model Layer / Runtime Layer | 自定义 User-Agent；LiteLLM Proxy；Moonshot 标准 API 兜底 |
| 自研 Core 初期短板 | Harness Layer | 保留 Codex 作为 Teacher；Runtime Registry 允许降级 |
| SWE-bench Docker 依赖重 | Evaluation Layer | 预构建镜像 + 缓存 + 子集评测 |
| 记忆系统检索衰退 | Memory Layer | `wiki-lint` 定期；hybrid search 后备 |
| Auto-Research 噪声大 | Auto-Research Layer | 多种子 + 统计显著性；patch 分支可回滚 |
| 教学 artifact 成为负担 | Teaching Layer | M1 半强制（warn），M2 强制（fail），避免一次性压垮开发节奏 |

---

## 16. 命令行接口预览（与 PRD 场景对齐）

```bash
# Milestone 0 环境验收
phoenix doctor

# 常规执行
phoenix run --task "重构模块 X" --runtime=self --model=kimi

# 持久化任务恢复
phoenix execute --plan-id abc123
phoenix status

# Benchmark
phoenix eval --benchmark=swe-bench-verified --runtime=self --model=codex
phoenix eval --benchmark=swe-bench-verified --runtime=self --model=kimi
phoenix eval --benchmark=swe-evo --runtime=self

# Auto-Research
phoenix research --rounds=10 --benchmark=swe-bench-verified

# 教学产物
phoenix teach build --milestone=M1.2
phoenix teach publish --dry-run
```

---

## 17. 与 PRD 的对应表

| PRD 编号 | TRD 章节 | SPEC 章节 |
|---|---|---|
| FR-01 AgentRuntime | §2 | SPEC v1.1 §2 |
| FR-02 Model Routing | §3 | SPEC v1.1 §4 |
| FR-03 12 层 Harness | §4 | SPEC v1.1 §5 |
| FR-04 Plugin | §5 | SPEC v1.1 §3 |
| FR-05 Memory | §6 | SPEC v1.1 §6 |
| FR-06 Evaluation | §7 | SPEC v1.1 §7 |
| FR-07 Auto-Research | §8 | SPEC v1.1 §8 |
| FR-08 Teaching | §9 | SPEC v1.1 §9 |

---

## 18. 下一步

1. 基于 TRD 锁定 SPEC.md 中每个接口的最小实现。
2. Milestone 0 `phoenix doctor` 脚本可立即开工：校验 Python 版本、Docker、LiteLLM、Anthropic / OpenAI 可达性、AK-llm-wiki 路径、SWE-bench 镜像。
3. 所有决策（D-RT / D-ML / D-HR / D-PL / D-MM / D-EV / D-AR / D-TL）作为开发过程中的不可降级约束；若需修改，必须先更新 TRD 并重新 `wiki-ingest`。


---

## 19. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；定义八层架构、关键决策、接口对应表与实现路径。 |
