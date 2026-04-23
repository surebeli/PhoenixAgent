# Milestone M0 验收 — 2026-04-23 — 作者: dy

- 版本：v0.1（2026-04-23）
- Milestone 基线：`SPEC v1.2`
- 范围：M0 Step 1 ~ Step 12 收尾复盘、DoD-1 ~ DoD-7 闭合、接口冻结结论与后续 backlog 归宿。

---

## 1. DoD-1 ~ DoD-7 闭合

- [x] DoD-1 `bash tools/phoenix-doctor.sh` 输出 `FAIL=0`，核心条目全部 PASS。 → 证据: `artifacts/doctor-m0-final.json`; `docs/milestones/M0-doctor-baseline.md`
- [x] DoD-2 `phoenix run --task "hello" --runtime=claude` 返回 `status="success"` 的 `TaskResult`。 → 证据: `logs/01KPWXP5WH7PPFZMB2CWB8N0FE.jsonl`; `src/phoenix/runtime/claude.py`
- [x] DoD-3 AK-llm-wiki `phoenix-docs` namespace 已收录 PRD / TRD / RnD / SPEC，且 query 闭环已打通。 → 证据: `.ingested.json`; `artifacts/M0/step2-wiki-query.json`; `docs/teaching/M0/foundations/F-mem-1-wiki-why.md`
- [x] DoD-4 SWE-bench Verified 官方 Docker harness 本地跑通 ≥ 1 个 instance 的完整流程。 → 证据: `artifacts/M0/baseline-swebench.json`; `artifacts/M0/swebench-first-run/m0-step8-flask-5014-r3.predictions.json`
- [x] DoD-5 学习 artifact `F-01 ~ F-06` 全部入库。 → 证据: `.ingested.json`; `docs/teaching/M0/foundations/F-06-eval-methodology.md`; `docs/teaching/M0/foundations/F-04-context-engineering.md`
- [x] DoD-6 工程 artifact `M-runtime-abstraction` / `M-evaluation-setup` / `M-walkthrough` 已入库，且 `docs/teaching/M0/.ingested.json` 存在。 → 证据: `docs/teaching/M0/.ingested.json`; `docs/teaching/M0/M-runtime-abstraction.md`; `docs/teaching/M0/M-evaluation-setup.md`; `docs/teaching/M0/M-walkthrough.ipynb`
- [x] DoD-7 `AgentRuntime` / `MemoryBackend` / `ToolSpec + PluginRegistry` 在 M0 收尾时已完成签名冻结。 → 证据: `docs/milestones/M0-interface-backlog.md`; `docs/SPEC.md`; `src/phoenix/runtime/claude.py`

## 2. 完成项

- 环境与基础设施：完成 doctor 基线、wiki 冷启动、Claude SDK 最小可运行链路，并在企业限制下将容器底座从 Docker Desktop 切换到 Rancher Desktop。
- 三大接口最小闭环：`AgentRuntime`、`PluginRegistry`、`MemoryBackend` 都已在 M0 形成可运行最小链路，支撑 `phoenix run`、`phoenix eval`、memory digest 与 milestone teaching ingest。
- 评测与可观测：完成 SWE-bench Verified 单实例基线、`BenchmarkReport` JSON + SQLite 双产物、usage observation 日志、以及 M0 教学汇总 artifact。
- 收官校验：Step 12 复核补上了 `phoenix_tasks` 持久化缺口，并将剩余 deferred 项集中整理到 `docs/milestones/M0-interface-backlog.md`。

## 3. 未完成项与最终归宿

- `MemoryBackend.tier()` 仍未在 `AKLLMWikiBackend` 实装；归宿：M1a `DoD-M1-5a`。
- `MemoryBackend.import_bulk() / graph() / lint()` 仍未在 `AKLLMWikiBackend` 实装；归宿：M1b `DoD-M1-5b`。
- `PluginRegistry.reload()` 仍未实现；归宿：M1a soft-freeze 窗口。
- `wiki-lint --auto-fix` 在当前安装的 `wiki` CLI 上没有独立命令面；M0 以 `docs/milestones/M0-memory-graph.md` 的“无孤岛”报告保留证据，`lint` 能力跟随上条 Memory backlog 一并进入 M1。
- Step 1 在 `docs/milestones/M0-doctor-baseline.md` 登记的 docker 暂缓项已最终关闭：Docker Desktop 已卸载，M0 基线改由 Rancher Desktop + moby backend 承接，不再保留为风险敞口。

## 4. 意外发现

- Windows 上直接从 PowerShell 调 `bash` 会落到 WSL bash，而不是 Git Bash；这会让 `phoenix-doctor.sh` 的 Python / git / daemon 诊断出现假阴性。M0 的官方 doctor 基线必须显式走 Git Bash。
- 企业内环境不允许安装 Docker Desktop，但 Rancher Desktop 的 `moby` backend 可以满足 M0 的 SWE-bench Harness 需求；最小回归应优先选 Step 9 的 `phoenix eval --subset=1`，不必每次重跑 Step 8。
- Step 12 暴露的最真实接口问题不是“字段不够”，而是“规范已写明的不变量还没落到实现”；`phoenix_tasks` 持久化就是这类问题，适合在 freeze 前直接补实现，而不是把规范再往后推。
- 当前 `wiki` 工具面缺少 `wiki-lint` / `wiki-graph` 原生命令，说明 M0 对 Memory 七动词的承诺应理解为“职责边界已冻结，M1a / M1b 再逐项补齐实现”。

## 5. Step 学习自评

- Step 1：能。不看笔记也能说明 ReAct 最小循环，以及为什么 `Reason -> Act -> Observe` 比纯 CoT 更适合带工具的 Agent。
- Step 2：能。能解释为什么本项目用 wiki 记忆而不是纯向量 RAG，也能把 `ingest / query / digest` 的职责说清。
- Step 3：能。能描述 Claude SDK 的主循环、消息类型和最小 `run_task` 成功路径。
- Step 4：能。能解释为什么先冻结 `AgentRuntime` 协议，再让不同 provider 去适配，而不是把 SDK 细节泄到 CLI。
- Step 5：能。能说明 `ModelProfile`、provider 路由、企业代理和合规边界之间的关系。
- Step 6：能。能说明 `ToolSpec` 的最小必要字段，以及 `PluginRegistry` 为什么先做注册/执行闭环再谈热重载。
- Step 7：能。能解释 memory digest 为什么按 namespace 隔离，以及为什么 M0 只做三动词最小闭环。
- Step 8：能。能完整复述 SWE-bench 官方 Docker harness 的基本流程和宿主机依赖。
- Step 9：能。能说明 `BenchmarkReport` 为什么同时落 JSON、Markdown 和 SQLite，以及为什么最小回归选 `subset=1`。
- Step 10：能。能说明 usage observation 的记录粒度，以及 context/token observability 对后续成本归因的价值。
- Step 11：能。能把分散的 F-* 节点串成 M-* artifact，并解释 memory graph “无孤岛”对后续召回质量的意义。
- Step 12：能。能区分“接口签名冻结”和“实现 backlog 递延”，也能说明什么问题该在 freeze 前直接修、什么问题应进入 M1 backlog。

## 6. 下一 Milestone 入口

- M1 启动前先读 `docs/milestones/M0-interface-backlog.md`，把 B 类事项映射到 M1a / M1b 的真实 Step，而不是在 soft-freeze 窗口里重新开题。
- M0 结束时三个硬接口的冻结结论是：签名不再做破坏性变更，但实现补齐仍允许在 `docs/rules/spec-change-policy.md` 定义的 soft-freeze 窗口内做 Patch 级收敛。
- M0 本身没有遗留会阻断 `DoD-1 ~ DoD-7` 的未清项；剩余事项已经归档为下 Milestone backlog，而不是留在 M0 内部悬空。

## 7. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | 初版创建：完成 M0 收尾复盘、DoD 闭合与 Step 12 接口冻结结论记录。 |