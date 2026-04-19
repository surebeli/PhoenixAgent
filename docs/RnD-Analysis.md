# PhoenixAgent 研发分析（RnD-Analysis）

- 版本：v1.0
- 日期：2026-04-18
- 作者：dy
- 关联：PRD.md、TRD.md、SPEC.md

本文档回答三件事：
1. **可行吗**：八层架构在 2026-04 的技术栈与作者所处环境下是否可落地。
2. **风险在哪**：按层列出风险 × 概率 × 影响 × 缓解。
3. **如何排期**：资源、能力缺口、里程碑里"每天做什么"的可操作粒度，以及教学环节具体落地点。

---

## 1. 总体可行性结论

**结论：高可行，整体成功概率 ≥ 95%。** 主要依据：

| 维度 | 结论 | 关键依据 |
|---|---|---|
| 技术成熟度 | 所有层有开源或官方成熟实现 | TRD §14 证据表 |
| 地域可达性 | 香港直连 Codex / Kimi 国际路由 / GitHub / Docker Hub 正常 | Kimi Moonshot `api.moonshot.ai/anthropic` 国际路由、Codex `api.openai.com`、OpenAI Agents SDK 2026-04-15 更新 |
| 硬件门槛 | SWE-bench Verified 本地运行硬件要求合理（120GB 磁盘、16GB RAM、8 核） | epoch.ai 预构建 Docker 镜像 1h 跑完 Verified 子集 |
| 合规 | API Key 自管 + 禁用订阅套利 + User-Agent 可按需 | Kimi / Anthropic 2026 TOS 可满足 |
| 成本 | Kimi Coding Plan \$10–\$50/月；Codex 按 token 计费（用于评测为主） | 预算在"个人研发"可承受范围 |
| 学习曲线 | 作者已有 Claude Agent SDK 基础；12 层 Harness 有完整开源教程 | sanbuphy/learn-coding-agent + walkinglabs/learn-harness-engineering |

**主要不确定性**（不是否决因素，但需要在 M0 前明确）：
- U-01：Kimi whitelist 策略是否仍兼容自研 CLI（社区普遍验证可行，但作者需在 M0 亲验）。
- U-02：SWE-bench Verified 在作者 Windows + WSL2 / Docker Desktop 环境下的跑通速度。
- U-03：AK-llm-wiki 在 ≥ 200 节点规模下 query 延迟是否仍可接受。

---

## 2. 关键外部依赖审计

每一项都必须在 M0 完成可达性 + 可替换性评估。

| 依赖 | 作用 | 当前状态 | 替换方案（若失败） | 在 PhoenixAgent 中的位置 |
|---|---|---|---|---|
| Claude Agent SDK | M0 起始 Runtime | 官方稳定 | 自研 Core 已规划 | Runtime Layer |
| OpenAI Agents SDK / Codex SDK | 第三方对齐 Runtime | 2026-04-15 更新后生产可用 | 跳过或换 Anthropic SDK 走 Anthropic-compatible | Runtime Layer |
| Codex API | 基准评测 / Auto-Research Evaluator | 官方稳定 | Claude 4.5 Sonnet 作为次选 Evaluator | Model Layer / Auto-Research |
| Kimi K2.5 Coding Plan | 执行主力模型 | 香港国际路由稳定 | GLM 4.7 Coding Plan 备选 | Model Layer |
| LiteLLM | 多 Provider 路由 | 成熟开源 | 自写 wrapper（成本有限） | Model Layer |
| MCP（Model Context Protocol） | 插件工具接口 | 2026 已成事实标准 | 本地 entry-point 兜底 | Plugin Layer |
| AK-llm-wiki | 记忆默认实现 | 作者 fork，社区活跃 | qmd / agentmemory / 自写最小 wiki | Memory Layer |
| SWE-bench Verified 官方 harness | 主基准 | 官方 Docker 容器化 | epoch.ai 预构建镜像 | Evaluation Layer |
| SWE-EVO / SlopCodeBench | 长程扩展基准 | 均为 2026 Q1 开源 | 自建多文件重构任务集 | Evaluation Layer |
| Karpathy Auto-Research gist | Auto-Research 灵感原点 | 社区多个复刻 | 自行实现 Generator-Evaluator 循环 | Auto-Research Layer |
| Docker Desktop / WSL2 | 本地 Docker 运行 SWE-bench | Windows 11 支持 | 纯 Linux 主机 | Evaluation Layer |
| sanbuphy/learn-coding-agent | 12 层 Harness 教学蓝本 | 开源活跃 | walkinglabs/learn-harness-engineering | Harness Layer |

---

## 3. 能力缺口与学习曲线

### 3.1 作者当前能力自评（基于 grok-chat 的上下文）
- **已具备**：Claude Agent SDK 使用、Kimi / Codex 接入、Python 工程、对 Harness Engineering 概念清晰、AK-llm-wiki 作为记忆方案的掌控。
- **薄弱项**：12 层中 s08–s11（后台任务 / 团队协作 / 自主调度）的生产化实现经验；MCP 自定义工具的完整生命周期；SWE-bench 官方 harness 的具体运行细节；Auto-Research 的超参调试经验。
- **未知项**：自研 Agent Core 在生产级编码任务上能否稳定 ≥ Claude Agent SDK + Codex 85%（M1-KPI-1 的风险点）。

### 3.2 针对性学习路径（教学环节落地）

| 里程碑 | 必读资料 | 预期掌握点 | 产出教学 artifact |
|---|---|---|---|
| M0 | Claude Agent SDK 官方 docs、LiteLLM README、AK-llm-wiki README、SWE-bench Setup Guide | SDK + LiteLLM 路由 + wiki 基本操作 + Docker harness 能跑 | `M0-walkthrough.ipynb`、`M0-evaluation-setup.md` |
| M1 前半 | sanbuphy/learn-coding-agent（12 层拆解）、walkinglabs/learn-harness-engineering 第 1–6 章 | s01–s06 实现 + 验证链实现 | `M1a-harness-principles.ipynb`、`M1a-validation-chain.md` |
| M1 后半 | sanbuphy 第 7–12 章、Karpathy Auto-Research gist、SWE-EVO 论文 | s07–s12 + Auto-Research 循环闭合 | `M1b-autoresearch-lab.ipynb`、`M1b-longhorizon-eval.md` |
| M2 | Moonshot Kimi 文档 + Composio 对比报告 + OpenAI Agents SDK 文档 | 多 Runtime 对齐 + Kimi 压测 + 性价比结论 | `M2-codex-vs-kimi-report.md`、`M2-runtime-switch.ipynb` |

### 3.3 学习方法硬约束
- 每一份必读资料在消化后必须通过 `wiki-ingest` 入库并写简短笔记节点（≥ 100 字）。
- 每个 Milestone 结束，用 `wiki-query` 自测若干问题（例如"Plan Mode 为什么提高成功率 2–3x？"），答不出的要补读。
- 禁止"光看不做"：每个机制必须在 PhoenixAgent 里跑一个最小实验。

---

## 4. 风险矩阵（层级 × 风险 × 概率 × 影响 × 缓解）

概率 / 影响：L=低、M=中、H=高。

### 4.1 Runtime Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-RT-1 | 自研 Core 初期 Resolved Rate 不达 85% | M | H | 保留 Claude SDK Runtime 作为 Teacher；M1 前置 4 周专项调教 |
| R-RT-2 | OpenAI Agents SDK 接入超预期复杂 | L | M | M2 再接入；如超预期直接跳过，不卡里程碑 |
| R-RT-3 | Runtime 切换时会话 / 记忆不一致 | M | M | 在 `PhoenixContext` 层统一管理 session + memory；切换必走清洗 |

### 4.2 Model Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-ML-1 | Kimi whitelist 挡掉自研 CLI | M | M | 自定义 User-Agent；LiteLLM Proxy；Moonshot 标准 API（非 Coding 专用）兜底 |
| R-ML-2 | Codex 成本超预算 | L | M | 仅用于评测与 Auto-Research Evaluator；单轮评测预算上限硬编码 |
| R-ML-3 | 本地模型在编码任务上能力不足 | H | L | 仅用于子任务压缩 / 非关键步骤；主力仍是 Kimi |
| R-ML-4 | 地域 / 合规问题（香港之外的读者） | L | L | 文档标注"Kimi 中国大陆用户走 `api.moonshot.cn`" |

### 4.3 Harness Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-HR-1 | 12 层全部自研耗时过长 | M | M | 按 PRD §10 顺序叠加；每层独立 AB 实验；s08–s11 M2 后补齐即可 |
| R-HR-2 | 验证链过严导致吞吐低 | M | M | Hook 性能预算 < 50ms；可关闭 `alwaysAsk` 用于 benchmark |
| R-HR-3 | Hook 脚本注入带来 shell 安全问题 | L | H | Hook 必须来自本地受控目录；`PreToolUse Hook` 配置项支持只读模式 |

### 4.4 Plugin Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-PL-1 | 编程插件 4 个工具实现超预期 | M | L | 复用 `git`、`pytest`、`ruff`、`jq` 等现成 CLI，最小包装 |
| R-PL-2 | MCP 协议版本变动 | L | L | 锁定 MCP 2026-Q1 版本；抽象适配层吸收变动 |

### 4.5 Memory Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-MM-1 | 节点 ≥ 200 后 query 延迟高 | M | M | 启用 qmd / hybrid RAG 备选；`wiki-tier` 定期老化 |
| R-MM-2 | AK-llm-wiki API 不稳定（早期项目） | M | M | 抽象 `MemoryBackend` 接口；代码中禁止直接依赖 wiki 具体 CLI |
| R-MM-3 | digest 规则过拟合导致历史冲突 | M | M | 每轮跑 `wiki-lint` + Auto-Research 只调 digest 规则不改 schema |

### 4.6 Evaluation Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-EV-1 | SWE-bench Docker 在 Windows + WSL2 跑不动或极慢 | M | H | 使用 epoch.ai 预构建镜像 + 只跑 Verified 子集（50–100 个）+ `cache_level=env` |
| R-EV-2 | SWE-EVO / SlopCodeBench 任务偏离 PhoenixAgent 目标 | L | M | 用自定义任务集补齐 |
| R-EV-3 | Evaluator 打分不稳定 | M | M | 固定 prompt + 固定 seed + 多次平均 + pass@1 主指标 |
| R-EV-4 | runtime-parity 差异过大难判定是能力差异还是 bug | M | M | 隔离能力差异 vs bug：`capability_profile` 表显式标注 tool/格式支持差异；差异归因优先查 Harness 日志与 ToolSpec 校验；必要时对齐 prompt/温度/max_tokens 后重跑 |

### 4.7 Auto-Research Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-AR-1 | 迭代改动相互冲突 | M | M | 每次迭代走独立 git branch；`harness-validator` 插件检测反模式 |
| R-AR-2 | 长期收益递减但迭代消耗累积 | H | M | 收益 3 轮无显著正向则自动终止；Milestone 级人工 review |
| R-AR-3 | Evaluator 被 Prompt Injection | L | H | Evaluator prompt 隔离；禁止把用户任务直接喂给 Evaluator |

### 4.8 Teaching Layer
| 编号 | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R-TL-1 | artifact 成本拖慢开发节奏 | M | M | M1 半强制（warn），M2 强制（fail），允许合并小阶段 |
| R-TL-2 | artifact 质量参差，未来复利失效 | M | H | 每阶段 artifact 有模板 + review checklist；定期 `wiki-lint` |

---

## 5. 资源评估

### 5.1 人力 / 时间
- 执行者：作者 dy（假定每周可投入 15–20 小时）。
- M0：1–2 周（20–40h）。
- M1：4–6 周（80–120h）。
- M2：3–5 周（60–100h）。
- 总计 8–13 周（160–260h）到 M2 完成。

### 5.2 硬件
- 开发机：Windows 11 + WSL2 + Docker Desktop，≥ 32GB RAM、≥ 500GB SSD（当前环境符合）。
- 评估阶段推荐额外预留 ≥ 150GB 磁盘给 SWE-bench 镜像与缓存。
- GPU 非必需；若跑本地模型（Ollama / vLLM）建议 ≥ 24GB 显存，但属于可选路径。

### 5.3 成本估算（月度，保守）
| 项目 | 预估 | 说明 |
|---|---|---|
| Codex API（评测 + Auto-Research Evaluator） | \$30–\$80 / 月 | 单轮 Verified 子集评测控制在 \$2–\$5 |
| Kimi Coding Plan | \$10–\$50 / 月 | 执行主力 |
| GLM 4.7 Coding Plan（备选） | \$3–\$50 / 月 | 仅在 Kimi 不可用时启用 |
| Claude API（保留用于 Runtime 对比） | \$10–\$30 / 月 | 保留 Claude Agent SDK 对比 |
| 其他（域名 / 仓库托管 / ≤ 负载） | ≤ \$10 / 月 | 可选 |
| **合计** | **\$40–\$200 / 月** | 与 PRD NFR-01 的降本目标一致 |

### 5.4 软件 / SaaS
- 必须：GitHub、Docker Hub、Anthropic、OpenAI、Moonshot（Kimi）。
- 可选：Z.ai（GLM）、Obsidian（wiki 预览）、Playwright MCP（浏览器验证）。

---

## 6. 里程碑分解（按天 / 按任务）

每个里程碑下给出"关键任务 + 验收条件 + 教学产物"。所有任务必须进入 `phoenix tasks`（s07 持久化）跟踪。

### 6.1 Milestone 0（准备，1–2 周 / 20–40h）
**目标**：跑通所有依赖，确立最小 `AgentRuntime` 抽象与基线评测环境。

关键任务：
- M0-T1：环境 `phoenix doctor` 脚本：Python / Docker / LiteLLM / Anthropic / OpenAI / Kimi 可达性检查。
- M0-T2：Claude Agent SDK 跑通 Hello Task；同任务用 Codex API 直接跑一次。
- M0-T3：`AgentRuntime` 接口原型 + `ClaudeAgentSDKRuntime` 最小实现；`--runtime=claude` 命令可用。
- M0-T4：AK-llm-wiki 安装 + `wiki-import` 把本 PRD / TRD / RnD / SPEC 导入；`wiki-query` 可召回。
- M0-T5：SWE-bench Verified 官方 Docker harness 跑通 1 个任务；记录硬件 / 时间。
- M0-T6：输出 `M0-walkthrough.ipynb` + `M0-evaluation-setup.md`，`wiki-ingest` 入库。

验收条件：
- ✅ `phoenix run --task "hello" --runtime=claude` 返回结构化结果。
- ✅ 一次 `wiki-query "PhoenixAgent 愿景"` 命中本 PRD §2。
- ✅ SWE-bench Verified 完成 ≥ 1 个任务的全流程（Docker 拉取 / 评测 / 报告）。
- ✅ 两份教学 artifact 在 wiki 内可检索。

### 6.2 Milestone 1（自研 Core + 切换 + 插件 + 记忆 + 检验，4–6 周 / 80–120h）
**目标**：自研 `PhoenixCoreRuntime` 达到 ≥ Claude Agent SDK + Codex 基准的 85% Resolved Rate；编程插件完整；MemoryBackend 闭环；检验框架集成。

关键任务：
- M1-T1：实现 `PhoenixCoreRuntime` 最小 ReAct（s01 + s02）。
- M1-T2：s03 规划模式 + s06 压缩叠加；对比开启前后 Resolved Rate。
- M1-T3：验证链 5 步（`validateInput → Hook → Permissions → execute → mapResult`）。
- M1-T4：`PluginRegistry` + 编程插件（`git-worktree`、`multi-file-edit`、`test-runner`、`harness-validator`）。
- M1-T5：`MemoryBackend` 接口 + AK-llm-wiki 适配实现；ingest / query / digest 闭环。
- M1-T6：Evaluation Runner：SWE-bench Docker 集成 + Codex Evaluator 自动打分。
- M1-T7：s07 持久化任务 + s04 子代理；长程任务集 ≥ 5 个。
- M1-T8：Auto-Research 循环 v1：Generator = self，Evaluator = Codex，3–5 轮。
- M1-T9：每子阶段输出教学 artifact（≥ 6 份）。

验收条件：
- ✅ M1-KPI-1 达标：Resolved Rate ≥ Claude Agent SDK + Codex 的 85%。
- ✅ M1-KPI-2 达标：长程任务完成率 ≥ 80%。
- ✅ 3 轮 Auto-Research 至少保留 2 项显著正向变更。
- ✅ 所有教学 artifact 全部 `wiki-ingest`。

### 6.3 Milestone 2（Kimi 接入与对齐，3–5 周 / 60–100h）
**目标**：把自研 Core 的执行主力切换到 Kimi，同时验证 token 成本 ≥ 60% 下降且准确率只掉 ≤ 5 个百分点。加接 OpenAI Agents SDK 做三方对齐。

关键任务：
- M2-T1：Model Profile 配置 `kimi-worker`；Runtime 内显式传递 `--model` / `--provider`。
- M2-T2：基于 Kimi 跑 SWE-bench Verified，与 M1 Codex 基线对比。
- M2-T3：长程任务压力测试（≥ 10 个任务，每个 ≥ 5 步）。
- M2-T4：`OpenAIAgentsRuntime` 接入；同任务集 AB。
- M2-T5：Runtime / Model 热切换回归（记忆一致性测试）。
- M2-T6：s08 后台任务 + s09–s11 团队协作初版（可选延后）。
- M2-T7：输出 Codex vs Kimi 完整对比报告 + Runtime 切换教程。

验收条件：
- ✅ M2-KPI-1：准确率下降 ≤ 5 个百分点。
- ✅ M2-KPI-2：长程任务完成率 ≥ 75%。
- ✅ M2-KPI-3：Token 成本 ≥ 60% 下降。
- ✅ M2-KPI-4：热切换回归通过。

### 6.4 Milestone 3+
- 每 2–4 周一轮小 Milestone，每轮至少一个新增（插件 / Memory Backend / 基准任务）。
- 每轮 Auto-Research ≥ 5 轮；KPI 必须量化入 `experiment-report.md`。

---

## 7. 教学环节落地建议（回应作者原始需求 §3）

1. **固化为 Git Hook**：pre-push 检查当前分支是否有 `docs/teaching/` 下对应 Milestone 的 artifact，否则阻止推送。
2. **Template 化**：`tools/teaching-templates/` 目录存放 `README-teaching.md`、`walkthrough.ipynb`、`experiment-report.md` 三个模板，`phoenix teach build` 自动填充元数据。
3. **wiki 双向链接**：artifact 生成时自动插入"关联节点"段，链接到 wiki 中相应 concept node；反向在 wiki 节点末尾记录"被哪些 artifact 引用"。
4. **定期反思 Notebook**：每 4 周一次 `reflection-${yyyy-mm}.ipynb`，强制包含：
   - Resolved Rate / Completion Rate / Token Cost 曲线。
   - 本月 Auto-Research 保留的变更列表。
   - 失败实验的反思（≥ 3 条）。
5. **公开化的评估点**：Milestone 结束后评估是否把 artifact 以脱敏版发布（Blog / GitHub / AK-llm-wiki 公开分支），但不做硬性要求。

---

## 8. 评估方案本地可行性专项分析

作者 grok-chat v0.3 末尾新增的补充需求 1：**SWE 这类测试在本地是否可行**。

### 8.1 结论：可行。

### 8.2 详细论证

SWE-bench Verified 官方已完全容器化（`swebench.harness.run_evaluation`），典型流程：
1. 拉取 500 个 Verified 任务实例（一次性，总大小约 80–100GB）。
2. 对每个 instance 启动一个包含 repo + issue 状态的 Docker 容器。
3. 运行目标 Agent 生成的 patch → 在容器内跑测试。
4. 汇总 Resolved Rate / pass@1 等指标。

硬件门槛（根据 2026 Q1 官方 Setup Guide）：
- x86_64、16GB+ RAM、8+ 核、120GB+ 磁盘。
- 作者 Windows 11 开发机符合（走 WSL2 + Docker Desktop）。

加速策略：
- **使用 epoch.ai 预构建镜像**：避免首次本地构建镜像耗时 2–4h；预构建后 1h 内跑完 Verified 子集（100 个）。
- **Verified 子集评测**：日常迭代只跑 50–100 个任务，Milestone 级再跑全量 500 个。
- **`cache_level=env`**：复用 conda 环境，降低重复构建耗时。

长程任务补充：
- SWE-EVO（arXiv:2512.18470）：多 commit 软件演化任务，数据集本地可跑；自建 harness 将任务抽象为"多个 SWE-bench-like instance 串联"。
- SlopCodeBench：迭代扩展任务集，更贴近 PhoenixAgent 的持久化任务场景。
- 自定义任务集：由 PhoenixAgent 自身产生（多文件重构 + 长持久化任务），兼职测试 s07 持久化和 s12 worktree。

**组合使用方案**：
- 日常迭代（每 PR / 每轮 Auto-Research）：Verified 子集 50 个（30–45min）。
- Milestone 验收：Verified 全量 500 个（≤ 4h）+ SWE-EVO 子集 + 自定义任务 ≥ 10 个。
- 长程检验（Kimi 压力测试）：SlopCodeBench 迭代任务 ≥ 5 个 × ≥ 10 步。

### 8.3 风险与兜底
- 风险 R-EV-1（WSL2 性能）：已在缓解方案中；若依旧过慢，可在纯 Linux 云机（按小时租用，例如 Hetzner CAX41）上搭并发 Runner。
- 风险 R-EV-2（SWE-EVO 不匹配 PhoenixAgent 目标）：用自定义任务兜底；SWE-EVO 作为参考值。
- 风险 R-EV-3（Evaluator 稳定性）：见风险表 R-AR-3 / R-EV-3，靠多 seed + pass@1 + 固定 prompt 缓解。

---

## 9. 里程碑之间的复盘与调整点

每个 Milestone 结束必须做三件事：
1. **量化回顾**：读取 `experiment-report.md` 最近 N 份，输出 KPI 曲线。
2. **风险重估**：按本文 §4 风险矩阵重打分；若有新风险升 H 则触发方案变更。
3. **下一阶段 PRD / TRD 更新**：若目标、范围或依赖出现重要变化，回写 PRD / TRD 并 `wiki-ingest`，版本号 +1。

---

## 10. 开发哲学硬约束（可操作的执行准则）

- **工程纪律 > 模型能力**：先保证 Harness 与验证链完备，再追求模型升级。
- **数据驱动改进**：凡是在聊天里的"觉得变好了"必须在下一轮通过基准量化，否则回滚。
- **一次编译 · 复利工程**：每一次手动学习 / 解决问题后必须固化为 wiki 节点或教学 artifact；否则不算完成。
- **显式胜过隐式**：Runtime / Model / Plugin / Memory Backend 的选择始终显式；拒绝全局单例与默认隐藏行为。
- **减法优先**：先叠加最小必要层，再引入增强层；M0 禁止叠加 s04–s12。

---

## 11. 开放问题（需作者在 M0 结束前决定）

| 编号 | 问题 | 建议默认 |
|---|---|---|
| OP-01 | M2 后是否引入 GLM 4.7 作为第三执行模型 | 先不引入，M2 验收后再评估 |
| OP-02 | 教学 artifact 是否公开开源 | 先私有，≥ 3 个 Milestone 后评估 |
| OP-03 | 自研 Core 是否 TypeScript 版本 | 不做；坚持 Python 一种语言 |
| OP-04 | 是否集成 Playwright MCP（浏览器真实验证） | 可选，M2 再评估 |
| OP-05 | wiki 节点是否启用向量搜索（qmd / hybrid） | M1 尾声视查询延迟决定 |
| OP-06 | Milestone 间是否插入"纯学习周"（不做新功能，只补读资料 + 整理 wiki） | 强烈建议每 2 个 Milestone 插 1 周 |

---

## 12. 下一步交付物清单

基于本 RnD-Analysis，作者可按顺序完成：
1. `tools/phoenix-doctor.sh`（M0-T1）：环境预检脚本。
2. `docs/milestones/M0-plan.md`：把 M0 任务落到具体 Step，并配 DoD 与学习 artifact 挂钩。
3. `wiki-import` 本 PRD / TRD / RnD / SPEC → AK-llm-wiki。
4. `docs/teaching/templates/`：三个教学 artifact 模板。
5. 基于 SPEC.md 开发 `AgentRuntime` + `ClaudeAgentSDKRuntime` 最小实现。

文档闭环：任何超出本 RnD-Analysis 的风险 / 决策变更必须在本文档 `§4 风险矩阵` / `§11 开放问题` 中显式更新。
