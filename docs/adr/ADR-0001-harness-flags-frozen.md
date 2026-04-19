---
id: ADR-0001
title: HarnessFlags dataclass 声明 frozen=True 以硬化不可变语义
status: Accepted
date: 2026-04-19
authors: [dy]
related_spec: v1.1
related_dod: []
related_risk: [R-HR-1, R-HR-2, R-HR-3, R-AR-1]
related_flag: [s01, s02, s12]
superseded_by: null
---

# ADR-0001：HarnessFlags dataclass 声明 frozen=True 以硬化不可变语义

- 状态：Accepted
- 日期：2026-04-19
- 作者：dy
- 摘要：SPEC v1.0 §5.1 的 `HarnessFlags` 目前仅以普通 `@dataclass` 声明，实例可变；harness-flags-policy HF-IMPL-1（第三波引入）要求其为 frozen。本 ADR 把 SPEC 升到 v1.1，给 `HarnessFlags` 加 `frozen=True`，让不可变语义由语言层静态保证。

---

## 1. 背景（Context）

- 现状：
  - `docs/SPEC.md:339-354` 声明 `@dataclass class HarnessFlags`（可变）。
  - `docs/rules/harness-flags-policy.md §4.4` 在第三波交付时新增 **HF-IMPL-1**：`HarnessFlags` dataclass 必须为 frozen；修改只能通过 `dataclasses.replace(...)` 产生新实例（与 INV-RT-* 一致）。
- 触发事件：2026-04-19 `tools/ci-check-flags.py`（占位版 C-9 / B-4 后置交付）首跑即捕获 HF-IMPL-1 drift：SPEC 未同步 policy 新增约束。
- 既有规则 / 文档指向：
  - `docs/rules/harness-flags-policy.md §4.4`（policy 侧硬约束）。
  - `docs/rules/spec-change-policy.md §4.2`（SPEC Minor 变更流程 = ADR + SPEC 改动 + 版本号递进）。
  - `docs/adr/ADR-0000-adopt-adr.md §8 follow-up`（明示 ADR-0001 在 `self-runtime` 首次 SPEC 变更处落地，本次正好对齐）。

## 2. 问题（Problem）

- **核心问题**：policy HF-IMPL-1 自第三波起成立，但 SPEC v1.0 未同步升级；若不决策，policy 约束沦为空条款，CI 长期挂一条 error，"治理文件 ↔ 权威 SPEC"一致性破功。
- **不决策的代价**：
  1. `s01 / s02 / s12` 等 Safety-Critical flag 可在运行中被 `ctx.harness_flags.sNN = False` 绕过（HF-SEC-1 例外条款失效）且无显式审计路径。
  2. Auto-Research Generator 在同一次会话内原地改 flag 将使 experiment-report 无法精确记录"本轮实际使用的 flag 向量"，污染 `R-AR-1` 复现性。
  3. Runtime 主循环里把 `HarnessFlags` 当配置快照读；若 helper 误改，破坏 INV-RT-1/2/3。

## 3. 候选方案（Options）

### 3.1 方案 A：`@dataclass(frozen=True)` + 所有修改走 `dataclasses.replace(...)`

- 描述：在 SPEC v1.1 §5.1 的 dataclass 装饰器加 `frozen=True`；语言层保证属性只读；CLI `--harness-flag` 覆盖（HF-IMPL-3）已天然经 `replace()` 创建新实例，与本方案零摩擦。
- 优点：
  - 零运行时成本；静态保证一劳永逸。
  - `__setattr__` 在 frozen dataclass 上会抛 `FrozenInstanceError`，误用必然在测试期暴露，比运行时 guard 更早。
  - 现存 SPEC 里 3 处 `ctx.harness_flags.*` 全为读操作（`SPEC.md:162/178/182`），改动不破坏任何示例代码。
- 缺点：
  - 后续若出现"必须原地改 flag"的真实需求（目前看不到），需要新 ADR 撤销；小概率但存在。
- 成本 / 复杂度：**极低**。SPEC 改一行；无代码实现层影响（实现层尚未启动）。

### 3.2 方案 B：保持可变 `@dataclass`；Runtime 入口深拷贝 + 运行时 guard

- 描述：SPEC 不动；由 `phoenix.harness.loop` 在 Task 入口处 `copy.deepcopy(harness_flags)` 切断外部引用；对 Safety-Critical flag 增加"写拦截"装饰器。
- 优点：
  - 不改 SPEC，不需要 Minor bump。
- 缺点：
  - 约定式保护靠后续代码自律；任一 Runtime 之外的消费点（比如教学 artifact 的示例）都可绕过。
  - 与 HF-IMPL-2（"Flag 消费点必须出现在 `phoenix.harness.*`"）组合后实际只保护了一层；其它层若读到已被改的实例仍然污染复现性。
  - 运行时成本（深拷贝 + guard 分支）虽小但非零；且错误只能在运行时暴露，不如 `FrozenInstanceError` 在单元测试期即失败。
- 成本 / 复杂度：**中**。SPEC 不动；实现侧复杂度上升。

### 3.3 方案 C：迁移到 Pydantic `BaseModel` 并设置 `model_config = {"frozen": True}`

- 描述：放弃 `dataclass`，改用 Pydantic v2 frozen model，顺带获得 schema 导出与 JSON 序列化能力。
- 优点：
  - 除 frozen 之外额外收获 schema；CLI override 参数天然可校验。
- 缺点：
  - 引入新三方依赖（与当前 SPEC v1.1 §0 约定"类型签名使用 `typing` + `dataclasses`"冲突）。
  - 体量远超"加一个装饰器参数"的本次需求，属于过度设计（违反开发原则 "Don't design for hypothetical future requirements"）。
- 成本 / 复杂度：**高**。需要同步改 `spec-change-policy` 里的 dataclass 约定与多处代码示例。

## 4. 决策（Decision）

- 采用方案：**A**（`@dataclass(frozen=True)`）。
- 判定依据：
  1. 语言层静态保证 > 运行时约定（与 INV-RT-* 一致性最强）。
  2. SPEC 现有代码示例全为读，零回归风险（已 grep 验证 `docs/SPEC.md:162,178,182` 三处仅读）。
  3. CLI override 路径（HF-IMPL-3）已经通过新实例实现，无需改动。
  4. 改动面最小：SPEC 一行；本 ADR 自身；三条 CI 脚本不需要改。
  5. 借本次把 ADR-0000 §8 follow-up 中"首次真实 ADR"这一条目就地落地，验证 ADR 模板 + CI + frontmatter 链路可用。
- 放弃 B：约定式保护有泄漏面且运行时成本非零，不如 frozen 彻底。
- 放弃 C：引入 Pydantic 与 SPEC v1.1 §0 约定冲突，且超出本次需求。

## 5. 影响面（Consequences）

- **代码影响**（预期）：`phoenix.harness.*`（尚未实现）今后修改 flag 必须走 `dataclasses.replace(...)`；CLI `--harness-flag` 覆盖路径天然匹配。
- **SPEC 影响**：`docs/SPEC.md` §5.1 装饰器从 `@dataclass` 改为 `@dataclass(frozen=True)`；版本号 `v1.0 → v1.1`（Minor，向后兼容——字段列表 / 默认值 / 类型全部不变，仅强化可变性语义）。
- **DoD / KPI 影响**：无。DoD-M1-* 的达标口径不依赖 flag 可变性。
- **教学 artifact 影响**：无。首个涉及 `HarnessFlags` 的 F-* 节点在 M1 Step 1 之后出现，届时将以 v1.1 为基线。
- **风险影响**：
  - `R-HR-1/2/3`（Harness 层错误 / 配置漂移 / 安全逃逸）缓解度提升；policy HF-IMPL-1 从"空条款"变为"有语言层保证"。
  - `R-AR-1`（Auto-Research 不可复现）缓解度提升；原地改 flag 路径关闭。
- **其他 ADR 影响**：无前置 ADR 被 supersede；本 ADR 是 `ADR-0000` 体系下的首个"真实 ADR"，正好兑现 ADR-0000 §8 follow-up。

## 6. 迁移与回滚（Migration & Rollback）

- 迁移步骤：
  1. 本 ADR（ADR-0001）合入 `docs/adr/`。
  2. `docs/SPEC.md` 首部 `- 版本：v1.0 → v1.1`、`- 日期：2026-04-18 → 2026-04-19`。
  3. `docs/SPEC.md §5.1` 装饰器 `@dataclass → @dataclass(frozen=True)`。
  4. `docs/SPEC.md` 追加 §19 变更日志（顺带清掉 D-CHANGELOG 告警）。
  5. 重跑 `tools/ci-check-adr.py` / `tools/ci-check-flags.py` / `tools/ci-check-spec.py`，三者均 0 error。
- 回滚预案：
  - 若 M1 Step 1 实现阶段发现必须原地修改 flag 的场景（当前评估概率极低），通过新 ADR 撤回到 v1.0 语义，并在 Runtime 入口补深拷贝 + 写拦截（即本 ADR 的方案 B）。
  - 回滚窗口：M1 Step 1 实现完成前。一旦实现层写死 `replace()` 的用法，回滚成本递增。
- 本决策属可回滚类，不封闭未来演进。

## 7. 证据与参考（Evidence）

- `docs/rules/harness-flags-policy.md §4.4` HF-IMPL-1（policy 侧硬约束，第三波引入）。
- `docs/rules/spec-change-policy.md §4.2`（SPEC Minor 流程）。
- `docs/SPEC.md:339-354`（当前 `@dataclass` 定义，待改点）。
- `docs/SPEC.md:162 / :178 / :182`（现存 3 处 `ctx.harness_flags.*` 读操作；grep 验证无写）。
- `tools/ci-check-flags.py`（2026-04-19 占位版；首跑捕获 HF-IMPL-1 drift —— 本 ADR 的直接触发者）。
- `docs/adr/ADR-0000-adopt-adr.md §8 follow-up`（ADR-0001 首出对齐点）。

## 8. 后续行动（Follow-ups）

- [x] 本 ADR 合入 `docs/adr/`。
- [x] SPEC v1.0 → v1.1：装饰器改动 + 首部版本号 + 变更日志。
- [x] `ci-check-flags.py` 再跑，确认 HF-IMPL-1 error 消失。
- [x] `ci-check-adr.py` 再跑，确认 ADR-0001 通过命名 / frontmatter / 编号唯一校验。
- [x] `ci-check-spec.py` 再跑，确认新 SPEC 版本号被正确识别，无新增 error。
- [ ] M1 Step 1 实现层起步时：`phoenix.harness.flags`（或等价模块）单元测试必须覆盖 `FrozenInstanceError` 行为；CLI `--harness-flag sNN=true/false` 覆盖路径测试必须断言产生的是新实例。
- [ ] retrospective 登记：第三波交付（2026-04-18）→ ADR-0001 合入（2026-04-19）周转 1 天，作为"ADR 体系首跑"的基线学习数据。

---

## 修订记录

| 日期 | 状态变化 | 修订说明 |
|---|---|---|
| 2026-04-19 | Proposed → Accepted | 单人同批合入；改动面极小且 CI 证据闭环。 |
