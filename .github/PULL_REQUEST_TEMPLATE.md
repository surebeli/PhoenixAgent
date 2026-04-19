<!--
PhoenixAgent PR 模板（对齐 docs/rules/git-workflow.md §4.4、docs/quality/code-review-checklist.md）。
每个 section 都必须填写；不适用的条目写 N/A + 一句理由，禁止删除或留空。
-->

## 摘要

<!-- 一到两句话说明变更目的与范围。避免粘贴 diff。 -->

## 变更类型

- [ ] feat（新功能）
- [ ] fix（缺陷修复）
- [ ] refactor（无行为变更的结构调整）
- [ ] spec（SPEC 文本变更；Patch / Minor / Major 必须在下方标注）
- [ ] docs（Tier-0/1/2 文档变更）
- [ ] teach（教学 artifact，`docs/teaching/**`）
- [ ] adr（Architecture Decision Record）
- [ ] research（Auto-Research 产出）
- [ ] ci（CI 脚本 / 工具链）
- [ ] chore（依赖 / 构建 / 脚手架）

## 关联 ID

<!-- 不适用的行填 N/A；不得整行删除，便于模板化审计。 -->

- PRD: FR-__ / NFR-__ / OOS-__
- TRD: D-<layer>-__ / SEC-__
- SPEC: v__.__（必填；代码 PR 同 `Spec-Version` footer）
- DoD: DoD-M<N>-<K>
- Risk: R-<layer>-__ / OP-__
- ADR: ADR-NNNN
- Teaching: F-<idx> / M-<slug>
- Flag: s<NN>（若涉及 HarnessFlags）

## SPEC 变更分级（仅 spec 类 PR 必填）

- [ ] Patch（编辑性；无 ADR）
- [ ] Minor（向后兼容；必须有 ADR）
- [ ] Major（破坏性；必须有 ADR + Migration Guide）
- SPEC 版本：`vX.Y.Z` → `vX.Y.Z`

## 影响面

<!-- 列出受影响的文档、代码模块、wiki namespace、CI 脚本；与 docs/quality/code-review-checklist.md §3.7 对齐。 -->

- 文档：
- 代码模块：
- wiki / memory namespace：
- 其他：

## 测试 / 校验证据

- [ ] `py -3 tools/ci-check-spec.py` 0 error
- [ ] `py -3 tools/ci-check-adr.py` 0 error（若涉及 ADR）
- [ ] `py -3 tools/ci-check-flags.py` 0 error（若涉及 HarnessFlags / SPEC §5.1）
- [ ] `py -3 tools/ci-check-teaching.py` 0 error（若涉及 `docs/teaching/**`）
- [ ] `py -3 tools/ci-check-milestone-dod.py` 0 error（若涉及 `docs/milestones/**`）
- [ ] `pytest tests/unit -q` 全部通过
- [ ] `pytest tests/integration -q -m "not slow"` 全部通过
- [ ] 按 `docs/quality/test-strategy.md §8.1` 跑了受影响层的 e2e 子集
- [ ] 覆盖率变动 ≤ 1pp 或下方附降幅理由
- 覆盖率变动说明：

## Code Review Checklist 自评

<!-- 粘贴 docs/quality/code-review-checklist.md 相关分节并逐条 ✓/✗/N/A；下方复选代表全清单已过。 -->

- [ ] §3.1 PR 分类正确性（CR-G-*）
- [ ] §3.2 SPEC 对齐（CR-S-*）
- [ ] §3.3 INV 守护（CR-I-*）
- [ ] §3.4 HarnessFlags 语义（CR-F-*）
- [ ] §3.5 权限 / 工具契约（CR-T-*）
- [ ] §3.6 记忆（CR-M-*）
- [ ] §3.7 文档同 PR（CR-D-*）
- [ ] §3.8 教学 tier（CR-L-*）
- [ ] §3.9 测试充分性（CR-TS-*）
- [ ] §3.10 ADR 触发（CR-A-*）
- [ ] §4 反假检查（CR-AN-*）全部 ✗（即未中任一反假陷阱）

## 风险登记影响

<!-- 本 PR 是否触发 / 缓解 / 关闭任一 R-*；若否，写 N/A + 一句理由。 -->

- R-<layer>-__：<active / watch / mitigated / triggered / archived> → <新状态>
- 证据：

## 回滚预案

<!-- 可回滚的 PR 写回滚命令 / 窗口；不可回滚的变更显式说明冻结窗口与补偿动作。 -->

## Commit 与分支

- 分支：`<prefix>/<slug>`（参见 git-workflow §2.1）
- Commit footer 已含：
  - [ ] `Spec-Version: vX.Y[.Z]`（代码 PR）
  - [ ] `ADR: ADR-NNNN`（若适用）
  - [ ] `Refs: <issue / 任务 / F-*>`（可选）
  - [ ] `Co-Authored-By:` 行（若 Agent 代笔）

## Reviewer 签字

<!-- 自审完成后粘贴一行：
Reviewed: dy / YYYY-MM-DD / commit <sha>; all CR-* pass (CR-XX-N=N/A 理由如下)
-->
