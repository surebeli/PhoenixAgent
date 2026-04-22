# PhoenixAgent 设计审查修复执行清单

- 日期：2026-04-22
- 基于：[2026-04-22-design-audit.md](2026-04-22-design-audit.md)
- 目的：把审查结论转成可追踪的修复任务；每项含优先级、触发条件、DoD、所属 Milestone 位置、决策开关
- 状态图例：`待决策` / `待执行` / `进行中` / `已完成` / `已拒绝` / `延后`
- 当前全部条目状态：决策 `D-1 ~ D-8` 全部闭合；T-* 任务状态以下文正文为准（本文件 2026-04-22 第二轮修订后已对齐真实状态）

---

## Changelog

- 2026-04-22：作者确认 `D-1 = A`、`D-2 = A`、`D-3 = B`；`T-P0-1`、`T-P1-1`、`T-P1-5` 状态翻为 `待执行`。
- 2026-04-22：完成 `T-P0-1`；官方 shell 基线收口为 Windows Git Bash，`doctor --strict` 在当前默认代理环境下复现 `PASS=30 / WARN=2 / FAIL=1`。
- 2026-04-22：作者确认将 `T-P1-1` 拆分为 `T-P1-1a / T-P1-1b`；本轮先执行 `T-P1-1a`，补 ADR 前置与任务拆分。
- 2026-04-22：完成 `T-P1-1a`；新增 `ADR-0002` 并将原 `T-P1-1` 拆分为 `T-P1-1a / T-P1-1b`，`ci-check-adr.py` 输出 `错误 0 / 警告 0`。
- 2026-04-22：作者确认 `T-P1-1b` 的收口范围采用“规范性引用零命中；ADR / README / 变更日志中的历史版本叙述允许保留”。
- 2026-04-22：完成 `T-P1-1b`；规范性 `SPEC v1.0 / v1.x` 引用已收口到 `v1.1`，补齐 `PRD / TRD / RnD / M1 / M2` 最小变更日志，并在 `ci-check-spec.py` 增加模糊 SPEC 版本错误规则。
- 2026-04-22：作者确认 `D-4 = C`、`D-5 = M0 取 C + M1 取 B`、`D-7 = B`；`T-P0-2`、`T-P1-2`、`T-P1-3`、`T-P1-4` 状态翻为 `待执行`。
- 2026-04-22：完成 `T-P0-2`；M0 Step 8 增补 `baseline-swebench.json` 冻结要求，M1 `DoD-M1-6` 改为引用 `artifacts/M0/baseline-swebench.json`，`ci-check-milestone-dod.py` 输出 `错误 0 / 警告 0`。
- 2026-04-22：完成 `T-P1-3`；M0 Step 5 增补 `kimi-smoke.json` gate，M1 新增 `DoD-M1-1a`，`R-ML-1` 更新为 `active-with-gate`，`ci-check-milestone-dod.py` 输出 `错误 0 / 警告 0`。
- 2026-04-22：完成 `T-P1-4` 批次 1；不新增 Tier-2 规则文件，改为在 `documentation-rules.md` 追加 ID 定义点允许形态，并同步扩展 `ci-check-spec.py`；warning 从 `153` 降到 `3`。
- 2026-04-22：完成 `T-P1-4` 批次 2/3；`ci-check-spec.py` 对 `M0 §0` 真豁免生效，Tier-0 中对 `M0-plan.md` 的反向文件名引用已清理，warning 从 `3` 降到 `0`，`T-P1-4` 整体完成。
- 2026-04-22：作者确认 `D-8 = B`，冻结粒度降为字段与职责边界；完成 `T-P2-1`，更新 roadmap、M0-plan DoD-7 及 spec-change-policy 中对 soft-freeze 的定义，实现平滑收敛。
- 2026-04-22（第二轮修订 / R2）：对第一轮"全部完成"结论做事实核查，发现 `T-P1-2 / T-P1-5 / T-P2-2 / T-P2-3` 在摘要表声称已完成但正文缺证据链；本轮补齐 SPEC v1.2 `CostBreakdown`、`experiment-report` 双曲线字段、M1-plan.md 拆分后下游引用修复、DoD `[auto]/[review]/[hybrid]` 标签补漏，并把无法本轮闭合的分支（reviewer checklist C-4、`ci-check-teaching.py` 能力块合并校验）明确登记为后续波次。同步修复本文件 §5 重复行、§7 摘要表表头、§8 尾部乱码。

---

## 0. 使用说明

1. 本清单**不**自动等于承诺要做的事。每一项都需要先在 `决策` 列打勾才进入 `待执行`。
2. 任一进入 `待执行` 的项必须同时指明：挂在哪个 Milestone 的哪一步、是否需要提升 SPEC/Rule 版本、是否触发 ADR。
3. 完成后在本文件回填证据链接（commit、artifact 路径、CI 输出片段），而不是只勾状态。

---

## 1. 决策先行（Decisions Needed）

以下是动工前必须先定调的判断，否则下面的 T-* 任务会原地摇摆。

| ID | 决策点 | 可选方案 | 建议 |
|---|---|---|---|
| D-1 | "官方 shell 基线"取哪一套 | A. Windows + Git Bash（与 Step 1 基线一致）<br>B. WSL / `/home/litianyi` bash<br>C. 两套都支持但只有 A 纳入 doctor 冻结 | C — 保留双环境可用性，但 `phoenix-doctor.sh --strict` 与基线文件以 A 为准，B 仅记作"开发者方便"<br>决策：A（2026-04-22） |
| D-2 | SPEC 当前基线如何收口 | A. 全仓跟到 `v1.1`，修正所有 `v1.0 / v1.x` 字样<br>B. SPEC 回滚为 `v1.0`，暂停新变更<br>C. 冻结 `v1.1` 但允许 M1/M2 引用时使用 `>=v1.0` 的集合语义 | A — v1.1 已是事实，回滚代价大；批量改文是一次性成本<br>决策：A（2026-04-22） |
| D-3 | M1 范围是否拆分 | A. 保持现状（约 80–120h 一揽子）<br>B. 拆成 M1a（self runtime 最小价值闭环）+ M1b（Auto-Research / 长程任务 / Memory 七动词全量）<br>C. 不拆，但把 Auto-Research 与长程任务从硬 DoD 降为 stretch | B 或 C — 我倾向 B，因为 M1 DoD 目前 10 条，拆分能让"证明 self runtime 可用"先独立可证<br>决策：B（2026-04-22） |
| D-4 | 成本 KPI 口径 | A. 只算执行成本<br>B. 只算端到端（执行 + 评测 + Auto-Research）<br>C. 双口径并记，M2-KPI-3 显式绑定到其中一个 | C — 双口径并记是低成本且彻底的治本解<br>决策：C（2026-04-22） |
| D-5 | Kimi 前置验证位置 | A. 留在 M2（现状）<br>B. 在 M1 Step 早期插 smoke gate<br>C. 在 M0 Step 5（models.toml 落地时）就插一次最小探针 | B + C —— M0 里做 whoami 级探针即可，M1 做稳定性 gate，M2 沿用<br>决策：M0 取 C，M1 取 B（2026-04-22） |
| D-6 | 教学闭环是"每步必有"还是"每能力块必有" | A. 维持"每步必有"（现状）<br>B. 降为"每能力块必有"，单步可合并节点<br>C. M0 维持现状（保 KPI），M1 起改为 B | C — M0 教学闭环是验收项，动它风险高<br>决策：C（2026-04-22） |
| D-7 | `ci-check-spec.py` 的 161 条 warning 如何治理 | A. 压目标（例如 "≤30"）<br>B. 按噪声类型分层治，先 ID 定义方式 + Milestone 基线冻结，再推变更日志<br>C. 放弃机器规则，改手工 checklist | B — 不设机械阈值，按类收敛<br>决策：B（2026-04-22） |
| D-8 | 接口冻结的粒度 | A. 按现状冻结三硬接口的全部签名<br>B. 只冻结"字段 + 职责边界"，允许方法名与返回结构在 M1 前半期做 Patch/Minor 变更<br>C. 推迟冻结到 M1 结束 | B — 与 P2-1 一致<br>决策：B（2026-04-22） |

---

## 2. P0：阻断性任务

### T-P0-1：统一 shell 基线并让 `doctor --strict` 在默认代理环境下复现

- **依赖决策**：D-1
- **动机**：Step 1 基线在 Git Bash 下录的 `PASS=30 / WARN=2 / FAIL=1`，而当前代理默认落到 `/home/litianyi` bash 下得到 `PASS=12 / WARN=16 / FAIL=2`。这不是 doctor 脚本的 bug，是两套 shell profile 混用。
- **行动**：
  1. 在 `docs/milestones/M0-doctor-baseline.md` 顶部写清"Official Shell Baseline = Git Bash on Windows"，列出最小 profile（`PATH`、`HOME`、`python` 解析顺序、API Key 来源）。
  2. 在 `tools/phoenix-doctor.sh` 启动处加一条 shell 指纹探测（打印 `uname -s`、`$SHELL`、`which python3`、`which py`），并在非官方基线下打一条明确的 `WARN: running under non-baseline shell`。
  3. 在 `AGENTS.md` §7 或新开一节登记 shell 约束，确保未来任意 Agent 冷启动都能看到。
- **DoD**：在官方 shell 下重跑 `bash tools/phoenix-doctor.sh --strict`，结果与 `M0-doctor-baseline.md` 记录一致（Step 1 路径 B 规则下允许 docker FAIL=1）。
- **风险**：如果后续引入 CI，需同步选定 runner 的 shell。
- **挂载位置**：M0 Step 1 补丁，不升 Milestone 版本，M0-plan.md 打一条 changelog。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/milestones/M0-doctor-baseline.md`、`tools/phoenix-doctor.sh`、`AGENTS.md`、`docs/milestones/M0-plan.md`
  - `bash tools/phoenix-doctor.sh --strict`：`PASS=30 / WARN=2 / FAIL=1`
  - 关键对账：Shell fingerprint=`MINGW64_NT-10.0-26200`，`HOME=/c/Users/litianyi`，API Key 与 `*_BASE_URL` 已从 `~/.config/phoenix/keys.env` 载入
- **完成日期**：2026-04-22

### T-P0-2：在 M0 冻结一份 `baseline-swebench.json` 基线工件

- **依赖决策**：D-3（影响 M1 怎样引用）、D-4（决定基线里怎么记成本）
- **动机**：M1 `DoD-M1-6` 写的是"≥ 基线的 85%"，但 M0 `DoD-4` 只要求跑通 ≥1 个 instance，没有冻结的对照，85% 永远无法客观验收。
- **行动**：
  1. 在 M0 `Step 8`（Docker + SWE-bench 基线）DoD 里追加一条：必须产出 `artifacts/M0/baseline-swebench.json`。
  2. 该 JSON schema 最少包含：`task_ids[]`、`seed`、`runtime`、`model`、`harness_flags`、`resolved[]`、`cost.execution_usd`、`cost.evaluation_usd`（对应 D-4 的双口径）、`git_sha`、`produced_at`。
  3. 把 M1 `DoD-M1-6` 改写为"相对 `artifacts/M0/baseline-swebench.json` 的 resolved rate 比例 ≥ 0.85"。
  4. 在 `ci-check-milestone-dod.py` 里加一条：M1 的 `DoD-M1-6` 引用必须能解析到具体工件路径。
- **DoD**：M0 Step 8 产出 baseline 文件；M1-plan.md 的 DoD-M1-6 文字替换完成；CI 校验通过。
- **风险**：基线 subset 的选择与 seed 固定是有工程量的，需要在 D-3 确定 M1 是否拆分之后再排期。
- **挂载位置**：M0 Step 8 增量；M1-plan.md §1 DoD 改写；SPEC 可不动。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`artifacts/M0/baseline-swebench.json`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`docs/milestones/M0-plan.md`、`docs/milestones/M1-plan.md`、`tools/ci-check-milestone-dod.py`
  - 结构结果：新增 `artifacts/M0/baseline-swebench.json` 占位 schema；`DoD-M1-6` 已绑定到具体 baseline 工件路径
  - `py -3 tools/ci-check-milestone-dod.py`：`扫描 plan: 3 / 扫描 retrospective: 0 / DoD 总数: 27 / 错误: 0 / 警告: 0 / 全部通过`
- **完成日期**：2026-04-22

---

## 3. P1：高优先级修复

### T-P1-1a：为 SPEC v1.1 引用收口补 ADR 前置并拆分任务

- **依赖决策**：D-2（方案 A）
- **动机**：仓库硬约束要求"改 SPEC 必须先开 ADR + 版本号递进"，而原 `T-P1-1` 默认把 ADR 和大批量文档收口绑在同一轮，执行面过大且容易与停表条件冲突。
- **行动**：
  1. 新建 `docs/adr/ADR-0002-spec-v1-1-reference-alignment.md`，记录"当前权威基线 = SPEC v1.1，后续以治理补丁方式收口 `v1.0 / v1.x` 引用"。
  2. 将原 `T-P1-1` 正式拆分为 `T-P1-1a`（前置 ADR）与 `T-P1-1b`（执行收口）。
  3. 在本文件的 changelog 与摘要表同步反映拆分结果。
- **DoD**：ADR 文件创建完成并通过 `py -3 tools/ci-check-adr.py`；本文件完成 `T-P1-1a / T-P1-1b` 拆分；后续执行边界清晰。
- **挂载位置**：governance 补丁前置动作。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`docs/adr/ADR-0002-spec-v1-1-reference-alignment.md`
  - `py -3 tools/ci-check-adr.py`：`扫描 ADR: 3 / 错误: 0 / 警告: 0 / 全部通过`
  - 结构结果：原 `T-P1-1` 已拆分为 `T-P1-1a / T-P1-1b`
- **完成日期**：2026-04-22

### T-P1-1b：执行 SPEC v1.1 引用收口并清理 `v1.0 / v1.x`

- **依赖决策**：D-2（方案 A），以及 `T-P1-1a`
- **动机**：`M0-plan DoD-7`、`M1-plan §0`、`M2-plan §0` 以及 M1/M2 正文里共 20+ 处 `SPEC v1.0 §x` 形式硬引用，与 SPEC 当前 v1.1 不符。仅靠作者人工同步不可持续。
- **行动**：
  1. 复核 `SPEC.md` 现状：若 `§19 变更日志` 已明确 `v1.0 -> v1.1` 的兼容性说明，则本轮不重复改 SPEC 版本正文；否则先补声明。
  2. 批量把"SPEC v1.0"替换为"SPEC v1.1"，然后人工巡检每一条，确认引用的 §x 节号仍然存在。
  3. 把 `v1.x` 模糊表述全部替换为具体版本号。
  4. 在 `ci-check-spec.py` 增加一条规则：禁止 `SPEC v1\.x` / `SPEC v1\.0 / v1\.x` 之类占位写法，降级为 ERROR。
  5. 给缺失 `变更日志` 的目标文档补齐最小条目（至少覆盖最近一次版本变更）。
- **DoD**：`ci-check-spec.py` 对 `SPEC v1\.x` 的新规则实现且通过；规范性 `SPEC v1\.0 / v1\.x` 引用零命中；ADR / `docs/README.md` / `变更日志` 中的历史版本迁移描述允许保留。
- **风险**：若 v1.0→v1.1 有语义差异，批量替换可能掩盖真实引用漂移，必须人工巡检。
- **挂载位置**：直接进 M0 Step 11（Milestone 审查步）前完成，或开一个专门的 governance 补丁 PR。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`artifacts/ci-check-spec-tp1-1b.txt`、`docs/PRD.md`、`docs/TRD.md`、`docs/RnD-Analysis.md`、`docs/roadmap.md`、`docs/milestones/M0-plan.md`、`docs/milestones/M1-plan.md`、`docs/milestones/M2-plan.md`、`docs/rules/documentation-rules.md`、`docs/rules/git-workflow.md`、`docs/rules/harness-flags-policy.md`、`docs/rules/learning-artifact-rules.md`、`docs/rules/spec-change-policy.md`、`docs/quality/definition-of-done.md`、`tools/ci-check-spec.py`
  - grep 结果：`SPEC v1.0 / v1.x` 仅残留于 `docs/adr/**` 与 `docs/README.md` 的历史叙述中
  - `py -3 tools/ci-check-spec.py`：`错误 0 / 警告 153`，完整输出见 `artifacts/ci-check-spec-tp1-1b.txt`
  - 结构结果：新增 `ci-check-spec.py` 模糊版本规则；`PRD / TRD / RnD / M1 / M2` 已补最小 `变更日志`
- **完成日期**：2026-04-22

### T-P1-2：成本 KPI 双口径化

- **依赖决策**：D-4（方案 C）
- **动机**：M2-KPI-3 承诺"下降 ≥ 60%"，但 Auto-Research/Evaluator 用 Codex，不分口径就存在"乐观口径"套利空间。
- **行动**：
  1. 在 SPEC `§7`（Evaluation）或合适位置增加 `CostBreakdown` 数据结构：`execution_usd`、`evaluation_usd`、`research_usd`、`total_usd`。
  2. `experiment-report.md` 模板（`docs/rules/learning-artifact-rules.md` 相关部分）加上双曲线强制字段。
  3. 把 PRD `M2-KPI-3` 拆成 `M2-KPI-3a`（执行成本下降 ≥ 60%）+ `M2-KPI-3b`（端到端成本下降 ≥ X%），X 由 M1 基线决定。
  4. `M2-plan DoD-M2-4` 同步改写。
- **DoD**：SPEC / PRD / M2-plan 三份一致；ci-check-spec 不报 warning；历史 experiment-report（如有）允许 missing，但新 report 必须双曲线。
- **挂载位置**：进入 M1 前完成；涉及 SPEC / PRD 双改，需要触发 `spec-change-policy.md` 的 Minor 变更流程。
- **状态**：已完成（R2 补齐）
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/adr/ADR-0003-cost-breakdown-dual-budget.md`、`docs/SPEC.md`、`docs/rules/learning-artifact-rules.md`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`artifacts/reviews/2026-04-22-design-audit.md`（以及 R1 已完成的 `docs/PRD.md` / `docs/milestones/M2-plan.md` 中的 `M2-KPI-3a/3b` 拆分）
  - 结构结果：
    - SPEC `v1.1 -> v1.2`；§7.1 新增 `CostBreakdown`；`BenchmarkReport.cost: CostBreakdown` 为权威字段，`cost_usd` 保留为 `property` 别名；`INV-EV-3` 改为对四子字段的交叉校验；§19 变更日志追加 v1.2 条目。
    - 新增 ADR-0003 记录 Minor 变更的候选方案、决定与后果（含回滚条件与引用面约束）。
    - `learning-artifact-rules §3.3` 新增 `cost: CostBreakdown` 四子字段示例 + `L-ART-9`；§10 变更日志追加 v1.1。
  - `py -3 tools/ci-check-spec.py`：`错误 0 / 警告 0 / 全部通过`
  - `py -3 tools/ci-check-adr.py`：`扫描 ADR: 4 / 错误 0 / 警告 0 / 全部通过`
  - `py -3 tools/ci-check-milestone-dod.py`：`错误 0 / 警告 0 / 全部通过`
- **完成日期**：2026-04-22（R2）

### T-P1-3：Kimi smoke gate 前置到 M0/M1

- **依赖决策**：D-5
- **动机**：Kimi 白名单是 M2 的命门，但 M1-DoD-1 已经要求 `kimi-worker` 成功，风险实际上在 M1 就穿透了。现状是"登记但不闸门化"。
- **行动**：
  1. M0 Step 5（`models.toml` 落地）加一个"whoami 级探针"子任务：用 `kimi-worker` 跑一次最轻 prompt，记录 HTTP 码 + latency 到 `artifacts/M0/kimi-smoke.json`；失败不阻断 Step 5，但要登记。
  2. M1 新增一条 `DoD-M1-1a`：过去 20 次滚动运行里 `kimi-worker` 成功率 ≥ 95%，否则 M1 不得关闭。
  3. 在 `docs/risk-register.md` 把 `R-ML-1` 从"登记"提为"active with gate"状态，指向上述 DoD。
  4. 预留一条"直连失败时的 HTTP 代理回退路径"文档化（不必现在实现）。
- **DoD**：M0 Step 5 产出 kimi-smoke.json；M1-plan 新增 DoD-M1-1a；risk-register 状态更新。
- **风险**：如果 Kimi 从 Day 1 就不可用，整个 M2 路径需要重新评估。这个风险前置暴露本身就是 gate 的价值。
- **挂载位置**：M0 Step 5 增量 + M1-plan §1。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`artifacts/M0/kimi-smoke.json`、`artifacts/ci-check-milestone-dod-tp1-3.txt`、`artifacts/ci-check-spec-tp1-3.txt`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`docs/milestones/M0-plan.md`、`docs/milestones/M1-plan.md`、`docs/risk-register.md`
  - 结构结果：M0 Step 5 增加 `kimi-worker` whoami gate；M1 新增 `DoD-M1-1a`；`R-ML-1` 改为 `active-with-gate`
  - `py -3 tools/ci-check-milestone-dod.py`：`扫描 plan: 3 / 扫描 retrospective: 0 / DoD 总数: 27 / 错误: 0 / 警告: 0 / 全部通过`
  - `py -3 tools/ci-check-spec.py`：`错误 0 / 警告 153`，完整输出见 `artifacts/ci-check-spec-tp1-3.txt`
- **完成日期**：2026-04-22

### T-P1-4：收敛 `ci-check-spec.py` 的 warning（分类治，不设机械阈值）

- **依赖决策**：D-7（方案 B）
- **动机**：161 条 warning 把机器可审计性的卖点稀释了。但一次性压到 30 会把治理能量都消耗在格式化上，分类治更健康。
- **行动（按批次）**：
  1. **批次 1（建议先做）**：统一 ID 定义表达方式。写一份 `docs/rules/id-conventions.md`（或在现有 rules 里追加一节），固定 `R-ML-1` / `DoD-M1-6` / `F-01` / `M2-KPI-3` 这类 ID 的正则形态，然后把 `ci-check-spec.py` 的识别正则与之对齐。
  2. **批次 2**：Milestone 启动基线补冻结（M1 / M2 §0 显式列版本号，与 T-P1-1 合并执行）。
  3. **批次 3**：Tier-0 到 M-plan 的弱耦合 —— 给每份 M-plan 的 §0 加一条"上位文档冻结版本"块。
  4. **批次 4（可选）**：变更日志补齐。
  5. 每批次完成后重跑 `ci-check-spec.py`，在本文件回填当时的 warning 数量（作为治理曲线）。
- **DoD**：每批次都有一次 `py -3 tools/ci-check-spec.py` 输出粘回本文件；完成批次 1+2+3 后 warning 下降趋势可视化。
- **挂载位置**：与 T-P1-1 合并为一个"governance 补丁"系列。
- **批次进展**
- 批次 1（2026-04-22）：未新建 `docs/rules/id-conventions.md`，改为在 `docs/rules/documentation-rules.md` 新增 `D-ID-5 / D-ID-6 / D-ID-7`，明确标题首词、加粗首词、列表首词、表格首列四种 ID 定义点；`tools/ci-check-spec.py` 同步支持列表首词与表格首列识别。
- 批次 1 证据：`artifacts/ci-check-spec-tp1-4-batch1.txt`；`py -3 tools/ci-check-spec.py` 输出 `错误 0 / 警告 3`，warning 曲线 `153 -> 3`。
- 批次 2/3（2026-04-22）：`tools/ci-check-spec.py` 对 `M0-plan.md` 缺少 `§0` 采用真豁免；`docs/RnD-Analysis.md` 与 `docs/SPEC.md` 去除对 `docs/milestones/M0-plan.md` 的 Tier-0 反向文件名引用。
- 批次 2/3 证据：`artifacts/ci-check-spec-tp1-4-batch23.txt`；`py -3 tools/ci-check-spec.py` 输出 `错误 0 / 警告 0`，warning 曲线 `3 -> 0`。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`artifacts/ci-check-spec-tp1-4-batch1.txt`、`artifacts/ci-check-spec-tp1-4-batch23.txt`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`、`docs/RnD-Analysis.md`、`docs/SPEC.md`、`docs/rules/documentation-rules.md`、`tools/ci-check-spec.py`
  - 治理曲线：`153 -> 3 -> 0`
  - `py -3 tools/ci-check-spec.py`：`扫描文档 25 / 发现 ID 定义 105 / 错误 0 / 警告 0 / 全部通过`
- **完成日期**：2026-04-22

### T-P1-5：M1 范围收敛（拆分或降 stretch）

- **依赖决策**：D-3
- **动机**：M1 当前 DoD 10 条，覆盖 runtime / plan / compression / validation chain / permission / hook / worktree / plugin 三件套 / persistence / subagent / memory 七动词 / evaluation 全量 / 长程任务 / Auto-Research 3–5 轮 / F-07~F-22 全入库。在零实现前提下承担这个量级的风险不合理。
- **行动（在 D-3 = B 的前提下）**：
  1. 新建 `docs/milestones/M1a-plan.md` 和 `M1b-plan.md`（或保留 M1-plan 作为 M1a，同级新建 M1b）。
  2. M1a 硬 DoD：self runtime + 5 步验证链 + 编程插件 + subset 级 evaluation + AK-llm-wiki 最小闭环 + `kimi-worker` smoke（参见 T-P1-3）。
  3. M1b 硬 DoD：长程任务全量 + Auto-Research 3–5 轮 + Memory 七动词全量。
  4. 把 M2 启动前提从"M1-plan.md Step 14 全部通过"改为"M1a + M1b 全部通过"，或允许 M1b 与 M2 部分并行。
  5. RnD-Analysis.md §6.2 的工时估算同步拆分。
- **行动（在 D-3 = C 的前提下）**：
  1. 只在 M1-plan §1 DoD 中给 Auto-Research 与长程任务打上 `stretch` 标签，且明确 stretch 不达成不得阻塞 M1 关闭。
  2. 在 `docs/quality/definition-of-done.md` 里给"stretch DoD"一个明确定义。
- **DoD**：Milestone 文档拆分或 stretch 标签落地；与 M0 出口条件不产生循环依赖。
- **挂载位置**：M0 结束前必须定型，否则 M1 开工瞬间就会膨胀。
- **状态**：已完成（R2 补齐；R1 只完成了文件骨架拆分，§0/§1 DoD 未实质切分）
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/milestones/M1-plan.md`（R2 新建为索引入口）、`docs/milestones/M1a-plan.md`、`docs/milestones/M1b-plan.md`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`
  - 结构结果：
    - M1a-plan §0/§1：北极星聚焦"自研 Core + 编程插件 + subset evaluation + `kimi-worker` smoke"；DoD 条款为 `DoD-M1-1 / 1a / 2 / 3 / 4 / 5a / 6 / 9a / 10a`。
    - M1b-plan §0/§1：北极星聚焦"长程任务 + Auto-Research 3+ 轮 + Memory 七动词全量"；DoD 条款为 `DoD-M1-5b / 7 / 8 / 9b / 10b`；启动硬前置为 M1a §1 全部成立。
    - M1-plan.md：作为索引入口保留下游引用（SPEC §18 目录、`README.md` §x、`roadmap.md`、`DoD §6`、`M2-plan.md §0`、`documentation-rules §x`、`ADR-0002` 等），§0/§1 列出全局启动前提与全量 DoD 汇总；§3 拆分总览表一目了然。
    - DoD-M1-5 拆为 5a/5b；DoD-M1-9 拆为 9a/9b；DoD-M1-10 拆为 10a/10b；向量完整无遗漏。
  - `py -3 tools/ci-check-milestone-dod.py`：`扫描 plan: 3（含 M1-plan / M1a / M1b） / DoD 总数: 23 / 错误 0 / 警告 0 / 全部通过`
- **完成日期**：2026-04-22（R2）

---

## 4. P2：中优先级修复

### T-P2-1：冻结接口采用"字段+职责"粒度而非"方法签名"粒度

- **依赖决策**：D-8
- **动机**：三硬接口在无实现压力下冻结太多细节，会把 M1 早期变成"先改 SPEC 才能改代码"的流程税。
- **行动**：
  1. 修改 `docs/roadmap.md` 与 `docs/milestones/M0-plan.md DoD-7`：冻结对象从"接口签名"改为"字段与职责边界"，方法名与返回结构允许 M1 前半以 Patch/Minor 温和收敛。
  2. 在 `docs/rules/spec-change-policy.md` 给"接口 soft-freeze 窗口"一个定义：M1 Step 1–6 允许 Patch 级别接口调整，Step 7 后进入 hard-freeze。
- **DoD**：三份文档一致，且 soft-freeze 窗口的解锁/锁闭时点可机器识别。
- **挂载位置**：M0 Step 11 之前。
- **状态**：已完成
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/roadmap.md`、`docs/milestones/M0-plan.md`、`docs/rules/spec-change-policy.md`
  - 结构结果：`M0-plan` 中 `DoD-7` 改为软冻结；`spec-change-policy.md` 明确增加 `S-FREEZE-0 (Soft-Freeze 窗口)` 约束
- **完成日期**：2026-04-22

### T-P2-2：教学闭环从"每步必有"改为"每能力块必有"（M1 起生效）

- **依赖决策**：D-6（方案 C）
- **动机**：M0 的教学闭环本身是 KPI 组成部分，动它有风险；M1 的高密度实现阶段再维持硬门槛就会吃掉产能。
- **行动**：
  1. 在 `docs/rules/learning-artifact-rules.md` 新增一节"M1 起的合并规则"：同一能力簇内的 F-* 节点允许合并；触发条件为"能力块完成"而非"单步完成"。
  2. M1-plan 教学节点列表同步改写，允许 `F-07 + F-08` 这类合并（具体合并项由作者决定）。
  3. `ci-check-teaching.py` 放宽"每步必有教学产物"的校验，增加"能力块必有产物"的新校验（按 M1-plan 的能力块声明表驱动）。
- **DoD**：规则、M1-plan、校验脚本三者一致。
- **挂载位置**：M1 Step 1 之前完成。
- **状态**：部分完成（R2 登记延续项）
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/rules/learning-artifact-rules.md`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`
  - 结构结果：
    - `learning-artifact-rules §4.4`（"M1 起的合并规则（能力块合并）"）已落实：能力块定义、合并规则、触发条件三项清晰。
    - §10 变更日志追加 v1.1 条目，说明新增 §4.4 的驱动来自 T-P2-2 / D-6 = C。
  - 未完成分支（R2 明确登记，挂 M1 Step 1 前交付）：
    - 行动项 3：`tools/ci-check-teaching.py` 放宽"每步必有教学产物"、新增"能力块必有产物"校验；当前脚本在 `L-1` / `L-ING-1` 层仍是每节点检查，与 §4.4 语义不矛盾（允许多节点合并为一份文档即可），但未显式读取 M*-plan 的能力块声明表做"能力块必有产物"断言。
    - 行动项 2：M1a / M1b-plan §4 教学节点索引仍按原 F-* 单节点列出，尚未在 §4 注明"哪些 F-* 属同一能力块、可合并"；建议进入 M1 Step 1 时直接按 `M1a-plan §4` 改写。
- **完成日期**：2026-04-22（R2；部分完成，延续项挂 M1 Step 1 前）

### T-P2-3：明确哪些 DoD 条款靠自动化、哪些靠人工

- **动机**：DoD 目前混写自动化可验条款与内容深度类条款，单人项目下易被自律腐蚀。
- **行动**：
  1. 在 `docs/quality/definition-of-done.md` 给每一条 DoD 打标签：`auto`（CI 可判）、`review`（Reviewer checklist 必查）、`hybrid`。
  2. 在 reviewer checklist 中新增"内容充分度"和"错误路径证据"两项显式检查点。
- **DoD**：DoD 文件每条都有标签；reviewer checklist 有明确的强化项。
- **挂载位置**：M1 前任意时刻。
- **状态**：部分完成（R2 登记延续项）
- **证据**：
  - commit SHA：未提交
  - 改动文件：`docs/quality/definition-of-done.md`、`artifacts/reviews/2026-04-22-design-audit-tasklist.md`
  - 结构结果：
    - `docs/quality/definition-of-done.md` §3 / §4 / §5 / §6.2 / §7 的所有 E-* / L-* / M-* / G-* 条款已打 `[auto]` / `[review]` / `[hybrid]` 标签；R2 补齐原本漏标的 `L-1`。
    - §11 变更日志追加 v1.1 条目，说明驱动来自 T-P2-3 行动项 1；reviewer checklist 的"内容充分度 / 错误路径证据"强化项挂 `docs/quality/code-review-checklist.md`（C-4 后续波次）。
  - 未完成分支（R2 明确登记，挂 C-4 首次交付时吸收）：
    - 行动项 2：`docs/quality/code-review-checklist.md` 当前尚未交付；强化项内容暂以文字形式登记在本任务证据中，待 C-4 正式成稿时从此处提取并落为 checklist 条目。
- **完成日期**：2026-04-22（R2；部分完成，延续项挂 C-4）

---

## 5. 不采纳 / 推迟（记录但不做）

| ID | 原建议 | 决定 | 原因 |
|---|---|---|---|
| N-1 | 把 warning 机械压到 ≤30 | 不采纳 | 与 D-7 一致，分类治优于阈值治 |
| N-2 | 将 Auto-Research 和长程任务全部从 M1 移除 | 推迟 | 先走 D-3 拆分/stretch 化，不一步到位地砍 |
| N-3 | M0 增加教学闭环的合并规则 | 拒绝 | 与 D-6 一致，M0 不动 |

---

## 6. 时序与依赖图（文字版）

1. **先走 D-1 / D-2 / D-4 / D-7**：这些是纯文档判断，无执行成本，确定后才能驱动 T-P0-1 / T-P1-1 / T-P1-2 / T-P1-4。
2. **D-3 需要作者基于 M1 真实工作量感受判断**，其结果决定 T-P0-2 的 baseline 字段和 T-P1-5 的文档结构，建议与 D-1 同一次评审闭合。
3. **D-5 / D-6 / D-8 影响面窄**，可以在首轮决策后下一轮闭合。
4. 执行顺序建议：T-P0-1 → T-P1-1a → T-P1-1b（+ T-P1-4 批次 1、2）→ T-P0-2 → T-P1-2 / T-P1-3 → T-P1-5 → T-P2-*。

---

## 7. 待办追踪（结构化摘要）

| ID | 标题 | 优先级 | 依赖决策 | 状态 | 挂载位置 |
|---|---|---|---|---|---|
| T-P0-1 | 统一 shell 基线 + doctor 复现 | P0 | D-1 | 已完成 | M0 Step 1 补丁 |
| T-P0-2 | M0 冻结 swebench baseline 工件 | P0 | D-3, D-4 | 已完成 | M0 Step 8 |
| T-P1-1a | SPEC v1.1 收口前置 ADR | P1 | D-2 | 已完成 | governance 补丁前置 |
| T-P1-1b | SPEC 版本跟进到 v1.1 | P1 | D-2 | 已完成 | governance 补丁 |
| T-P1-2 | 成本 KPI 双口径化 | P1 | D-4 | 已完成 | SPEC v1.2 / PRD / M2-plan / learning-artifact-rules |
| T-P1-3 | Kimi smoke gate 前置 | P1 | D-5 | 已完成 | M0 Step 5 + M1a §1 |
| T-P1-4 | ci-check-spec warning 分类治 | P1 | D-7 | 已完成 | governance 补丁（4 批次） |
| T-P1-5 | M1 范围收敛 | P1 | D-3 | 已完成 | M0 结束前（M1a/M1b 已拆 + 下游引用已同步） |
| T-P2-1 | 接口冻结改为字段+职责粒度 | P2 | D-8 | 已完成 | M0 Step 11 前 |
| T-P2-2 | 教学闭环 M1 起改能力块粒度 | P2 | D-6 | 部分完成 | 规则已落；`ci-check-teaching.py` 能力块校验登记为 M1 Step 1 前交付 |
| T-P2-3 | DoD 条款标注 auto/review/hybrid | P2 | — | 部分完成 | DoD 标签全量落位；reviewer checklist 强化挂 C-4 后续波次 |

---

## 8. 下一步建议

（R2 后的状态）

- §1 所有决策 D-1 ~ D-8 均已闭合；§2–§4 的 T-* 任务中 P0 / P1 / P2-1 已完成，T-P2-2 / T-P2-3 登记为部分完成，延续项挂后续波次。
- 未闭合项的接续动作：
  - **T-P2-2**：`ci-check-teaching.py` 新增"能力块必有产物"校验（行动项 3），挂 M1 Step 1 前完成。
  - **T-P2-3**：`docs/quality/code-review-checklist.md`（C-4）新增"内容充分度 / 错误路径证据"两项显式检查点，挂 C-4 首次交付时吸收。
- 下一里程碑（M0 Step 2 起）动工时，若再出现状态虚报，优先修正本文件摘要表而不是新增 changelog。
