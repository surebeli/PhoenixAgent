# Milestone 2 — 执行顺序计划（Step-based，工程 × 学习同步）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 上位文档：PRD.md §9.1 / §10（Milestone 2）、TRD.md §4（D-ML / D-RT）、RnD-Analysis.md §4（R-ML / R-RT）、SPEC.md §3（AgentRuntime）/ §4（LLMClient）、M1-plan.md
- 总目标：把执行主力切换到 Kimi Coding Plan 且 Resolved Rate 相对 M1 基准下降 ≤ 5 pp；在 `PhoenixCoreRuntime` 之外再接入 `OpenAIAgentsRuntime` 形成三方对齐；长程任务完成率 ≥ 75%；Runtime/Model 热切换对记忆一致性 100% 回归通过；产出"Codex vs Kimi"完整对比报告。

---

## 0. 启动前提

- M1a-plan.md 和 M1b-plan.md 的所有 Step 已验收通过，DoD 全部成立。
- `AgentRuntime` / `MemoryBackend` / `ToolSpec + PluginRegistry` / `HarnessFlags` / `PermissionRules` / `EvaluationRunner` 在 M1b retrospective 后已再次冻结（SPEC v1.1）。
- 学习节点 `F-01 ~ F-22`（M0 + M1a + M1b）全部 ingest 并可召回；`M1b-retrospective.md` 已入 wiki。
- 拥有：Kimi Coding Plan 订阅（`api.moonshot.ai/anthropic` 国际路由）+ Codex API Key + 可本地跑 SWE-bench Verified 的 Docker 环境（M0 Step 8 交付）。
- 启动冻结版本：`PRD v1.0` / `TRD v1.0` / `SPEC v1.1`。

---

## 1. 完成定义（DoD，状态驱动）

- **DoD-M2-1**：`phoenix run --task "hello" --runtime=self --model=kimi-worker` 稳定返回 `status="success"`；连续 20 次无网络层非预期失败（排除上游 429 / 503 合理值）。
- **DoD-M2-2**：同一 SWE-bench Verified 子集（与 M1 Step 10 完全一致）上，`--runtime=self --model=kimi-worker` 的 Resolved Rate 相对 `--runtime=self --model=codex-base` 下降 ≤ 5 pp（PRD M2-KPI-1）。
- **DoD-M2-3**：长程任务集（M1 Step 11 交付的 SWE-EVO/SlopCodeBench + `phoenix-custom/*.yaml`）完成率 ≥ 75%（PRD M2-KPI-2）。
- **DoD-M2-4a**：Token 成本（`$/任务` 估算，仅执行口径）相对"Codex 单独执行"基准下降 ≥ 60%（PRD M2-KPI-3a）。
- **DoD-M2-4b**：端到端总成本（含评测及 Research 口径）相对 M1 基线有可跟踪的对比数据（PRD M2-KPI-3b）。
- **DoD-M2-5**：`OpenAIAgentsRuntime` 作为 `AgentRuntime` 的第三个具体实现上线；在 ≥ 10 个相同任务上与 `ClaudeAgentSDKRuntime` / `PhoenixCoreRuntime` 产生可对比的三方结果表。
- **DoD-M2-6**：Runtime / Model 热切换回归：中途 `--runtime` 或 `--model` 切换不破坏 `MemoryBackend` 的 INV-MM-1/2/3 不变量；全回归用例 100% 通过（PRD M2-KPI-4）。
- **DoD-M2-7**：`docs/teaching/M2/M-codex-vs-kimi-report.md` 产出；含 Resolved Rate / Long-horizon / 成本 / 失败模式画像四张图表。
- **DoD-M2-8**：Auto-Research 在 M2 期间至少再跑 ≥ 2 轮"模型差异驱动"的优化实验（针对 Kimi 专属痛点），Kept 变更 ≥ 1。
- **DoD-M2-9**：学习节点 `F-23 ~ F-34`（见 §4 索引）全部 `wiki-ingest` 并可召回。
- **DoD-M2-10**：M2 retrospective + interface-backlog 写入 wiki；进入 M3 前，`AgentRuntime` / `LLMClient` / `ModelProfile` 三个接口再次冻结。

---

## 2. 整体依赖图

```
Step 1 (Kimi Profile 接线) ──▶ Step 2 (Kimi 网络硬化) ──▶ Step 3 (Kimi vs Codex 基准对测)
                                         │
                                         ▼
                                 Step 4 (Kimi 长程压测 + 失败模式画像)
                                         │
         ┌───────────────────────────────┤
         ▼                               ▼
Step 5 (OpenAI Agents SDK 研读 +      Step 8 (Runtime/Model 热切换
        OpenAIAgentsRuntime 骨架)          记忆一致性回归)
         │
         ▼
Step 6 (OpenAIAgentsRuntime 完整集成)
         │
         ▼
Step 7 (三方 Runtime 对齐测试)
         │
         ├──────────────▶ Step 9 (Codex vs Kimi 综合报告)
         │
         ▼
Step 10 (Auto-Research v2：面向模型差异的迭代 ≥ 2 轮)
         │
         ▼
Step 11（可选） s08 后台工具 / s09-s11 多 Agent 协作原语
         │
         ▼
Step 12 (M2 retrospective + interface freeze + M3 预告)
```

- Step 4 与 Step 5 可并行（前者偏 Kimi 侧，后者偏 OpenAI 侧）。
- Step 8 依赖 Step 3 的基线与 Step 6 的第三 Runtime，若 Step 6 滑期则 Step 8 先做 Claude SDK ↔ self 的二方版本。
- Step 11 标记"可选"：若 Step 1–10 消耗超出预算，该步骤可整体延到 M3。

---

## 3. Step 清单

### Step 1 — Kimi ModelProfile 接线与 hello-world 〔量级：S〕

**工程任务**
- 在 `~/.config/phoenix/models.toml` 新增 `kimi-worker` profile：`provider="anthropic-compatible"`、`base_url="https://api.moonshot.ai/anthropic"`、`model="kimi-k2.5"`（或当期最新）、`auth_env="KIMI_API_KEY"`、`headers={"X-Phoenix-Client"="phoenix/M2"}`。
- `src/phoenix/model/registry.py` 补充 `ModelProfile` 装载验证（SPEC v1.1 §4）：能从 `keys.env` 读取 `KIMI_API_KEY` 并做 `whoami` 级探针（如调用一次最轻 prompt 确认 200）。
- `phoenix-doctor.sh` 新增 Kimi 段落：检测 `KIMI_API_KEY` 存在、`base_url` 可达（只 HEAD，不扣费）。

**内嵌学习（产出 F-23）**
- 必读：
  - Kimi 官方文档中 Anthropic-compatible endpoint 段落（路径 / 支持字段差异 / 不支持的功能）。
  - Anthropic Messages API 的 `messages[]` / `tool_use` / `stop_reason` 规范（对照 Kimi 是否全量支持 `tool_use` 并发、`cache_control`、`thinking`）。
- 要回答（写进 `F-23-kimi-anthropic-compat.md`）：
  - Kimi 的 Anthropic 兼容层与 Claude 原生 API 的字段差异矩阵（逐字段 ✅/⚠️/❌）。
  - `cache_control` 在 Kimi 上是否生效？若不生效，对 Context Compression 策略（F-09）的影响？
  - 国际路由 `api.moonshot.ai/anthropic` 与大陆 `api.moonshot.cn` 的差异与选择依据（香港网络 / 合规 / 账单）。

**产物**
- `models.toml` 追加 kimi-worker 段；`keys.env.template` 新增 `KIMI_API_KEY=`。
- `phoenix-doctor.sh` 追加 Kimi 检查段（S 级补丁）。
- `docs/teaching/M2/foundations/F-23-kimi-anthropic-compat.md`

**进入下一步条件**
- `phoenix run --task "echo hi" --runtime=self --model=kimi-worker` 一次成功；探针 round-trip ≤ 3s。
- F-23 入库。

---

### Step 2 — Kimi 网络硬化：whitelist / UA / Proxy fallback 〔量级：M〕

**工程任务**
- 在 `src/phoenix/model/http_client.py`（LLMClient 内部工厂）新增 `RequestFingerprint` 抽象：
  - 默认直连：自定义 `User-Agent="phoenix/M2 (+https://…)"`；自定义 `X-Phoenix-Client` 头。
  - 兜底 proxy：LiteLLM Proxy 本地起服务（或直接 `litellm --config ~/.config/phoenix/litellm.yaml`），Phoenix 指向 `http://127.0.0.1:4000` 作为统一入口。
- 失败归因：连续 N 次 `429 / 403 / whitelist-like` 错误时自动切换到 proxy 路径；Hook 打 `logs/network-escalation.jsonl`。
- `tools/kimi-smoke.py`：用 20 次最小任务做 smoke run，输出成功率与中位 latency。

**内嵌学习（产出 F-24）**
- 必读：
  - LiteLLM Proxy 文档（config 格式 + router 模式）。
  - Kimi 官方 FAQ 关于 rate limit / whitelist / UA 校验的段落（若无公开文档则记录实测现象）。
- 要回答：
  - Kimi 对 standalone CLI 的 UA 校验触发条件（实测 + 假设）？
  - LiteLLM Proxy 作为 fallback 的延迟与功能损失（是否能透传 `tool_use` / `cache_control`）？
  - "失败归因 → 自动切换" 的开关是否应该对 Auto-Research 可见（以便评估 proxy 路径对 Resolved Rate 的影响）？

**产物**
- `src/phoenix/model/http_client.py`（含 fingerprint + proxy fallback）。
- `~/.config/phoenix/litellm.yaml` 模板 + `tools/kimi-smoke.py`。
- `docs/teaching/M2/foundations/F-24-kimi-network-hardening.md`

**进入下一步条件**
- `kimi-smoke.py` 成功率 ≥ 95%（直连或 proxy 任一）。
- F-24 入库。

---

### Step 3 — Kimi vs Codex 基准对测（SWE-bench Verified） 〔量级：L〕

**工程任务**
- 固定 M1 Step 10 使用的 subset（同 task id、同 seed、同 HarnessFlags）。
- 顺序跑两条线：
  - A 线：`--runtime=self --model=codex-base`（M1 基线再跑一次确认可复现）。
  - B 线：`--runtime=self --model=kimi-worker`。
- `src/phoenix/evaluation/compare.py` 产出 `benchmark-report.json`：每题 diff（pass/fail 变化、token 成本、latency、工具调用次数）。
- 若 B 线 Resolved Rate 下降 > 5 pp，**不修改 Kimi profile**，转记入失败样本池供 Step 4 / Step 10 使用。

**内嵌学习（产出 F-25）**
- 必读：
  - Anthropic / OpenAI 公开的 "controlled A/B for LLM" 讨论。
  - SWE-bench Verified README 中关于复现性（seed / retry / judge）段落。
- 要回答：
  - 控制变量的边界：HarnessFlags 必须完全一致，但 `temperature` / `max_tokens` 是否也统一？
  - 同一任务在两个模型上"成功但路径不同"的计费口径（以谁的 token 计成本基线）？
  - 显著性下限：本 subset 多大 N 才能检出 5 pp 差异？（结合 F-20 的 proportion z-test 推出）

**产物**
- `src/phoenix/evaluation/compare.py` + `artifacts/M2/bench/{A,B}-report.json`。
- `docs/teaching/M2/foundations/F-25-controlled-benchmarking.md`

**进入下一步条件**
- 两份 report 齐全；每题级 diff 可通过 `phoenix eval diff --a=… --b=…` 打印。
- F-25 入库。

---

### Step 4 — Kimi 长程任务压测 + 失败模式画像 〔量级：L〕

**工程任务**
- 在 M1 Step 11 的长程任务集（SWE-EVO / SlopCodeBench + `phoenix-custom/*.yaml`）上跑 `--model=kimi-worker`，收集 `LongHorizonMetrics`（completion / recovery / persistence / decision_stability）。
- `src/phoenix/evaluation/failure_taxonomy.py`：对每个失败 trace 打 tag：`tool_call_malform` / `plan_drift` / `context_overflow` / `permission_deny` / `worktree_conflict` / `oracle_mismatch` / `misc`。
- 将失败样本池（来自 Step 3 / Step 4）统一 ingest 到 wiki `namespace="failure-modes"`。

**内嵌学习（产出 F-26）**
- 必读：
  - 重读 F-18（长程指标）；补充一篇关于"错误分类学 (error taxonomy)"的 ML 论文或博客。
  - Anthropic / OpenAI 失败分析文章（ReAct 中常见失败模式的定性分类）。
- 要回答：
  - Kimi 在哪些 tag 上相对 Codex 更差？是否集中在 `plan_drift` / `tool_call_malform`？
  - 失败模式 → 后续优化的映射：哪些可以通过 Harness 层 patch（Auto-Research v2 目标）？哪些必须等模型迭代？
  - 样本再利用：如何用失败样本构建"专项 micro-bench"，避免每次都跑完整 benchmark？

**产物**
- `src/phoenix/evaluation/failure_taxonomy.py`
- wiki `namespace="failure-modes"` 内 ≥ 30 条样本
- `docs/teaching/M2/foundations/F-26-kimi-failure-taxonomy.md`

**进入下一步条件**
- DoD-M2-2、DoD-M2-3 初步结论产出（哪怕不达标）。
- F-26 入库。

---

### Step 5 — OpenAI Agents SDK / Codex SDK 研读 + Runtime 骨架 〔量级：M〕

**工程任务**
- `src/phoenix/runtime/openai_agents.py`：实现 `OpenAIAgentsRuntime(AgentRuntime)` 骨架：
  - `run_task` 内部用 `openai-agents` 包的 `Runner.run(...)`；输入 `PhoenixContext` → 内部 `Agent` / `Tool` 定义；`messages[]` / `tool_use` 映射由 `_adapt_openai_to_phoenix` 负责。
  - 暂不接 5 步验证链，仅做"能跑通 + 轨迹回填"，作为 Step 6 的前置。
- `~/.config/phoenix/models.toml` 新增 `codex-agents` profile（与 `codex-base` 同 Key，但标记 `runtime_hint="openai-agents"`）。

**内嵌学习（产出 F-27）**
- 必读：
  - OpenAI Agents SDK 官方 docs（Agent / Runner / Tool / Handoff 四个核心概念）。
  - Codex SDK 的 quickstart 与 examples（特别是 `tool_use` / `function-calling` 部分）。
- 要回答（写进 `F-27-openai-agents-vs-claude-sdk.md`）：
  - Agents SDK 的 `Runner` 与 Claude SDK 的 `query(...)` 在控制粒度上的差异？
  - Tool 定义方式（typed function vs JSON schema）对 PhoenixAgent `ToolSpec`（SPEC v1.1 §2）的映射成本？
  - `Handoff` 概念与 PhoenixAgent subagent（F-15）的相似与差异？

**产物**
- `src/phoenix/runtime/openai_agents.py`（骨架版）
- `docs/teaching/M2/foundations/F-27-openai-agents-vs-claude-sdk.md`

**进入下一步条件**
- `phoenix run --task "echo hi" --runtime=openai-agents --model=codex-agents` 跑通；Claude SDK / self / openai-agents 三个 Runtime 都能跑同一 echo 任务。
- F-27 入库。

---

### Step 6 — OpenAIAgentsRuntime 完整集成（验证链 + Memory + Harness） 〔量级：L〕

**工程任务**
- 在骨架基础上接入：
  - 5 步验证链：`validateInput → PreToolUse Hook → checkPermissions → executeTool → mapToolResultToAPI`（M1 Step 4 的实现抽离为可复用模块）。
  - Memory：每次 Tool 调用前后与 `MemoryBackend` 交互，保持与 `PhoenixCoreRuntime` 的 digest 节奏一致。
  - HarnessFlags：最小支持 `s01/s02/s03/s06/s12`；`s04/s07` 通过 Agents SDK 自带机制 + PhoenixAgent bridge 实现（SPEC INV-RT-1 要求外观一致）。
- 回填 `logs/openai-agents-trace.jsonl`：与 self 路径结构一致，以便 Step 7 对齐。

**内嵌学习（产出 F-28）**
- 必读：F-27 回看 + Agents SDK 的 `AgentHooks` / `lifecycle` 文档。
- 要回答：
  - 把 PhoenixAgent 的 Hook（JSONL 子进程协议，SPEC v1.1 §12）桥接到 Agents SDK lifecycle 的最佳方式？
  - Agents SDK 是否会"吞掉" `tool_use` 细节，导致某些验证链步骤无处插入？有哪些适配缺口？
  - 何时该认输——即"用 Agents SDK 做 Runtime 外观、但不强行把 PhoenixAgent 全部 Harness 塞进去"的边界？

**产物**
- `src/phoenix/runtime/openai_agents.py`（完整版）
- `docs/teaching/M2/foundations/F-28-openai-runtime-integration.md`

**进入下一步条件**
- 在一个"读 + 多文件修改 + 跑测试"的代表任务上，`--runtime=openai-agents` 全链路（含 Hook / Permission / Memory）跑通。
- F-28 入库。

---

### Step 7 — 三方 Runtime 对齐测试 〔量级：M〕

**工程任务**
- `src/phoenix/evaluation/runtime_parity.py`：同一任务依次在 `claude-sdk / self / openai-agents` 上跑；固定 seed / 同一模型（Codex）/ 同一 HarnessFlags。
- 产出 `runtime-parity-report.json`：
  - 每题的 pass/fail 一致性矩阵。
  - 工具调用序列相似度（Levenshtein on tool_name 序列）。
  - 成本 / latency 对比。
- ≥ 10 个任务；若某 runtime 在 ≥ 20% 任务上与其他两个完全不一致，Step 6 的集成视为"部分达标"，补 issue 延到 M3。

**内嵌学习（产出 F-29）**
- 必读：F-25 回看 + 关于 "outcome equivalence vs trace equivalence" 的 agent 评测讨论。
- 要回答：
  - 结果等价（最终 pass）与轨迹等价（工具序列）分别验证什么？哪个更重要？
  - Claude SDK 与自研 Core 在同模型下仍可能产生不同轨迹的原因（message 组织、停止条件、并发 tool_use 处理）？
  - 若三方 runtime 在"Claude SDK 独占能力"（如 extended thinking）上差异显著，如何在 parity 矩阵中标注而不是粗暴扣分？

**产物**
- `src/phoenix/evaluation/runtime_parity.py`
- `artifacts/M2/parity/runtime-parity-report.json`
- `docs/teaching/M2/foundations/F-29-three-way-runtime-parity.md`

**进入下一步条件**
- 三方对齐报告产出且 DoD-M2-5 满足。
- F-29 入库。

---

### Step 8 — Runtime/Model 热切换 × 记忆一致性回归 〔量级：M〕

**工程任务**
- `src/phoenix/evaluation/hotswap_regression.py`：构造 ≥ 5 条"长程会话"，在中途切换：
  - 仅换 `--model`（codex → kimi / kimi → codex）。
  - 仅换 `--runtime`（self → claude-sdk / self → openai-agents）。
  - 同时换 `--runtime` + `--model`。
- 每次切换后验证 `MemoryBackend` 的三个不变量（SPEC v1.1 §6 INV-MM-1/2/3）：
  - 跨 namespace digest 不重复。
  - subagent digest 不污染主 agent。
  - 新 ingest 一定会更新 digest。
- 失败即 P0 bug，Step 8 不完结 → 阻塞 Step 9。

**内嵌学习（产出 F-30）**
- 必读：回看 F-mem-1 / F-mem-2（M0 的 Memory 基础节点）；补读 `AK-llm-wiki` 关于 `tier` / `namespace` 并发访问的段落。
- 要回答：
  - 哪些 Runtime-specific 状态（如 Claude SDK 的 conversation id）必须 persistence 到 SQLite 中以支持热切换？
  - Runtime 切换后，正在进行的 Plan / PlanStep 如何判定"可继续 vs 必须重规划"？
  - 记忆一致性回归用例如何避免"上次 Kimi 写的 digest 被下次 Codex 重写"的幂等问题？

**产物**
- `src/phoenix/evaluation/hotswap_regression.py`
- 回归用例目录 `evaluation/hotswap/*.yaml`（≥ 5）
- `docs/teaching/M2/foundations/F-30-hotswap-memory-invariants.md`

**进入下一步条件**
- DoD-M2-6 满足（100% 通过）。
- F-30 入库。

---

### Step 9 — Codex vs Kimi 综合对比报告 〔量级：M〕

**工程任务**
- 汇总 Step 3 / Step 4 / Step 7 / Step 8 的所有指标，产出 `docs/teaching/M2/M-codex-vs-kimi-report.md`：
  - 第 1 节：Resolved Rate 对比（SWE-bench Verified subset）。
  - 第 2 节：Long-horizon 指标（completion / recovery / persistence / decision_stability）。
  - 第 3 节：成本对比（token × 单价，直连 + proxy 两条）。
  - 第 4 节：失败模式画像（Step 4 的 taxonomy）。
  - 第 5 节：Runtime 对齐附录（Step 7 的 parity）。
  - 第 6 节：可执行结论 — "在哪些任务/场景优先用 Kimi，哪些场景保留 Codex"。
- `phoenix memory ingest --source docs/teaching/M2/M-codex-vs-kimi-report.md --namespace evaluation --tier active`。

**内嵌学习（产出 F-31）**
- 必读：F-25 / F-26 回看 + 一篇关于"模型能力画像 (capability profile)"的文章（可用 Anthropic 或 Karpathy 的相关讨论）。
- 要回答：
  - 能力画像的稳定性：若下月 Kimi 升级到 K2.6，哪些结论大概率失效？哪些是结构性的？
  - 报告如何被 Auto-Research 利用作为"模型路由"先验（Step 10 会接手）？

**产物**
- `docs/teaching/M2/M-codex-vs-kimi-report.md`
- `docs/teaching/M2/foundations/F-31-model-capability-profile.md`

**进入下一步条件**
- 报告 ingest 成功且可被 `phoenix memory query "kimi vs codex"` 召回。
- DoD-M2-7 成立。
- F-31 入库。

---

### Step 10 — Auto-Research v2：面向模型差异的专项迭代 〔量级：L〕

**工程任务**
- 基于 Step 4 / Step 9 的失败模式画像，选定 ≥ 2 个 Kimi 专属痛点（例如 `tool_call_malform`、`plan_drift`），定义针对性 patch 空间（仅限 `harness/ + plugins/ + memory/digest_rules/`，严格沿用 M1 Step 12 的 `allowed_change_globs`）。
- `phoenix research --rounds=N --benchmark=swe-bench-verified --subset=20 --model=kimi-worker --focus=<tag>`：
  - Generator = Kimi（执行者，目标是修 Harness）。
  - Evaluator = Codex（评测者，保持与 M1 一致以避免评测漂移）。
- 每轮结束写 `experiment-report.md`；至少 1 项 Kept 变更回灌到 wiki + `docs/teaching/M2/foundations/`。

**内嵌学习（产出 F-32）**
- 必读：重读 F-19（Generator-Evaluator）/ F-20（显著性）/ F-21（Auto-Research ops）。
- 要回答：
  - "Generator 切成 Kimi"对 GAN 循环稳定性的影响？是否需要换 Evaluator 来防止"Kimi 自评"？
  - 专项迭代（focus=<tag>）相比"全局迭代"的 sample efficiency 优势？
  - Kept 变更如何同时对 Codex 生效？若对 Codex 反而变差，如何处置（per-model harness variant 必要性讨论）？

**产物**
- ≥ 2 份 Kimi-focused `experiment-report.md`
- ≥ 1 份 Kept 变更的"机理解读 + 跨模型影响分析"笔记
- `docs/teaching/M2/foundations/F-32-autoresearch-v2-model-aware.md`

**进入下一步条件**
- DoD-M2-8 成立。
- F-32 入库。

---

### Step 11 — 可选：s08 后台工具 / s09-s11 多 Agent 协作原语 〔量级：M，**可选**〕

**本步标记可选**：若 Step 1–10 消耗超预算，本步整体延到 M3，仅保留占位 issue 与学习 backlog 条目。

**工程任务（若开展）**
- `src/phoenix/harness/background.py`（s08）：把长耗时工具（test-runner 跑大型 suite / evaluation Runner）放到后台 worker，通过 Persistence（M1 Step 7）的 `phoenix_tasks` 表作为交互媒介；主 loop 拿到 `task_id` 立刻返回。
- `src/phoenix/harness/team.py`（s09-s11 的最小子集）：`TeamRuntime` 协调 N 个 `PhoenixCoreRuntime` 实例，通过共享 Memory namespace 做信息交换；初版仅实现"Planner → Worker × K"两级。

**内嵌学习（产出 F-33，若开展；若延期则仅登记 backlog）**
- 必读：sanbuphy s08 / s09 / s10 / s11 章节；关于 multi-agent orchestration 的 Anthropic blog / OpenAI Agents Handoff 实践。
- 要回答：
  - 后台工具与前台工具的契约差异（status polling vs event push）？
  - 多 Agent 共享 Memory 时如何防止 race condition（结合 INV-MM-1 扩展）？
  - 多 Agent 对评测的影响：是否需要"团队粒度 Resolved Rate"指标？

**产物（若开展）**
- `src/phoenix/harness/background.py`、`src/phoenix/harness/team.py`（骨架 + 1 个端到端样例）
- `docs/teaching/M2/foundations/F-33-s08-s11-team-primitives.md`

**进入下一步条件**
- 若开展：样例"Planner + 2 Worker"多 Agent 任务跑通，未破坏 INV-MM-*。F-33 入库。
- 若延期：在 `docs/milestones/M2-retrospective.md` 显式登记为 M3 backlog 条目，并在本步骤 `产物` 占位处写"Skipped, see backlog"。

---

### Step 12 — M2 retrospective + 接口冻结 checkpoint 〔量级：S〕

**工程任务**
- 汇总 milestone-level artifact：
  - `docs/teaching/M2/M-codex-vs-kimi-report.md`（Step 9 产出）
  - `docs/teaching/M2/M-three-way-parity.md`（基于 Step 7 parity report 的可读版）
  - `docs/teaching/M2/M-hotswap-playbook.md`（基于 Step 8 的运维手册）
- 接口稳定性 checkpoint：
  - `AgentRuntime`：三方实现是否暴露出新的接口缺口？（例如 `Runtime.capabilities()` 返回 `{extended_thinking, parallel_tool_use, ...}`）。
  - `LLMClient` / `ModelProfile`：新增 Kimi 后是否有字段遗漏？
  - 若需变更，升 SPEC v1.y 或 v2.0，并通过 `wiki-ingest`。
- `phoenix-doctor.sh --json > artifacts/doctor-m2-final.json`；`wiki-lint --auto-fix`。
- `docs/milestones/M2-retrospective.md`：KPI 达成情况、失败模式沉淀、每个 F-* 的自测结果、M3 backlog（含 Step 11 可选项的去留决策）。

**内嵌学习（产出 F-34）**
- 无新资料阅读；本节点是"本阶段学到了什么"的元反思，要求写两段：
  - "若现在让我重写 M2，会改哪 3 件事"。
  - "哪些 M1 的结论在 M2 被推翻或修订"（最重要：避免假性复利）。

**产物**
- 3 份 milestone artifact 全部 ingest 到 wiki。
- `docs/milestones/M2-retrospective.md`
- `artifacts/doctor-m2-final.json`
- 可能的 SPEC v1.y / v2.0 → 同步 `wiki-ingest`
- `docs/teaching/M2/foundations/F-34-milestone-meta-reflection.md`

**进入下一步条件**
- DoD-M2-1 ~ DoD-M2-10 全部成立。
- `AgentRuntime` / `LLMClient` / `ModelProfile` 三个接口在 M3 Step 1 启动前不再破坏性变更。

---

## 4. 学习节点索引

| 节点 | 产自 Step | 主题 |
|---|---|---|
| F-23 | 1 | Kimi 的 Anthropic-compatible endpoint 差异 |
| F-24 | 2 | Kimi 网络硬化：UA / whitelist / LiteLLM Proxy |
| F-25 | 3 | 控制变量的 LLM A/B 基准对测方法 |
| F-26 | 4 | Kimi 长程失败模式画像 |
| F-27 | 5 | OpenAI Agents SDK 与 Claude SDK 差异 |
| F-28 | 6 | OpenAIAgentsRuntime 的接口映射与验证链桥接 |
| F-29 | 7 | 三方 Runtime 对齐测试方法论 |
| F-30 | 8 | Runtime/Model 热切换 × 记忆一致性不变量 |
| F-31 | 9 | 模型能力画像与路由先验 |
| F-32 | 10 | Auto-Research v2：模型感知的迭代 |
| F-33 | 11（可选） | s08 后台 / s09-s11 多 Agent 协作原语 |
| F-34 | 12 | M2 元反思 |

---

## 5. 风险预警（M2 阶段新增 / 升级）

| 编号 | 风险 | 触发步骤 | 缓解 |
|---|---|---|---|
| R-ML-1↑ | Kimi 路由层频繁 429 / 403 挡住评测 | Step 2 / 3 | `tools/kimi-smoke.py` 阈值告警；必要时切 LiteLLM Proxy；评测期间预留第二把 Key |
| R-ML-2 | Kimi 兼容层不支持 `cache_control`，Compression 失效 → 成本飙升 | Step 3 / 4 | 若 F-23 确认不支持，Step 3 在 Kimi 线关闭 `auto_compact`，以"关闭 cache 后成本"重新做 M2-KPI-3 口径讨论 |
| R-RT-2 | OpenAI Agents SDK 的 lifecycle 吞掉 Hook 接入点 | Step 6 | Step 6 学习节点要求显式记录"无法桥接"的缺口；缺口集中则在 Step 12 升 SPEC v2 引入 `Runtime.capabilities()` |
| R-EV-4 | runtime-parity 差异过大导致 M2-KPI-4 回归失败 | Step 7 / 8 | 首先隔离"能力差异"与"bug"：能力差异进 SPEC capabilities 表；bug 转 P0 issue，不放行 Step 9 |
| R-AR-3 | Auto-Research v2 的 Kept 变更只对 Kimi 生效、对 Codex 反而变差 | Step 10 | 允许引入 per-model harness variant（SPEC 增 `HarnessFlags.model_overrides`），但每个 override 必须有 F-* 学习笔记 |
| R-MM-2 | 热切换后 digest 幂等被破坏（Kimi 写 / Codex 覆写） | Step 8 | 引入 `digest_version` 字段 + 同 slug 冲突走"合并 summary"策略；F-30 详述 |
| 新发现 | 任何未登记风险 | 随时 | Step 12 retrospective 新增 R-* 编号并同步 RnD-Analysis §4 |

---

## 6. 与 M3 的衔接

M3 的候选主线（M2 retrospective 后决策，不在本文档锁死）：
- 引入第 4 个执行模型（GLM 4.7 / MiniMax）作为 Kimi 备选，扩展 F-31 的能力画像。
- Hybrid RAG 与 wiki 的融合（RnD-Analysis OP-03），让长程任务的历史片段按需召回。
- 多 Agent 协作正式化（若 Step 11 延期，M3 Step 1 启动）。
- PhoenixAgent 自研插件生态开放（第三方 plugin 安全扫描 + 注册协议）。

学习节点 `F-*` 从 F-35 接续。起笔时机：M2 Step 12 验收通过且 `M2-retrospective.md` ingest 到 wiki 之后，并依据 PRD OP-01 在 M2 验收会上确认 M3 主线。


---

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；锁定 Kimi 接入、三方 Runtime 对齐与热切换回归计划。 |
