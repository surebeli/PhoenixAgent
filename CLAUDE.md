# CLAUDE.md — Claude Code 专用入口

> Claude Code 自动加载本文件到对话上下文。其他 LLM 工具（Codex / Cursor / 自研 PhoenixAgent）请读 [`AGENTS.md`](AGENTS.md)。

---

## 1. 必读跳转

**全部硬约束 / 必跑 CI / PR 流程 / 阅读路径，见** [`AGENTS.md`](AGENTS.md)。

**完整设计原理 / Tier 体系 / Rule-Quality-ADR 角色矩阵，见** [`docs/README.md`](docs/README.md)。

本文件不复制上述内容；只承载 Claude Code 工具特定的补充。

---

## 2. Claude Code 特定补充

### 2.1 当前未配置项

- 自定义 hooks：无。
- 自定义 slash commands：无（仅使用内置 `/help` / `/clear` / `/compact` 等）。
- MCP servers：无。
- IDE 集成：暂无（计划 M1 起评估 VS Code 插件）。

未来引入任一项时，须在本文件 §2 追加说明，并同步到 `AGENTS.md` §7"平台与工具约定"。

### 2.2 推荐 Claude Code 行为

- **冷启动每次先扫**：`docs/README.md` + `AGENTS.md` + 当前任务相关 1-2 个具体文档。不要一次吞整个 `docs/`。
- **CI 跑完必粘输出**：`py -3 tools/ci-check-*.py` 的完整输出粘到对话或 PR 评论；不要只说"通过了"。
- **改 SPEC / Rule / Quality 任一份必先停下确认**：这些文件改动连带影响多处 ID 闭环，先口头与作者对齐方案再动笔。
- **教学 artifact 起草后必须由作者修订**：Agent 起草是允许的，但合入前作者签字（`learning-artifact-rules.md`）。

### 2.3 已知陷阱

- **路径**：本仓库在 Windows 上，shell 用 bash；Python 调用是 `py -3` 不是 `python`。绝对路径形如 `F:\workspace\ai\PhoenixAgent\...` 或 `F:/workspace/ai/PhoenixAgent/...`。
- **Unicode**：CI 脚本统一 `sys.stdout.reconfigure(encoding="utf-8")`；新写脚本沿用此模式以免 Windows GBK 控制台崩溃。
- **commit / push**：仅在用户显式要求时才执行 `git commit` / `git push`；从不主动提交。

---

## 3. 维护

- 本文件保持极简（< 80 行）。任何"硬约束"或"通用 agent 指引"变更，改 `AGENTS.md`，不改本文件。
- 仅当出现 Claude Code 工具特定的新设置（hooks / MCP / slash commands）时才扩张本文件 §2.1。

---

最后更新：2026-04-19。
