# Code Review Checklist（Reviewer 侧）

- 版本：v1.0（2026-04-19）
- 作者：dy
- 适用范围：所有进入 main 的 PR；reviewer = 作者本人 + Agent 辅助（参见 `git-workflow §4.5`）。本文件与 `acceptance-checklist.md`（执行者侧）互为对偶。
- 上位依据：`docs/quality/definition-of-done.md`、`docs/quality/test-strategy.md`、`docs/rules/documentation-rules.md`、`docs/rules/spec-change-policy.md`、`docs/rules/harness-flags-policy.md`、`docs/rules/git-workflow.md`。
- 下位依据：`.github/PULL_REQUEST_TEMPLATE.md`（PR 模板内的 checkbox 直接引用本文件条款编号）。

---

## 1. 本清单存在的理由（Why）

单人项目下没有 second pair of eyes；代码 / 文档 / SPEC 变更全部由作者或 Agent 自审。若无显式清单，三类漂移会悄然发生：

1. **SPEC / 实现 / 测试三者脱节**：改 SPEC 没改实现，或改实现没改测试，或改实现没改 SPEC。
2. **ADR 应开未开**：flag 翻转 / risk 触发 / SPEC Minor 被塞进"普通代码 PR"的 commit 里。
3. **反假陷阱**：用 TODO / 占位 / disable hook / 降覆盖率门槛让 PR "通过"。

本清单把 reviewer 必答的问题显式化，每条对应一个可审计的判定。未答或含糊回答的 PR 不得合入。

---

## 2. 使用方式

- 每次 PR 由作者本人或 Agent 在"PR Review 评论"中粘贴本清单相关分节，逐条判定 `✓ / ✗ / N/A`。
- `✗` 必须附理由 + 后续动作；`N/A` 必须附"为何不适用"一句话。
- Agent（Claude Code / Codex / PhoenixAgent）辅助 review 时，必须同时粘贴各 `ci-check-*.py` 的输出；不得替代作者判定。
- 所有 `✗` 在合入前必须转 `✓` 或走 ADR 豁免。

---

## 3. 通用分节

### 3.1 PR 分类正确性（对齐 `git-workflow §4.2`）

- **CR-G-1**：branch prefix 与 PR 标题描述的变更性质一致（`feat/` / `fix/` / `docs/` / `spec/` / `adr/` / `teach/` / `research/` / `ci/` / `chore/`）。
- **CR-G-2**：单 PR 未混合 SPEC 变更与实现代码（SPEC 先行原则）。
- **CR-G-3**：commit message 满足 Conventional Commits + `Spec-Version: vX.Y[.Z]` footer（代码类）/ `ADR: ADR-NNNN` footer（ADR 类）。
- **CR-G-4**：PR 描述填满 `.github/PULL_REQUEST_TEMPLATE.md` 的所有 section，无"略"/"TODO"。

### 3.2 SPEC 对齐

- **CR-S-1**：引用 SPEC 时带版本号（`SPEC v1.1 §…`），未出现裸 `SPEC §` / `SPEC.md §`（D-REF-2）。
- **CR-S-2**：若改动涉及 SPEC 中已定义的 dataclass / Protocol / INV：
  - 是否同步修改了 SPEC 正文？
  - 版本号按 `spec-change-policy §4` 正确升档（Patch / Minor / Major）？
  - 有 ADR 链接？（Minor / Major 强制）
- **CR-S-3**：PR 中新增的公共函数 / 类是否都可追溯到 SPEC 中某一节或某一 `D-<layer>-N` 决策？若无，必须在 PR 描述或对应 ADR 中说明。
- **CR-S-4**：SPEC 中 `PhoenixContext` / `ToolSpec` / `HarnessFlags` / `AgentRuntime` 等硬接口若改动，同 PR 内未出现其他未经 ADR 授权的接口变更。

### 3.3 INV-* 与守护测试（对齐 `test-strategy.md §5`）

- **CR-I-1**：若 PR 新增 INV，同 PR 包含对应 `test_inv_<layer>_<n>_*`，含正面 + 负面两条断言（TS-INV-2）。
- **CR-I-2**：若 PR 删除 / 改名既有 INV，对应 `test_inv_*` 同 PR 删除 / 改名，不留孤儿。
- **CR-I-3**：若 PR 修改 INV 实现而不改 SPEC 条款文字，reviewer 必须自问"语义是否实际已变"；若答案"变了"，必须退回 PR 要求走 SPEC Minor。
- **CR-I-4**：新 INV 未被降级为 warning-only 检查（即必须在正面 / 负面路径上均起阻塞作用）。

### 3.4 HarnessFlags 语义（对齐 `harness-flags-policy` + ADR-0001）

- **CR-F-1**：代码中未出现 `harness_flags.sNN = <value>` 形式的属性赋值；所有修改走 `dataclasses.replace(ctx.harness_flags, ...)`。
- **CR-F-2**：若改动包含 flag 翻转 default，PR 链接对应 ADR（`ADR-NNNN-flag-<sNN>-default.md`）且含 `experiment-report.md`（`harness-flags-policy §5`）。
- **CR-F-3**：Safety-Critical flag（s01 / s02 / s12）的 default 未被改为 False；任何 Experimental Override = False 必须按 §4.1 例外登记。
- **CR-F-4**：新增 flag 消费点出现在 `phoenix.harness.*`（或 SPEC v1.1 §5.1 显式例外）下，不扩散到其他模块（HF-IMPL-2）。
- **CR-F-5**：CLI `--harness-flag` 覆盖路径若被改，打日志到 `PhoenixContext.session.flag_overrides` 的行为保留（HF-IMPL-3）。

### 3.5 权限 / 工具契约（对齐 SPEC v1.1 §11 + TRD SEC-*）

- **CR-T-1**：新增 Tool 时 `requires_worktree` / `dangerous` 显式设置（不使用默认值）。
- **CR-T-2**：新增 Tool 的 JSON Schema 覆盖 input / output；`permissions.toml` 至少一条规则对齐。
- **CR-T-3**：`git` / 文件写 / 网络出站类操作是否经 `PermissionRules.check`？
- **CR-T-4**：Hook 场景至少 1 条被测试覆盖（unit 或 integration）。

### 3.6 记忆（对齐 INV-MM-* + `learning-artifact-rules`）

- **CR-M-1**：新 ingest 节点的 `slug` 在 `.ingested.json` 中唯一；`tier` 与用途匹配（active / archived / frozen）。
- **CR-M-2**：subagent 产出未污染主 agent namespace（INV-MM-2）。
- **CR-M-3**：digest 变更同步 `digest_version`；M2 起热切换路径有回归测试。

### 3.7 文档同 PR（对齐 `documentation-rules` + `spec-change-policy §5 Step 3`）

- **CR-D-1**：受影响的 Tier-0 / Tier-1 / Tier-2 文档在同 PR 内已更新（版本号、§ 章节、`变更日志`）。
- **CR-D-2**：`docs/` 根目录未新增散落 `.md`（D-DIR-2；允许清单见 `ci-check-spec.py`）。
- **CR-D-3**：rules/* 未反向引用 `PRD §` / `TRD §`（D-REF-5）；Tier-0 未跨引 M*-plan 的章节（D-REF-4）。
- **CR-D-4**：M*-plan §0 启动前提若被改动，四件套基线版本号仍对齐当前（D-REF-3）。

### 3.8 教学 artifact tier

- **CR-L-1**：新 F-* 的字数在 [400, 3000]；必答问题在正文有直接回应。
- **CR-L-2**：`related_spec` / `related_inv` / `related_flag` 字段真实存在，不悬空。
- **CR-L-3**：tier 转换（active → archived → frozen）按 `learning-artifact-rules §5` 节律执行；未直接删除。
- **CR-L-4**：**内容充分度**：教学 artifact 与总结文档不是空泛的占位符，其核心概念、映射和失败模式等内容详实，足以为后续提供知识复利。

### 3.9 测试充分性（对齐 `test-strategy.md`）

- **CR-TS-1**：改动层的覆盖率未降超过 1 个百分点；若降则 PR 描述含降幅理由（TS-COV-1）。
- **CR-TS-2**：至少 1 条 **负面测试** 覆盖 E-5 错误路径（DoD §3 / `test-strategy §5.INV-2`）。
- **CR-TS-3**：Flag 翻转 PR 满足 TS-FLAG-1/2/3；Safety-Critical 翻转满足 TS-FLAG-SC-1/2/3。
- **CR-TS-4**：Auto-Research `Kept` 变更有对应 `tests/replay/golden/<slug>.yaml`（TS-AR-1）。

### 3.10 ADR 触发（对齐 `docs/adr/README.md §2`）

- **CR-A-1**：PR 是否命中 ADR trigger 表的任一行？命中即同 PR 或前置 PR 提供对应 ADR。
- **CR-A-2**：DoD 豁免、flag 翻转、risk `triggered`、新顶级目录、硬接口实现更替：任一出现即检查是否有 ADR。
- **CR-A-3**：ADR 本身若在本 PR 内，frontmatter 必填字段齐备（`ci-check-adr.py` 通过）。

---

## 4. 反假检查（对齐 DoD §8.2 AN-*）

reviewer 必须自问以下 5 条，任一"是"即阻塞合入：

- **CR-AN-1**：是否以 `TODO: 后续补` 代替应当 PR 内完成的学习节点或 INV 测试？
- **CR-AN-2**：是否用空函数 / 占位类 / 仅字符串返回的函数凑 E-1 "产物齐备"？
- **CR-AN-3**：是否临时 disable Hook / Permission / `--no-verify` 绕过 CI？
- **CR-AN-4**：是否在未经 ADR 的情况下修改了 DoD 条款文字、覆盖率门限、或本清单本身？
- **CR-AN-5**：PR / work log 中是否存在 `[x]` 勾选但无证据链接的行？

---

## 5. 升级与决策点

reviewer 判定以下任一情形时，**不能在本 PR 内 fix**，必须退回作者并新起 ADR / 拆 PR：

| 情形 | 推荐行动 |
|---|---|
| PR 描述"只是重构"但触及 SPEC 条款语义 | 退回；拆 SPEC PR → 实现 PR |
| 覆盖率门限首次下调 | 新 ADR（DoD 豁免） |
| 新增顶级目录 | 新 ADR（`documentation-rules` D-DIR-1） |
| Safety-Critical flag 发现需要 False default | 拒合入；走 `spec-change-policy` S-FREEZE-2 事后审查通道 |
| Auto-Research Generator 产出越界改动 | 拒合入；触发 `R-AR-1` |
| Agent commit 含 `--no-verify` | 拒合入；追加 ADR 或人工改提交 |

---

## 6. 完成判定

- 本 PR 全部清单条目 `✓` 或带证据的 `N/A`。
- 所有 `ci-check-*.py` 0 error（warning 列入 PR 描述尾部"已知存量"表）。
- `pytest` 按 `test-strategy §8.1` 结果齐备。
- PR 描述 `.github/PULL_REQUEST_TEMPLATE.md` 的所有复选框已打勾或显式 N/A。
- 若 PR 触发任一 ADR trigger，对应 ADR 已合入或同 PR 合入。

完成后 reviewer（自己或 Agent）留一条形如
`Reviewed: dy / <date> / commit <sha>; all CR-* pass (CR-XX-N=N/A 理由如下)`
的最终评论，方可合入。

---

## 7. 与其他文档的交叉引用

- `docs/quality/definition-of-done.md`：E-* / L-* / M-* / G-* / AN-* 条款的定义源。
- `docs/quality/test-strategy.md`：§3.9 CR-TS-* 的具体门限 / 测试分层。
- `docs/quality/acceptance-checklist.md`：执行者侧自审清单；本文件是 reviewer 侧的对偶。
- `docs/rules/git-workflow.md` §4：PR 分类 + 描述模板的规则源。
- `docs/rules/harness-flags-policy.md`：§3.4 CR-F-* 的规则源。
- `docs/rules/spec-change-policy.md`：§3.2 CR-S-* 的规则源。
- `docs/adr/README.md`：§3.10 CR-A-* 的触发条件源。
- `.github/PULL_REQUEST_TEMPLATE.md`：PR 描述模板；其 checkbox 编号与本清单条款一一对应。

---

## 8. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-19 | 首版；分 10 类 reviewer 清单（PR 分类 / SPEC 对齐 / INV 守护 / HarnessFlags 语义 / 权限工具 / 记忆 / 文档同 PR / 教学 tier / 测试充分性 / ADR 触发）+ 5 条反假 + 升级与决策点；与 C-2 acceptance-checklist 对偶；与 C-3 test-strategy 门限对齐；C-8 PR 模板承载编号。 |
