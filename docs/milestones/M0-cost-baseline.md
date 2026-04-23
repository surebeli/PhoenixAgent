# M0 Cost Baseline — Step 3 Claude SDK / Codex Hello Smoketest

- 版本：v0.1（2026-04-23，Step 3 首次实测）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` Step 3、`docs/SPEC.md` `SPEC v1.2 §13.1`
- 目的：记录 M0 Step 3 的最小对照实验，给 M2 成本/时延对比留下第一个可复核原点。

---

## 1. 本次运行范围

本次只跑一个最小任务：`hello phoenix`。目标不是比较“哪个模型更强”，而是确认 PhoenixAgent 当前能否在**同一任务**上看到 Claude Agent SDK 与 OpenAI Chat Completions / function calling 的最小协议面，并把 token、耗时、停止原因与日志形态先落到仓库里。对应工程脚本为 `scripts/smoketest-claude.py`，结构化日志落在 `logs/<session_id>.jsonl`，与 `SPEC v1.2 §13.1` 的 `AgentEvent` 约定对齐。

本次实测使用的成功证据文件是：

- `logs/m0-step3-20260423-010259-2f2d0554.jsonl`

---

## 2. 运行结果总表

| Provider | Surface | Model | 结果 | Stop / Finish | Tokens | 耗时 | 备注 |
|---|---|---|---|---|---:|---:|---|
| Claude | `claude_agent_sdk.query(...)` | `claude-opus-4-7` | **Blocked** | `stop_sequence` | 0 | 176824 ms | 连续 10 次 `429 rate_limit` / `MONTHLY_LIMIT_EXCEEDED`，最终落成 synthetic assistant error text |
| Codex | `OpenAI().chat.completions.create(...)` | `codex-mini-2026-04` | **Pass** | `stop` | 77 | 1653 ms | 返回 `Hello phoenix!`，未触发 `tool_calls` |

> Tokens 口径：Claude 取 `usage.input_tokens + usage.output_tokens`，Codex 取 `usage.total_tokens`。本次 Claude 因 quota block 为 0，不可直接与正常回答场景横比。

---

## 3. Claude 侧观测

### 3.1 看到的不是“无输出”，而是“有完整协议事件但任务被额度阻断”

`logs/m0-step3-20260423-010259-2f2d0554.jsonl` 里可以看到完整的 SDK 会话骨架：

1. `system.init`：启动时已经给出 `cwd`、工具列表、`permissionMode=default`、`apiKeySource=ANTHROPIC_API_KEY` 等上下文。
2. `system.api_retry`：随后连续出现 10 次 429 重试事件。
3. `assistant`：最终 assistant 消息不是正常问答，而是 synthetic error text：`API Error: Request rejected (429) ... MONTHLY_LIMIT_EXCEEDED ...`
4. `result`：`stop_reason` 依旧是 `stop_sequence`，`total_cost_usd=0`，`duration_ms=176824`。

这说明两个重要事实。第一，**Claude Agent SDK 的协议面已经跑通**：我们确实拿到了 `init -> retry -> assistant -> result` 的流式 JSON 事件，并且全部写入了 JSONL。第二，**M0 Step 3 的“Claude 端 hello 跑通”尚未成立**，因为这次 assistant 并没有完成 `hello phoenix`，而是被 provider 月限额提前截断。

### 3.2 stop_reason 不能脱离 payload 单看

这次最有价值的教训是：`stop_reason=stop_sequence` 并不自动等于“任务成功完成”。在 Claude 侧，真正的业务状态必须结合 assistant 内容、`system.api_retry` 历史和 `ResultMessage.result` 一起看。否则会把“额度打满后生成的一条错误文本”误判成“正常停机”。

这也是为什么 `SPEC v1.2 §13.1` 要求保留结构化事件，而不是只保留最终字符串输出。没有 retry 轨迹，就无法复盘这次阻塞到底是 Prompt、工具、权限还是 provider 额度。

---

## 4. Codex / OpenAI 侧观测

Codex 路径走的是 `OpenAI().chat.completions.create(...)`，请求里带了一个最小 function tool schema，但 prompt 只是 `hello phoenix`，因此模型直接自然结束：

- `assistant_text = "Hello phoenix!"`
- `finish_reason = "stop"`
- `tool_calls = []`
- `usage.total_tokens = 77`
- `wall_clock_ms = 1653.06`

这给 Step 3 留下了一个干净基线：**同一个任务在 OpenAI surface 上不需要工具也能完成，finish_reason 为自然 stop；而 Claude surface 当前被 quota 阻断，尚未形成可比较的正常 token 样本。**

---

## 5. 当前结论

### 5.1 已成立

- `scripts/smoketest-claude.py` 已落盘。
- `logs/` 下已有符合 `SPEC v1.2 §13.1` 的完整 session JSONL。
- Codex / OpenAI function calling 路径至少成功跑过一次。
- Claude Agent SDK 的流式协议面、重试事件与结果事件已经被真实观测并归档。

### 5.2 尚未成立

- `M0-plan.md` Step 3 的“Claude 端 hello 跑通”**尚未成立**。
- 因此 DoD-2 目前只能算**部分完成**，不能宣称 Step 3 已闭环。

### 5.3 下一次重试条件

只有在以下任一条件满足后，才值得重跑同一脚本更新本表：

1. Claude 额度在本地时区重置；
2. 切换到另一条可用的 Claude 认证来源；
3. Step 5/后续模型路由工作确认应改用其他 Anthropic 入口。

在此之前，本文件保持为**“首次真实观测基线 + 显式阻塞登记”**，不伪造成功结果。

---

## 6. 参考

- `docs/milestones/M0-plan.md` Step 3
- `docs/SPEC.md` `SPEC v1.2 §13.1`
- `scripts/smoketest-claude.py`
- `logs/m0-step3-20260423-010259-2f2d0554.jsonl`

---

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | Step 3 首次创建：记录 Claude Agent SDK / Codex hello smoketest 的 tokens、耗时、日志路径与当前 quota blocker。 |
