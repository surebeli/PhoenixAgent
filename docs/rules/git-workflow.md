# Git 工作流规则（Git Workflow）

- 版本：v1.0（2026-04-18）
- 作者：dy
- 适用范围：PhoenixAgent 单仓（`F:\workspace\ai\PhoenixAgent`）的一切 git 操作：分支、commit、PR、worktree、rebase、revert、release tag。
- 上位依据：TRD §5 / SPEC v1.0 §5.1（`s12_worktree` = True，worktree 为基本安全隔离）、TRD SEC-02（代码改动必须在 git worktree 内）。
- 下位依据：`documentation-rules.md`、`spec-change-policy.md`、`definition-of-done.md`、`acceptance-checklist.md`。

---

## 1. 本规则存在的理由（Why）

PhoenixAgent 同时承载两类产物：代码（`src/phoenix/**`）与文档 / 教学 / 规则（`docs/**`、`tools/**`）。它们对 git 的需求不一致：

- **代码**：必须走 worktree（s12 / SEC-02），任一改动都要可还原；Agent 自我驱动的实验必须可隔离（否则 `R-AR-1` / `R-PL-1` 的概率会显著上升）。
- **文档 / 规则**：要求 LLM-ready（`documentation-rules` D-LLM-12），其 commit message 必须包含版本号 + 章节编号，因为文档会被 ingest 到 wiki，commit 本身就是 ingest 的触发信号。

所以"一把尺子量到底"的 git 流程会同时伤害两边。本规则为两类产物各自定义约束，并在交叉场景（ADR / SPEC 变更 / DoD 豁免）给出联合规则。

---

## 2. 分支模型

单仓 / 单人 / 单 main：

- **唯一长期分支**：`main`。保持始终可跑（`ci-check-spec.py` / `ci-check-teaching.py` / `ci-check-milestone-dod.py` 全部通过）。
- **工作分支**：以目的命名，合入后立即删除。详见 §2.2。
- **标签**：Milestone 验收后打 annotated tag；详见 §7。
- **禁止**：`develop` / `release/*` / GitFlow 风格的长期分支；禁止在 main 上直接力推（`git push --force`）。

### 2.1 命名约定

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feat/` | 新功能代码 | `feat/self-runtime-dispatch` |
| `fix/` | Bug 修复 | `fix/memory-ingest-race` |
| `docs/` | 文档（含 rules / quality / ADR / milestones） | `docs/m2-plan-retrospective` |
| `spec/` | SPEC 变更（独立前缀方便 reviewer 抓取） | `spec/v1.1-harness-flags-minor` |
| `adr/` | ADR 新增 / 修订 | `adr/0003-kimi-endpoint` |
| `teach/` | 教学 artifact（F-* / M-*） | `teach/m1-f12-validation-chain` |
| `ci/` | 工具链 / 校验脚本 | `ci/check-adr-script` |
| `chore/` | 其他杂项（依赖升级 / 目录整理） | `chore/pin-python-3.11` |
| `research/` | Auto-Research 实验分支 | `research/ar-round-3-compressor` |
| `exp/` | 一次性探索（不保证合入） | `exp/bench-qwen3-coder` |

- **G-BR-1**：分支名 slug 采用 kebab-case、`a-z0-9-`、≤ 50 字符、必须含目的而非仅用户名或日期。
- **G-BR-2**：`research/` 与 `exp/` 允许存在 > 14 天；其他前缀分支超过 14 天未合入必须开 ADR 或删除。

### 2.2 生命周期

1. 从最新 `main` 拉出工作分支。
2. 代码类分支首次写入前必须进入 git worktree（§5）。
3. commit 频率参照 §3。
4. 通过本地 CI（§6）后 PR 到 main。
5. 合入后 **立即删除**工作分支（本地 + 远端）。

---

## 3. Commit 规约

采用 Conventional Commits（3-句式缩略版），以便自动生成变更日志并与 wiki ingest 对接。

### 3.1 格式

```
<type>(<scope>): <subject>

<body — 可选，硬换行 72 列>

<footer — 可选，Refs / Closes / Co-Authored-By / ADR 引用 等>
```

### 3.2 `type` 取值

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档（PRD/TRD/RnD/SPEC/rules/quality/teaching/adr/milestones） |
| `spec` | **专用于 SPEC.md 的变更**；与 `docs` 分开便于 `spec-change-policy` 审计 |
| `refactor` | 不改行为的内部重构 |
| `test` | 仅测试相关 |
| `ci` | 校验脚本、hook、仓设置 |
| `chore` | 其他杂项（版本固定、依赖升级） |
| `revert` | 明确 revert |
| `research` | Auto-Research 实验产出（报告 / 节点） |

### 3.3 `scope` 取值

对代码类：使用 `phoenix.<layer>`（`runtime` / `model` / `harness` / `plugin` / `memory` / `evaluation` / `auto_research` / `teaching`）。
对文档类：使用文档名或目录，`prd` / `trd` / `rnd` / `spec` / `rules/<file>` / `quality/<file>` / `adr` / `m0-plan` / `m1-plan` / `m2-plan` / `teaching/m<N>`。
对 CI：使用 `ci-check-<name>`。

### 3.4 `subject` 规则

- 祈使句，**中文或英文均可**；全仓保持单一语种即可，不强制混用。
- 长度 ≤ 72 字符（含 type/scope）。
- 禁止以句号结尾。
- 禁止"update / fix stuff"等无信息动词。

### 3.5 SPEC 专用格式（type=spec）

- subject 必须包含起止版本号，例如：`spec(spec): bump v1.0 → v1.1 add HarnessFlags.s13_*`。
- footer 必须含 `ADR: ADR-NNNN`（对应 Minor / Major 变更；Patch 级豁免）。
- 同一 PR 内 SPEC 与实现文件**不得混合提交**（见 §4.3）。

### 3.6 Body

- 可选但 Major / 冻结期破冻 / DoD 豁免相关 commit 必填；解释"为什么"而非"做了什么"。
- 禁止粘贴 chat 对话截图 / URL 作为唯一动机（违反 `documentation-rules` D-LLM-13）。

### 3.7 Footer

- `Refs:` 引用 ID 清单（FR-NN / D-RT-N / R-RT-N / DoD-M<N>-<K> / ADR-NNNN / F-NN / M-<slug>）。
- `Closes:` 关联 issue（若启用 issues）。
- `Co-Authored-By:` Agent 协作时附上（如 Claude Code 自动 commit 场景）。
- `Spec-Version:` 代码类 commit 若依赖特定 SPEC 版本必填。

### 3.8 约束汇总

- **G-CM-1**：任一 commit 只涉及一个"逻辑变更单位"；多目的必须拆 commit。
- **G-CM-2**：代码 commit 必须包含 `Spec-Version: vX.Y[.Z]` footer，指向其所对齐的 SPEC 版本。
- **G-CM-3**：禁止 `--no-verify` 绕过 hook；确实需要绕过必须在 PR 描述中说明并走人工审查。
- **G-CM-4**：禁止 amend 已 push 到远端的 commit（即使单人项目，避免将来误用）。
- **G-CM-5**：wip / temp commit 禁止进入 main；通过本地 rebase squash 清理。

---

## 4. PR（Pull Request）规范

### 4.1 何时必须开 PR

所有进入 main 的变更都经由 PR。单人项目仍开 PR 的理由：

1. 强制 CI 通过门槛。
2. PR 描述承载"变更摘要 / 影响面"，成为将来审计的索引。
3. 与 ADR / SPEC / DoD 触发条件天然耦合。

### 4.2 PR 分类与附加要求

| 分类 | 触发 | 额外要求 |
|---|---|---|
| 常规代码 | `feat/*`, `fix/*`, `refactor/*` | 本地 CI 全绿；对齐的 `Spec-Version` 已冻结；不触发 SPEC 变更 |
| SPEC 变更 | `spec/*` | 包含 ADR 链接（Minor/Major）；迁移指引（Major）；`ci-check-spec.py` 0 error |
| 文档 | `docs/*` | `ci-check-spec.py` 0 error；受影响 Tier-0 的 `变更日志` 章节已更新 |
| 教学 | `teach/*` | `ci-check-teaching.py` 通过；wiki-ingest marker（`.ingested.json`）已更新 |
| ADR | `adr/*` | 使用 `ADR-TEMPLATE.md`；与 SPEC / DoD / risk / roadmap 的关联字段已填 |
| Milestone retrospective | `docs/m*-retrospective` | `ci-check-milestone-dod.py` 通过；冻结清单显式列出 |
| Auto-Research | `research/*` | `experiment-report.md` 齐备；受影响 `R-*` status 已更新 |

### 4.3 一 PR 多类混合

- **禁止**同一 PR 同时修改 SPEC 和对应层代码（违反 `spec-change-policy` §5 Step 3/4：SPEC 先行、实现跟进）。
- **允许**同一 PR 修改多份文档（如 retrospective + roadmap + risk-register 联动）。
- **允许**ADR 与触发它的 SPEC 变更分拆到两个 PR，但顺序必须是 ADR 先合入；spec PR 中的 footer 引用已合入 ADR。

### 4.4 PR 描述模板

```markdown
## 摘要
<一两句话说明变更目的>

## 变更类型
- [ ] feat / fix / refactor
- [ ] docs / spec
- [ ] teach
- [ ] adr
- [ ] research / ci / chore

## 关联 ID
- PRD: FR-__
- TRD: D-__-__
- SPEC: v__.__.__
- DoD: DoD-M<N>-<K>
- Risk: R-__-__
- ADR: ADR-NNNN
- Teaching: F-__ / M-<slug>

## 影响面
<列出受影响文档 / 代码 / wiki namespace>

## 测试 / 校验证据
- [ ] 本地 `py -3 tools/ci-check-spec.py` 0 error
- [ ] 本地 `py -3 tools/ci-check-teaching.py` 通过
- [ ] 本地 `py -3 tools/ci-check-milestone-dod.py` 通过
- [ ] 手动验证（对 UI / CLI 场景补充说明）

## 回滚预案
<不可回滚的变更必须显式说明冻结窗口>
```

### 4.5 Review 节律

- 单人项目下 reviewer = 作者自己 + Agent 辅助：
  - Agent（Claude Code / Codex）必须跑一次 `ci-check-spec.py` / 相关 CI，并把输出粘贴进 PR 评论。
  - 作者必须在合入前读完本 PR 的 diff 并回答 PR 描述中每个 checkbox。
- 未来引入协作者时，reviewer 必须 ≥ 1 人非作者。

---

## 5. git worktree 规则（对齐 s12 / SEC-02）

`SPEC v1.0 §5.1` 默认 `s12_worktree = True`；`TRD SEC-02` 规定"代码改动必须在 git worktree 内"。本节把这两条落成可操作规则。

### 5.1 何时必须走 worktree

任一下列情形：

- Agent（`ClaudeAgentSDKRuntime` / `PhoenixCoreRuntime` / `OpenAIAgentsRuntime`）被授权改写 `src/phoenix/**` 或 `tools/**`。
- Auto-Research 的 Generator 产出代码 patch。
- 批量文档重构（改动 > 5 文件）时建议走 worktree 隔离回滚。
- 任一破坏性本地实验（引入新依赖、重构目录结构）。

**可不走** worktree 的情形：

- 纯 PR 描述 / Markdown 文档单文件小改。
- CI 脚本的 bugfix 且影响面清楚。

### 5.2 约束

- **G-WT-1**：worktree 路径必须在 `F:\workspace\ai\PhoenixAgent.worktrees\<branch-slug>` 下；禁止散落到临时目录。
- **G-WT-2**：worktree 内提交后，使用 `git worktree remove` 清理；禁止留下僵尸 worktree > 48h。
- **G-WT-3**：Agent 在 worktree 内运行时，必须同时开启 `HarnessFlags.s12_worktree = True`（已是默认）；`PermissionRules` 中涉及代码写操作的 tool 必须 `requires_worktree = True`。
- **G-WT-4**：失败的实验 branch 允许直接删除；删除前先 push 到 remote 归档（若影响面评估时需要后向追溯）。

### 5.3 与 Claude Code 的 Agent 工具集成

- Claude Code 的 `EnterWorktree` / `ExitWorktree` 工具对齐 `s12`。
- `Agent` 工具的 `isolation: "worktree"` 参数在需要破坏性探索时打开；常规文档 agent 不必启用。

---

## 6. 本地 CI Gate

合入 main 前本地必须跑过下列脚本，全绿才允许 PR（未来 GitHub Actions 落地后重复执行）：

| 脚本 | 门槛 | 关联规则 |
|---|---|---|
| `py -3 tools/ci-check-spec.py` | 0 error | `documentation-rules` / `spec-change-policy` |
| `py -3 tools/ci-check-teaching.py` | exit 0 | `learning-artifact-rules` |
| `py -3 tools/ci-check-milestone-dod.py` | exit 0 | `definition-of-done` / `acceptance-checklist` |
| （将来）`tools/ci-check-adr.py` | 0 error | `docs/adr/README.md §8` |
| （可选）`pytest -q` / `ruff check .` | 0 failure | 代码类 PR |

- **G-CI-1**：PR 描述必须粘贴上述脚本的 exit 码与关键摘要行。
- **G-CI-2**：`.git/hooks/pre-commit` 必须至少跑 `ci-check-spec.py`；`pre-push` 跑全套。
- **G-CI-3**：CI 失败不得通过 `--no-verify` 绕过；需绕过见 G-CM-3。

---

## 7. Tag、Release 与 Milestone

- **G-TAG-1**：每个 Milestone 验收合入后打 annotated tag：`M<N>-complete`（例：`M1-complete`）。
- **G-TAG-2**：SPEC 版本跃迁打 tag：`spec/v<X>.<Y>[.<Z>]`。
- **G-TAG-3**：tag commit message 必须含：
  - 对应 `M*-retrospective.md` 路径；
  - 冻结的硬接口清单（与 `roadmap.md §3` 一致）；
  - KPI 达成摘要（与 `PRD §9` 一致）。
- **G-TAG-4**：禁止移动 / 删除已 push 的 tag。

---

## 8. 回滚与 revert

- **G-RV-1**：main 上发现错误优先用 `git revert <sha>`（保留历史），而非 `git reset --hard`。
- **G-RV-2**：涉及 SPEC 的 revert 必须同步处理：
  - 回滚 SPEC 版本号（若 Y/Z 已递增）；
  - 更新对应 ADR 状态为 `Superseded`（由新 ADR supersede 原 ADR）；
  - 更新 `risk-register` 若相关风险状态因变更已调整。
- **G-RV-3**：涉及 Milestone tag 的 revert 属于重大事件，须开紧急 ADR（见 `spec-change-policy` S-FREEZE-2）。

---

## 9. 与 Agent 协作的特例

- 本项目大量由 LLM Agent（Claude Code / Codex / 自研 PhoenixAgent）代笔 commit；下列约束同等适用：
  - Agent 生成的 commit 必须走同一格式（§3）。
  - Agent 生成的 PR 描述必须通过 §4.4 模板（允许作者最后修订）。
  - Agent **禁止**在没有显式用户确认下：`git push --force`、`git reset --hard`、删除 tag、修改 `.git/config`、跳过 hook。
- Agent 的所有 `git` 写操作必须在 PhoenixContext 下经 `PermissionRules.check` 放行（见 SPEC v1.0 §11）。

---

## 10. 违规与检查

| 违规 | 检查点 | 行为 |
|---|---|---|
| 分支命名不符 §2.1 | PR 打开时自动脚本 + reviewer | 阻塞 |
| commit 格式不符 §3 | `pre-commit` hook + PR 校验 | 阻塞 |
| SPEC 与实现混在一 PR | `spec-change-policy` §9 | 阻塞 |
| 代码改动未走 worktree（敏感目录） | `HarnessFlags.s12` + `PermissionRules` | 拒绝工具调用 |
| PR 描述未填模板 | reviewer 人工 | 要求修订 |
| 本地 CI 未跑 / 失败 | PR 描述缺脚本输出 | 阻塞 |
| `--no-verify` 未说明 | commit footer + PR 审查 | 阻塞 |
| Tag 被移动 / 删除 | 远端保护规则（启用后） | 拒绝推送 |

---

## 11. 与其他规则的交叉引用

- `docs/rules/documentation-rules.md`：PR 类别对文档 `变更日志` 的要求。
- `docs/rules/spec-change-policy.md §5 / §9`：SPEC 变更 PR 流程与违规检查。
- `docs/rules/learning-artifact-rules.md §5`：教学 PR 的 ingest 与 `.ingested.json` 更新。
- `docs/rules/harness-flags-policy.md §5`（B-4）：flag 翻转 PR 的 ADR 要求。
- `docs/quality/definition-of-done.md §9`：DoD 豁免 PR 的 ADR 要求。
- `docs/adr/README.md §2`：ADR 触发器清单。

---

## 12. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-18 | 首版；落实分支 / commit / PR / worktree / CI gate / tag / revert 全部约束，对齐 s12 与 SEC-02。 |
