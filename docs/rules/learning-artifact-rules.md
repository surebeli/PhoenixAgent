# 学习 Artifact 规则（Learning Artifact Rules）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：`docs/teaching/**` 下所有教学资产（`F-*`、`M-*`、`experiment-report.md` 等）与其在 AK-llm-wiki 的 ingest 记录。
- 上位依据：PRD §8（教学交付物要求）、TRD §4.8（D-TL TeachingEmitter）、SPEC v1.0 §9（TeachingEmitter 接口）、`docs/rules/spec-change-policy.md`。
- 下位依据：`docs/quality/definition-of-done.md`、`docs/quality/acceptance-checklist.md`、未来交付的 `tools/ci-check-teaching.py`（C-5）。

---

## 1. 本规则存在的理由（Why）

PhoenixAgent 的学习资产不是副产品，而是**与代码同等重要的第一类交付物**。它们必须：

- 能被大模型直接 ingest（Claude Agent SDK / Codex / Kimi 任一）作为下一轮任务的上下文。
- 能被 `phoenix memory query` 精准召回（不靠 RAG 拉距离，而靠 slug + namespace + tier 精确命中）。
- 能跨 Milestone 追踪溯源（F-07 的内容被 F-19 继承/修订时，链式可追）。
- 在 SPEC 变更时能自动发现"哪些节点失效"（对应 `docs/rules/spec-change-policy.md` §5 Step 2）。

为此，所有学习 artifact 必须遵守：**命名稳定、frontmatter 统一、ingest marker 显式、跨节点引用用 slug 不用路径**。

---

## 2. Artifact 类型与命名

### 2.1 类型

| 类型 | 定义 | 存放位置 |
|---|---|---|
| **Foundation Node（F-*）** | 一个具体概念 / 原理 / 实践的最小教学单元；1 个 concept = 1 个节点 | `docs/teaching/M<N>/foundations/F-<idx>-<slug>.md` |
| **Milestone Artifact（M-*）** | Milestone 级别的串讲型资产（playbook / walkthrough / 实验合集） | `docs/teaching/M<N>/M-<slug>.md` 或 `.ipynb` |
| **Experiment Report** | 每轮 Auto-Research 的实验记录 | `docs/teaching/M<N>/experiments/experiment-<YYYYMMDD>-<slug>.md` |
| **Engineering Note（M-eng-*）** | 工程侧的轻量笔记（ablation、profile、A/B 对比） | `docs/teaching/M<N>/engineering/M-eng-<slug>.md` |
| **Retrospective** | Milestone 收尾复盘 | `docs/milestones/M<N>-retrospective.md`（注意不在 teaching 目录，但 ingest 到 `namespace="retrospective"`） |

### 2.2 F-* 编号规则

- **单调递增、跨 Milestone 连续**。M0 产出 F-01 ~ F-06（+ F-mem-1/2、F-05a/b、F-model-1 等补号）；M1 从 F-07 起；M2 从 F-23 起；M3 从 F-35 起（M2-plan.md §6 已锁定）。
- **补号规则**：若在某 Milestone 内临时发现"两个原计划节点之间需要插入一个更基础的概念"，允许使用 `F-<idx>a` / `F-<idx>b` 形式（如 F-05a、F-05b）。**不允许**事后插入 `F-05.5` / `F-6-bis` 等其他形式。
- **编号一经 ingest 即冻结**：`F-07` 的 slug 一旦进入 wiki，即使内容被大幅重写，编号与 slug 不变；如需替换，旧节点降 tier 至 `archived`，新节点用新编号 + `replaces: F-07` frontmatter。

### 2.3 slug 规则

- slug 为 kebab-case，仅 `a-z0-9-`。
- 最长 60 字符；≤ 5 个 `-` 分段（可读性约束）。
- 必须能在无上下文时大致推断内容主题（反例：`F-07-misc.md`、`F-08-note.md`）。
- 禁止中文、下划线、空格、大写。
- 与 frontmatter `name` 字段语义一致但不必字字对应（name 可以写中文）。

### 2.4 命名示例

```
F-07-react-self-vs-sdk.md          ✅
F-09-compression-tradeoffs.md      ✅
F-11-hooks-permissions.md          ✅
F-05a-tool-use-protocol.md         ✅ 补号
F-07-misc.md                       ❌ slug 无意义
F-7-react.md                       ❌ 编号缺 0 填充
F-07_react_self_vs_sdk.md          ❌ 下划线
```

---

## 3. Frontmatter 规范

所有 `F-*` 与 `M-*` artifact 必须以 YAML frontmatter 开头。

### 3.1 Foundation Node（F-*）必填字段

```yaml
---
id: F-07                           # 与文件名编号一致
slug: react-self-vs-sdk            # 与文件名 slug 一致
name: 自研 ReAct 与 Claude SDK 主循环对比
milestone: M1                      # 所属 Milestone（M0/M1/M2/M3）
step: 1                            # 产自哪个 Step（整数；M0 无 step 字段时用 null）
type: foundation                   # foundation / milestone / experiment / engineering / retrospective
tier: active                       # active / archived / frozen
spec_version: v1.1                 # 撰写时对齐的 SPEC 版本（SPEC-change-policy S-REPRO-1）
related_spec: [§3, §5.2]           # SPEC 中直接相关的章节号（可空数组）
related_fr: [FR-02, FR-03]         # PRD 相关 FR 条款
related_inv: [INV-RT-1]            # SPEC 相关 INV 条款（可空）
related_nodes: [F-05a, F-06]       # 上游依赖的学习节点
replaces: null                     # 若替代了旧节点，填旧节点 id
ingested: true                     # ingest 到 wiki 后置 true；CI 校验
ingested_at: 2026-05-10T12:00:00+08:00   # ISO8601，ingest 时写入
readers: [llm, human]              # 目标读者；至少含 llm
---
```

### 3.2 Milestone Artifact（M-*）必填字段

```yaml
---
id: M1-harness-walkthrough
slug: harness-walkthrough
name: M1 Harness 走读 Notebook
milestone: M1
type: milestone
tier: active
spec_version: v1.2
covers_foundations: [F-07, F-08, F-09, F-10, F-11, F-12]   # 串讲覆盖的 F-* 列表
ingested: true
ingested_at: ...
---
```

### 3.3 Experiment Report 必填字段

```yaml
---
id: exp-20260512-kimi-plan-drift
slug: kimi-plan-drift
name: Kimi 在 plan_drift tag 上的 Auto-Research 第 2 轮
milestone: M2
step: 10
type: experiment
tier: active
spec_version: v1.5
runtime: self
model_generator: kimi-worker
model_evaluator: codex-base
benchmark: swe-bench-verified
subset: 20
seed: 42
result: kept                       # kept / discarded / inconclusive
significance: 0.032                # p-value；inconclusive 时为 null
ingested: true
ingested_at: ...
---
```

### 3.4 字段硬约束

- **L-ART-1**：`id` 必须全局唯一；跨 Milestone 查重。
- **L-ART-2**：`spec_version` 必须是当前或历史 `SPEC.md` 存在过的版本号。
- **L-ART-3**：`related_spec` / `related_fr` / `related_inv` 中引用的条款必须真实存在于 PRD / TRD / SPEC 当前版本；CI 校验悬空引用。
- **L-ART-4**：`related_nodes` 中引用的节点 id 必须存在且 `tier != archived`，或显式 `replaces:` 关系可解释。
- **L-ART-5**：`tier=archived` 的节点禁止被 `tier=active` 节点的 `related_nodes` 直接引用（必须改为引用其 `replaces` 目标）。
- **L-ART-6**：`ingested=true` 但无 `ingested_at` 或其早于文件最后修改时间 → CI 告警，要求重新 ingest。

---

## 4. 内容结构规范

### 4.1 F-* 节点的标准结构

```markdown
# <name>

## 动机（Why）
<不超过 5 行；解释这个概念对 PhoenixAgent 项目为什么重要。>

## 核心内容
<概念主体；可分 2–4 个小节。每个小节必须"自包含"，即脱离本项目仍可读。>

## 与 PhoenixAgent 的映射
<具体落到哪个 SPEC 条款 / 哪段代码 / 哪个 HarnessFlag / 哪个 INV-*。>

## 失败模式（若适用）
<若此概念处理不当会产生的问题；引用真实案例或外部资料。>

## 延伸与争议
<未解决问题、作者判断分歧、推荐后续阅读。禁止留空；若确无，写一行"本节点无已知未解决争议，待后续 Milestone 复核"。>

## 参考
- <URL / arXiv / repo 路径 / 章节定位>
- ...
```

- **L-ART-7**：每个 F-* 节点字数 ≥ 400 字、≤ 3000 字。低于下限说明承载内容过稀，应并入相邻节点；高于上限说明边界过宽，应拆分。
- **L-ART-8**：禁止外部上下文依赖（"如 README 所述..."而不指路径）；所有引用必须给出 URL / 文件路径 / 章节号。

### 4.2 M-* 节点的标准结构

```markdown
# <name>

## 1. 本 Milestone 的学习主线
<把 covers_foundations 连成一句话主线。>

## 2. 路线串讲
<按 Step 顺序把 F-* 节点的要点串成一条完整剧情。每个 F-* 至多 1–2 段。>

## 3. 关键权衡
<这个 Milestone 做过的 3–5 个关键取舍；每项给"做了什么 / 为什么不做另一条 / 后果观测"。>

## 4. 教训
<本阶段踩过的坑；与 retrospective 不重复，更偏"为后来者准备的警示"。>

## 5. 延伸阅读索引
<外链 + 本项目 wiki 查询示例。>
```

### 4.3 Experiment Report 的标准结构

```markdown
# <name>

## 背景
<为什么跑这轮；目标假设（H0 / H1）；引用 F-19 / F-20。>

## 设置
<Runtime / Model / HarnessFlags / Benchmark / subset / seed / 允许变更的 glob / 预算上限>

## 结果
<三张表最少：pass/fail diff、token 成本、latency。若有 significance，列出 proportion z 或 bootstrap p。>

## 分析
<为什么 Kept / Discarded / Inconclusive；机理解读（引用哪些 F-*）。>

## 对 SPEC / 代码 / 教学的影响
<如 Kept：列出后续要新增的 F-*、要改的 SPEC 条款、要更新的 HarnessFlags 默认值。>

## 复现方式
<给出一条 `phoenix research` 命令，参数完整。>
```

---

## 5. Ingest 规则

### 5.1 Ingest 触发条件

- **L-ING-1**：所有 `tier=active` 的 F-* / M-* / experiment 节点必须在"文件创建后的同一个 PR 内"完成 `wiki-ingest`。
- **L-ING-2**：允许在 PR 中使用"待 ingest"占位（frontmatter `ingested: false`），但合并前必须置为 `true`；CI 阻塞。
- **L-ING-3**：文件发生任一实质性变更（非 typo 级）后必须重新 ingest，`ingested_at` 同步更新。CI 通过对比 git 文件 mtime 与 `ingested_at` 发现遗漏。

### 5.2 Ingest 命令契约

命令形态固定为：

```bash
phoenix memory ingest \
  --source docs/teaching/M1/foundations/F-07-react-self-vs-sdk.md \
  --namespace foundations \
  --tier active \
  --slug F-07-react-self-vs-sdk
```

- `--namespace`：由 `type` 决定 → `foundations` / `milestones` / `experiments` / `engineering` / `retrospective` / `spec`。
- `--tier`：与 frontmatter 同步；CI 校验一致性。
- `--slug`：规则见 §2.3；一旦写入不可变。

### 5.3 Marker 文件

- 项目根下 `.ingested.json` 维护"已 ingest 节点清单"（id → ingested_at 映射）。
- **L-ING-4**：`.ingested.json` 必须与所有 `tier=active` 节点的 frontmatter 一致；CI 对 diff。
- **L-ING-5**：`.ingested.json` 是机器产物，不手改；仅由 `phoenix memory ingest` 或专用修复脚本写入。

---

## 6. Tier 管理与降级

### 6.1 三层定义

| Tier | 可召回权重 | 可被引用 | 使用场景 |
|---|---|---|---|
| `active` | 高 | 是 | 当前或近期 Milestone 的主内容 |
| `archived` | 低 | 仅历史追溯；新节点不得 `related_nodes` 引用（L-ART-5） | 被新节点取代的老知识 |
| `frozen` | 极低（需精确 slug 命中） | 否 | 确认已过时但留存为教学对比 |

### 6.2 降级规则

- 每个 Milestone 结束（retrospective 通过）自动执行：
  - 上一个 Milestone（M<N-1>）的无人引用节点：`active → archived`。
  - 上上个 Milestone（M<N-2>）的全部节点：`archived → frozen`，除非在本 Milestone 再次被引用。
- 显式保留：frontmatter 增 `keep_active: true`，retrospective 说明原因。

### 6.3 SPEC 变更驱动的降级

见 `docs/rules/spec-change-policy.md` §5 Step 6：

- SPEC Major 变更 → 受影响 F-* 节点立即 `archived`，由新节点通过 `replaces:` 承接。

---

## 7. 跨节点引用规则

### 7.1 引用方式

- **节点间引用**：用 `related_nodes` frontmatter + 正文 `[F-07](../../M1/foundations/F-07-react-self-vs-sdk.md)` 双写；CI 校验两者一致。
- **SPEC 引用**：用 `related_spec` + 正文直接引用章节号 `SPEC v1.3 §5.2`（**不允许**只写 `SPEC v1.0 §5.2`，必须带版本）。
- **PRD / TRD / RnD 引用**：用 `related_fr` / `related_tr` / `related_rr` 等字段 + 正文带版本引用。
- **外部资源**：正文给完整 URL；禁止只写"Anthropic 博客"。

### 7.2 禁止项

- **L-REF-1**：禁止跨 Milestone 反向依赖（M1 节点 `related_nodes` 中不可出现 M2 节点 id；除非 M1 节点是在 M2 期间修订）。
- **L-REF-2**：禁止循环引用（A → B → A）；CI 检测。
- **L-REF-3**：禁止"深引用 archived 节点"，详见 L-ART-5。

---

## 8. CI 校验点（对应未来的 C-5 `ci-check-teaching.py`）

CI 脚本交付时需实现至少以下检查（按优先级）：

| 检查 | 对应规则 | 行为 |
|---|---|---|
| Frontmatter 必填字段齐备 | §3 | 阻塞 |
| `id` / `slug` / 文件名三者一致 | §2.3 §3.4 | 阻塞 |
| `spec_version` 真实存在 | L-ART-2 | 阻塞 |
| `related_*` 引用不悬空 | L-ART-3 | 阻塞 |
| `related_nodes` 无循环、无 archived 深引用 | L-REF-2 L-ART-5 | 阻塞 |
| `tier=active` 且 `ingested=false`（占位） | L-ING-1 + L-ING-2 | 告警（PR 草稿允许；合并前由 PR template 勾选项强制翻 true） |
| `tier=active` 且 `ingested` 非合法 bool | L-ING-1 | 阻塞 |
| `ingested_at` ≥ 文件 mtime | L-ING-3 | 告警；M*-retrospective 前必须清零 |
| `.ingested.json` 与 frontmatter 一致 | L-ING-4 | 阻塞 |
| F-* 字数区间 [400, 3000] | L-ART-7 | 告警 |
| slug 格式合规 | §2.3 | 阻塞 |

---

## 9. 与其他规则的交叉引用

- `docs/rules/spec-change-policy.md`：SPEC 变更驱动的节点降级 / 新增。
- `docs/rules/documentation-rules.md`：PRD/TRD/RnD/SPEC 级文档的交叉引用规则（与本规则的节点引用规则互补）。
- `docs/quality/definition-of-done.md`：每个 Step 的 DoD 默认含"本步骤 F-* 已按本规则 ingest"。
- `docs/quality/acceptance-checklist.md`：验收 checklist 的"学习达标"板块逐条映射本规则。

---

## 10. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；对齐 M0/M1/M2 plan 已隐含的 F-* / M-* 约定。 |
