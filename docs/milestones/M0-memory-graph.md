# M0 Memory Graph — Step 11 图谱整理报告

- 版本：v0.1（2026-04-23，Step 11 首次整理）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` §Step 11、`docs/rules/learning-artifact-rules.md` §4、`docs/SPEC.md` §13
- 目的：验证 M0 的 F-*、M-*、M-eng-* 节点是否已经形成最小知识网，而不是一组相互独立的文档孤岛。

---

## 1. 方法说明

Step 11 原始计划要求使用 `wiki-graph --scope phoenix-docs --scope evaluation --scope foundations-M0` 生成图谱报告。但当前本机安装的 wiki CLI 仅支持 `init / import / ingest / query`，不支持 `graph` 子命令；在 Windows PowerShell 和 Git Bash 下都已经确认这一点。因此本报告采用可复现的 repo-local fallback：

- 扫描 `docs/teaching/M0/**` 下全部 `.md` / `.ipynb` 教学节点；
- 对 `foundation` / `engineering` 节点读取 `related_nodes`；
- 对 `milestone` 节点读取 `covers_foundations`；
- 以此构建无向边并检查是否存在 degree=0 的孤岛节点。

这个 fallback 不能替代未来真正的 wiki graph 可视化，但足以验证 Step 11 要求的“节点之间至少存在最小连通关系”。

---

## 2. 节点与边概览

- 节点总数：14
- 边总数：27
- 孤岛节点：0

关键边示例：

- `M-runtime-abstraction -> F-02 / F-03 / F-05a / F-05b`
- `M-evaluation-setup -> F-06`
- `M-walkthrough -> F-01 / F-02 / F-04`
- `M-eng-eval-runner-design -> F-05b / F-06`
- `F-mem-2 -> F-mem-1 / F-03`

从这个结构看，M0 目前至少形成了三条明显的主链：

- Runtime / Tool 协议链：`F-01 -> F-02 -> F-05a -> F-05b -> M-runtime-abstraction`
- Evaluation 链：`F-05b -> F-06 -> M-eng-eval-runner-design -> M-evaluation-setup`
- Walkthrough / Context 观察链：`F-01 / F-02 / F-04 -> M-walkthrough`

---

## 3. 邻接摘要

| 节点 | 邻接节点 |
|---|---|
| `F-01` | `F-02`, `F-05a`, `F-mem-1`, `M-walkthrough` |
| `F-02` | `F-01`, `F-03`, `F-04`, `F-05a`, `F-05b`, `F-model-1`, `M-runtime-abstraction`, `M-walkthrough` |
| `F-03` | `F-02`, `F-05b`, `F-mem-2`, `M-runtime-abstraction` |
| `F-04` | `F-02`, `F-05a`, `F-05b`, `M-walkthrough` |
| `F-05a` | `F-01`, `F-02`, `F-04`, `F-05b`, `M-runtime-abstraction` |
| `F-05b` | `F-02`, `F-03`, `F-04`, `F-05a`, `F-06`, `F-model-1`, `M-eng-eval-runner-design`, `M-runtime-abstraction` |
| `F-06` | `F-05b`, `F-model-1`, `M-eng-eval-runner-design`, `M-evaluation-setup` |
| `F-mem-1` | `F-01`, `F-mem-2` |
| `F-mem-2` | `F-03`, `F-mem-1` |
| `F-model-1` | `F-02`, `F-05b`, `F-06` |
| `M-eng-eval-runner-design` | `F-05b`, `F-06` |
| `M-evaluation-setup` | `F-06` |
| `M-runtime-abstraction` | `F-02`, `F-03`, `F-05a`, `F-05b` |
| `M-walkthrough` | `F-01`, `F-02`, `F-04` |

---

## 4. 结论

- 当前 M0 教学节点不存在孤岛，满足 Step 11 对最小知识网的要求。
- 三份 milestone artifact 已经把运行时、评测和 walkthrough 三条主线各自挂到现有 foundations 上，不再是孤立的单篇学习笔记。
- 真正缺的不是连通性，而是图谱展示能力：等所用 wiki CLI 提供 `graph` 子命令后，应将本报告升级为真实的 graph export，而不是继续依赖 frontmatter fallback。

---

## 5. 后续补强

待 `wiki graph` 能力可用后，建议补三项：

- 输出可视化节点图或最短路径列表；
- 把 `evaluation` namespace 中的 `BenchmarkReport` 节点纳入同一张图；
- 对“高中心度节点”做排序，识别哪些 foundations 在 M1 应继续保持为主轴节点。

---

## 6. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | 首次落盘：因当前 wiki CLI 缺 `graph` 子命令，改用 frontmatter 关系图 fallback 生成 M0 知识网摘要，并确认无孤岛。 |