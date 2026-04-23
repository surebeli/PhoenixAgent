# M0 Token Profile — Step 10 观察结果

- 版本：v0.1（2026-04-23，Step 10 首次画像）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` §Step 10、`docs/PRD.md` NFR-01 / NFR-04、`docs/SPEC.md` §13.1 / §13.2
- 目的：基于最近 3 次 `phoenix run` 的 JSONL 日志，对 `prompt_tokens` / `completion_tokens` / `cache_read` / `cache_creation` 做最小画像，验证 Step 10 的观测面是否已经打通。

---

## 1. 样本说明

本次画像取最近 3 次已包含 `usage.observation` 事件的 run：

- `logs/01KPWCAMN8HJ5CQA3ZW88AS8XZ.jsonl`：`hello phoenix`，走 Claude SDK 远端路径，但被 `429 MONTHLY_LIMIT_EXCEEDED` 拦截。
- `logs/01KPWCH74BMZCG3D8PMA2YTBSF.jsonl`：`请调用 echo.say step10-sample-a`，走本地 tool dispatch。
- `logs/01KPWCH874S0019RNWPJ4SSRHD.jsonl`：`请调用 echo.say step10-sample-b`，走本地 tool dispatch。

这三次样本的共同点是：`usage.observation` 事件已经稳定写入 JSONL。它们的局限也很明显：当前 Claude 账户月额度耗尽，唯一一条远端样本返回的是 429 synthetic assistant；另两条是本地 tool-dispatch，本身不消耗模型 token。因此，这是一份**观测链路 smoke profile**，不是正常负载下的成本基线。

---

## 2. 观测表

| Run | 路径 | message_kind | prompt_tokens | completion_tokens | cache_read | cache_creation | 备注 |
|---|---|---|---:|---:|---:|---:|---|
| `01KPWCAMN8HJ5CQA3ZW88AS8XZ` | Claude SDK 远端 | assistant | 0 | 0 | 0 | 0 | 429 月额度耗尽；usage 为 SDK 返回的 synthetic 0 |
| `01KPWCH74BMZCG3D8PMA2YTBSF` | local-tool-dispatch | assistant | 0 | 0 | 0 | 0 | 本地路由，不走模型 |
| `01KPWCH74BMZCG3D8PMA2YTBSF` | local-tool-dispatch | tool_result | 0 | 0 | 0 | 0 | 本地工具结果回写 |
| `01KPWCH874S0019RNWPJ4SSRHD` | local-tool-dispatch | assistant | 0 | 0 | 0 | 0 | 本地路由，不走模型 |
| `01KPWCH874S0019RNWPJ4SSRHD` | local-tool-dispatch | tool_result | 0 | 0 | 0 | 0 | 本地工具结果回写 |

---

## 3. 简单画像

以当前 3 次样本看，四个字段都已经有固定落点，但数值仍全为 0：

```text
prompt_tokens      | 
completion_tokens  | 
cache_read         | 
cache_creation     | 
```

这不是“Phoenix 现在零成本运行”，而是因为当前样本恰好都不代表正常远端推理负载：

- 一条是额度耗尽后的 429 synthetic assistant；
- 两条是本地 tool-dispatch，天然不会产生模型 token。

因此，这份画像真正证明的是：Step 10 的 `usage.observation` 埋点已经进入 `logs/*.jsonl`，并且对 assistant 与 tool_result 两类消息都能稳定落盘。

---

## 4. 当前结论

- 结构化字段已经打通：`prompt_tokens` / `completion_tokens` / `cache_read` / `cache_creation` 会写入 JSONL。
- 本地 tool-dispatch 路径会写出 0 值观测，这对后续区分“模型消耗”与“本地工具路径”有帮助。
- 远端 Claude SDK 路径在额度耗尽时仍会产出可解析的 synthetic usage 结构，因此日志链路在失败场景下也不断裂。

当前缺口是：还没有一条**正常成功的远端 Claude run** 来展示非零 `prompt_tokens` / `completion_tokens`，也没有真实 cache 命中样本来观察 `cache_read` / `cache_creation` 的分布。等账户额度恢复后，应补至少 3 条成功远端样本，覆盖：

- 无工具纯 assistant；
- assistant + tool_result；
- 相同前缀重复请求，用于观察 cache 字段是否出现非零。

---

## 5. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | 首次记录 Step 10 的 3 次 run 画像，确认 `usage.observation` 事件已落盘，并注明当前样本受 429 与本地 tool 路径影响。 |