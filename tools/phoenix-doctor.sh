#!/usr/bin/env bash
# phoenix-doctor.sh — PhoenixAgent M0 环境预检脚本
# 覆盖 SPEC §16 最小可运行骨架 / RnD §6.1 M0-T1 验收点
#
# 退出码（与 SPEC §14 CLI 契约一致）：
#   0  全部通过
#   1  用户错误 / 配置缺失
#   2  依赖不可达（网络 / 工具）
#   3  严重依赖版本不匹配
#
# 用法：bash tools/phoenix-doctor.sh [--strict] [--json]
# 环境：Git Bash on Windows、WSL2 bash、Linux 均可运行
set -u
# 不设 -e：我们希望即使某一项 check 失败也继续跑完全部诊断

STRICT=0
JSON=0
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --json) JSON=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
  esac
done

# ANSI（Git Bash / WSL2 支持；--json 模式关闭）
if [ "$JSON" -eq 0 ] && [ -t 1 ]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_RST=""
fi

PASS=0
WARN=0
FAIL=0
RESULTS=()   # "status|name|detail"

record() {
  local status="$1" name="$2" detail="$3"
  RESULTS+=("$status|$name|$detail")
  case "$status" in
    PASS) PASS=$((PASS+1)); [ "$JSON" -eq 0 ] && printf "  %s[PASS]%s %-32s %s\n" "$C_OK" "$C_RST" "$name" "$detail" ;;
    WARN) WARN=$((WARN+1)); [ "$JSON" -eq 0 ] && printf "  %s[WARN]%s %-32s %s\n" "$C_WARN" "$C_RST" "$name" "$detail" ;;
    FAIL) FAIL=$((FAIL+1)); [ "$JSON" -eq 0 ] && printf "  %s[FAIL]%s %-32s %s\n" "$C_ERR" "$C_RST" "$name" "$detail" ;;
  esac
}

section() {
  [ "$JSON" -eq 0 ] && printf "\n%s== %s ==%s\n" "$C_DIM" "$1" "$C_RST"
}

have() { command -v "$1" >/dev/null 2>&1; }

http_probe() {
  # $1=url $2=timeout
  local url="$1" t="${2:-8}"
  if have curl; then
    # --ssl-no-revoke：Windows schannel 下绕过 CRL/OCSP 吊销检查
    # （内网常访问不到吊销列表；本函数只做"端点可达"探针，不做证书安全审计）
    curl -sS --ssl-no-revoke -o /dev/null -m "$t" -w "%{http_code}" -L "$url" 2>/dev/null
  elif have wget; then
    # wget 不方便拿到 http_code；用 --spider + exit code
    if wget -q --spider -T "$t" "$url" 2>/dev/null; then echo 200; else echo 000; fi
  else
    echo "000"
  fi
}

ver_ge() {
  # $1 current $2 required  — 语义版本号 >= 比较
  printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# ----------------------------------------------------------------------
section "1. 基础运行时"

# Python >= 3.11
# 扫描所有可用的 Python 解释器，挑选版本最高且 >= 3.11 的那个。
# Windows 兼容考虑：`py -3` launcher、`python3` 可能是 Microsoft Store shim（命令存在但不可用）、
# 以及残留的 Python 2.x 与 Python 3.x 并存。
PY_CANDIDATES=(python3.13 python3.12 python3.11 python3 python)
if have py; then
  PY_CANDIDATES+=("py -3.13" "py -3.12" "py -3.11" "py -3")
fi

PYCMD=""
PYV="0.0.0"
PY_BEST_ANY=""
PY_BEST_ANY_V="0.0.0"
for cand in "${PY_CANDIDATES[@]}"; do
  cmd_head="${cand%% *}"
  have "$cmd_head" || continue
  v=$($cand -c "import sys; print('%d.%d.%d'%sys.version_info[:3])" 2>/dev/null)
  [ -z "$v" ] && continue
  if ver_ge "$v" "3.11.0" && ( [ -z "$PYCMD" ] || ver_ge "$v" "$PYV" ); then
    PYCMD="$cand"; PYV="$v"
  fi
  if [ -z "$PY_BEST_ANY" ] || ver_ge "$v" "$PY_BEST_ANY_V"; then
    PY_BEST_ANY="$cand"; PY_BEST_ANY_V="$v"
  fi
done
if [ -n "$PYCMD" ]; then
  record PASS "$PYCMD" "$PYV"
elif [ -n "$PY_BEST_ANY" ]; then
  record FAIL "$PY_BEST_ANY" "$PY_BEST_ANY_V (需要 >= 3.11.0；PATH 中只有低版本)"
else
  record FAIL "python" "未找到可用的 python 解释器（Windows 提示：装 python 3.11+ 或 py launcher）"
fi
export PYCMD

# pip
if have pip || have pip3; then
  record PASS "pip" "$(pip --version 2>/dev/null || pip3 --version 2>/dev/null | head -n1)"
else
  record WARN "pip" "未找到；建议 python -m ensurepip"
fi

# Git（s12 worktree 必需）
if have git; then
  record PASS "git" "$(git --version | awk '{print $3}')"
else
  record FAIL "git" "未安装；s12 Worktree 隔离无法使用"
fi

# Docker（SWE-bench 评测必需）
if have docker; then
  if docker info >/dev/null 2>&1; then
    DKV=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    record PASS "docker" "server $DKV (daemon running)"
  else
    record WARN "docker" "CLI 存在但 daemon 不可达；启动 Docker Desktop / WSL2 docker"
  fi
else
  record FAIL "docker" "未安装；Evaluation Layer 依赖"
fi

# Node.js（可选，MCP 工具常用；LSP / npm CLI 也可能用到）
if have node; then
  record PASS "node" "$(node -v)"
else
  record WARN "node" "未安装（可选，MCP server 经常为 node 实现）"
fi

# ----------------------------------------------------------------------
section "2. Python SDK / 关键库"

check_py_mod() {
  local mod="$1" label="${2:-$1}" required="${3:-optional}"
  # 使用 §1 检测到的 PYCMD；若缺失则跳过并标 WARN
  if [ -z "${PYCMD:-}" ]; then
    record WARN "$label" "跳过（无可用 python 解释器）"
    return
  fi
  # PYCMD 可能是 "py -3" 这类多 token（Windows py launcher）；
  # 必须切数组传参，否则 "$PYCMD" 加引号会被当成单个命令名导致 exec 失败。
  local _cmd
  read -r -a _cmd <<<"$PYCMD"
  if "${_cmd[@]}" -c "import ${mod}" 2>/dev/null; then
    local v
    v=$("${_cmd[@]}" -c "import ${mod} as m; print(getattr(m,'__version__','?'))" 2>/dev/null || echo "?")
    record PASS "$label" "v$v"
  else
    if [ "$required" = "required" ]; then
      record FAIL "$label" "未安装（${PYCMD} -m pip install ${mod}）"
    else
      record WARN "$label" "未安装（${PYCMD} -m pip install ${mod}）"
    fi
  fi
}

check_py_mod "anthropic"           "anthropic SDK"       required
check_py_mod "openai"              "openai SDK"          required
check_py_mod "litellm"             "litellm"             optional
check_py_mod "claude_agent_sdk"    "claude-agent-sdk"    optional   # M0 起始 Runtime
check_py_mod "mcp"                 "mcp (MCP SDK)"       optional

# ----------------------------------------------------------------------
section "3. API 密钥与 Model Profiles"

check_env() {
  local name="$1" level="${2:-warn}"
  if [ -n "${!name:-}" ]; then
    # 只显示长度与前 4 位，避免泄露
    local v="${!name}"
    local tail="${v:0:4}…(${#v} chars)"
    record PASS "$name" "$tail"
  else
    if [ "$level" = "fail" ]; then
      record FAIL "$name" "未设置"
    else
      record WARN "$name" "未设置（对应角色模型不可用）"
    fi
  fi
}

# 映射到 SPEC §4.1 profiles.toml 中的 api_key_env
check_env "OPENAI_API_KEY"         warn
check_env "ANTHROPIC_API_KEY"      warn
check_env "MOONSHOT_API_KEY"       warn

# 自定义端点覆盖（用户走代理 / Kimi-as-Anthropic-compatible / 本地 Ollama 等场景）
# Step 5 起 base_url 改由 ~/.config/phoenix/models.toml per-profile 配置；env 是过渡方案
if [ -n "${ANTHROPIC_BASE_URL:-}" ]; then
  record PASS "ANTHROPIC_BASE_URL" "$ANTHROPIC_BASE_URL"
fi
if [ -n "${OPENAI_BASE_URL:-}" ]; then
  record PASS "OPENAI_BASE_URL" "$OPENAI_BASE_URL"
fi
if [ -n "${MOONSHOT_BASE_URL:-}" ]; then
  record PASS "MOONSHOT_BASE_URL" "$MOONSHOT_BASE_URL"
fi

# ----------------------------------------------------------------------
section "4. 网络可达性（Provider 端点）"

probe_endpoint() {
  local name="$1" url="$2"
  local code
  code=$(http_probe "$url" 8)
  case "$code" in
    000) record FAIL "$name" "不可达（URL=$url）" ;;
    2??|3??|401|403|404|405) record PASS "$name" "HTTP $code" ;;
    *) record WARN "$name" "HTTP $code（可能限流 / 临时故障）" ;;
  esac
}

# 三个 LLM 端点遵循 *_BASE_URL env override（与 Anthropic / OpenAI SDK 默认行为一致）
ANT_BASE="${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
OAI_BASE="${OPENAI_BASE_URL:-https://api.openai.com}"
KIMI_BASE="${MOONSHOT_BASE_URL:-https://api.moonshot.ai}"
probe_endpoint "anthropic"              "${ANT_BASE%/}/v1/models"
probe_endpoint "openai (codex)"         "${OAI_BASE%/}/v1/models"
probe_endpoint "moonshot (kimi)"        "${KIMI_BASE%/}/anthropic"
probe_endpoint "github.com"             "https://github.com"
probe_endpoint "docker registry"        "https://registry-1.docker.io/v2/"

# ----------------------------------------------------------------------
section "5. 记忆系统（AK-llm-wiki）"

if have wiki; then
  record PASS "wiki CLI" "$(wiki --version 2>/dev/null || echo 'present')"
elif have wiki-ingest; then
  record PASS "wiki-ingest" "present（分命令形态）"
else
  record WARN "AK-llm-wiki CLI" "未在 PATH；参考 https://github.com/surebeli/AK-llm-wiki"
fi

# ----------------------------------------------------------------------
section "6. 评测框架（SWE-bench）"

# SWE-bench 官方包（Python）
_swe_ok=0
if [ -n "${PYCMD:-}" ]; then
  read -r -a _swecmd <<<"$PYCMD"
  "${_swecmd[@]}" -c "import swebench" 2>/dev/null && _swe_ok=1
fi
if [ "$_swe_ok" -eq 1 ]; then
  record PASS "swebench (python)" "importable"
else
  record WARN "swebench (python)" "未安装（${PYCMD:-python} -m pip install swebench；或使用 docker harness）"
fi

# 预构建 docker 镜像（epoch.ai）
if have docker && docker info >/dev/null 2>&1; then
  if docker image inspect swebench/sweb.eval.x86_64:latest >/dev/null 2>&1; then
    record PASS "swebench docker image" "已拉取"
  else
    record WARN "swebench docker image" "未拉取（首次评测前 docker pull swebench/sweb.eval.x86_64:latest）"
  fi
fi

# 磁盘空间（SWE-bench Verified 需要 ~120GB）
if have df; then
  # 取当前目录所在挂载点可用空间（GB）
  AVAIL_GB=$(df -Pk . | awk 'NR==2 {printf "%d", $4/1024/1024}')
  if [ "$AVAIL_GB" -ge 120 ]; then
    record PASS "disk free" "${AVAIL_GB}GB (>=120GB)"
  elif [ "$AVAIL_GB" -ge 50 ]; then
    record WARN "disk free" "${AVAIL_GB}GB (SWE-bench Verified 推荐 >=120GB)"
  else
    record FAIL "disk free" "${AVAIL_GB}GB 严重不足"
  fi
fi

# ----------------------------------------------------------------------
section "7. Phoenix 配置与目录"

PHX_CFG="${HOME}/.config/phoenix"
if [ -d "$PHX_CFG" ]; then
  record PASS "config dir" "$PHX_CFG"
else
  record WARN "config dir" "$PHX_CFG 不存在；首次启动时自动创建"
fi

for f in "models.toml" "permissions.toml" "mcp.json" "keys.env"; do
  if [ -f "$PHX_CFG/$f" ]; then
    record PASS "config file" "$f"
  else
    record WARN "config file" "$f 未创建（见 SPEC §4.1 / §11）"
  fi
done

# 仓库结构健康度（docs 四件套必须存在）
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
for f in "docs/PRD.md" "docs/TRD.md" "docs/RnD-Analysis.md" "docs/SPEC.md"; do
  if [ -f "$REPO_ROOT/$f" ]; then
    record PASS "docs" "$f"
  else
    record FAIL "docs" "$f 缺失（单一真相源被破坏）"
  fi
done

# ----------------------------------------------------------------------
# 输出汇总
if [ "$JSON" -eq 1 ]; then
  # 极简 JSON，避免依赖 jq
  printf '{"pass":%d,"warn":%d,"fail":%d,"results":[' "$PASS" "$WARN" "$FAIL"
  first=1
  for item in "${RESULTS[@]}"; do
    IFS='|' read -r st nm dt <<<"$item"
    [ $first -eq 0 ] && printf ','
    first=0
    # 粗略转义：把 " 换成 \"
    nm_e=${nm//\"/\\\"}
    dt_e=${dt//\"/\\\"}
    printf '{"status":"%s","name":"%s","detail":"%s"}' "$st" "$nm_e" "$dt_e"
  done
  printf ']}\n'
else
  printf "\n%s------------------ summary ------------------%s\n" "$C_DIM" "$C_RST"
  printf "  %sPASS%s=%d  %sWARN%s=%d  %sFAIL%s=%d\n" \
    "$C_OK" "$C_RST" "$PASS" "$C_WARN" "$C_RST" "$WARN" "$C_ERR" "$C_RST" "$FAIL"
fi

# 退出码
if [ "$FAIL" -gt 0 ]; then
  exit 2
fi
if [ "$STRICT" -eq 1 ] && [ "$WARN" -gt 0 ]; then
  exit 1
fi
exit 0
