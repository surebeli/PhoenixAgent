# M0 SWE-bench First Run — Docker Harness 首跑记录

- 版本：v0.1（2026-04-23，Step 8 首次实跑落档）
- 作者：dy
- 上位文档：`docs/milestones/M0-plan.md` §Step 8、`docs/PRD.md` FR-06、`docs/SPEC.md` §7.1 / §7.2 / §7.3 / §7.4
- 目的：记录 M0 Step 8 的第一次本地 SWE-bench Verified Docker harness 实跑，冻结最小方法学证据与运行产物路径。

---

## 1. 本次运行的结论

- 本机已具备本地 Docker harness 跑通 SWE-bench Verified 单实例的能力。
- 最终冻结 run：`m0-step8-flask-5014-r3`
- 数据集：`SWE-bench/SWE-bench_Verified`
- 目标 instance：`pallets__flask-5014`
- patch 来源：`gold`
- 结果：`resolved=true`
- 总耗时：`144.66s`
- 容器内测试耗时：`6.00s`

本次 run 的意义是**评测方法学 smoke**，不是 M1 KPI 所需的多实例 Phoenix runtime 基线。它证明的是“Verified + 本地 Docker harness + 归档报告”这条路径在当前 Windows 11 + Docker Desktop 环境下可复现。

---

## 2. 官方基线与运行环境

- 宿主环境：Windows 11 + Docker Desktop（WSL2 backend）
- Docker CLI：`29.4.0`
- Docker Host：`24 CPU` / `31.22 GiB RAM`
- Docker OS / Kernel：`Docker Desktop` / `6.6.87.2-microsoft-standard-WSL2`
- Git SHA：`ed093934b8c4a5625825382f5b3f673c18ccbd62`

远端目标镜像（由 harness 在运行期拉取后再清理）：

- 镜像名：`swebench/sweb.eval.x86_64.pallets_1776_flask-5014:latest`
- Digest：`sha256:ffa7af7191f8aca58cc00db4582c7b0cb1aab91d395dc470baeac8cd7a5758ee`
- 压缩层总大小：`1,103,704,773 bytes`（约 `1052.57 MiB` / `1.03 GiB`）

---

## 3. 运行命令与冻结 run

实际冻结命令：

```powershell
f:/workspace/ai/PhoenixAgent/.venv/Scripts/python.exe scripts/swebench-first-run.py --instance-id pallets__flask-5014 --run-id m0-step8-flask-5014-r3
```

脚本行为：

- 显式导入仓库 `sitecustomize.py`，为 Windows 注入 `resource` shim，绕开 `swebench` 对 Unix-only `resource` 模块的 import 假设。
- 自动把 `C:\Program Files\Docker\Docker\resources\bin` 加入当前进程 `PATH`，保证 `docker-credential-desktop.exe` 对 Python Docker SDK 可见。
- 当 `--predictions-path=gold` 时，先裁出当前 instance 对应的最小 predictions 文件，避免上游 report 把 500 个 Verified 任务都记为“submitted”。
- 在 Windows 上把 harness 生成的 `.sh` / `.diff` 文本文件强制写为 LF，避免容器内 `/bin/bash` 因 CRLF 误读 eval script。

---

## 4. 运行结果

`logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/report.json` 的关键结果：

- `patch_successfully_applied=true`
- `resolved=true`
- `FAIL_TO_PASS.success = ["tests/test_blueprints.py::test_empty_name_not_allowed"]`
- `PASS_TO_PASS.failure = []`

这说明：

- gold patch 在容器内成功应用到 `src/flask/blueprints.py`
- 目标 fail-to-pass 用例被修复
- 相关 pass-to-pass 用例未回归

---

## 5. 产物结构

冻结产物：

- `artifacts/M0/baseline-swebench.json`
- `artifacts/M0/swebench-first-run/gold.m0-step8-flask-5014-r3.json`
- `artifacts/M0/swebench-first-run/m0-step8-flask-5014-r3.predictions.json`

运行日志目录：

- `logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/patch.diff`
- `logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/eval.sh`
- `logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/test_output.txt`
- `logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/report.json`
- `logs/run_evaluation/m0-step8-flask-5014-r3/gold/pallets__flask-5014/run_instance.log`

---

## 6. 已知偏差与修复记录

### 6.1 r1：Docker credential helper 不在 Python 进程 PATH

- 现象：`docker-credential-desktop` 已安装，但 Python Docker SDK 在当前 shell 中不可见，导致 harness 早期失败。
- 修复：Step 8 wrapper 自动把 Docker Desktop 的 resource bin 前置到当前进程 `PATH`。

### 6.2 r2：Windows CRLF 让 eval script 被 bash 误读

- 现象：`test_output.txt` 中出现 `set: pipefail: invalid option name`、`/opt/miniconda3/bin/activate\r`、`pytest: command not found`。
- 根因：Windows 默认文本写入把 harness 生成的 `eval.sh` 变成了 CRLF，Linux 容器里的 `/bin/bash` 逐行执行时把 `\r` 当成命令名的一部分。
- 修复：wrapper 在 Windows 上把 harness 生成的 `.sh` / `.diff` 文件统一写为 LF。

### 6.3 r3：最终冻结 run

- 结果：`resolved=true`
- 结论：当前仓内兼容补丁已足以让 Step 8 的最小 Verified smoke 在 Windows 11 + Docker Desktop 下稳定跑通。

---

## 7. 对后续 Step 的影响

- Step 8 本身的最小 DoD-4 证据已经成立：本地 Docker harness 完整跑过 `patch -> 容器内测试 -> 报告`。
- `F-06-eval-methodology.md` 已写成并 ingest，可作为后续 Step 9 / M1 的方法学注释层。
- 下一阶段若要把 `artifacts/M0/baseline-swebench.json` 用作 M1 KPI 分母，仍需再补一份**非 gold、且更接近 Phoenix runtime/model 真实执行**的多实例基线；本次冻结工件更偏 Step 8 方法学 smoke，而非最终性能口径。

---

## 8. 变更日志

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-23 | 首次落盘：记录 `pallets__flask-5014` 的 Step 8 Docker harness 首跑、Windows 兼容修复点、冻结产物路径与结果。 |