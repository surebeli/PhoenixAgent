---
id: F-model-1
slug: 1-routing-and-compliance
name: 多 Provider 路由为什么必须绑在 Profile 与合规边界上
milestone: M0
step: 5
type: foundation
tier: active
spec_version: v1.2
related_spec: ["§4.1", "§4.2", "§4.3", "§14"]
related_fr: ["FR-02", "FR-08"]
related_inv: ["INV-ML-1", "INV-ML-3", "INV-ML-4"]
related_nodes: [F-02, F-05b]
replaces: null
ingested: true
ingested_at: 2026-04-23T10:50:06.8151704+08:00
readers: [llm, human]
---

# 多 Provider 路由为什么必须绑在 Profile 与合规边界上

## 动机（Why）

到了 Step 5，PhoenixAgent 面临的已经不是“能不能打一条模型请求”，而是**同一个 Runtime 未来怎样在 Codex、Kimi、本地模型之间切换，同时不把密钥、端点和合规边界搅成一锅粥**。如果模型路由只靠散落的环境变量、临时 `base_url` 覆盖和“这次先试试哪个能通”，短期看似灵活，长期会把审计、回放、教学和排障都做废。

这一步尤其敏感，因为 Phoenix 的目标不是单模型聊天机器人，而是一个会起 subprocess、会 spawn 子代理、会长期演进 Runtime/Harness/Memory 的 coding agent。模型层一旦没有“以 Profile 为单位”的稳定抽象，后面 M1/M2 的 Auto-Research、Teaching、成本对比就很难复现。Step 5 因此不是简单把 `openai` 或 `anthropic` SDK 包一层，而是要把“**模型是谁、端点在哪、密钥从哪里来、这个角色承担什么职责、失败时如何留档**”统一冻结到 `ModelProfile` 与 `LLMClient`。

## 核心内容

### 1. 为什么 subprocess 必须显式传 `--model` / `--provider`

`SPEC v1.2 INV-ML-4` 与 `TRD §3.5 D-ML-1` 都强调：subprocess 不得靠父进程环境变量“顺便继承”模型身份。原因不是形式主义，而是合规与审计。

第一，隐式继承环境变量会让**实际调用的 provider 边界不可见**。父进程若同时持有 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`MOONSHOT_API_KEY`，子进程只要拿到一组默认环境，就可能在没有显式声明的情况下把任务发到错误端点。对单机脚本这只是“打错 API”，对多代理系统则会变成“谁在用哪家的 key、是否越过了允许范围”都难以回溯。

第二，显式 `--model` / `--provider` 是**把 operator intent 落成证据**。Phoenix 未来的 CLI、日志、teaching artifact、benchmark report 都要回答：为什么这次生成器用 Kimi，评测器用 Codex，失败后为什么没有自动切到 Claude。只有把 profile 名字写进命令行、日志和 JSON 工件，后续人才能复现当时的决策。

第三，隐式继承还会放大**订阅套利与越权复用**的风险。Anthropic 2026 的商业条款明确把 API keys 和商业服务与 consumer 订阅面分开，TRD §3.6 也明确写了“禁止订阅套利”。如果 subprocess 只是继承一堆上层环境变量，那么“这次到底在用公司 API key、个人代理、还是某个共享订阅入口”会迅速失真。显式 profile 至少能把“这次调用 intended target 是谁”先钉死，再由各 profile 自己决定 key 名称、base URL 和后续审批边界。

### 2. `ANTHROPIC_BASE_URL` 覆盖到 Kimi / Ollama 时，真正变化的是端点路径

Step 5 最容易混淆的一点，是“Anthropic-compatible”并不等于“所有服务都长成同一个 URL”。本次代码里之所以把 `ModelProfile` 和 `infer_transport()` 单独抽出来，就是为了把这个差异显式化。

对真正的 Anthropic Messages 兼容端点，调用形状是：

`<base_url>/v1/messages`

这对应 `TRD §3.4` 里给出的 Kimi 国际路由示例 `https://api.moonshot.ai/anthropic`，拼出来就是 `https://api.moonshot.ai/anthropic/v1/messages`。若未来本地代理或 LiteLLM Proxy 暴露的是 Anthropic surface，这类 profile 也应走 `/v1/messages`。

但本次作者机器上的实际 `kimi-worker` profile 指向的是：

`https://api.kimi.com/coding`

这个入口不是 `Messages API` 形状，而是 **Coding Plan / OpenAI-style chat completions** 形状，因此 Step 5 的实测请求落在：

`https://api.kimi.com/coding/v1/chat/completions`

本地 Ollama 也类似：若走 OpenAI 兼容层，常见路径是 `http://localhost:11434/v1/chat/completions`；若未来前面再挂一个 Anthropic-compatible proxy，才会重新回到 `/v1/messages`。所以这里的关键不是死记某个全局 `ANTHROPIC_BASE_URL`，而是**每个 profile 必须知道自己到底对应哪种 transport surface**。这就是 `profiles.py` 里的 `infer_transport()` 为什么存在：它不是花哨抽象，而是在防止“base URL 一样看起来像兼容，其实 endpoint path 完全不同”的误用。

### 3. “平庸模型 + 强 Harness”里，Kimi、Codex 各干什么

PhoenixAgent 从一开始就不是“找一个最强模型包打天下”，而是让不同模型承担不同角色。`PRD FR-02`、`TRD §3.2` 和 `TRD §8.5 D-AR-1` 的组合，已经把分工说得很清楚：**Codex 负责 evaluator / baseline，Kimi 负责 worker / 执行，本地模型负责 cheap fallback 或压缩类任务**。

为什么是这个切法？因为“强 Harness”意味着真正决定安全性、可控性和复现性的，不是单个模型是否无所不能，而是 Phoenix 自己的 Runtime、Plugin、Permission、Memory、Evaluation 这些层能不能把行为钉住。模型层在这个体系里更像“按角色调度的外脑”：

1. **Codex**：适合做基准和评测，因为 Step 3、Step 5 的实测都说明它在当前环境下连通性最好，且作为 OpenAI 兼容端点更稳定。本次 `codex-base` 在 `scripts/smoketest-model.py` 里成功返回 `hello phoenix`，用时约 2066ms，tokens `23 -> 6`，足够作为后续 compare-to-baseline 的稳定参照。
2. **Kimi**：更适合承担 worker / code executor 这类“生成量大、成本敏感、需要 coding plan”的角色，但它同时带来 whitelist、User-Agent、路由差异和地域策略这些现实约束。Step 5 的价值不在“强行把它打通”，而在于先把这些约束留下机器可读证据。
3. **本地 Ollama**：不是主力，而是便宜兜底。它的意义在于当外部 provider 额度、地域、白名单或合规条件失效时，Phoenix 还能保留低成本、低权限的退路。

这也解释了为什么 Step 5 接受标准允许“至少一个 profile 成功，另一个失败但必须留档”。Phoenix 的胜负手不是“今天必须所有 provider 都通”，而是**不把失败藏起来，并且把失败转化成后续可执行的回退路径**。

### 4. Step 5 的真实观测：Kimi 失败不是代码坏了，而是入口策略不满足

`artifacts/M0/kimi-smoke.json` 已经把这件事记录清楚了。本次 `kimi-worker` whoami 探针与真实 chat 尝试都打到了 `https://api.kimi.com/coding/v1/chat/completions`，结果如下：

1. 直接请求：HTTP 403，返回 `Kimi For Coding is currently only available for Coding Agents ...`
2. 伪装 `User-Agent: Claude-Code`：仍然 HTTP 403，同一条 `access_terminated_error`

这组结果的重要性在于，它把 Step 5 的结论从“猜测可能要加个 User-Agent”推进到了“**当前 author machine 上，单改 User-Agent 不足以穿透 whitelist**”。因此合理的下一步不是继续在本 Step 里乱试 header，而是把回退路径记清楚：要么切回 `api.moonshot.ai/anthropic` 的 Messages 兼容入口，要么挂 LiteLLM / 代理层，要么把 Kimi 保留为后续手动接入项。

## 与 PhoenixAgent 的映射

- `SPEC v1.2 §4.1`：`~/.config/phoenix/models.toml` 是模型身份、端点与角色的冻结点，不能让调用侧到处散落 `base_url` 字符串。
- `SPEC v1.2 §4.2`：`src/phoenix/model/client.py` 提供 `ChatRequest`、`ChatResponse`、`LLMClient` 和最小 provider routing；`src/phoenix/model/profiles.py` 负责加载 profile、密钥 fail-fast 与 transport 判定。
- `SPEC v1.2 INV-ML-1` / `INV-ML-3`：其他层不应直接 import provider SDK；缺失 `api_key_env` 时要直接 fail-fast，而不是静默降级。
- `SPEC v1.2 INV-ML-4`：Step 5 的 smoke 和后续 CLI 都应显式带 profile，而不是靠父进程环境变量“碰运气”。
- `docs/TRD.md §3.6`：Kimi whitelist、User-Agent 和“禁止订阅套利”在本次产物里都落成了明确的诊断与约束。

## 失败模式（若适用）

最常见的失败模式是**把 provider 差异误当成只有 key 不同**。这样做出来的代码通常会把任何 base URL 都强行拼成同一种 endpoint，结果是 Kimi `/coding`、Moonshot `/anthropic`、本地 Ollama `/v1/chat/completions` 被混成一个“兼容端点”概念，最后不是 404 就是 403。

第二种失败模式是**把 User-Agent 伪装误当成万能钥匙**。TRD §3.6 的确把它列成一个可能手段，但 Step 5 的实测已经说明：在当前环境里，`User-Agent: Claude-Code` 仍不足以通过 `api.kimi.com/coding` 的 whitelist。继续在这个基础上无休止试 header，只会制造新的不可复现状态。

第三种失败模式是**为了让子进程“方便一点”而让它继承整包环境变量**。这会让 profile 与 provider 边界在日志中消失，也会让合规审计失去抓手。对 Phoenix 这种未来要跑 swarm/subagent/benchmark 的系统，这种“省事”属于技术债和合规债同时积累。

## 延伸与争议

当前 Step 5 仍有一个未闭合问题：Model Layer 未来是否要真的切到 LiteLLM，而不是继续保留现在这套最小直连实现。LiteLLM 的价值在于统一 100+ providers，并能把代理、鉴权和 spend tracking 收到一处；而本次直连实现的价值，在于它把端点路径和失败原因暴露得足够透明。M0 选择先用最小直连实现，是为了先理解“哪条路在当前环境下会被 whitelist、哪条路是 OpenAI-compatible、哪条路是 Anthropic Messages-compatible”；等 Step 6/7/8 继续展开时，再决定是否把这些差异收敛进 LiteLLM Proxy。

另一个争议点是 `kimi-worker` 最终应长期绑定 `api.kimi.com/coding` 还是回退到 `api.moonshot.ai/anthropic`。本次证据更支持“不要在 Step 5 强行拍板”，因为当前 author machine 上 `/coding` 明确被 whitelist 挡住，但这并不 automatically 证明 `/anthropic` 就一定更优。正确做法是：把当前失败路径记录为工件，待后续网络/代理/官方接入条件变化后再重试，而不是让 M0 的 teaching 节点替未来做过度承诺。

## 参考

- PhoenixAgent `docs/SPEC.md`：`SPEC v1.2 §4.1` / `§4.2` / `§4.3` / `§14`
- PhoenixAgent `docs/PRD.md`：`FR-02` / `FR-08` / `NFR-06`
- PhoenixAgent `docs/TRD.md`：`§3.2` / `§3.4` / `§3.5` / `§3.6`
- PhoenixAgent `artifacts/M0/kimi-smoke.json`
- PhoenixAgent `src/phoenix/model/profiles.py`
- PhoenixAgent `src/phoenix/model/client.py`
- PhoenixAgent `scripts/smoketest-model.py`
- Moonshot docs — Chat API: https://platform.moonshot.ai/docs/api/chat
- Moonshot docs — Model list: https://platform.moonshot.ai/docs/models
- LiteLLM README: https://github.com/BerriAI/litellm/blob/main/README.md
- Anthropic Commercial Terms: https://www.anthropic.com/legal/commercial-terms
