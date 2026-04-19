# ADR 体系（Architecture Decision Records）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：`docs/adr/ADR-NNNN-<slug>.md` 全体；任一"带不可逆代价的架构 / 规则 / 决策"。
- 上位依据：`documentation-rules.md` §3.1（ADR-NNNN 归属）、`spec-change-policy.md` §5 Step 1、`definition-of-done.md` §9（DoD 豁免必须走 ADR）。
- 下位依据：`ADR-TEMPLATE.md`、`ADR-0000-adopt-adr.md`。

---

## 1. 本体系存在的理由（Why）

PhoenixAgent 的"单一真相源"由 PRD / TRD / RnD / SPEC 承担"**当前正确的做法**"；但这些文档不回答"**当初为什么这样做、放弃了哪些候选、按什么证据判断**"。缺失这个层面的记录会在三处出问题：

1. **SPEC 变更失去对照**：spec-change-policy §5 Step 1 要求登记"为什么要变"；若没有独立载体会被塞进 SPEC 正文，污染接口定义。
2. **DoD 豁免不可追溯**：DoD §9 要求任一阈值下调 / 条款豁免都走 ADR；没有 ADR 体系时会沦为 retrospective 里的一条普通注记。
3. **路线图决策点失忆**：`roadmap.md §6` 的 5 个决策分支在时间推进时需要回看"当时是基于什么证据倾向 B 而不是 A"。

所以本目录承载**决策的"为什么"**，与 Tier-0 的"是什么"明确分工。

---

## 2. 何时必须创建 ADR（Triggers）

任一下列情形必须创建 ADR（不是"可选"）：

| 触发 | 上位规则 | 关联文档 |
|---|---|---|
| SPEC Minor / Major 变更 | `spec-change-policy` §4.2/§4.3 + §5 Step 1 | 新 ADR → 修订 SPEC |
| DoD 条款豁免或阈值调整 | `definition-of-done` §9 | `ADR-NNNN-dod-exception-<slug>.md` |
| `risk-register` 任一 `R-*` 转入 `triggered` | `risk-register` §3 R-2 | `ADR-NNNN-risk-<id>-triggered.md` |
| `roadmap.md §6` 决策分支落地（D-ROAD-*） | `roadmap.md §6` | `ADR-NNNN-road-<slug>.md` |
| 冻结期破冻 | `spec-change-policy` S-FREEZE-2 | 紧急 ADR + retrospective 登记 |
| `HarnessFlags` 默认值翻转 | `harness-flags-policy` §5 | `ADR-NNNN-flag-<sNN>-default.md` |
| 接入 / 替换 / 下线一个硬接口的具体实现 | TRD §1 接口抽象原则 | `ADR-NNNN-impl-<layer>-<slug>.md` |
| 引入一个新顶级目录 / 新 Tier-2 规则文件 | `documentation-rules` D-DIR-1 | `ADR-NNNN-struct-<slug>.md` |

**不需要 ADR** 的变更：typo、格式、示例修正、纯重命名未引用的内部实现、测试用例增删（除非改变达标口径）。

---

## 3. 命名与编号

- **文件名**：`docs/adr/ADR-NNNN-<slug>.md`
  - `NNNN`：四位零填充；单调递增；**永不复用**。
  - `<slug>`：kebab-case、≤ 60 字符、`a-z0-9-`。
- **ID 稳定性**：ADR 一旦合入 main，标题中的编号与 slug 即冻结；内容可修订，但必须走"新追加 § 修订段"方式（见 §5）。
- **首编号**：`ADR-0000` 保留给 meta-ADR（本体系自证）；正式 ADR 从 `ADR-0001` 起。

---

## 4. 状态机

```
┌──────────┐    ┌──────────┐    ┌──────────────┐
│ Proposed │ -> │ Accepted │ -> │  Superseded  │
└────┬─────┘    └────┬─────┘    └──────┬───────┘
     │               │                 │
     ▼               ▼                 ▼
┌───────────┐   ┌──────────┐      （指向后继 ADR）
│ Rejected  │   │Deprecated│
└───────────┘   └──────────┘
```

| 状态 | 进入条件 | 约束 |
|---|---|---|
| `Proposed` | PR 打开 | 正文完整、影响面清楚、至少 1 个候选方案 |
| `Accepted` | PR 合入 | 决策明确；绑定相关 SPEC / DoD / flag 变更 |
| `Rejected` | PR 关闭但保留文件 | 必须写"为何拒绝"；避免将来重复提案再次讨论 |
| `Superseded` | 被新 ADR 取代 | 必须在首部写 `Superseded-By: ADR-NNNN` |
| `Deprecated` | 不再适用但无直接后继 | 必须写"为何不再适用"与建议做法 |

**禁止**删除任何已合入的 ADR；老旧内容通过状态流转处理。

---

## 5. 修订约定

- ADR 内容可追加修订段（标题 `## 修订 YYYY-MM-DD`），但**不可悄悄改写已记录的决策**。
- 若决策整体推翻，新建 ADR 并在旧 ADR 首部追加 `Superseded-By: ADR-NNNN`，将旧 ADR 状态改为 `Superseded`。
- 首部字段（`Status`、`Date`、`Superseded-By` 等）允许更新；正文主体内容仅允许追加。

---

## 6. 必备字段（frontmatter + 首部）

YAML frontmatter（机读）：

```yaml
---
id: ADR-0001
title: <一句话标题>
status: Proposed | Accepted | Rejected | Superseded | Deprecated
date: 2026-04-18
authors: [dy]
related_spec: v1.0            # 可选；SPEC 变更类 ADR 必填
related_dod: []               # 如 [DoD-M1-6]
related_risk: []              # 如 [R-RT-1]
related_flag: []              # 如 [s03]
superseded_by: null           # 或 ADR-NNNN
---
```

人读首部（紧随 frontmatter）：

- `标题`（与 frontmatter `title` 一致）。
- `状态`、`日期`、`作者`。
- 一段不超过 3 行的"决策一句话摘要"。

正文章节见 `ADR-TEMPLATE.md`。

---

## 7. 目录结构

```
docs/adr/
├── README.md                      ← 本文件
├── ADR-TEMPLATE.md                ← 复制后改名
├── ADR-0000-adopt-adr.md          ← 本体系自证
└── ADR-NNNN-<slug>.md             ← 所有正式 ADR
```

- **A-3 禁止**将 ADR 放在其他目录；`documentation-rules` D-DIR-1 已锁定。
- ADR 数量超过 100 后再考虑按年份分子目录，当前不分。

---

## 8. CI 与校验点

| 检查 | 对应规则 | 行为 |
|---|---|---|
| 文件名 `ADR-NNNN-<slug>.md` 合法 | §3 | 阻塞 |
| frontmatter 必填字段齐备 | §6 | 阻塞 |
| 编号无重复、无跳号 | §3 | 阻塞 |
| `Superseded` 状态必须有 `superseded_by` 字段 | §4 | 阻塞 |
| SPEC Minor / Major 变更的 PR 含对应 ADR | `spec-change-policy` §9 | 阻塞（C-6 扩展） |
| DoD 豁免 PR 含对应 ADR | `definition-of-done` §9 | 阻塞（C-7 扩展） |
| `ADR-TEMPLATE.md` 不被直接使用（必须复制改名） | 本文件 §7 | 告警 |

CI 实现落在 `tools/ci-check-adr.py`（占位，下一波次 C-9 交付）；在 CI 落地前由 `documentation-rules` D-LLM-12 + PR reviewer 人工把关。

---

## 9. 与其他规则的交叉引用

- `docs/rules/spec-change-policy.md §5 Step 1`：SPEC 变更的第一步即 ADR。
- `docs/quality/definition-of-done.md §9`：DoD 豁免 ADR。
- `docs/risk-register.md §3 R-2`：风险触发必须开 ADR。
- `docs/roadmap.md §6`：路线图决策分支通过 ADR 落实。
- `docs/rules/harness-flags-policy.md §5`：HarnessFlags 默认值翻转需 ADR。
- `docs/rules/git-workflow.md §4`：ADR PR 的提交与分支规范。

---

## 10. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；锁定命名 / 状态机 / 必备字段 / 触发清单；与 spec-change-policy / DoD / risk-register / roadmap 打通。 |
