# PhoenixAgent 总路线图（Roadmap）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：跨 Milestone 的总体排布、基线冻结、KPI 横切、关键决策分叉。
- 上位依据：PRD §9（KPI）、PRD §10（里程碑）、TRD §2 ~ §6、SPEC v1.1 §14。
- 下位依据：`docs/milestones/M*-plan.md`、`docs/risk-register.md`、`docs/adr/**`。
- 身份：**本文件不是执行计划，不分配日程**。Step 级别的任务在 `docs/milestones/M<N>-plan.md` 内展开；本文件只定义"Milestone 之间的承接关系、冻结点、决策分支"。

---

## 1. 本文件存在的理由（Why）

`M*-plan.md` 回答"这个 Milestone 里要做什么"；本文件回答三件 `M*-plan` 不应承担的事：

1. **Milestone 之间如何承接**：每一个 Milestone 结束时冻结哪些硬接口，下一个 Milestone 在这些接口之上构建什么。
2. **KPI 在时间轴上的对照**：M1/M2/M3 的 KPI 是"单 Milestone 验收"，需要一张横切表看清楚"什么 KPI 何时固化、什么 KPI 何时允许回撤"。
3. **关键决策分叉**：形如"M2 结束后是否开 M3"的决策点，放在这里统一登记；具体决策走 ADR。

---

## 2. Milestone 序列与身份

| Milestone | 身份（一句话） | 状态 | 计划文件 | 验收标志 |
|---|---|---|---|---|
| M0 | 环境 + 四件套文档 + `ClaudeAgentSDKRuntime` 最小骨架 | 进行中 | `docs/milestones/M0-plan.md` | Step 12 验收 + `docs/SPEC.md` v1.1 冻结 |
| M1 | 自研 `PhoenixCoreRuntime` + 编程插件 + `MemoryBackend` + 检验框架 + Auto-Research | 计划 | `docs/milestones/M1-plan.md` | DoD-M1-1 ~ DoD-M1-10 全成立 |
| M2 | Kimi 接入 + 模型热切换 + `OpenAIAgentsRuntime` + 三方对齐 | 计划 | `docs/milestones/M2-plan.md` | DoD-M2-1 ~ DoD-M2-10 全成立 |
| M3+ | 以 M1/M2 模板交替推进：新 Runtime / 新 Model / 新插件 / 新 Benchmark | 未定 | 待 M2 验收后按 §6 决策分支产出 | — |

M0/M1/M2 的 KPI、DoD、Step 全部由对应 `M*-plan.md` 权威承载；本文件只做**承接关系**。

---

## 3. 冻结基线表（Freeze Baseline）

每个 Milestone 结束时冻结一批硬接口。冻结对象为"字段与职责边界"而非具体接口签名，方法名与返回结构允许在下一 Milestone 前半段以 Patch / Minor 温和收敛。硬冻结期内 Major 变更必须延到再下一 Milestone 的 Step 1 之后（见 `spec-change-policy` §7）。

| 冻结时点 | 新冻结的硬接口 | 已冻结累计 | 对应 SPEC 版本 | 解冻条件 |
|---|---|---|---|---|
| M0 结束 | `AgentRuntime`、`MemoryBackend`、`ToolSpec + PluginRegistry` | 上列 3 项 | v1.1 | 仅 Major 变更 + ADR |
| M1a 结束 | `HarnessFlags`、`PermissionRules` | 上列 5 项 | v1.1（若 M1a 期间升版，retrospective 必须回填具体版本） | 同上 |
| M1b 结束 | `EvaluationRunner` | 上列 6 项 | v1.1 | 同上 |
| M2 结束 | `LLMClient`、`ModelProfile`（`AgentRuntime` 再冻结一次） | 上列 8 项 | v1.y / v2.0（视变更级别） | 同上 |
| 每个 Auto-Research 轮次 | 该轮锁定的全部 SPEC 条款（通常不新增） | — | 该轮 `spec_version` | 轮次收尾后自动解锁 |

冻结事件必须在对应 `M*-retrospective.md` 的"接口冻结清单"章节显式登记。破冻（冻结期内仍动）走 `spec-change-policy` S-FREEZE-2。

---

## 4. KPI 横切表

按 KPI 纵向排列、Milestone 横向对照。"—"表示该 Milestone 不考核本项；"承"表示沿用上一 Milestone 阈值。

| KPI | M1a+M1b | M2 | M3+（默认策略） |
|---|---|---|---|
| Resolved Rate（SWE-bench Verified subset） | ≥ 基线 85%（M1-KPI-1） | 相对 M1 基准下降 ≤ 5 pp（M2-KPI-1） | 不低于 M2 同值；新 Runtime 上线时允许首轮 −5 pp 但 retrospective 内必须回升 |
| 长程任务完成率 | ≥ 80%（M1-KPI-2） | ≥ 75%（M2-KPI-2） | 承 M2 且每新增一个 Benchmark 不下降 |
| Token 成本下降 | — | ≥ 60%（M2-KPI-3） | 承 M2；若接入新模型导致成本上浮需 ADR |
| Runtime / Model 热切换通过率 | — | 100%（M2-KPI-4） | 承 M2；新增 Runtime 必须进同套回归 |
| 教学 artifact ingest 率 | 100%（M1-KPI-3） | 承 M1（retrospective 100% 归档） | 承 M1 |

阈值只能在 retrospective 内通过 ADR 下调，且必须说明是"能力限制"还是"目标漂移"。见 `definition-of-done.md` §9。

---

## 5. 关键依赖图（Milestone 级）

```
M0 Step 12 验收
   │
   ├── 冻结 AgentRuntime / MemoryBackend / ToolSpec+Registry
   │
   ▼
M1a Step 1..8（见 M1a-plan.md §2）
   │  - Step 1..3: 自研 Runtime + HarnessFlags + PermissionRules
   │  - Step 4..6: 编程插件 + 基础 Memory
   │  - Step 7..8: 基础评测集成 + retrospective
   │
   ├── 冻结 HarnessFlags / PermissionRules (部分)
   │
   ▼
M1b Step 1..7（见 M1b-plan.md §2）
   │  - Step 1..3: 完整 Memory 动词 + `EvaluationRunner`
   │  - Step 4..5: 长程任务 + Auto-Research 迭代
   │  - Step 6..7: 教学闭环 + retrospective
   │
   ├── 冻结 EvaluationRunner
   │
   ▼
M2 Step 1..12（见 M2-plan.md §2）
   │  - Step 1..4: Kimi 接线 + 网络硬化 + 基准对齐
   │  - Step 5..7: OpenAI Agents SDK + 三方对齐 + 热切换回归
   │  - Step 8..10: 综合报告 + Auto-Research v2
   │  - Step 11..12: 可选多 Agent + retrospective
   │
   ├── 冻结 LLMClient / ModelProfile（AgentRuntime 再冻结）
   │
   ▼
M3+ 决策分支（见 §6）
```

本图只列 Milestone 级承接，Step 级依赖在 `M*-plan.md §2` 内。

---

## 6. 决策分支（M3+ Decision Tree）

每个分支在对应时点走 ADR 确认；在 ADR 落地前，本表仅作为"候选走向"登记。

| 决策点 | 触发时点 | 候选分支 | 默认倾向 | 决策依据 |
|---|---|---|---|---|
| D-ROAD-1：是否接入第 4 个模型（GLM-4.7 / MiniMax / Qwen-Coder） | M2 retrospective 后 | A. 接入 1 个；B. 维持三方；C. 换掉现有某家 | B（维持三方，积累 M3 数据） | M2-KPI-1 达标情况 + 新模型能力报告（见 `RnD-Analysis` OP-01） |
| D-ROAD-2：教学 artifact 是否公开（开源 / Blog） | ≥ 3 个 Milestone 完成后 | A. 公开全部；B. 公开 F-* 不公开 M-*；C. 维持私有 | C（默认私有） | 作者时间成本 + 合规（`RnD-Analysis` OP-02） |
| D-ROAD-3：是否独立开启"团队 / 多 Agent"Milestone（聚焦 s09~s11） | M2 Step 11（可选）延期未做时 | A. M3 专做；B. 合并进 M3 的一小节；C. 继续缓 | B | M2 Step 11 的 DreamTask POC 结论 |
| D-ROAD-4：是否把 `EvaluationRunner` 替换为外部 SWE-bench harness | M2/M3 期间 Runner 可复现性若持续不达标时 | A. 外包；B. 维持自研 | B | `R-EV-1` 实际发生概率 + 自研 Runner 稳定度 |
| D-ROAD-5：是否引入向量搜索 backend（qdrant / hybrid） | wiki 节点 ≥ 200 且 p95 query > 2s 时 | A. 启用向量；B. 仅 BM25 | A | `RnD-Analysis` OP-05 + wiki-lint 数据 |

新决策点在本表登记后，才允许被 `M*-plan.md` / ADR 引用。

---

## 7. 与其他文档的交叉引用

- `docs/PRD.md §9/§10`：KPI 与 Milestone 的产品侧承诺；本文件 §4 对齐但不替代。
- `docs/TRD.md §2 ~ §6`：分层架构与 Harness 层次；本文件 §3 冻结粒度与 TRD 对齐。
- `docs/SPEC.md` 版本与冻结：由 `spec-change-policy.md` §3/§7 权威承载；本文件 §3 是可读索引。
- `docs/risk-register.md`（A-2）：`R-*` 风险在执行期间的状态变化；本文件只提 Milestone 级别风险承接。
- `docs/adr/**`（A-3）：任一路线图决策（§6 表中任一行）的落实都走 ADR。

---

## 8. 更新节律

- 每个 Milestone 的 retrospective 合入后，必须更新本文件 §2 / §3 / §4 / §6；§5 依赖图仅在 Milestone 结构发生变化时更新。
- 本文件升版规则同 `documentation-rules.md` §5（vX.Y）。

---

## 9. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；承接 PRD §10 与 M0/M1/M2-plan，锁定冻结基线、KPI 横切、M3+ 决策分支。 |
