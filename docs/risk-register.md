# 风险执行登记（Risk Register）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：`docs/RnD-Analysis.md §4` 登记的全部 `R-*` 风险，以及项目执行期间新发现的风险。
- 上位依据：`RnD-Analysis.md §4`（风险矩阵权威出处）、`PRD §9` KPI。
- 下位依据：`docs/milestones/M*-plan.md §5`（每个 Milestone 的风险预警小节）、`docs/adr/**`（风险触发的决策）。
- 身份：**RnD-Analysis 是"静态风险清单"，本文件是"运行时状态表"**。`R-*` 编号与文本以 RnD-Analysis 为准；本文件增加 owner / status / last_review / evidence / related_DoD 五个执行态字段。

---

## 1. 本文件存在的理由（Why）

RnD-Analysis §4 的风险矩阵足够用作"项目初始风险识别"，但它有两个硬缺陷让它不能直接驱动执行：

1. **没有 owner 与 review 节奏**：风险一旦被写进表格就容易"被看了但不会被盯"。
2. **没有状态流转**：M1/M2 期间某条风险已被缓解 / 已触发 / 已归档，需要一个独立载体记录，而不是反复重写 RnD-Analysis（RnD 要保持分析稳定）。

因此本文件是 `R-*` 风险的**执行态镜像**：字段模式稳定、状态可推进、每 Milestone 结束时必须 review。

---

## 2. 字段定义

| 字段 | 说明 | 允许值 |
|---|---|---|
| `id` | 风险 ID | 与 RnD-Analysis §4 完全一致（如 `R-RT-1`） |
| `name` | 一句话风险描述 | 与 RnD-Analysis 一致；不同步即 CI 告警 |
| `owner` | 当前负责人 | `dy`（默认）或具体协作者；禁止留空 |
| `status` | 执行态 | `active` / `mitigated` / `triggered` / `archived` / `watch` |
| `milestone_scope` | 预期活跃窗口 | 形如 `M1-M2` / `M1` / `M2+` |
| `last_review` | 上次 review 日期 | `YYYY-MM-DD` |
| `next_review` | 下次必须 review 的时点 | Milestone 名或 `YYYY-MM-DD` |
| `evidence` | 风险发生/缓解的证据 | 文件路径、commit、benchmark 报告；每次状态变化必须追加 |
| `related_DoD` | 风险触发会冲击的 DoD 条款 | 如 `DoD-M1-6, DoD-M2-2` |
| `mitigation` | 缓解动作摘要 | 与 RnD-Analysis 缓解列一致即可 |

### 2.1 状态机

```
         ┌──────────────┐
         │ active（默认）│
         └──────┬───────┘
                │
    ┌───────────┼────────────┐
    ▼           ▼            ▼
┌─────────┐ ┌──────────┐ ┌───────┐
│mitigated│ │triggered │ │ watch │
└────┬────┘ └────┬─────┘ └───┬───┘
     │           │           │
     ▼           ▼           ▼
┌──────────────────────────────┐
│         archived            │
└──────────────────────────────┘
```

- `active`：风险仍在预期窗口内且尚未发生或缓解。
- `watch`：概率显著下降或当前 Milestone 不考核，但保留观测。
- `triggered`：已发生；必须链接触发证据 + ADR（§3 R-1）。
- `mitigated`：通过具体动作使概率或影响显著下降；必须链接缓解证据。
- `archived`：在当前 Milestone 已不再关联 KPI/DoD；下一次 scope 扩大时重新 `active`。

---

## 3. 登记硬约束

- **R-1**：`R-*` 状态变化必须伴随 `evidence` 字段新增至少 1 条；仅改状态不补证据的 PR 阻塞。
- **R-2**：`triggered` 转入必须同 PR 新建 ADR（触发根因 / 影响 / 是否调整 DoD / 迁移动作）。
- **R-3**：`mitigated` 状态下的风险在下一 Milestone review 时必须被显式重评；不重评默认回滚为 `active`。
- **R-4**：任一新识别的风险必须先登记到 `RnD-Analysis.md §4` 获得 `R-*` 编号，再登记到本文件；禁止跳过 RnD 直接登记。
- **R-5**：本文件与 RnD-Analysis 的 `id + name` 必须逐条一致；新增 / 废弃由 `spec-change-policy` 的 Minor 级流程处理（RnD 是 Tier-0）。
- **R-6**：`related_DoD` 若发生变更（如 DoD 编号重排、DoD 条款删除），必须同步更新本文件；对应校验在 C-7 `ci-check-milestone-dod.py` 将来扩展。

---

## 4. 执行态登记（当前快照）

### 4.1 Runtime Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-RT-1 | dy | active | M1 | 2026-04-18 | M1 Step 10 | DoD-M1-6 | — |
| R-RT-2 | dy | watch | M2 | 2026-04-18 | M2 Step 5 | DoD-M2-5 | — |
| R-RT-3 | dy | active | M2 | 2026-04-18 | M2 Step 7 | DoD-M2-6 | — |

### 4.2 Model Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-ML-1 | dy | active | M2 | 2026-04-18 | M2 Step 1 | DoD-M2-1 | — |
| R-ML-2 | dy | watch | M1-M2 | 2026-04-18 | 每月首工作日 | DoD-M2-4 | — |
| R-ML-3 | dy | watch | M2+ | 2026-04-18 | M3 规划前 | — | — |
| R-ML-4 | dy | watch | M0+ | 2026-04-18 | M3 规划前 | — | — |

### 4.3 Harness Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-HR-1 | dy | active | M1-M2 | 2026-04-18 | M1 Step 14 | DoD-M1-2 | — |
| R-HR-2 | dy | active | M1 | 2026-04-18 | M1 Step 3 | DoD-M1-3 | — |
| R-HR-3 | dy | active | M1 | 2026-04-18 | M1 Step 3 | — | — |

### 4.4 Plugin Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-PL-1 | dy | watch | M1 | 2026-04-18 | M1 Step 4 | DoD-M1-4 | — |
| R-PL-2 | dy | watch | M1+ | 2026-04-18 | M2 规划前 | — | — |

### 4.5 Memory Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-MM-1 | dy | watch | M1+ | 2026-04-18 | wiki ≥ 200 节点时 | — | — |
| R-MM-2 | dy | active | M1-M2 | 2026-04-18 | M1 Step 5 | DoD-M1-5 | — |
| R-MM-3 | dy | active | M1+ | 2026-04-18 | 每 Auto-Research 轮次 | — | — |

### 4.6 Evaluation Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-EV-1 | dy | active | M1 | 2026-04-18 | M1 Step 7 | DoD-M1-6 | — |
| R-EV-2 | dy | watch | M1-M2 | 2026-04-18 | M1 Step 7 | DoD-M1-7, DoD-M2-3 | — |
| R-EV-3 | dy | active | M1-M2 | 2026-04-18 | M1 Step 10, M2 Step 3 | DoD-M1-6, DoD-M2-2 | — |
| R-EV-4 | dy | active | M2 | 2026-04-18 | M2 Step 7 | DoD-M2-5, DoD-M2-6 | — |

### 4.7 Auto-Research Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-AR-1 | dy | active | M1-M2 | 2026-04-18 | 每 Auto-Research 轮次 | DoD-M1-8, DoD-M2-8 | — |
| R-AR-2 | dy | active | M1-M2 | 2026-04-18 | 每 Auto-Research 轮次 | DoD-M1-8, DoD-M2-8 | — |
| R-AR-3 | dy | active | M1+ | 2026-04-18 | 每 Auto-Research 轮次 | — | — |

### 4.8 Teaching Layer

| id | owner | status | scope | last_review | next_review | related_DoD | evidence |
|---|---|---|---|---|---|---|---|
| R-TL-1 | dy | active | M1-M2 | 2026-04-18 | 每 Milestone retrospective | DoD-M1-9, DoD-M2-9 | — |
| R-TL-2 | dy | active | M1+ | 2026-04-18 | 每 Milestone retrospective | DoD-M1-9, DoD-M2-9 | — |

---

## 5. Review 节律

| 节奏 | 动作 | 产出 |
|---|---|---|
| 每个 Milestone retrospective | 逐条重评 status + 更新 `last_review` / `next_review` | retrospective 内"风险表"附录 |
| 每个 Auto-Research 轮次结束 | 重评 `R-AR-*` + 受影响的 `R-EV-*` / `R-MM-3` | `experiment-report.md` 末尾风险小节 |
| 风险 `triggered` 即时 | 开 ADR + 更新本文件 | ADR-NNNN-risk-<id>-triggered |
| 月度（如启用 Codex 成本风险） | `R-ML-2` 对照当期成本数据 | 更新 evidence 字段 |

---

## 6. 与其他文档的关系

- `RnD-Analysis.md §4`：`R-*` 的**名称 + 缓解**权威出处。本文件是执行态镜像。
- `M*-plan.md §5`：每个 Milestone 本轮重点关注的 `R-*` 列表；与本文件 `milestone_scope` 字段对应。
- `M*-retrospective.md`：`triggered` 事件的完整复盘；本文件的 evidence 字段指向 retrospective。
- `docs/adr/**`：所有 `triggered` / 阈值变更必须走 ADR。
- `docs/roadmap.md §3/§4`：冻结与 KPI 决定 `related_DoD` 字段的引用对象。

---

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；引入 owner / status / last_review / evidence / related_DoD 五字段；登记 RnD §4 全部 22 条 `R-*` 初始态。 |
