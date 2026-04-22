# PhoenixAgent 设计全景审查报告

- 日期：2026-04-22
- 审查对象：PhoenixAgent 当前仓库的立项、架构设计、实施路径、治理落地与目标达成可行性
- 审查边界：当前仓库仍处于 governance-first 阶段，`src/phoenix/**` 与 `tests/**` 尚未落地；因此本报告重点审查的是项目设计、执行设计、机器化治理、启动可达性与里程碑可兑现性，而不是运行时代码质量

## 增量复盘（基于 Step 1 已完成）

本节覆盖 Step 1 完成后新增出现的事实；若与下方初版全景审查结论冲突，以本节为准。

### 结论更新

1. Step 1 可以判定为已完成，但属于 [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md) 允许的“路径 B 完成”，不是“全部前提都已物理满足”的路径 A 完成。
2. 上一版审查里最重的结论 `P0-1：M0 起跑条件尚未满足` 需要局部修正：
  - 对 Step 1 本身：该结论不再成立。
  - 对整个 M0：该结论仍部分成立，因为当前默认 `bash` 运行环境无法稳定复现 Step 1 基线。
3. 对 M1 / M2 的结构性判断暂不改变：基线定义、成本口径、Kimi 前置验证、M1 交付面过宽，这几类问题仍然成立。

### 新增证据

Step 1 已完成的直接证据：

- [docs/milestones/M0-doctor-baseline.md](../../docs/milestones/M0-doctor-baseline.md) 已把 Step 1 基线回填为 `PASS=30 / WARN=2 / FAIL=1`，且唯一 FAIL 为 docker，已按“暂缓，Step 8 前补齐”登记。
- 同一文件的 [Step 1 退出判定](../../docs/milestones/M0-doctor-baseline.md) 已勾选路径 B，说明按当前计划写法，Step 1 的工程出口条件已满足。
- [docs/teaching/M0/foundations/F-01-react-paradigm.md](../../docs/teaching/M0/foundations/F-01-react-paradigm.md) 已完整落盘，frontmatter 与正文都已具备 Step 1 所需的基础形态。
- [artifacts/doctor-m0-baseline.json](../doctor-m0-baseline.json) 记录的基线与 `M0-doctor-baseline.md` 一致，表明 Step 1 不是口头完成，而是有归档产物的完成。

本轮复核的当前状态：

- 重新执行 `py -3 tools/ci-check-teaching.py`：`错误 0 / 警告 2`。这与 [M0-plan.md](../../docs/milestones/M0-plan.md) Step 1 对 `ingested:false` 占位允许 warning 的设计一致。
- 重新执行 `py -3 tools/ci-check-milestone-dod.py`：`错误 0 / 警告 0`。Milestone 级 DoD 结构仍然闭合。
- 重新执行 `bash tools/phoenix-doctor.sh --strict`：结果回退到 `PASS=12 / WARN=16 / FAIL=2`，表现为 `python3=3.6.9`、`pip` 指向 Python 2.7、Docker 未安装、`~/.config/phoenix` 与 API Key 不可见。

### 关键新发现

当前最大的增量发现，不是 Step 1 失败，而是 **Step 1 基线与当前默认 bash 环境不一致**。

直接证据：

- Step 1 基线文档 [docs/milestones/M0-doctor-baseline.md](../../docs/milestones/M0-doctor-baseline.md) 记录的是 Windows/Git-Bash 风格可用环境：`py -3 = 3.14.0`、Python SDK 可导入、`~/.config/phoenix/*.toml` 存在、API Key 已配置。
- 当前复核命令下的 bash 环境实测为：`HOME=/home/litianyi`、`/usr/bin/python3`、`Python 3.6.9`、`/usr/local/bin/pip` 指向 Python 2.7。

这说明当前仓库至少存在两套 bash 语义环境：

1. 能支撑 Step 1 完成记录的 Windows/Git-Bash 式环境。
2. 当前代理默认调用到的 `/home/litianyi` WSL/bash 式环境。

这个分裂本身就是新的风险，因为它意味着：

- Step 1 虽然已经按计划完成，但**尚未在“默认代理执行环境”上实现可复现**。
- 后续 Step 2 的 wiki CLI、Step 5 的 `models.toml`、Step 8 的 Docker 评测，很可能继续受这个环境分裂影响。
- 上一版审查里“环境未收敛”的判断，应从“尚未完成 Step 1”更新为“Step 1 已完成，但 shell/profile 基线尚未统一”。

### 对原审查结论的修正

原结论中需要更新的部分：

- `当前实施准备度 = 低`：保留，但要细化为“文档与治理准备度已提升，默认执行环境准备度仍低”。
- `M0 = No-Go`：不再适用于 Step 1 这一局部结论；更准确的说法应为“Step 1 已 Go，M0 总体仍为 Conditional Go”。
- `P0-1：M0 起跑条件尚未满足`：应改写成“Step 1 已通过路径 B 完成，但默认 bash 环境未统一，因此 M0 起跑条件尚未完全标准化”。

原结论中暂不变化的部分：

- `P0-2：M1 的 85% 基线没有封闭定义`。
- `P1-1：版本冻结与复现基线存在漂移`。
- `P1-2：M2 成本 KPI 没有闭合定义`。
- `P1-3：Kimi 外部依赖前置消化不够`。
- `P1-4：治理自动化落后于规则野心`。
- `P1-5：M1 交付面过大`。

### 当前阶段的更新判断

| 主题 | 初版判断 | Step 1 完成后的判断 |
|---|---|---|
| Step 1 是否完成 | 否 | 是，且有产物与 Milestone 证据 |
| M0 是否已完全就绪 | 否 | 仍否，但问题从“Step 1 未完成”转为“环境基线未统一” |
| 是否可以进入 Step 2 | 存疑 | 可以，且应尽快进入 |
| M1 / M2 结构性风险 | 高 | 不变 |

### 增量建议

1. 先把“官方 shell 基线”说清楚：到底以 Git Bash 还是当前 `/home/litianyi` 这套 bash 为准。否则 Step 1 之后的所有 doctor、wiki、docker 证据都会继续分裂。
2. 进入 Step 2 时，不要只做 wiki 功能本身，还要把 `.ingested.json` 和 `wiki CLI in PATH` 当成环境统一的一部分一起收口。
3. 在 Step 8 前，必须再次用“官方 shell 基线”重跑一次 doctor，并把结果附回 [docs/milestones/M0-doctor-baseline.md](../../docs/milestones/M0-doctor-baseline.md)，否则 Docker 相关结论无法和 Step 1 基线并账。

## 结论先行

1. 当前项目更接近“高质量治理草案”，不是“已经被实现层验证过的工程系统”。
2. 立项方向成立：把 Runtime、Model、Harness、Plugin、Memory、Evaluation、Auto-Research、Teaching 拆成八层，并把 5 步验证链作为硬安全路径，这个设计方向清晰、差异化明确，而且有长期价值。
3. 但我不接受 [docs/RnD-Analysis.md](../../docs/RnD-Analysis.md) 中“整体成功概率 ≥ 95%”的结论。以当前证据，只能支持：
   - M0：修复环境后高可行。
   - M1：有条件可行，但必须先补齐基线定义并收窄交付面。
   - M2：当前承诺偏重，关键外部依赖与成本口径都还没有被前置验证。
4. 当前最硬的现实问题不是“架构想不清楚”，而是“起跑条件、验收基线、版本冻结和治理自动化还没有完全闭环”。

## 审查方法与证据面

本次审查同时使用了文档阅读和可执行校验两类证据。

已审阅的核心文档：

- [docs/PRD.md](../../docs/PRD.md)
- [docs/TRD.md](../../docs/TRD.md)
- [docs/RnD-Analysis.md](../../docs/RnD-Analysis.md)
- [docs/SPEC.md](../../docs/SPEC.md)
- [docs/roadmap.md](../../docs/roadmap.md)
- [docs/risk-register.md](../../docs/risk-register.md)
- [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md)
- [docs/milestones/M1-plan.md](../../docs/milestones/M1-plan.md)
- [docs/milestones/M2-plan.md](../../docs/milestones/M2-plan.md)
- [docs/quality/definition-of-done.md](../../docs/quality/definition-of-done.md)
- [docs/quality/test-strategy.md](../../docs/quality/test-strategy.md)
- [docs/rules/documentation-rules.md](../../docs/rules/documentation-rules.md)
- [docs/rules/spec-change-policy.md](../../docs/rules/spec-change-policy.md)
- [docs/rules/harness-flags-policy.md](../../docs/rules/harness-flags-policy.md)
- [docs/rules/learning-artifact-rules.md](../../docs/rules/learning-artifact-rules.md)
- [docs/adr/README.md](../../docs/adr/README.md)
- [docs/adr/ADR-0001-harness-flags-frozen.md](../../docs/adr/ADR-0001-harness-flags-frozen.md)
- [tools/phoenix-doctor.sh](../../tools/phoenix-doctor.sh)
- [tools/ci-check-spec.py](../../tools/ci-check-spec.py)
- [tools/ci-check-teaching.py](../../tools/ci-check-teaching.py)

已执行的校验命令与结果摘要：

| 检查 | 结果 | 关键信息 |
|---|---|---|
| `bash tools/phoenix-doctor.sh --strict` | 失败 | `PASS=12 / WARN=16 / FAIL=2`；`python3=3.6.9`、`pip` 指向 Python 2.7、Docker 未安装、未配置 API Key、AK-llm-wiki CLI 未在 PATH |
| `py -3 tools/ci-check-spec.py` | 通过但高噪声 | `错误 0 / 警告 161`；集中暴露 ID 定义检测、Milestone 启动基线冻结、变更日志缺失、Tier-0 到 M-plan 的弱耦合 |
| `py -3 tools/ci-check-adr.py` | 通过 | `错误 0 / 警告 0` |
| `py -3 tools/ci-check-flags.py` | 通过 | `SPEC flags=13 / policy flags=13 / 错误 0 / 警告 0` |
| `py -3 tools/ci-check-teaching.py` | 通过但未闭环 | `错误 0 / 警告 2`；`F-01` 仍为 `ingested=false`，仓库缺少 `.ingested.json` |
| `py -3 tools/ci-check-milestone-dod.py` | 通过 | `错误 0 / 警告 0` |

需要强调：`ci-check-spec.py` 的 161 条 warning 不等于 161 个事实性错误，但它清楚表明“文档自称的机器可审计性”还没有真正达到目标状态。

## 核心问题

### P0-1：M0 起跑条件尚未满足，当前不能视为已进入实施阶段

证据：

- [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md) 的 `DoD-1` 明确要求 `bash tools/phoenix-doctor.sh` 输出 `FAIL=0`。
- 实测 `bash tools/phoenix-doctor.sh --strict` 失败，直接暴露以下关键现实：
  - `python3` 只有 `3.6.9`，低于要求的 `>=3.11`。
  - `pip` 实际绑定 Python 2.7，环境存在明显解释器偏差。
  - Docker 未安装，SWE-bench 执行前提不成立。
  - `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`MOONSHOT_API_KEY` 均未设置。
  - AK-llm-wiki CLI 未在 PATH。
  - `.ingested.json` 尚不存在，教学/记忆闭环没有初始化完成。

为什么这是硬问题：

M0 不只是“写文档准备一下”，而是整个项目从治理层切入实现层的起跑门槛。若 `DoD-1` 本身没有达成，后面的 `DoD-2/3/4/5/6/7` 都没有稳定的落脚点，M1 与 M2 的所有论证都会悬空。

最小修复方向：

1. 先把 M0 限定为“环境与基线收敛阶段”，直到 doctor 严格模式通过。
2. 固定一套唯一受支持的 Python/Bash 组合，避免当前 Windows + bash 路径下出现 Python 3.6 / pip 2.7 的混合环境。
3. 把 AK-llm-wiki 的安装与 `.ingested.json` 的初始化视为 M0 出口条件，而不是可选项。

### P0-2：M1 的 85% 基线没有封闭定义，导致 KPI 无法客观验收

证据：

- [docs/PRD.md](../../docs/PRD.md) 的 `M1-KPI-1` 承诺“自研 Core 在 SWE-bench Verified 上达到 Claude Agent SDK + Codex 基准的 85%”。
- [docs/milestones/M1-plan.md](../../docs/milestones/M1-plan.md) 的 `DoD-M1-6` 要求 `Resolved Rate ≥ 对应 --runtime=claude 基线的 85%`。
- 但 [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md) 的 `DoD-4` 只要求“跑通 ≥ 1 个 instance”，没有要求产出固定 subset、固定 seed、固定 runtime/model 的基线报告。

为什么这是硬问题：

M1 的成败被写成了相对指标，但 M0 没有交付一个可重复引用的基线工件。没有基线工件，就没有可复核的 85%；没有固定 subset 与 seed，就没有稳定的对照；没有统一成本口径，就无法判断“追平/掉点”的真实含义。

最小修复方向：

1. 在 M0 增加一份冻结基线产物，例如 `artifacts/M0/baseline-swebench.json`。
2. 这份基线必须固定：任务集合、seed、runtime、model、harness flags、计费口径。
3. 把 M1 的 `DoD-M1-6` 改写成“相对 M0 基线工件”的比较，而不是相对一个口头描述。

### P1-1：版本冻结与复现基线存在漂移，已经削弱了治理可信度

证据：

- [docs/SPEC.md](../../docs/SPEC.md) 当前版本是 `v1.1`。
- [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md) 的 `DoD-7` 仍写“在 SPEC v1.0 的签名下稳定冻结”。
- [docs/milestones/M1-plan.md](../../docs/milestones/M1-plan.md) 的启动前提仍写成 `SPEC v1.0 / v1.x` 这种模糊表述。
- `ci-check-spec.py` 实测 warning 指出：
  - M1 启动前提缺少 `PRD` / `TRD` 的明确冻结版本。
  - M2 启动前提缺少 `SPEC` / `PRD` / `TRD` 的明确冻结版本。
  - 多份 Tier-0 / Milestone 文档缺少 `变更日志`。

为什么这是问题：

PhoenixAgent 的一个核心卖点就是“版本化、可追溯、可复现”。如果最基础的冻结基线都出现漂移，Auto-Research 报告、Teaching 节点、Milestone 入口条件和 Reviewer 清单都会逐步失真。

最小修复方向：

1. 明确当前全仓基线到底是 `SPEC v1.1` 还是要回滚到 `v1.0`。
2. 把 M1 / M2 的 `§0 启动前提` 改成显式版本冻结，不允许使用 `v1.x` 这类模糊文字。
3. 给 PRD、TRD、RnD、M0/M1/M2-plan 补齐变更日志，降低后续版本治理噪声。

### P1-2：M2 成本 KPI 没有闭合定义，当前无法证明“成本下降 ≥ 60%”

证据：

- [docs/PRD.md](../../docs/PRD.md) 的 `M2-KPI-3` 要求“Token 成本相对 Codex 基准下降 ≥ 60%”。
- [docs/milestones/M2-plan.md](../../docs/milestones/M2-plan.md) 的 `DoD-M2-4` 采用的是“相对 Codex 单独执行基准下降 ≥ 60%”。
- 但 [docs/TRD.md](../../docs/TRD.md) 与 [docs/SPEC.md](../../docs/SPEC.md) 又同时规定 Auto-Research / Evaluation 的 Evaluator 使用 Codex，这意味着系统级成本并不只来自执行模型。

为什么这是问题：

如果“成本”只算执行成本，不算评测成本，那么 KPI 是可达但可能过度乐观。
如果“成本”算端到端成本，那么 Codex Evaluator 的持续消耗会显著压缩节省空间。当前文档没有把这两种口径分开，导致 KPI 看似精确，实则不可审计。

最小修复方向：

1. 把成本拆成两个字段：执行成本、评测成本。
2. 明确 M2-KPI-3 到底针对哪个口径。
3. 要求所有 `experiment-report.md` 和 benchmark report 同时记录两条成本曲线。

### P1-3：Kimi 是 M2 的关键外部依赖，但风险前置消化不够

证据：

- [docs/RnD-Analysis.md](../../docs/RnD-Analysis.md) 将 `R-ML-1` 定义为“Kimi whitelist 挡掉自研 CLI”，概率为中。
- [docs/milestones/M2-plan.md](../../docs/milestones/M2-plan.md) 的 `DoD-M2-1` 直接要求 `self + kimi-worker` 连续 20 次稳定成功。
- [docs/milestones/M1-plan.md](../../docs/milestones/M1-plan.md) 的 `DoD-M1-1` 又已经要求 `--runtime=self --model=kimi-worker` 成功，说明 Kimi 风险事实上已经穿透到 M1。

为什么这是问题：

这类风险不能留到 M2 才处理。Kimi 如果在 CLI / User-Agent / proxy 路径上不稳定，M1 和 M2 的多项里程碑都会被一起拖住。当前风险登记是正确的，但时间位置偏后，尚未形成真正的前置闸门。

最小修复方向：

1. 在 M1 中新增 Kimi smoke gate，而不是等到 M2 再验证。
2. 固定一条“直连失败时的代理回退路径”，并让其参与基线统计。
3. 在 M2 启动前提中加入“Kimi smoke 通过率阈值”。

### P1-4：治理规则写得很强，但机器化落实明显落后于规则野心

证据：

- [docs/rules/spec-change-policy.md](../../docs/rules/spec-change-policy.md) 把 Minor / Major 变更的影响面扫描、教学追认、迁移指引写成了刚性流程。
- [tools/ci-check-spec.py](../../tools/ci-check-spec.py) 实际只覆盖版本头、ID 闭环、SPEC 引用、Milestone 基线、根目录散落文档、变更日志等基础规则。
- [docs/quality/definition-of-done.md](../../docs/quality/definition-of-done.md) 中大量条款仍然只能靠人工证据与 Reviewer 自审完成。
- 实测 `ci-check-spec.py` 虽无 error，但有 `161` 条 warning。

为什么这是问题：

这说明当前仓库“有治理语言”，但还没有形成与之对等的“治理机器”。尤其是在单作者 + LLM 协作的场景下，自动化不足会迅速把严谨规则退化成需要人记忆的繁琐仪式。

需要特别说明的是：这 `161` 条 warning 很大一部分是“ID 定义方式与校验器识别方式不一致”，而不是逻辑自相矛盾。问题仍然存在，因为项目明确要求的是 LLM-ready、可机器查询、可机器校验，而不是“人类能看懂就行”。

最小修复方向：

1. 先把 warning 目标压到可管理范围，而不是继续堆新规则。
2. 优先修正三类噪声：ID 定义表达方式、Milestone 启动基线、变更日志缺失。
3. 只有在这些 warning 收敛后，才值得继续扩展 impact scan、teaching 深度审查等更高阶 CI。

### P1-5：M1 的交付面偏大，超出了当前证据支撑的单阶段负荷

证据：

- [docs/RnD-Analysis.md](../../docs/RnD-Analysis.md) 估算 M1 为 `80–120h`。
- [docs/milestones/M1-plan.md](../../docs/milestones/M1-plan.md) 同时要求：
  - 自研 Runtime 最小 ReAct。
  - Plan、Compression、Validation Chain、Permission、Hook。
  - Worktree、编程插件三件套。
  - Persistence、Subagent。
  - Memory 七动词补全。
  - EvaluationRunner 全量。
  - 长程任务集接入。
  - Auto-Research 3–5 轮。
  - `F-07 ~ F-22` 全部入库。

为什么这是问题：

这不是“写得细”，而是交付集合已经包含了一个完整平台的多个核心面。当前没有 `src/phoenix/**` 初始代码、没有基础测试、M0 环境还未就绪，在这种前提下把 Auto-Research 和长程任务也强压进同一 Milestone，兑现风险很高。

最小修复方向：

1. 把 M1 拆成“证明自研 Core 可跑”的主目标和“证明自我优化循环有效”的次目标。
2. 优先保留：self runtime、5 步验证链、编程插件、subset 级 evaluation、AK-llm-wiki 最小闭环。
3. 后移：长程任务全量、Auto-Research 3–5 轮、Memory 七动词全补全。

### P2-1：当前冻结节律偏激进，部分硬接口在被验证之前就被要求冻结

证据：

- [docs/roadmap.md](../../docs/roadmap.md) 要求 M0 结束冻结 `AgentRuntime`、`MemoryBackend`、`ToolSpec + PluginRegistry`。
- [docs/milestones/M0-plan.md](../../docs/milestones/M0-plan.md) 的 `DoD-7` 也要求三个硬接口在 M1 前冻结。
- 但当前仓库并无 `src/phoenix/**`，这些接口尚未经历真实实现压力。

为什么这是问题：

冻结本身不是坏事，但在“零实现压力”阶段过早冻结，容易把还没有被事实验证的抽象提升成高成本约束。对单作者项目而言，这会把后续最需要灵活调整的阶段变成文档先行的负担。

最小修复方向：

1. 冻结“字段与职责边界”，不要冻结过多细节语义。
2. 允许 M1 前半以 Patch/Minor 的方式温和收敛接口，而不是把 M0 当成抽象终局。

### P2-2：教学与治理闭环很完整，但当前门槛可能反向吞掉实现产能

证据：

- [docs/RnD-Analysis.md](../../docs/RnD-Analysis.md) 已把 `R-TL-1` 和 `R-TL-2` 标为 active。
- M0、M1、M2 的每一步几乎都伴随 F-* 或 M-* 产物、ingest、query 召回、frontmatter 维护。
- [docs/rules/learning-artifact-rules.md](../../docs/rules/learning-artifact-rules.md) 对 frontmatter、tier、引用、replaces 都提出了高要求。

为什么这是问题：

这套设计的长期价值很高，但在实现面尚未启动时，过强的学习与记忆硬门槛可能直接蚕食主线开发时间。尤其在 M1 这种高密度实现阶段，如果每个 Step 都要求完整教学闭环，容易出现“治理先丰满，实现后滞后”的反噬。

最小修复方向：

1. 把“每步必有完整教学产物”收敛为“每个关键能力面必须有教学产物”。
2. 允许在同一能力簇内合并 F-* 节点，避免碎片化产出。
3. 对学习质量继续保持高标准，但把触发点从“每一步”改成“每个完成的能力块”。

### P2-3：Teaching 与 DoD 的深度质量仍然主要依赖人工，不足以支撑“无死角”自证

证据：

- [tools/ci-check-teaching.py](../../tools/ci-check-teaching.py) 主要校验 frontmatter、slug、tier、字数和 ingest 元数据。
- [docs/quality/definition-of-done.md](../../docs/quality/definition-of-done.md) 中 `L-3`、`E-3`、`E-4`、`E-5` 这类条款，本质上仍需要人工判断内容深度和失败路径质量。

为什么这是问题：

这不是实现错误，而是审查边界问题：当前系统可以保证“格式化合规”，还不能保证“教学内容真的够深，错误路径真的覆盖到位”。对单人项目来说，这意味着最终质量还是取决于作者自律，而非工具。

最小修复方向：

1. 把哪些条款是自动化证明、哪些条款是人工审查，明确分层写出来。
2. 在 reviewer checklist 中强化“内容充分度”和“错误路径证据”的显式检查。

## 分维度判断

| 维度 | 判断 | 说明 |
|---|---|---|
| 立项价值 | 高 | 选题清晰，差异化明确，长期价值真实存在 |
| 架构设计质量 | 高 | 八层划分、5 步验证链、HarnessFlags 治理、ADR/风险体系都比较成熟 |
| 治理设计质量 | 中高 | 规则完整，但当前自动化覆盖和机器可审计性还不够收敛 |
| 当前实施准备度 | 低 | doctor 严格模式未通过，记忆与评测依赖未就位 |
| M1 达成可行性 | 中 | 需要先补基线、收窄范围、前置外部依赖验证 |
| M2 达成可行性 | 低到中 | Kimi 风险、成本口径、三方 runtime 对齐都还没有被前置证明 |

## 立项审查

立项本身是成立的，而且判断有高度一致性：

- [docs/PRD.md](../../docs/PRD.md) 清楚回答了“为什么做”，并把全链路自研可控、可教学、可插拔、可验证、低成本高性能五个关键词放到了产品核心。
- [docs/TRD.md](../../docs/TRD.md) 没有把项目做成一个模糊的“万能 Agent”，而是把编程场景、记忆闭环、评测闭环和教学闭环全部显式化，这比很多仅有愿景没有执行支点的项目成熟得多。

真正的问题不在“要不要做”，而在“第一阶段想证明什么”。当前立项同时追求：

- 自研 Core。
- 强 Harness。
- AK-llm-wiki 记忆闭环。
- SWE-bench / 长程评测。
- Auto-Research 自我调优。
- Teaching 资产沉淀。
- Kimi 成本优化。

这组目标单独看都合理，但放到 M0→M2 的首轮兑现路径里，目标面偏宽。对单作者项目而言，第一阶段最需要的是一个更窄、更硬、更可证伪的北极星。

## 设计审查

设计层最大的优点是“抽象层次分得非常明白”。

- Runtime 决定怎么跑。
- Model 决定用谁跑。
- Harness 决定跑得稳不稳。
- Plugin 决定能做什么。
- Memory / Evaluation / Auto-Research / Teaching 则把长期复利能力单独拎出来。

这套设计有两个很强的优点：

1. 安全路径不是附加品，而是核心路径。5 步验证链是整套设计里最值得保留的硬约束。
2. Memory、Evaluation、Teaching 被视作一等公民，而不是“以后再补”的外围系统。这使项目真正具备复利潜力。

设计层的主要问题不在“方向错”，而在“冻结过早”和“度量闭环不够实”。换句话说，设计质量高，但设计已经先于实现压力做了太多精细承诺。

## 实施审查

当前实施层的真实状态可以概括为一句话：治理实现已经开始，产品实现尚未开始。

这不是坏事，但必须据此修正预期。当前真正已经落地的，是这些东西：

- 文档治理体系。
- 风险与 ADR 机制。
- doctor / validator 脚本。
- M0/M1/M2 的 step-based 计划。

当前尚未落地的，是项目真正要拿来证明价值的实现面：

- `src/phoenix/**`
- `tests/**`
- 实际的 runtime、plugin、memory adapter、evaluation runner

因此，现阶段最关键的实施判断不应是“架构漂亮不漂亮”，而应是：

1. 当前环境能不能让 M0 开始。
2. M0 结束后能不能产生一份真正可复用的基线。
3. M1 是否能在单作者资源范围内证明自研 Core 的存在价值。

按照当前证据，第 1 条尚未满足，第 2 条尚未定义清楚，第 3 条需要大幅收敛范围后才有把握。

## 目标达成可行性判断

### M0

判断：当前 `No-Go`，修复环境后可转 `Go`。

原因很直接：M0 的出口条件依赖 doctor、wiki、SWE-bench、teaching ingest，而这些前提当前并未全部到位。

### M1

判断：当前 `Conditional Go`。

前提条件：

1. M0 必须产出冻结基线工件。
2. M1 目标必须收敛到“证明 self runtime + validation chain + coding plugin + subset evaluation 可运行”。
3. Auto-Research 和长程任务要从“必须达成”降为“有余力时推进”或拆成 M1b。

### M2

判断：当前 `No-Go`，除非 M1 先证明两件事。

必须先被证明的两件事：

1. Kimi 的接入与稳定性在 CLI 路径上真实可用。
2. 成本 KPI 的计算口径已经被固定，不会在执行成本和端到端成本之间摇摆。

如果这两件事不先收敛，M2 的“准确率下降不超过 5pp + 成本下降 60% + 三方 runtime 对齐 + 热切换回归”会变成一组不可同时审计的承诺。

## 主要优势

### 优势 1：产品判断成熟，不是空泛的“做个 Agent”

[docs/PRD.md](../../docs/PRD.md) 和 [docs/TRD.md](../../docs/TRD.md) 都体现出很强的产品判断力：PhoenixAgent 要解决的不是单次代码生成，而是一个可验证、可记忆、可复利的长期编码代理体系。

### 优势 2：安全与治理思路是成体系的

5 步验证链、HarnessFlags 冻结策略、ADR 触发条件、Risk Register 状态机，这些都不是装饰性规则，而是实打实在约束未来实现的设计。

### 优势 3：Step-based 计划非常适合单作者推进

M0/M1/M2 的步骤依赖图和“进入下一步条件”设计得很好，适合作为作者与 Agent 协同推进的共同操作界面。

### 优势 4：Evaluation 与 Teaching 被放进主路径，这是长期复利的关键

很多项目把评测和知识沉淀放在最后补。PhoenixAgent 把它们放在主路径上，这个判断从长期来看是对的。

## 最小纠偏路径

如果目标是把当前项目从“治理草案”推向“可执行计划”，我建议按下面顺序修正，而不是继续加新规则。

1. 先把 M0 环境收敛到 `doctor --strict` 通过。
2. 在 M0 固定一份真正可复用的 baseline 工件，包含 subset、seed、runtime、model、flags、cost 口径。
3. 重写 M1 出口，把 `Auto-Research 3–5 轮` 和 `长程任务全量`从硬门槛里移出去，先证明 self runtime 的最小价值闭环。
4. 在 M1 内前置 Kimi smoke gate，并在 M2 前冻结成本计算口径。
5. 把 `ci-check-spec` 的 warning 从三位数压到可管理范围，优先修正 ID 定义方式、Milestone 启动基线和变更日志。

## 最终判断

PhoenixAgent 不是“方向错了”的项目，恰恰相反，它的方向判断相当强。问题在于：当前文档已经对未来的好系统描述得很清楚，但还没有把“如何从今天稳态走到那个系统”收敛成一个足够窄、足够硬、足够可验证的兑现路径。

所以我的审查结论是：

- 立项：通过。
- 架构设计：通过。
- 当前实施准备：不通过。
- 以当前文档原样直接承诺 M1/M2：不建议。
- 经过环境收敛、基线冻结、范围收窄后的继续推进：建议执行。

---

**2026-04-22 第一轮修复（R1）声明**：~~上述审查指出的主要问题已全部根据 tasklist 完成修复。~~（**已被 R2 撤回**）

**2026-04-22 第二轮事实核查（R2）更新**：R1 的"全部完成"声明经本轮核查被部分撤回；修复进入 R2 稳态后的实际结论如下：

- **已完成（有证据链）**：T-P0-1 / T-P0-2 / T-P1-1a / T-P1-1b / T-P1-3 / T-P1-4 / T-P2-1 七项。
- **R2 期新补完整**：T-P1-2（SPEC `v1.1 -> v1.2` 通过 ADR-0003 引入 `CostBreakdown` + `experiment-report` 双曲线字段）、T-P1-5（M1a/M1b 拆分后 §0/§1 DoD 按 `D-3 = B` 实质切分，新建 M1-plan.md 索引稳住下游引用）。
- **部分完成 / 延续项**：
  - T-P2-2：`learning-artifact-rules §4.4` 能力块合并规则已落；`ci-check-teaching.py` 的"能力块必有产物"校验登记为 M1 Step 1 前交付。
  - T-P2-3：DoD `[auto]/[review]/[hybrid]` 全量标签已落；reviewer checklist 的"内容充分度 / 错误路径证据"强化项挂 C-4 后续波次。
- 对应 CI 输出：`ci-check-spec.py` / `ci-check-milestone-dod.py` `错误 0 / 警告 0`；`ci-check-teaching.py` `错误 0 / 警告 2`（`F-01` 占位允许）。

当前项目进入"R2 事实稳态"，R1 的"全部完成"结论不再成立，但未完成分支已被显式登记与挂靠，M0 Step 2 可按此基线推进。
