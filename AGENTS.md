# AGENTS.md — PhoenixAgent 通用 LLM Agent 入口

适用工具：Claude Code、OpenAI Codex、Cursor、PhoenixAgent 自身、任何遵循 `AGENTS.md` 约定的 LLM 工具。

> **完整设计原理 / 文档导航 / 阅读路径**：见 [`docs/README.md`](docs/README.md)。本文件只承载"必须遵守的硬约束 + 跳转入口"，不复制详文。

---

## 1. 当前阶段（必读）

- **治理层完整、实现层为零**。`docs/` 已就位；`src/phoenix/**` 与 `tests/**` 在 M0 / M1 之前不存在。
- **当前 Milestone**：M0（环境预检 + 八层接口冻结准备）。下一个待执行 Step：M0 Step 1（见 `docs/milestones/M0-plan.md`）。
- **SPEC 基线**：`v1.1`（首部 `docs/SPEC.md`）。

---

## 2. 不可逾越的硬约束

| 约束 | 来源 | 违反代价 |
|---|---|---|
| 改 SPEC 必须先开 ADR + 版本号递进 | `docs/rules/spec-change-policy.md` §5 | PR 阻塞 |
| 引用 SPEC 必须带版本号（`SPEC v1.1 §...`） | `docs/rules/documentation-rules.md` D-REF-2 | `ci-check-spec.py` 阻塞 |
| `HarnessFlags` 必须 `dataclasses.replace()`，**禁止属性赋值** | `harness-flags-policy.md` HF-IMPL-1 + `ADR-0001` | `ci-check-flags.py` 阻塞；reviewer 拒合入 |
| Safety-Critical flag（`s01` / `s02` / `s12`）default 永远为 True | `harness-flags-policy.md` HF-SEC-1 | 零容忍；P0 事故 |
| Tier-0 不得引用 M\*-plan 章节；rules 不得引用 PRD/TRD 章节 | `documentation-rules.md` D-REF-4 / D-REF-5 | `ci-check-spec.py` 阻塞 |
| commit footer 必含 `Spec-Version: vX.Y[.Z]`（代码 PR） | `git-workflow.md` G-CM-2 | reviewer 拒合入 |
| 禁止 `--no-verify` / `git push --force` / `git reset --hard`（除非显式确认） | `git-workflow.md` §9 | 零容忍 |
| `docs/` 根目录禁新增散落 `.md`（除 4 件套 + README + roadmap + risk-register） | `documentation-rules.md` D-DIR-2 | `ci-check-spec.py` 阻塞 |
| ADR 一旦合入 main 不得改写正文；只能追加修订段或新 ADR supersede | `adr/README.md` §4-5 | 零容忍 |
| 教学 artifact F-\* 字数 [400, 3000]；frontmatter 全填 | `learning-artifact-rules.md` | `ci-check-teaching.py` 阻塞 |

---

## 3. 触发 ADR 的情形（命中即同 PR 或前置 PR 提供 ADR）

任一下列情形必须创建 `docs/adr/ADR-NNNN-<slug>.md`：

- SPEC Minor / Major 变更
- DoD 条款豁免或阈值调整
- `risk-register` 任一 R-\* 转入 `triggered`
- `roadmap.md §6` 决策分支落地
- `HarnessFlags` 默认值翻转
- 接入 / 替换 / 下线一个硬接口的具体实现
- 引入新顶级目录或新 Tier-2 规则文件

完整触发表：`docs/adr/README.md` §2。

---

## 4. 必须运行的 CI（PR 前 / 完成任务前）

```bash
py -3 tools/ci-check-spec.py        # Tier-0 + 跨文档 ID + SPEC 版本号
py -3 tools/ci-check-adr.py         # ADR 命名 / frontmatter / 编号唯一
py -3 tools/ci-check-flags.py       # SPEC §5.1 ↔ harness-flags-policy §3
py -3 tools/ci-check-teaching.py    # 教学 artifact（动到 docs/teaching/ 时）
py -3 tools/ci-check-milestone-dod.py  # M*-plan DoD 闭环（动到 milestones/ 时）
```

任一 0 error 才算通过；warning 列入 PR 描述"已知存量"。

---

## 5. PR 与 Review

- **PR 模板**：`.github/PULL_REQUEST_TEMPLATE.md`，所有 section 必填，N/A 必带理由。
- **Reviewer 自评**：照 `docs/quality/code-review-checklist.md` 10 类清单逐条 ✓/✗/N/A。Agent 辅助 review 时必须粘贴 CI 输出。
- **Acceptance**：照 `docs/quality/acceptance-checklist.md` Step / Milestone 勾选清单（执行者侧）。

---

## 6. Agent 应该读的文档（按场景）

| 你要做的事 | 必读 |
|---|---|
| 任何任务首次进入 | `docs/README.md`（治理结构）+ 本文件 |
| 改 SPEC | `docs/rules/spec-change-policy.md` + `docs/SPEC.md` 相关章节 + 起 ADR |
| 改 HarnessFlags | `docs/rules/harness-flags-policy.md` + `docs/adr/ADR-0001-harness-flags-frozen.md` |
| 加新 Tool / Runtime / Model | `docs/SPEC.md` §3-5 + `docs/quality/definition-of-done.md` E-T\* / E-R\* / E-M\* |
| 写教学节点 F-\* / M-\* | `docs/rules/learning-artifact-rules.md` + 当前 Milestone 的 plan |
| 跑 Auto-Research | `docs/SPEC.md` §8 + `docs/quality/test-strategy.md` §7 |
| 改 git / commit / PR 流程 | `docs/rules/git-workflow.md` |
| 评估自己的代码质量 | `docs/quality/code-review-checklist.md` |
| 起 ADR | `docs/adr/README.md` + `docs/adr/ADR-TEMPLATE.md` |

---

## 7. 平台与工具约定

- **OS**：Windows 11；shell 用 bash（不是 cmd / PowerShell）。
- **Python**：调用一律 `py -3 <script>`，不是 `python <script>`。
- **Git**：仓库根 `F:\workspace\ai\PhoenixAgent`；UTF-8 文件；CRLF 由 git 自动处理。
- **路径**：脚本内用 `pathlib.Path`；命令行参数用绝对路径或相对 repo 根。

---

## 8. 反假约定（reviewer 必查；对齐 DoD AN-\*）

任一情形即阻塞合入：

- 用 `TODO: 后续补` 代替应当 PR 内完成的内容
- 用空函数 / 占位类 / 仅返回字符串的函数凑"产物齐备"
- 临时 disable Hook / Permission / `--no-verify` 让 CI 走通
- 未经 ADR 改 DoD 条款 / 覆盖率门限 / 本文件
- `[x]` 勾选无证据链接

---

## 9. 升级 / 偏离场景

如果你（agent）发现：
- 某条规则与代码现实严重冲突 → **不要修改规则绕过**；停下来报告作者，待新 ADR 决定。
- 某个 INV / 不变量在实现中无法维持 → **不要降级为 warning**；新 ADR 改不变量。
- 跑出 CI error 你不理解 → **不要静默跳过**；把 error 完整粘到 PR 评论让作者判定。

唯一允许的"绕过"是：作者明确授权 + 同 PR 内有补救动作 + 走 retrospective 登记。

---

## 10. 谁维护本文件

- 任何"硬约束"清单变更必须同步更新本文件。
- 任何 ADR 的产出若改变 agent 行为约束（如 ADR-0001 引入 frozen 约束），必须把对应条目加到 §2。
- 本文件不写"原理"和"为什么"——那些在 `docs/README.md`；本文件只列 **必须遵守的事实**。

---

最后更新：2026-04-19。
