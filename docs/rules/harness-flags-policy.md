# HarnessFlags 治理策略（Harness Flags Policy）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：`SPEC v1.1 §5.1 HarnessFlags` 中定义的 `s01_main_loop` ~ `s12_worktree` 共 12 个机制开关，以及 `memory_digest_on_finish` 这类"非 sNN 前缀"的 Harness 级 flag。
- 上位依据：PRD §10（Harness 12 层推进顺序）、TRD §5（决策 D-HR-1/2/3）、SPEC v1.1 §5.1/§5.2/§5.3。
- 下位依据：`spec-change-policy.md`、`git-workflow.md`、`definition-of-done.md`、`acceptance-checklist.md`。

---

## 1. 本规则存在的理由（Why）

`HarnessFlags` 是 PhoenixAgent 的总开关盘：打开 / 关闭它直接决定 Agent 行为（是否规划、是否压缩、是否可 spawn 子代理、是否隔离 worktree）。但它有三条内生矛盾：

1. **Harness 层的核心创新在"叠加顺序"**：PRD 在 Harness 12 层推进顺序条款指出每层叠加会让 Resolved Rate 阶跃；无序翻转会污染实验结论（对齐 `R-AR-1`）。
2. **关键安全性依赖少数 flag**：`s12_worktree` / `s02_tool_dispatch` / `s01_main_loop` 中任一关闭都会使整个 Agent 不安全或不可运行（SEC-02、INV-RT-* 条款）。
3. **Milestone 期间默认值必须可控**：若每次实验都随手改 default，评测不可复现（违反 `spec-change-policy` S-REPRO-*）。

因此本规则把"每个 flag 的归属 Milestone + 默认值 + 翻转流程 + 实验窗口 + 回滚预案"全部显式化。任一 flag 的 default 翻转都等同于 SPEC Minor 变更，必须走 ADR。

---

## 2. 术语

| 术语 | 定义 |
|---|---|
| **Default** | `SPEC v1.1 §5.1` 中 dataclass 字段上的默认值；所有未显式覆盖的启动都用这个值 |
| **Experimental Override** | 在单次运行 / Auto-Research 轮次内通过 CLI / `PhoenixContext` 覆盖的 flag 值；不改 default |
| **Flip** | 修改 default 本身（SPEC v1.1 §5.1 内字段默认值变更）；等同 SPEC Minor |
| **Gate Milestone** | 本 flag 首次允许 default = True 的 Milestone；见 §3 |
| **Safety-Critical Flag** | 关闭会直接违反 `INV-*` / `SEC-*` 的 flag：当前 `s01` / `s02` / `s12` |

---

## 3. Flag 清单与治理状态

以 `SPEC v1.1 §5.1` 为权威源；本表新增"治理字段"（Gate Milestone / 当前 default / 翻转约束 / 监控指标）。若 SPEC 版本升级导致字段增删，本表必须同 PR 同步。

| Flag | SPEC default | Gate Milestone | 当前治理状态 | 安全分级 | 关键监控指标 | 翻转约束 |
|---|---|---|---|---|---|---|
| `s01_main_loop` | True | M0 | Locked-True | Safety-Critical | 循环断点回收率 / 每循环 p95 延迟 | 不允许 False（见 §4.1） |
| `s02_tool_dispatch` | True | M0 | Locked-True | Safety-Critical | 工具调用失败率 | 不允许 False（见 §4.1） |
| `s03_planning` | True | M1 | Active | Non-Safety | Plan 长度 / 完成率 | 仅 Experimental Override 可为 False |
| `s04_subagent` | False | M1 | Gated-Off | Non-Safety | subagent 成本 / 子任务通过率 | M1 Step 4 后允许提案 flip |
| `s05_knowledge_skills` | False | M1/M2 | Gated-Off | Non-Safety | skill 命中率 / token 节省率 | M1 Step 5 之后允许提案 flip |
| `s06_compression` | True | M1 | Active | Non-Safety | 压缩触发频率 / 后续成功率 | 冻结期不允许 flip |
| `s07_persistence` | True | M1 | Active | Non-Safety | 断点恢复成功率 | SQLite schema 变动一起走 Minor |
| `s08_background` | False | M2 | Gated-Off | Non-Safety | 后台任务死锁率 | M2 Step 11 评估后再议 |
| `s09_team` | False | M2+ | Gated-Off | Non-Safety | 团队协作失败率 | M3+ roadmap D-ROAD-3 后再议 |
| `s10_protocols` | False | M2+ | Gated-Off | Non-Safety | 消息丢失率 | 同 s09 |
| `s11_autonomous` | False | M2+ | Gated-Off | Non-Safety | 自主规划偏移率 | 同 s09 |
| `s12_worktree` | True | M0 | Locked-True | Safety-Critical | 逃逸事件 / worktree 泄漏 | 不允许 False（见 §4.1；对齐 SEC-02） |
| `memory_digest_on_finish` | True | M0 | Active | Non-Safety | digest 耗时 / 失败率 | 冻结期不允许 flip |

### 3.1 治理状态字段说明

- `Locked-True` / `Locked-False`：默认值不允许变更；关闭将直接违反不变量。
- `Active`：默认值当前为 True 且稳定；翻转走 Minor。
- `Gated-Off`：默认为 False，未达 gate 条件；翻转前必须通过 §5 gating 流程。
- `Gated-On`（未来可能）：某 flag 从 True 反向 flip 到 False 作为默认（极少数退化场景）。

---

## 4. 硬约束

### 4.1 安全关键 flag

**HF-SEC-1**：`s01_main_loop` / `s02_tool_dispatch` / `s12_worktree` 默认值锁定为 True；**永远不允许** flip 到 False 作为 default。

- 理由：
  - `s01=False` 等于无主循环，直接违反 `INV-RT-1/2/3`。
  - `s02=False` 等于无工具分发，所有 `ToolCall` 无处可执行。
  - `s12=False` 违反 `TRD SEC-02`（代码改动必须在 worktree 内）+ `R-HR-3` 缓解动作失效。
- 例外：某些 benchmark / 回归测试允许单次 Experimental Override = False（仅用于 harness 绕过基线对照实验），且必须：
  1. 在 `experiment-report.md` 首部标注 `safety_override: s<NN>` + 原因；
  2. 禁止将该 override 结果用于任何 KPI 达成判定；
  3. 不得走入 main 分支的默认配置。

### 4.2 冻结期

**HF-FREEZE-1**：与 `spec-change-policy` §7 冻结期一致：

| 冻结窗口 | 冻结范围 |
|---|---|
| Milestone 结束 → 下一 Milestone Step 1 | 所有 flag 的 default 禁止翻转 |
| Auto-Research 单轮内 | 轮次锁定的 flag 清单禁止翻转（Generator 若要翻转需开新轮次） |

- `HarnessFlags` 默认值是 SPEC v1.1 §5.1 内容；任一翻转同时是 SPEC Minor 变更，因此自然受 `spec-change-policy` §7 约束。本规则额外要求：**即使同 Milestone 内，safety-critical flag 的 Experimental Override 也必须事先登记**。

### 4.3 单 PR 原子性

**HF-ATOMIC-1**：单次翻转 PR 只涉及一个 flag；不得批量翻转。
**HF-ATOMIC-2**：若翻转依赖其他 flag 同时为真（例如 `s04 = True` 需 `s01 = True`），必须在 ADR 中显式列出依赖；实现侧在 `HarnessFlags.__post_init__` 中做一致性校验。

### 4.4 实现约束

**HF-IMPL-1**：`HarnessFlags` dataclass 必须为 frozen；修改只能通过 `replace(...)` 产生新实例（与 INV-RT-* 一致）。
**HF-IMPL-2**：Flag 消费点必须出现在 SPEC v1.1 §5.1 与 §5.3 对应的模块路径下；禁止在非 `phoenix.harness.*` 模块读取 HarnessFlags 字段（`memory_digest_on_finish` 由 `phoenix.memory.*` 读取属允许例外并须在 SPEC 内显式标注）。
**HF-IMPL-3**：CLI 层（`phoenix run`）允许以 `--harness-flag sNN=true/false` 方式做 Experimental Override；实现必须打日志并写入 `PhoenixContext.session.flag_overrides`。

---

## 5. Default 翻转流程（Gating）

任一 flag 从 False → True 或反向的 default 翻转必须走本流程：

### Step 1 — 动机 ADR
- 在 `docs/adr/ADR-NNNN-flag-<sNN>-default.md` 登记决策。
- ADR `related_flag` 字段填对应 sNN；`related_spec` 填目标 SPEC 版本。
- 必须列出 "不翻转的代价" + "翻转后的预期收益"；仅靠"默认值更合理"不构成理由。

### Step 2 — 实验证据
- 在翻转前必须有 ≥ 1 份证据（二者择一或兼有）：
  - Auto-Research 轮次：同基准下对比"flag=False vs True"的 Resolved Rate / 长程任务完成率 / 成本。
  - 回归实验：在 ≥ 10 个固定任务上运行，统计稳定性 / 失败率 / 监控指标（见 §3 列）。
- 证据必须以 `experiment-report.md` 形式落入 `docs/teaching/M<N>/experiments/<slug>/`。

### Step 3 — SPEC Minor 变更
- 修改 `SPEC v1.1 §5.1` 中 dataclass 的默认值；版本号递增 Minor。
- 同 PR 通过 `ci-check-spec.py`。

### Step 4 — 依赖校验更新
- 在 `HarnessFlags.__post_init__` 更新 HF-ATOMIC-2 一致性校验（若新翻转引入了跨 flag 依赖）。

### Step 5 — 教学追认
- 新增或修订一个 foundations F-* 节点，标题形如 `F-<idx>-flag-<sNN>-default-flip`。
- `frontmatter.related_spec` 指向新 SPEC Minor 版本号；`frontmatter.related_flag: [sNN]`。

### Step 6 — Runbook 更新
- 更新 `docs/milestones/M<N>-plan.md` 的 Step 中若涉及该 flag 的命令示例。
- 更新 `risk-register.md` 受影响行的 evidence / next_review。

翻转完成后，对应 flag 治理状态从 `Gated-Off` 变为 `Active`（或反向）；本文件 §3 表必须同 PR 更新。

---

## 6. Experimental Override 规则

非 default 变更的"单次运行内覆盖"比翻转轻量，但仍有下列约束：

| 场景 | 允许 | 约束 |
|---|---|---|
| 作者本地交互调试 | 是 | 无额外约束；不进 main |
| Auto-Research Generator 提案 | 是 | 必须在 `experiment-report.md` 记录所有 override 值 |
| Benchmark 对照实验 | 是 | 对照组必须显式记录 override；若结果用于 KPI 达成判定则必须使用 default 值 |
| Agent 自我驱动的改写 | 需 PermissionRules 放行 | `PhoenixContext` 中 flag_overrides 必须打日志；reviewer 可追 |
| 用户 UI 交互 | 是 | 当次会话内生效；session 结束即销毁 |

**HF-OVR-1**：Experimental Override 不是 default 翻转的替代品。若在 ≥ 3 次独立实验中连续依赖相同 override，必须走 §5 flip 流程正式化。
**HF-OVR-2**：Safety-Critical flag 的 override 仅允许"True → False"的方向，且按 §4.1 例外条款登记；禁止将 override 结果推广为 default。

---

## 7. 与其他规则 / 文档的交叉

- `docs/rules/spec-change-policy.md §4.2`：flag default 翻转 = SPEC Minor；§5 流程并入本文件 §5。
- `docs/rules/git-workflow.md §4.2 / §4.3`：flag 翻转 PR 归类为 `spec/*`，含对应 ADR。
- `docs/quality/definition-of-done.md`：任一 DoD 条款若依赖特定 flag（如 DoD-M1-2 依赖 s01/s02/s03/s04/s06/s07/s12），flag 翻转会触发 DoD 重评。
- `docs/risk-register.md`：flag 翻转会影响 `R-HR-*` / `R-AR-*` 的状态；必须同步 `evidence`。
- `docs/roadmap.md §3`：Milestone 结束冻结 `HarnessFlags` 整体字段布局；本规则 §3 的 gate 列与 roadmap 冻结节律一致。

---

## 8. CI 与校验点

| 检查 | 对应约束 | 行为 |
|---|---|---|
| SPEC 中 HarnessFlags default 与本文件 §3 表一致 | §3、HF-ATOMIC-1 | 阻塞（C-6 扩展） |
| Flag 翻转 PR 含 ADR 链接 | §5 Step 1 | 阻塞 |
| Flag 翻转 PR 含 `experiment-report.md` | §5 Step 2 | 阻塞（C-6 扩展 / C-9） |
| `HarnessFlags` dataclass 保持 frozen | HF-IMPL-1 | 阻塞（静态检查 / test） |
| Safety-Critical flag default = True | HF-SEC-1 | 阻塞（单元测试 + `ci-check-spec.py`） |
| 非 `phoenix.harness.*` 模块读取 HarnessFlags 字段 | HF-IMPL-2 | 阻塞（静态扫描，future） |
| `phoenix run --harness-flag` 可用且日志可追 | HF-IMPL-3 | 集成测试 |

CI 扩展落在 `tools/ci-check-flags.py`（占位版已交付：校验 SPEC v1.1 §5.1 字段与本文件 §3 表一致、Safety-Critical default、HarnessFlags frozen=True；未覆盖 HF-IMPL-2 静态扫描与 HF-IMPL-3 集成测试，待后续批次补齐）；在完整落地前由 reviewer 人工核对剩余项。

---

## 9. 违规与事后处理

| 违规 | 处置 |
|---|---|
| 冻结期内 flip default | PR 阻塞；若误合入必须紧急 ADR + revert（见 `git-workflow §8`） |
| Safety-Critical flag default = False | PR 阻塞；零容忍；已合入视为 P0 事故，按 `spec-change-policy` S-FREEZE-2 处理 |
| override 结果被误用于 KPI 达成判定 | 对应 KPI 作废；retrospective 登记 |
| 跨 flag 依赖未校验导致启动崩溃 | 新 ADR + 单元测试补全 HF-ATOMIC-2 |

---

## 10. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；锁定 12 flag 治理状态、gate 节律、翻转流程、Safety-Critical 零例外；与 spec-change-policy / git-workflow / DoD / risk-register / roadmap 打通。 |
