# 测试策略（Test Strategy）

- 版本：v1.0（2026-04-19）
- 作者：dy
- 适用范围：`src/phoenix/**` 全部实现代码；`tools/**` 下的 CI 脚本；`docs/teaching/` 的 ingest / lint 链路。SPEC / 规则 / ADR / 教学 artifact 的文本校验另由 `ci-check-*.py` 承担，不重复在测试层覆盖。
- 上位依据：`docs/quality/definition-of-done.md` §3（E-5 / E-6 错误路径与不破坏既有）、`docs/SPEC.md` §5.2（5 步验证链）、`docs/rules/harness-flags-policy.md` §8、`docs/rules/spec-change-policy.md` S-REPRO-*。
- 下位依据：`docs/quality/code-review-checklist.md`（reviewer 侧对本策略的执行校验）、`docs/quality/acceptance-checklist.md` §3.2（E-* 勾选）。

---

## 1. 本策略存在的理由（Why）

`definition-of-done.md` 的 E-5 / E-6 两条（"错误路径被验证" / "不破坏既有"）只给出了定性要求；没有具体的"什么层写什么测试、到什么覆盖率、哪些是阻塞"。该模糊区间过去被用作豁免的借口。本策略把它们硬化为：

1. **分层测试金字塔**：unit / integration / e2e / replay 四档，每档有明确定义与职责边界。
2. **按层差异化的覆盖率门限**：Safety-Critical 层（`phoenix.harness.*` / `phoenix.memory.*`）门限最高；I/O 密集层适度放宽。
3. **INV-* 必须 1:1 对应守护测试**：任一不变量若无单独的负面用例，即视为未达标。
4. **HarnessFlags gate 矩阵**：每个 flag 的 gate Milestone 必须同批引入 default=off / default=on / 跨 flag 依赖三类测试。
5. **Auto-Research 回放复现性**：每个被 Kept 的变更必须产出可回放的 golden case，绑定 `spec_version`。

上述五项共同保障"工程 ∧ 学习 ∧ 记忆"三达标中工程维度的证据可追。

---

## 2. 术语

| 术语 | 定义 |
|---|---|
| **Golden Set** | 被录制并冻结的真实任务回放集；每个条目含 prompt、预期输出摘要、`spec_version` 锚点 |
| **Recording 模式** | E2E 层对外部 LLM / 工具调用录制响应；Replay 层读取录制而非实发请求 |
| **Negative Test** | 只验证失败路径的测试（拒绝、超时、回滚、重试）；E-5 条款的唯一认证形式 |
| **Smoke** | 仅验证"进程可启动且关键命令不崩"的最简路径，不断言业务正确性 |
| **Regression Gate** | Milestone 收尾或 PR 合入前必须通过的最小测试子集 |

---

## 3. 测试分层

### 3.1 分层矩阵

| 层 | 目标 | 典型目录 | 速度上限（单 case） | 外部依赖 |
|---|---|---|---|---|
| **Unit** | 单函数 / 单类 / 单 dataclass 的纯逻辑 | `tests/unit/**` | 1 s | 无；禁 I/O；禁网络 |
| **Integration** | 多模块协作；真实 SQLite / 文件 MemoryBackend；本地 fake LLM | `tests/integration/**` | 10 s | 本地文件 / SQLite；fake LLM fixture |
| **E2E** | 完整 `phoenix run` / `phoenix memory ingest` / `phoenix eval` 走通 | `tests/e2e/**` | 60 s | 本地 + 录制的模型响应（recording 模式） |
| **Replay** | 从 `tests/replay/golden/*.yaml` 回放 Golden Set | `tests/replay/**` | 120 s | 只读 Golden Set；禁实发模型调用 |

### 3.2 运行时机

| 分层 | PR 触发 | nightly | 本地 pre-commit |
|---|---|---|---|
| Unit | 全跑 | 全跑 | 全跑 |
| Integration | 全跑 | 全跑 | 受影响子集（`pytest -k <layer>`） |
| E2E | 受影响子集 | 全跑 | 手动触发 |
| Replay | Regression Gate 子集 | 全跑 | 手动触发 |

PR 触发覆盖的子集由 CI 根据改动路径自动挑选（见 §8）；nightly 全跑失败会在 `R-AR-*` / `R-HR-*` 登记。

### 3.3 禁止事项

- **TS-BAN-1**：禁止 unit 层 mock `HarnessFlags` 对象；应直接构造 frozen 实例。
- **TS-BAN-2**：禁止 integration 层 mock MemoryBackend；必须使用真实 SQLite / 文件实现。Mock 会让 `R-MM-*` 相关的真实 I/O 缺陷逃逸。
- **TS-BAN-3**：禁止 e2e 层直接 assert 模型自然语言输出相等；应断言结构化字段（`ToolCall` 列表、最终状态、副作用文件集）。
- **TS-BAN-4**：禁止 replay 层访问网络；检测到出网一律视为 Golden Set 录制不完整。

---

## 4. 覆盖率门限

按模块分档（`pytest --cov` 行覆盖 line / 分支覆盖 branch）：

| 模块 | line | branch | 备注 |
|---|---|---|---|
| `phoenix.harness.*` | 90% | 85% | Safety-Critical；ADR-0001 后加入 frozen 相关测试门槛 |
| `phoenix.memory.*` | 90% | 85% | INV-MM-* 守护密集 |
| `phoenix.runtime.*` | 85% | 80% | 主循环 + 5 步验证链 |
| `phoenix.tools.*` | 80% | 75% | 新增 Tool 时下限抬高到 85% |
| `phoenix.eval.*` | 75% | 70% | I/O 密集；E2E 补偿 |
| `phoenix.research.*` | 70% | 65% | Generator / Evaluator 外部依赖重 |
| `phoenix.teaching.*` | 70% | 65% | ingest / lint 为主；CLI 面只 smoke |
| `phoenix.cli.*` | 60% line；branch 不强制 | — | e2e 层补足 |

- **TS-COV-1**：PR 级别允许覆盖率下降 ≤ 1 个百分点；超过必须在 PR 描述写"降幅理由"，并在 `risk-register.md` 登记或说明为什么不登记。
- **TS-COV-2**：Milestone 收尾时门限必须达标；不达标的模块禁止冻结接口（与 `roadmap.md §3` 冻结节律挂钩）。
- **TS-COV-3**：覆盖率是 **达标门槛** 而非 **目标**；绝对数字 100% 本身不被奖励；测试质量由 §5 INV 守护与 §6 Flag 矩阵判定。

---

## 5. INV-* 守护测试（Invariant Guards）

**TS-INV-1**：SPEC 中每条 `INV-<layer>-N` 必须有 ≥ 1 个 **单独命名**、以 `test_inv_<layer>_<n>_*` 开头的 unit 或 integration 测试。命名是锚点，方便未来 ADR 推翻某个 INV 时批量定位。

**TS-INV-2**：每个 INV 测试必须包含：
- 1 条 **正面断言**（执行合规路径不违反）
- 1 条 **负面断言**（人为制造违反条件，断言系统以 `ValidationError` / `PermissionDenied` / `RuntimeError` 之一明确失败，不允许静默通过）

**TS-INV-3**：SPEC Minor 变更删除 / 重命名某条 INV 时，对应 `test_inv_*` 测试必须同 PR 删除或改名；孤儿测试在 CI 中会被 `ci-check-spec.py` 的 INV 闭环校验捕获（未来扩展）。

**TS-INV-4**：新增 INV 的 PR 若未含对应 `test_inv_*`，视为 DoD E-1 未达标；reviewer 侧由 `code-review-checklist.md` 对应条目把关。

### 5.1 已冻结 INV 守护清单（v1.1 基线）

| INV 组 | 代表条款 | 守护测试位置 |
|---|---|---|
| INV-RT-* | 主循环 / PhoenixContext 不变量 | `tests/unit/runtime/test_inv_rt_*.py` |
| INV-ML-* | ModelClient 契约 | `tests/integration/model/test_inv_ml_*.py` |
| INV-HR-* | Harness 叠加顺序 / HarnessFlags 语义 | `tests/unit/harness/test_inv_hr_*.py` |
| INV-PL-* | PluginRegistry 注册幂等 | `tests/unit/plugin/test_inv_pl_*.py` |
| INV-MM-* | Memory 不重复 / 不污染 | `tests/integration/memory/test_inv_mm_*.py` |
| INV-EV-* | Evaluation 可复现 | `tests/integration/eval/test_inv_ev_*.py` |
| INV-AR-* | Auto-Research 预算 / 可控性 | `tests/integration/research/test_inv_ar_*.py` |
| INV-TL-* | Teaching ingest / tier 规则 | `tests/unit/teaching/test_inv_tl_*.py` |

实际文件在各层实现 Milestone 落地时创建；M1 Step 1 之前本表仅为占位契约。

---

## 6. HarnessFlags Gate 测试矩阵

每个 flag 在其 gate Milestone 必须同批引入以下三类测试（对齐 `harness-flags-policy §3` 表）：

**TS-FLAG-1**：`test_flag_<sNN>_default_off`：断言 default=False 时功能不启用、不消费 token、不产生副作用。
**TS-FLAG-2**：`test_flag_<sNN>_enabled`：断言 default=True 或 override=True 时功能正确启用。
**TS-FLAG-3**：`test_flag_<sNN>_dependencies`：若 HF-ATOMIC-2 列出跨 flag 依赖，验证依赖校验在 `__post_init__` 中拦截非法组合。

### 6.1 Safety-Critical 专项

对齐 HF-SEC-1 + ADR-0001：

**TS-FLAG-SC-1**：`test_harness_flags_frozen`：尝试 `flags.s01_main_loop = False` 必须 raise `FrozenInstanceError`。
**TS-FLAG-SC-2**：`test_harness_flags_replace_produces_new_instance`：`dataclasses.replace(flags, s03_planning=False)` 返回对象与原对象 `is not` 且两者 field 差异仅在指定字段。
**TS-FLAG-SC-3**：`test_safety_critical_default_true`：断言 s01 / s02 / s12 在未 override 时的 default 为 True；任何测试 fixture 若倒转此默认必须显式标注 `safety_override` 并在 CI 级别禁止进入 main 分支的 baseline。

这三条是 ADR-0001 §8 follow-up 的执行落点；M1 Step 1 起必须实现。

---

## 7. Auto-Research 回放链路

### 7.1 Kept 变更的 Golden 录制

**TS-AR-1**：任一 `experiment-report.md` 将变更标为 `Kept` 时，同 PR 必须新增 `tests/replay/golden/<experiment-slug>.yaml`：
- `prompt`: 原始任务
- `spec_version`: 录制时的 SPEC 版本
- `model_profile`: 录制使用的 Generator / Evaluator 配置
- `expected`: 结构化断言集（工具序列、最终文件 diff 的 hash、memory digest 指纹）

**TS-AR-2**：Replay 层读取该 yaml；若 `current_spec_version` 跨 Major 或 pulled 时 digest 指纹漂移超阈值（默认 5%），测试转为 `xfail` 并触发 `R-AR-1` 状态复核，而非直接 fail。

### 7.2 Discarded 变更的反例留存

**TS-AR-3**：`Discarded` 变更同样 ingest 为 F-* 或 experiment-report，但不产生 replay yaml；其价值是"失败是一等信息"（见 `learning-artifact-rules`），测试维度不占位。

### 7.3 复现性门槛

**TS-AR-4**：整份 Golden Set 在 nightly 全跑通过率 ≥ 90% 视为 `R-AR-1` 缓解成立；低于 90% 连续 2 次则 `R-AR-1` 转 `triggered`，触发 ADR。

---

## 8. CI 集成与本地运行

### 8.1 PR 触发链

```
phoenix-doctor.sh --strict
  └─ ci-check-spec.py        → 0 error
  └─ ci-check-adr.py         → 0 error
  └─ ci-check-flags.py       → 0 error
  └─ ci-check-teaching.py    → 0 error（如动到 docs/teaching/）
  └─ ci-check-milestone-dod.py → 0 error（如动到 milestones/）
pytest tests/unit -q
pytest tests/integration -q -m "not slow"
pytest tests/e2e -q -k "<changed-layer>"      ← 按 diff 挑选
pytest --cov=phoenix --cov-fail-under=<per-module-threshold>
```

### 8.2 Nightly 追加

```
pytest tests/e2e -q                    ← 全跑
pytest tests/replay -q                 ← Golden Set 全回放
pytest tests/integration -q -m slow    ← 被标 slow 的用例
```

### 8.3 本地开发推荐

- 每次 commit 前：`pytest tests/unit -q`（秒级）。
- 每次 PR 前：执行 §8.1 全链。
- 调试单 INV 守护：`pytest -k "test_inv_hr_"`。

### 8.4 CI 占位与交付节律

- 本文件所列门限在 M1 Step 1 启动前不产生阻塞（无实现代码可跑）；一旦 `phoenix.harness.*` / `phoenix.runtime.*` 首个 PR 提交，§4 门限即生效。
- `tools/ci-check-coverage.py`（占位，C-11 后续）将在 M1 末期交付，覆盖 §4 的门限自动判定。

---

## 9. 与其他规则 / 文档的交叉

- `docs/quality/definition-of-done.md` §3 E-5 / E-6：本文件是其具体化载体。
- `docs/quality/code-review-checklist.md`（C-4）：reviewer 侧核验测试分层是否匹配变更性质。
- `docs/quality/acceptance-checklist.md` §3.2：E-* 勾选时的证据格式（日志路径 / commit hash）必须对齐本文件 §8 的输出。
- `docs/rules/harness-flags-policy.md` §8：Flag default 翻转 PR 的测试要求具体落到本文件 §6。
- `docs/rules/spec-change-policy.md` §7 冻结节律：§4 覆盖率门限对齐冻结时机。
- `docs/risk-register.md`：`R-AR-1` / `R-HR-*` / `R-MM-*` 的缓解证据均引用本文件 §5 / §6 / §7 产出的测试。
- `docs/adr/ADR-0001-harness-flags-frozen.md` §8：§6.1 三条是其 follow-up 执行点。

---

## 10. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-19 | 首版；锁定四档金字塔、分层覆盖率门限、INV 守护 1:1 规则、HarnessFlags gate 三类测试矩阵（含 ADR-0001 frozen 三条）、Auto-Research Golden 回放链；与 C-2 acceptance-checklist + C-4 code-review-checklist + `harness-flags-policy` §8 打通。 |
