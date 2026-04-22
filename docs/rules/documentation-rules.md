# 文档治理规则（Documentation Rules）

- 版本：v1.1（2026-04-22）
- 作者：dy
- 适用范围：`docs/PRD.md`、`docs/TRD.md`、`docs/RnD-Analysis.md`、`docs/SPEC.md`、`docs/milestones/M*-plan.md`、`docs/milestones/M*-retrospective.md`、`docs/rules/**`、`docs/quality/**`、`docs/adr/**`、`docs/migrations/**`。
- 不覆盖范围：`docs/teaching/**` 由 `docs/rules/learning-artifact-rules.md` 单独治理；仅本规则 §6 定义两者的接口。
- 上位依据：PRD §1（文档性质与读者）、SPEC v1.1 §14（文档体系）。
- 下位依据：`docs/rules/spec-change-policy.md`、`docs/rules/learning-artifact-rules.md`、`docs/quality/definition-of-done.md`。

---

## 1. 本规则存在的理由（Why）

PhoenixAgent 的 4 件套文档（PRD / TRD / RnD-Analysis / SPEC）加上 milestone plans、rules、quality 目录，是整个项目的"单一真相源"。它们服务**两类读者**：

- **大模型**（Claude Agent SDK、Codex、Kimi 等）：文档必须可直接 ingest，不依赖任何外部上下文。
- **人类协作者**（作者 dy + 后续协作者）：文档必须能在离线打印、无搜索环境下仍可阅读理解。

由此衍生出四条总纲：

1. **职责边界清晰**：每份文档只回答自己负责的问题；重叠内容用交叉引用而非复制。
2. **ID 体系闭环**：FR-* / NFR-* / D-* / R-* / INV-* / SEC-* / OP-* / OOS-* 等 ID 跨文档稳定；悬空引用 CI 阻塞。
3. **LLM-ready**：不依赖外部上下文；所有资源引用给 URL / 文件路径 / 章节号。
4. **版本化可追**：每份顶级文档带版本号；`M*-plan` 引用的是 SPEC/PRD 的**特定版本**，而非浮动 HEAD。

---

## 2. 文档分层与职责

### 2.1 Tier-0：顶级 4 件套

| 文档 | 负责回答 | 禁止承担 | 版本化单位 |
|---|---|---|---|
| `PRD.md` | 做什么 / 为什么 / 对谁 / 验收什么 | 架构细节、接口签名、排期 | 产品版本（v1.0/v1.1/v2.0） |
| `TRD.md` | 用什么架构 / 怎么分层 / 技术栈 / 安全约束 | 产品目标重申、具体接口签名 | 架构版本（v1.0 起） |
| `RnD-Analysis.md` | 可行吗 / 风险在哪 / 资源估算 / 开放问题 | 产品需求、实现细节 | 研发版本（v1.0 起） |
| `SPEC.md` | 每个硬接口 / 数据结构 / 不变量的精确契约 | 动机说明、可行性、排期 | SPEC 语义化版本（见 spec-change-policy §3） |

### 2.2 Tier-1：规划与治理

| 文档 / 目录 | 职责 |
|---|---|
| `docs/milestones/M<N>-plan.md` | 单个 Milestone 的 Step-based 执行计划（见 `feedback_plan_style`） |
| `docs/milestones/M<N>-retrospective.md` | 单个 Milestone 收尾的复盘与 KPI 核对 |
| `docs/roadmap.md`（A-1，待交付） | 跨 Milestone 总路线图 |
| `docs/risk-register.md`（A-2，待交付） | R-* 风险的执行态登记与处置 |
| `docs/adr/ADR-NNNN-*.md`（A-3，待交付） | 架构决策记录 |
| `docs/migrations/SPEC-v*-to-v*.md` | SPEC Major 变更的迁移指引 |

### 2.3 Tier-2：规则与质量

| 文档 | 职责 |
|---|---|
| `docs/rules/spec-change-policy.md` | SPEC 变更治理 |
| `docs/rules/learning-artifact-rules.md` | 教学资产治理 |
| `docs/rules/documentation-rules.md`（本文件） | 文档体系治理 |
| `docs/rules/git-workflow.md`（B-3，后续波次） | git / 分支 / commit / PR 规则 |
| `docs/rules/harness-flags-policy.md`（B-4，后续波次） | HarnessFlags 翻转规则 |
| `docs/quality/*.md` | DoD / checklist / 测试策略 / code review |

### 2.4 Tier-3：教学

`docs/teaching/**` 由 `docs/rules/learning-artifact-rules.md` 单独治理。本规则只约束 Tier-3 与 Tier-0/1/2 之间的引用接口（§6）。

---

## 3. ID 体系与稳定性

### 3.1 ID 命名与归属

| ID 前缀 | 出处 | 说明 |
|---|---|---|
| `FR-NN` | PRD | Functional Requirement |
| `NFR-NN` | PRD | Non-Functional Requirement |
| `OOS-NN` | PRD | Out-of-Scope |
| `D-<层>` | TRD | Design decision（层：RT/ML/HR/PL/MM/EV/AR/TL） |
| `SEC-NN` | TRD | Security requirement |
| `R-<层>-N` | RnD-Analysis | 风险条款 |
| `OP-NN` | RnD-Analysis | Open Problem |
| `INV-<层>-N` | SPEC | 不变量条款 |
| `DoD-<M>-N` | M*-plan | Milestone-level Definition of Done |
| `Step N` | M*-plan | 执行顺序步骤 |
| `F-<idx>`、`M-<slug>` | teaching | 学习节点（详见 learning-artifact-rules） |
| `ADR-NNNN` | docs/adr | 架构决策记录 |

### 3.2 ID 稳定性

- **D-ID-1**：ID 一旦合入 main 分支即冻结；即使内容被整体重写，ID 不变。
- **D-ID-2**：需要废弃某 ID 时，在原位置保留占位条目并标 `DEPRECATED: 由 <新 ID> 取代`；禁止直接删除以避免跨文档悬空引用。
- **D-ID-3**：ID 递增采用两位数填充（`FR-03` 而非 `FR-3`）以保证排序稳定；超过 99 项时升到三位数并回填旧 ID 的宽度。
- **D-ID-4**：ID 单调递增，禁止复用已废弃 ID。

### 3.3 ID 定义点允许形态

- **D-ID-5**：对机器校验而言，ID 的“定义点”必须出现在该 ID 的归属文档内，且允许采用以下任一种稳定形态：
  - 标题首词：`### FR-01 ...`
  - 加粗首词：`- **FR-01**`
  - 列表首词：`- INV-EV-1：...`
  - Markdown 表格首列：`| R-ML-1 | ... |`
- **D-ID-6**：若某文档使用 Markdown 表格承载条目列表，则表格首列中的 ID 视为正式定义；后续列中的同名 ID 仍视为引用而非重复定义。
- **D-ID-7**：若某文档使用项目符号承载条目列表，则列表项必须以 ID 开头，后跟 `:` / `：` / 空白说明文字之一；禁止把 ID 埋在句中再依赖人工判断其是否为定义点。

### 3.4 跨文档引用规则

- **D-REF-1**：PRD / TRD / RnD / SPEC / M*-plan 之间相互引用时，**必须带文档名 + 章节号**（如 `TRD §4.3`、`SPEC v1.3 §5.2`）。
- **D-REF-2**：引用 SPEC 时**必须带版本号**（至少到 Minor）；见 `spec-change-policy` S-VER-2。
- **D-REF-3**：M*-plan.md 的 `§0 启动前提` 必须显式冻结 PRD / TRD / RnD / SPEC 的基线版本号。
- **D-REF-4**：PRD/TRD/RnD/SPEC 不得引用 M*-plan（反向依赖禁止）；M*-plan 可引用四件套。
- **D-REF-5**：rules 目录内部相互引用允许，但**禁止 rules 反向引用 PRD/TRD**（rules 是治理层，不承载产品或架构内容）。

---

## 4. LLM-ready 约束

### 4.1 自包含

- **D-LLM-1**：每份 Tier-0/1/2 文档必须能"单独 ingest 即可被有效 query"；不依赖"同时 ingest 了 X"。
- **D-LLM-2**：术语首次出现必须给定义；PRD §术语表 + 各文档自身术语段共同承载（优先就近）。
- **D-LLM-3**：禁止使用未定义的缩写。常见外部术语（ReAct / MCP / RAG / SWE-bench 等）首次出现时给一行解释 + URL。

### 4.2 结构可预测

- **D-LLM-4**：所有 Tier-0/1/2 文档以**版本号 + 作者 + 日期 + 上位/下位依据**开头（见本规则自身的首部格式）。
- **D-LLM-5**：所有表格、列表、代码块的"目的"必须在其前一段显式写出（避免"下方表格不解自明"依赖视觉推断）。
- **D-LLM-6**：章节层级控制在 4 级以内（`####` 为极限）；超过则拆文件。

### 4.3 避免视觉依赖

- **D-LLM-7**：禁止仅靠颜色 / 字体 / 斜体 / 图标传达语义；语义必须能被纯文本解析出来。
- **D-LLM-8**：图示必须同时提供可读的 ASCII 或文字描述段落；纯二进制图片不作为单一信息源。
- **D-LLM-9**：禁止 emoji 作为语义载体（允许装饰性使用，但删除后语义不能丢）。

### 4.4 代码与命令

- **D-LLM-10**：所有命令示例必须是"原样可运行"；使用占位符时用 `<...>` 包裹并给一行说明。
- **D-LLM-11**：禁止"省略号省略示例中间部分"（如 `...etc...`）；要么写全，要么显式说"此处省略 N 行见 XXX"。

### 4.5 禁止外部上下文依赖

- **D-LLM-12**：禁止"如 README 所述"、"见前文"、"如上所述"无具体定位的引用。必须给文件路径、章节号、行号或外部 URL 之一。
- **D-LLM-13**：禁止"作者邮件"、"Slack 里说过"等对话上下文的引用；此类内容要么写入文档，要么落到 ADR。

---

## 5. 版本化与变更

### 5.1 版本号规则

- Tier-0：PRD / TRD / RnD 使用 `vX.Y` 形式。X 代表结构性重组，Y 代表内容增补。
- SPEC 使用 `vX.Y.Z`（见 spec-change-policy §3）。
- Tier-1/2 文档使用 `vX.Y`，规则同 Tier-0。

### 5.2 必须升版的触发条件

- 任何改变 ID 表、章节结构、接口承诺、验收标准的变更 → 升 Y。
- 文档整体重写、职责边界重划、与其他文档关系变化 → 升 X。
- typo / 格式 / 图示修正 → 不升版；但必须在本文件 `变更日志` 登记。

### 5.3 变更日志

每份 Tier-0/1/2 文档末尾必须含 `变更日志` 章节，表格记录：

| 版本 | 日期 | 变更 |
|---|---|---|

变更描述写"做了什么"，不写"为什么做"（"为什么"留给 ADR）。

---

## 6. 教学层接口（Tier-3 Interface）

### 6.1 从 Tier-3 引用 Tier-0/1/2

F-* / M-* 的 frontmatter `related_spec` / `related_fr` / `related_inv` 等字段承担此引用（详见 `learning-artifact-rules` §7.1）。正文中引用 SPEC 必须带版本号。

### 6.2 从 Tier-0/1/2 引用 Tier-3

- 允许：M*-plan.md 在 Step 产出清单中列出 F-* / M-* id。
- 允许：rules / quality 文档在示例中引用 F-* 作为典型。
- 禁止：PRD / TRD / RnD / SPEC 在主体章节引用具体 F-* 节点（因为 F-* 会降 tier / 被 replace，而 Tier-0 稳定性要求更高）；如需引用，只通过"见 `docs/teaching/` 下对应节点"的粗引用。

### 6.3 ingest 差异

- Tier-0/1/2 文档仅在其内容发生升版时 ingest 到 wiki（`namespace=spec` / `prd` / `trd` / `rnd` / `rules` / `quality` / `milestone`）。
- Tier-3 的 ingest 规则见 `learning-artifact-rules` §5。

---

## 7. 目录结构锁定

当前 `docs/` 目录结构（M0–M2 已就位部分）：

```
docs/
├── PRD.md
├── TRD.md
├── RnD-Analysis.md
├── SPEC.md
├── milestones/
│   ├── M0-plan.md
│   ├── M1-plan.md
│   └── M2-plan.md
├── rules/
│   ├── spec-change-policy.md
│   ├── learning-artifact-rules.md
│   └── documentation-rules.md     ← 本文件
├── quality/                        ← C-1 / C-2 即将落位
├── adr/                            ← A-3 将来落位
├── migrations/                     ← SPEC Major 变更触发时创建
└── teaching/                       ← 由 learning-artifact-rules 治理
    ├── M0/
    ├── M1/
    └── M2/
```

- **D-DIR-1**：上述目录为受管目录；新增顶级目录必须先更新本规则 §7。
- **D-DIR-2**：禁止在 `docs/` 直接落地零散 `.md`（除 4 件套外）；必须归入子目录。

---

## 8. CI 校验点（对应未来的 C-6 `ci-check-spec.py` 与通用文档 CI）

| 检查 | 对应规则 | 行为 |
|---|---|---|
| PRD/TRD/RnD/SPEC 首部版本号齐备 | D-LLM-4 | 阻塞 |
| 跨文档 ID 引用无悬空 | D-REF-1/2 | 阻塞 |
| SPEC 引用带版本号 | D-REF-2 | 阻塞 |
| M*-plan §0 列出四件套基线版本 | D-REF-3 | 阻塞 |
| 四件套未反向引用 M*-plan | D-REF-4 | 阻塞 |
| rules 未反向引用 PRD/TRD | D-REF-5 | 阻塞 |
| 变更日志章节存在且版本递增 | §5.3 | 告警 |
| `docs/` 根目录无散落 `.md` | D-DIR-2 | 阻塞 |
| 文档内 URL 200 可达 | D-LLM-12 | 周期性检查；告警不阻塞 |

---

## 9. 与其他规则的交叉引用

- `docs/rules/spec-change-policy.md`：SPEC 版本号规则 + ingest 流程。
- `docs/rules/learning-artifact-rules.md`：教学层治理。
- `docs/quality/definition-of-done.md`：DoD 中的"文档达标"子项定义。
- `docs/quality/acceptance-checklist.md`：验收 checklist 中的"文档"板块。

---

## 10. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.1 | 2026-04-22 | 补充 ID 定义点允许形态，明确表格首列与列表首词可作为机器校验的正式定义点。 |
| v1.0 | 2026-04-18 | 首版；锁定 4 件套职责、ID 体系、LLM-ready 约束、目录结构。 |
