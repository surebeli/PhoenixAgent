# M0 Doctor Baseline — 环境预检结果与已知偏差登记

- 版本：v0.2（2026-04-20，Step 1 首次运行回填）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` §Step 1、`docs/quality/definition-of-done.md` DoD-M0-1
- 目的：登记 `bash tools/phoenix-doctor.sh --json` 的本地基线、所有 FAIL 条目的"已知偏差 + 缓解方案"。本文件是 M0 Step 1 退出条件的证据载体（DoD-1 替代路径）。

---

## 0. Official Shell Baseline

- 官方基线：`Windows 11 + Git Bash (MSYS/MINGW)`。
- `doctor` 的冻结证据、Step 1 的通过性判断、后续与本文件的结果对账，均以这套 shell 语义为准。
- 最小 profile：
  - `HOME` 指向 Windows 用户目录映射（示例：`/c/Users/<user>`），Phoenix 配置位于 `~/.config/phoenix/`。
  - Python 入口优先用 `py -3`，与仓库脚本和 `AGENTS.md` 约定一致。
  - API Key 与 `*_BASE_URL` 默认从 `~/.config/phoenix/keys.env` 提供；若当前 shell 未 `export`，`tools/phoenix-doctor.sh` 会自动加载该文件用于对账。
  - 非 Git Bash 的 bash 环境允许作为兼容运行环境，但不作为 Step 1 / M0 的冻结基线。

---

## 1. 运行命令与产物

```bash
bash tools/phoenix-doctor.sh --json > artifacts/doctor-m0-baseline.json
```

- 运行时间：`2026-04-20 00:32:?? +0800`
- 主机：`<corp-host>` / Windows 11 Enterprise / MSYS (Git Bash) / shell=`bash 5.2.37`
- 产物：`artifacts/doctor-m0-baseline.json`（JSON 详情归档；内网 URL / 用户名 / key 前缀已脱敏）
- 终态计数：`PASS=30` / `WARN=2` / `FAIL=1`
- 运行环境 env override（**公开仓已脱敏，真实值见本机 `~/.config/phoenix/keys.env`**）：
  - `ANTHROPIC_BASE_URL=<internal-proxy>`（企业内网 OpenAI/Anthropic 代理）
  - `OPENAI_BASE_URL=<internal-proxy>`（同上，统一代理）
  - `MOONSHOT_BASE_URL=<kimi-coding-endpoint>`（Kimi Coding Plan）
- 运行时附加 patch（见 `tools/phoenix-doctor.sh`）：
  - http_probe 带 `--ssl-no-revoke`（Windows schannel 在内网访问不到 CRL/OCSP 列表；本 probe 只做可达性探针，不做证书吊销审计）
  - 端点探测遵循 `*_BASE_URL` env override

> 本次 `FAIL=1`（docker），按路径 B 登记 §3 后推进。

---

## 2. 核心检查项清单（与 phoenix-doctor.sh 对齐）

| 类别 | 项 | 期望 | 状态 | 备注 |
|---|---|---|---|---|
| 运行时 | Python | ≥ 3.11 | ✅ PASS | 实测 `3.14.0` |
| 运行时 | git | 可执行 | ✅ PASS | 版本 `2.53.0.windows.3` |
| 运行时 | node | 可执行 | ✅ PASS | `v20.20.0` |
| 运行时 | docker daemon | 可连 | ❌ FAIL | 未安装 → §3 第 1 行登记 |
| Python 包 | anthropic | importable | ✅ PASS | v0.96.0 |
| Python 包 | openai | importable | ✅ PASS | v2.30.0 |
| Python 包 | litellm | importable | ✅ PASS | |
| Python 包 | claude_agent_sdk | importable | ✅ PASS | v0.1.63 |
| Python 包 | mcp (MCP SDK) | importable | ✅ PASS | |
| 文档骨架 | `docs/PRD.md` 存在 | yes | ✅ PASS | |
| 文档骨架 | `docs/TRD.md` 存在 | yes | ✅ PASS | |
| 文档骨架 | `docs/RnD-Analysis.md` 存在 | yes | ✅ PASS | |
| 文档骨架 | `docs/SPEC.md` 存在 | yes | ✅ PASS | |
| 凭证 | `OPENAI_API_KEY` 已设 | yes | ✅ PASS | `sk-***(67)` |
| 凭证 | `ANTHROPIC_API_KEY` 已设 | yes | ✅ PASS | `sk-***(67)` |
| 凭证 | `MOONSHOT_API_KEY` 已设 | yes | ✅ PASS | `sk-***(72)` |
| 网络 | Anthropic 端点可达 | HTTP 2xx/401 | ✅ PASS | 走 override → HTTP 401（可达） |
| 网络 | OpenAI 端点可达 | HTTP 2xx/401 | ✅ PASS | 走 override → HTTP 401 |
| 网络 | Moonshot 端点可达 | HTTP 2xx/4xx | ✅ PASS | 走 override → HTTP 404（路径待 Step 5 校准，端点可达） |
| 网络 | github.com | 可达 | ✅ PASS | HTTP 200 |
| 网络 | docker registry | 可达 | ✅ PASS | HTTP 401 |
| 端点覆盖 | `ANTHROPIC_BASE_URL` | 默认 / 自定义 | ✅ override → `<internal-proxy>` | 企业内网代理（真实值仅在本机 keys.env）|
| 端点覆盖 | `OPENAI_BASE_URL` | 默认 / 自定义 | ✅ override → `<internal-proxy>` | 同上 |
| 端点覆盖 | `MOONSHOT_BASE_URL` | 默认 / 自定义 | ✅ override → `<kimi-coding-endpoint>` | Step 5 起迁入 `models.toml` per-profile |
| 记忆系统 | AK-llm-wiki CLI | 可调 | ⚠️ WARN | Step 2 装（不阻塞） |
| 评测框架 | swebench | importable | ⚠️ WARN | Step 8 装（或 docker harness） |
| 评测框架 | disk free ≥ 120GB | yes | ✅ PASS | 3047GB |
| 配置 | `~/.config/phoenix/models.toml` | yes | ✅ PASS | 骨架 v0.1 |
| 配置 | `~/.config/phoenix/permissions.toml` | yes | ✅ PASS | 骨架（空规则） |
| 配置 | `~/.config/phoenix/mcp.json` | yes | ✅ PASS | 骨架（空注册表） |
| 凭证 | `~/.config/phoenix/keys.env` 存在 | yes | ✅ PASS | |
| 凭证 | `keys.env` 权限 0600 | yes | ✅ PASS | 已 `chmod 600`（Git Bash 等价 ACL） |

> CI / 评审时只看本表勾选 + §3 偏差表的闭环。任何"☐"都视为未填。

---

## 3. FAIL 偏差登记（每条 FAIL 一行）

> 模板：每行一条 FAIL，包含 **诊断 → 决策 → 缓解 → 重检时机**。无 FAIL 时整个表写 `N/A — 本次预检 FAIL=0`。

| # | FAIL 项 | 实测现象 | 根因诊断 | 决策 | 缓解方案 | 重检时机（哪个 Step） | Owner |
|---|---|---|---|---|---|---|---|
| 1 | docker (CLI & daemon) | `未安装；Evaluation Layer 依赖` | 本机未装 Docker Desktop（WSL2 backend 亦未启）；SWE-bench Harness 依赖 | 暂缓 | Step 8 入口前装 Docker Desktop（或用无 docker 的替代评测路径）；M0 Step 2–7 不依赖 docker。登记为"可接受 FAIL"。 | Step 8 入口前 | dy |

### 附：本次观察到的 WARN（非 FAIL，不阻塞 Step 1）

| # | WARN 项 | 处置 | 重检时机 |
|---|---|---|---|
| W1 | AK-llm-wiki CLI 未在 PATH | Step 2 工程任务之一：安装并联通 wiki-ingest / wiki-query | Step 2 进入前 |
| W2 | swebench (python) 未安装 | Step 8 装；或选择 docker harness 路径 | Step 8 入口前 |

### 附：本次发现的 doctor 自身 bug（已在本次 commit 内修复）

| # | Bug | 根因 | 修复 |
|---|---|---|---|
| D1 | §4 端点探测硬编码，不跟随 env override | 原 probe 写死 `api.anthropic.com` 等 | 改为 `${VAR:-default}` + `${VAR%/}` 去尾斜杠 |
| D2 | `check_py_mod` 和 swebench 检查执行 `"$PYCMD" -c ...` → `"py -3"` 被当单命令名 FAIL | bash 变量展开单词化错误 | `read -r -a _cmd <<<"$PYCMD"` 数组拆分后 `"${_cmd[@]}" -c ...` |
| D3 | 3 个 LLM 端点误报 FAIL（实际可达） | Windows schannel 访问不到 CRL/OCSP 吊销列表 → `CRYPT_E_NO_REVOCATION_CHECK` | `http_probe` curl 加 `--ssl-no-revoke`（探针只查可达性，不做证书吊销审计）|
| D4 | `ci-check-milestone-dod.py` Windows 控制台 GBK 乱码 | 默认 stdout 编码非 UTF-8 | 加 `sys.stdout.reconfigure(encoding="utf-8")` |

**决策合法值**：`暂缓 / 立即修 / 永久豁免`。
- 暂缓：必须给"重检 Step"；进入该 Step 时本表对应行需重新评估。
- 立即修：本 Step 内必须修；修复后把行标 `[已修复 YYYY-MM-DD]` 并把状态回写 §2。
- 永久豁免：必须开 ADR；本行 `决策` 列填 `永久豁免 (ADR-NNNN)`。

---

## 4. Step 1 退出判定

按 `M0-plan.md §Step 1 进入下一步条件`：

- [ ] ~~**路径 A**：`FAIL=0`（§2 全部 PASS） → DoD-1 直接成立。~~（本次 FAIL=1，不走 A）
- [x] **路径 B**：`FAIL=1`（docker），§3 第 1 行已登记"决策=暂缓 / 缓解=Step 8 入口前补 / Owner=dy" → DoD-1 以替代路径成立；进入 Step 8 前必须回头复核本文件。
- [x] F-01（`docs/teaching/M0/foundations/F-01-react-paradigm.md`）已物理落盘；`ci-check-teaching.py` 对 L-ING-1 的 ingest=false 放 WARN（tier=active 允许草稿期，L-ING-2 兜底）。Step 2 完成 wiki-ingest 后回写 `ingested: true` 并勾选下一行。
- [ ] F-01 已 ingest 到 AK-llm-wiki（`ingested: true` + `ingested_at` 时间戳）— **Step 2 执行**。

路径 B 勾起即可推进 Step 2；Step 8 前须重新复核。

---

## 5. 引用与下游

- 触发本文件更新的下游 Step：Step 5（Kimi 端点联通）、Step 7（AK-llm-wiki CLI）、Step 8（Docker / SWE-bench 镜像）。任一进入前先 grep 本文件 §3 是否有对应 FAIL 行。
- 与 `docs/milestones/M0-retrospective.md`（Step 12 产出）对照：所有"暂缓"行必须在 retrospective 中标注最终归宿（已修 / 升级为 R-* 风险 / 转入 M1 backlog）。
- 与 `artifacts/doctor-m0-baseline.json`（机器可读基线）一一对应；本文件偏差表是 JSON 的人类可读注释层，不替代 JSON。

---

## 6. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-19 | 模板创建；待 Step 1 真实运行后填 §1 / §2 / §3 / §4。 |
| v0.2 | 2026-04-20 | Step 1 首次运行回填：PASS=30 / WARN=2 / FAIL=1（docker）；§3 登记 docker 暂缓 + 2 WARN 附录 + 4 项 doctor 自身 bug 修复（端点 override / PYCMD 空格 / schannel CRL / stdout UTF-8）；§4 勾路径 B + F-01 落盘条。 |
