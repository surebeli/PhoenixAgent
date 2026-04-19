# PhoenixAgent 模块 Spec 设计（SPEC）

- 版本：v1.1
- 日期：2026-04-19
- 作者：dy
- 关联：PRD.md（WHY / WHAT）、TRD.md（HOW 架构）、RnD-Analysis.md（风险 / 排期）
- 目的：把 TRD 描述的八层架构落到**可直接编码**的接口契约、数据结构、关键流程与最小可运行骨架。本文件是大模型执行代码实现时的权威 Spec。

---

## 0. 约定

- 所有代码示例以 Python 3.11+ 语法书写；类型签名使用 `typing` + `dataclasses`。接口统一使用 `typing.Protocol`，允许 duck typing。
- 所有异步接口使用 `async def`；同步接口明确不带 `async`。
- 所有 ID 使用 ULID（字母序可排序，统一 26 字符），在日志、wiki、experiment-report 中保持一致。
- 错误处理：顶层 `PhoenixError`，子类 `RuntimeError`、`ModelError`、`ValidationError`、`PermissionDenied`、`MemoryError`、`EvaluationError`、`PluginError`。
- 所有公共接口必须保留 `ctx: PhoenixContext` 或等价的注入参数；禁止全局单例。
- 所有文件路径在跨平台场景使用 `pathlib.Path`。
- 配置加载顺序：CLI 参数 > 环境变量 > `~/.config/phoenix/config.toml` > 内置默认值。

---

## 1. 顶层数据模型

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, Protocol, runtime_checkable

ULID = str  # 26 chars, lexicographically sortable
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

@dataclass(frozen=True)
class Task:
    id: ULID
    prompt: str                         # 人类 / 上游 Agent 提交的原始自然语言任务
    workspace: Path                     # 任务作用域目录（通常是 git 仓库根）
    constraints: dict[str, JSONValue] = field(default_factory=dict)  # 预算、超时、允许模型等
    metadata: dict[str, JSONValue] = field(default_factory=dict)

@dataclass
class Plan:
    id: ULID
    task_id: ULID
    steps: list["PlanStep"]
    estimated_tokens: int
    model_profile: str

@dataclass
class PlanStep:
    id: ULID
    description: str
    tool: str | None                    # None 表示纯推理步骤
    tool_args: dict[str, JSONValue] = field(default_factory=dict)
    depends_on: list[ULID] = field(default_factory=list)
    subagent: bool = False

@dataclass
class AgentEvent:
    kind: Literal[
        "plan_proposed", "tool_invoked", "tool_completed",
        "hook_approved", "hook_denied", "message",
        "subagent_spawned", "memory_digested", "error"
    ]
    payload: dict[str, JSONValue]
    ts: datetime

@dataclass
class TaskResult:
    task_id: ULID
    status: Literal["success", "failed", "cancelled", "partial"]
    plan: Plan | None
    artifacts: list[Path] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    error: str | None = None

@dataclass
class Episode:
    """Memory Layer 消费单位：一次任务 run 结束产出的可 ingest 对象。"""
    task: Task
    result: TaskResult
    namespace: str                      # 插件 / 场景 namespace，避免 memory 污染
    extracted_facts: list[dict[str, JSONValue]] = field(default_factory=list)
```

---

## 2. Runtime Layer

### 2.1 接口

```python
@dataclass(frozen=True)
class RuntimeConfig:
    name: Literal["claude", "self", "openai"]
    model_profile: str
    harness_flags: "HarnessFlags"
    permissions: "PermissionRules"
    timeout_s: int = 1800
    extras: dict[str, JSONValue] = field(default_factory=dict)

@dataclass
class SessionHandle:
    id: ULID
    runtime_name: str
    started_at: datetime
    ctx: "PhoenixContext"

@runtime_checkable
class AgentRuntime(Protocol):
    name: str

    def start_session(self, cfg: RuntimeConfig, ctx: "PhoenixContext") -> SessionHandle: ...
    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult: ...
    def register_tool(self, handle: SessionHandle, tool: "ToolSpec") -> None: ...
    def install_hook(self, handle: SessionHandle, event: "HookEvent", fn: "HookFn") -> None: ...
    def stream_events(self, handle: SessionHandle) -> Iterator[AgentEvent]: ...
    def stop_session(self, handle: SessionHandle) -> None: ...
```

### 2.2 具体实现清单

| 名称 | 模块路径 | 提交 M | 关键依赖 | 备注 |
|---|---|---|---|---|
| `ClaudeAgentSDKRuntime` | `phoenix.runtime.claude` | M0 | `claude-agent-sdk` | M0 即刻可用；复用官方 ReAct Loop + Tools + Permission |
| `PhoenixCoreRuntime` | `phoenix.runtime.core` | M1 | `anthropic`（用于 Anthropic 兼容调用） | 自研；内部显式实现 12 层 Harness 的开关位 |
| `OpenAIAgentsRuntime` | `phoenix.runtime.openai` | M1/M2 | `openai-agents-sdk`, `codex-sdk` | 第三方对齐；sandbox + filesystem tools 走 SDK 默认 |

### 2.3 Runtime Registry（选型入口）

```python
RUNTIME_REGISTRY: dict[str, type[AgentRuntime]] = {
    "claude": ClaudeAgentSDKRuntime,
    "self": PhoenixCoreRuntime,
    "openai": OpenAIAgentsRuntime,
}

def make_runtime(name: str) -> AgentRuntime:
    if name not in RUNTIME_REGISTRY:
        raise RuntimeError(f"unknown runtime: {name}")
    return RUNTIME_REGISTRY[name]()
```

### 2.4 PhoenixCoreRuntime 最小 ReAct 骨架（M1 必须落地）

```python
class PhoenixCoreRuntime:
    name = "self"

    def run_task(self, handle: SessionHandle, task: Task) -> TaskResult:
        ctx = handle.ctx
        messages: list[dict] = self._seed_messages(task, ctx)
        plan: Plan | None = None
        events: list[AgentEvent] = []

        if ctx.harness_flags.s03_planning:
            plan = self._plan(task, messages, ctx)
            events.append(AgentEvent("plan_proposed", {"plan_id": plan.id}, utcnow()))

        while True:
            response = ctx.model_profile.client.chat(messages, tools=ctx.plugins.tool_specs())
            messages.append(response.raw)
            if response.finish_reason == "stop":
                break

            for call in response.tool_calls:
                self._enforce_validation_chain(call, ctx)   # validateInput → hooks → permissions
                tool_result = ctx.plugins.execute(call, ctx)
                messages.append(self._map_tool_result(call, tool_result))
                events.append(AgentEvent("tool_completed", {...}, utcnow()))

            if ctx.harness_flags.s06_compression and self._needs_compress(messages, ctx):
                messages = self._compress(messages, ctx)

        result = TaskResult(task_id=task.id, status="success", plan=plan, events=events, ...)
        if ctx.harness_flags.memory_digest_on_finish:
            ctx.memory.digest(Episode(task, result, namespace=ctx.plugins.active_namespace))
        return result
```

### 2.5 必须满足的不变量

- INV-RT-1：`run_task` 的每一次 Tool 调用必须路由经过 `_enforce_validation_chain`（见 §5 验证链规范）。
- INV-RT-2：`run_task` 结束时必须写一条 `TaskResult` 到 SQLite `phoenix_tasks` 表；中断后可通过 `task_id` 恢复。
- INV-RT-3：`PhoenixCoreRuntime` 对 Claude / Codex / Kimi 的调用必须通过 Model Layer 抽象，不直接 import `anthropic` / `openai`。

---

## 3. Plugin Layer

### 3.1 ToolSpec

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str                            # 全局唯一 <plugin>.<tool>，如 "coding.multi_file_edit"
    plugin: str
    description: str
    input_schema: dict[str, JSONValue]   # JSON Schema
    handler: "ToolHandler"               # 可调用；签名见下
    side_effect: Literal["none", "read", "write", "network", "exec"]
    requires_worktree: bool = False
    namespace: str = "default"           # 与 Memory Layer 的 namespace 对齐

class ToolHandler(Protocol):
    def __call__(self, args: dict[str, JSONValue], ctx: "PhoenixContext") -> "ToolResult": ...

@dataclass
class ToolResult:
    ok: bool
    data: JSONValue
    artifacts: list[Path] = field(default_factory=list)
    stderr: str | None = None
    tokens_consumed: int = 0
```

### 3.2 PluginRegistry

```python
class PluginRegistry:
    def register(self, plugin: "Plugin") -> None: ...
    def unregister(self, name: str) -> None: ...
    def list(self) -> list["Plugin"]: ...
    def tool_specs(self) -> list[ToolSpec]: ...
    def execute(self, call: ToolCall, ctx: "PhoenixContext") -> ToolResult: ...
    def reload(self, name: str) -> None: ...        # 热加载
    @property
    def active_namespace(self) -> str: ...

@runtime_checkable
class Plugin(Protocol):
    name: str
    version: str
    tools: list[ToolSpec]
    def on_load(self, ctx: "PhoenixContext") -> None: ...
    def on_unload(self, ctx: "PhoenixContext") -> None: ...
```

### 3.3 编程插件（必交付）

模块：`phoenix.plugins.coding`

| Tool | 说明 | `side_effect` | `requires_worktree` |
|---|---|---|---|
| `coding.git_worktree` | create/list/remove | write | no（它本身就是在管理 worktree） |
| `coding.multi_file_edit` | 批量 diff 应用 + atomic commit | write | yes |
| `coding.test_runner` | 自动探测 pytest/jest/go test，返回结构化结果 | exec | yes |
| `coding.harness_validator` | 在执行前 lint 当前工具调用链（反模式：无 plan 直接改代码、同一文件并发修改等） | read | no |

### 3.4 MCP 适配
- 模块：`phoenix.plugins.mcp`
- 读取 `~/.config/phoenix/mcp.json`，对每个 server 建 session，把其工具映射为 `ToolSpec`（`plugin="mcp.<server>"`）。
- `ToolSpec.handler` 内部通过 MCP stdio 调用对应 server。

### 3.5 不变量

- INV-PL-1：任意 Tool 调用必须声明 `side_effect`；Harness Layer 据此判断需要走哪几层验证。
- INV-PL-2：`requires_worktree=True` 的 Tool 必须在 worktree 内执行（由 `_enforce_validation_chain` 检查）。
- INV-PL-3：插件间不得共享 memory namespace，除非显式声明 `shared: true`。

---

## 4. Model Layer

### 4.1 ModelProfile 配置

`~/.config/phoenix/models.toml`：
```toml
[profiles.codex-base]
provider = "openai"
model = "codex-mini-2026-04"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
role = "evaluator"

[profiles.kimi-worker]
provider = "anthropic-compatible"
model = "moonshot/kimi-k2.5-coding"
base_url = "https://api.moonshot.ai/anthropic"
api_key_env = "MOONSHOT_API_KEY"
role = "worker"

[profiles.local-ollama]
provider = "anthropic-compatible"
model = "qwen2.5-coder-32b"
base_url = "http://localhost:11434"
api_key_env = ""
role = "cheap"
```

### 4.2 统一客户端接口

```python
@dataclass
class ChatRequest:
    messages: list[dict]
    tools: list[ToolSpec] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False

@dataclass
class ChatResponse:
    raw: dict                          # provider 原始 assistant message
    text: str
    tool_calls: list["ToolCall"]
    finish_reason: Literal["stop", "tool_use", "length", "error"]
    tokens_in: int
    tokens_out: int

class LLMClient(Protocol):
    profile: "ModelProfile"
    def chat(self, req: ChatRequest) -> ChatResponse: ...
    def stream(self, req: ChatRequest) -> Iterator[dict]: ...
```

实现：`phoenix.model.client` 内部用 LiteLLM 路由；不同 `profile.provider` 走不同 adapter（`openai`、`anthropic`、`anthropic-compatible`）。

### 4.3 不变量

- INV-ML-1：所有 LLM 调用必须通过 `LLMClient`；禁止在其他层直接 `import anthropic` / `import openai`。
- INV-ML-2：`ChatResponse.tokens_in/out` 必须被 `MetricsSink` 记录，用于 PRD KPI。
- INV-ML-3：`api_key_env` 的值必须在运行时存在；缺失直接 fail-fast。
- INV-ML-4：subprocess 调用 CLI 时，**显式**传 `--model` / `--provider`；禁止依赖父进程环境变量传递密钥。

---

## 5. Harness Layer

### 5.1 HarnessFlags

```python
@dataclass(frozen=True)
class HarnessFlags:
    s01_main_loop: bool = True
    s02_tool_dispatch: bool = True
    s03_planning: bool = True
    s04_subagent: bool = False
    s05_knowledge_skills: bool = False
    s06_compression: bool = True
    s07_persistence: bool = True
    s08_background: bool = False
    s09_team: bool = False
    s10_protocols: bool = False
    s11_autonomous: bool = False
    s12_worktree: bool = True
    memory_digest_on_finish: bool = True
```

### 5.2 5 步验证链规范

```python
def _enforce_validation_chain(call: ToolCall, ctx: PhoenixContext) -> None:
    # 1) validateInput — 静态参数检查
    errs = validate_input(call.tool_spec.input_schema, call.args)
    if errs:
        raise ValidationError(errs)

    # 2) PreToolUse Hook — 用户自定义脚本，JSONL stdin/stdout
    verdict = run_pretool_hooks(call, ctx)
    if verdict.decision == "deny":
        raise PermissionDenied(verdict.reason)
    if verdict.decision == "modify":
        call = call.with_args(verdict.modified_args)

    # 3) checkPermissions — 基于 alwaysAllow / alwaysDeny / alwaysAsk 三层规则
    perm = ctx.permissions.check(call)
    if perm == "deny":
        raise PermissionDenied(f"permission rule denied: {call.tool_spec.name}")
    if perm == "ask":
        if not ctx.interactive or not ctx.prompt_user_confirm(call):
            raise PermissionDenied("user denied")

    # 4) worktree 隔离（s12）
    if call.tool_spec.requires_worktree and not in_worktree(ctx):
        raise ValidationError("tool requires git worktree but session not in one")
```

第 5 步 `mapToolResultToAPI` 由 `Runtime.run_task` 在 `_map_tool_result` 内完成。

### 5.3 各层最小实现要求

| 层 | 模块路径 | 关键函数 | 交付里程碑 |
|---|---|---|---|
| s01 | `phoenix.harness.loop` | `main_loop()` 基础 while | M0 |
| s02 | `phoenix.harness.dispatch` | `dispatch(call, ctx)` | M0 |
| s03 | `phoenix.harness.planning` | `plan(task) -> Plan`、Todo Writer | M1 |
| s04 | `phoenix.harness.subagent` | `spawn_subagent(task, ctx)` | M1 |
| s05 | `phoenix.harness.skills` | `inject_skill(name, ctx)` | M1/M2 |
| s06 | `phoenix.harness.compression` | `auto_compact`, `snip_compact`, `collapse` | M1 |
| s07 | `phoenix.harness.persistence` | SQLite schema + `TaskStore` | M1 |
| s08 | `phoenix.harness.background` | `DreamTask` | M2 |
| s09 | `phoenix.harness.team` | `TeamCreate`, `InProcessTeamCraftTask` | M2+ |
| s10 | `phoenix.harness.protocols` | `SendMessageTool` | M2+ |
| s11 | `phoenix.harness.autonomous` | `orchestrate_mode(task, ctx)` | M2+ |
| s12 | `phoenix.harness.worktree` | `EnterWorktree` / git worktree wrapper | M0 |

### 5.4 s07 持久化 SQLite schema（最小）

```sql
CREATE TABLE phoenix_tasks (
  id TEXT PRIMARY KEY,
  prompt TEXT NOT NULL,
  workspace TEXT NOT NULL,
  status TEXT NOT NULL,
  plan_json TEXT,
  events_jsonl_path TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX idx_tasks_status ON phoenix_tasks(status);
```

`phoenix execute --plan-id <id>`：从 `phoenix_tasks` 读到 `plan_json` + `events_jsonl_path`，从最后一个未完成 `PlanStep` 继续。

### 5.5 s06 压缩策略（最小）

- `auto_compact`：当 messages 的 token 超过 model 上下文 × 0.75，调用 cheap 模型（如 `local-ollama` / Haiku）总结最早 60% 的历史。
- `snip_compact`：工具结果 > 8KB 自动截断，保留前 1KB + 后 1KB + 摘要。
- `collapse`：对大量相似 tool_result，合并为"执行了 N 次 X，结果一致"。

---

## 6. Memory Layer

### 6.1 MemoryBackend

```python
@dataclass(frozen=True)
class IngestSource:
    path: Path | None = None
    text: str | None = None
    url: str | None = None
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    namespace: str = "default"

@dataclass
class IngestResult:
    node_id: str
    ingested_chunks: int
    created_links: list[str]

@dataclass
class MemoryHit:
    node_id: str
    score: float
    excerpt: str
    path: Path | None

@dataclass
class DigestResult:
    nodes_updated: int
    new_facts: int
    lint_warnings: list[str]

@dataclass
class ImportConfig:
    source_kind: Literal["obsidian", "notion", "markdown_dir", "url_list"]
    root: Path | None = None
    urls: list[str] = field(default_factory=list)
    namespace: str = "default"

@runtime_checkable
class MemoryBackend(Protocol):
    def ingest(self, source: IngestSource) -> IngestResult: ...
    def query(self, q: str, *, limit: int = 10, namespace: str | None = None) -> list[MemoryHit]: ...
    def digest(self, episode: Episode) -> DigestResult: ...
    def import_bulk(self, cfg: ImportConfig) -> "ImportReport": ...
    def graph(self, *, scope: str | None = None) -> "MemoryGraph": ...
    def lint(self, *, auto_fix: bool = False) -> "LintReport": ...
    def tier(self, *, policy: "TieringPolicy") -> "TieringReport": ...
```

### 6.2 AK-llm-wiki 适配

模块：`phoenix.memory.akllmwiki`

实现策略：subprocess 调用 `wiki-ingest` / `wiki-query` / `wiki-lint` / `wiki-import` / `wiki-graph` / `wiki-tier`；标准输出使用 JSONL；进程返回码 ≠ 0 抛 `MemoryError`。

```python
class AKLLMWikiBackend:
    def __init__(self, wiki_root: Path, cli: str = "wiki"):
        self.wiki_root = wiki_root
        self.cli = cli

    def ingest(self, source: IngestSource) -> IngestResult:
        args = [self.cli, "ingest", "--json", "--namespace", source.namespace]
        if source.path:
            args += ["--path", str(source.path)]
        elif source.text:
            args += ["--text", "-"]  # stdin
        # ...
        return self._run_json(args, stdin=source.text)
```

### 6.3 Digest 规则

- 每一次 `digest(episode)` 必须：
  1. 抽取 `episode.result.events` 中关键事件（plan、核心 tool 调用、失败恢复点）。
  2. 按 `namespace` 回写到 wiki；若节点已存在则新增 section，不覆盖。
  3. 更新 `graph` 链接：引用的外部资料（PRD / TRD / 他节点）必须显式 link。
  4. 完成后调用 `lint(auto_fix=True)`。
- Digest 规则文件：`memory/digest_rules/*.yaml`，Auto-Research 只允许修改此目录。

### 6.4 不变量

- INV-MM-1：所有任务 run 结束必须触发 digest；CI 检查 `TaskResult.status == success` 后是否存在对应 `DigestResult`。
- INV-MM-2：query 调用必须传 namespace（显式或 `None`，`None` 表示跨 namespace）。
- INV-MM-3：任何层不得绕过接口直接读写 wiki 文件。

---

## 7. Evaluation Layer

### 7.1 数据结构

```python
@dataclass(frozen=True)
class BenchmarkTask:
    id: str                             # e.g. "swebench-verified/astropy-1234"
    family: Literal["swe-bench-verified", "swe-evo", "slopcodebench", "phoenix-custom"]
    prompt: str
    workspace_image: str                # docker image tag
    verifier: "TaskVerifier"

class TaskVerifier(Protocol):
    def verify(self, patch: "Patch", ctx: PhoenixContext) -> "VerifyResult": ...

@dataclass
class Patch:
    files: dict[str, str]               # path -> diff
    commit_message: str | None = None

@dataclass
class VerifyResult:
    resolved: bool
    pass_at_1: float
    tests_passed: int
    tests_failed: int
    human_edit_distance: float | None = None
    long_horizon: "LongHorizonMetrics | None" = None

@dataclass
class LongHorizonMetrics:
    completion_rate: float
    recovery_rate: float
    persistence_score: float
    decision_stability: float

@dataclass
class BenchmarkReport:
    runtime: str
    model_profile: str
    family: str
    tasks_total: int
    resolved: int
    cost_usd: float
    tokens_in: int
    tokens_out: int
    per_task: list[tuple[str, VerifyResult]]
    generated_at: datetime
```

### 7.2 Runner

```python
class EvaluationRunner:
    def __init__(self, ctx: PhoenixContext): ...
    def run(self, family: str, *, subset: int | None = None,
            runtime: str, model_profile: str, seed: int = 0) -> BenchmarkReport: ...
    def export_report(self, report: BenchmarkReport, out: Path) -> Path: ...
```

实现细节（M1 必须落地）：
- `family == "swe-bench-verified"`：封装 `swebench.harness.run_evaluation`；加载 epoch.ai 预构建镜像；`cache_level=env`。
- `family == "swe-evo"` / `"slopcodebench"`：官方数据集解析器；任务驱动 Agent 跑完整个多 commit 流程后产出 `Patch` 序列。
- `family == "phoenix-custom"`：从 `evaluation/tasks/phoenix-custom/*.yaml` 读任务描述。

### 7.3 Evaluator Prompt 约束

- Evaluator（Codex）prompt 固定模板，保存在 `evaluation/prompts/evaluator.v1.md`，变更需 PR review。
- 固定 seed + temperature=0；多次取样均值化。
- 禁止把原始 task prompt 直接喂给 Evaluator（只喂 diff + verify 输出），避免 Prompt Injection。

### 7.4 不变量

- INV-EV-1：所有 BenchmarkReport 自动 ingest 到 wiki `namespace="evaluation"`。
- INV-EV-2：Auto-Research 不得直接调用 Evaluator；必须走 `EvaluationRunner.run()`。
- INV-EV-3：`BenchmarkReport.cost_usd` 必须与 MetricsSink 数据一致（交叉校验）。

---

## 8. Auto-Research Layer

### 8.1 接口

```python
@dataclass
class ResearchConfig:
    rounds: int = 10
    benchmark: str = "swe-bench-verified"
    subset: int = 50
    generator_runtime: str = "self"
    generator_model: str = "kimi-worker"
    evaluator_model: str = "codex-base"
    allowed_change_globs: list[str] = field(default_factory=lambda: [
        "harness/**", "plugins/**", "memory/digest_rules/**"
    ])
    significance_alpha: float = 0.05
    stop_on_n_noop_rounds: int = 3

@dataclass
class ResearchRoundReport:
    round_no: int
    baseline: BenchmarkReport
    candidate: BenchmarkReport
    kept: bool
    significant: bool
    p_value: float
    patch: "Patch"

class AutoResearchLoop:
    def __init__(self, ctx: PhoenixContext): ...
    def run(self, cfg: ResearchConfig) -> list[ResearchRoundReport]: ...
```

### 8.2 流程（必须复现）

1. 以当前代码为 baseline 跑 `EvaluationRunner.run(...)`。
2. Generator 对允许变更的目录提出 patch（以 git diff 输出）。
3. 在新分支应用 patch，再跑 `EvaluationRunner.run(...)`；seed 与 baseline 相同。
4. 对 `candidate.resolved / tasks_total` 相对 baseline 做 proportion z-test（或 bootstrap）；p ≤ alpha 视为显著。
5. Keep（`git checkout <candidate-branch>`）/ Discard（丢弃分支）。
6. `ResearchRoundReport` 写入 wiki + 触发 `wiki-lint`。
7. 连续 `stop_on_n_noop_rounds` 轮无 keep 则提前终止。

### 8.3 Prompt 注入防御
- Generator prompt 不接受网络抓取内容；所有输入来自本地 repo + wiki。
- Evaluator prompt 不包含 Generator 的 chain-of-thought。

### 8.4 不变量
- INV-AR-1：Auto-Research 变更只能动 `allowed_change_globs`。
- INV-AR-2：每轮 Kept 结果必须在下一轮开始前重跑 baseline 校准。
- INV-AR-3：`significant == False` 时默认 Discard（即使分数更高），避免噪声累积。

---

## 9. Teaching Layer

### 9.1 TeachingEmitter

```python
@dataclass
class TeachingArtifactSpec:
    milestone: str                      # "M1.2"
    kind: Literal["readme", "notebook", "experiment_report"]
    title: str
    related_nodes: list[str] = field(default_factory=list)

class TeachingEmitter:
    def __init__(self, ctx: PhoenixContext): ...
    def build(self, spec: TeachingArtifactSpec) -> Path: ...
    def publish(self, artifact: Path, *, dry_run: bool = False) -> None: ...
```

### 9.2 模板

`tools/teaching-templates/`：
- `README-teaching.md.j2`：Jinja2 模板，变量 `milestone`, `harness_flags`, `plugins`, `experiments_summary`。
- `walkthrough.ipynb.j2`：基于 nbformat 生成的 Notebook 骨架。
- `experiment-report.md.j2`：嵌入 BenchmarkReport 表格与曲线（可选用 matplotlib）。

### 9.3 CI 检查

`tools/ci-check-teaching.py`（pre-push hook）：
- 若当前分支 commit 标签含 `milestone/M*`，则检查 `docs/teaching/M*/` 下必须存在对应三份 artifact，且 `wiki-ingest` 已成功（以 `.ingested.json` marker 文件为准）。

### 9.4 不变量
- INV-TL-1：`publish` 必须在 `dry_run=False` 时写入 artifact 元数据中的 `ingested_at`。
- INV-TL-2：artifact front-matter 必须包含：`milestone`, `stage`, `related_nodes`, `generated_by`, `date`。

---

## 10. PhoenixContext

```python
@dataclass
class PhoenixContext:
    session_id: ULID
    workspace: Path
    runtime: AgentRuntime
    model_profile: "ModelProfile"
    memory: MemoryBackend
    plugins: PluginRegistry
    permissions: "PermissionRules"
    harness_flags: HarnessFlags
    evaluation: "EvaluationRunner | None" = None
    teaching: "TeachingEmitter | None" = None
    logger: "StructuredLogger" = field(default_factory=...)
    metrics: "MetricsSink" = field(default_factory=...)
    interactive: bool = True

    def prompt_user_confirm(self, call: "ToolCall") -> bool: ...
```

构造入口：`phoenix.bootstrap.build_context(cfg: CLIConfig) -> PhoenixContext`。

---

## 11. PermissionRules

```python
@dataclass
class PermissionRule:
    pattern: str            # glob over "tool_name/arg_path"
    decision: Literal["allow", "deny", "ask"]
    note: str = ""

@dataclass
class PermissionRules:
    allow: list[PermissionRule] = field(default_factory=list)
    deny: list[PermissionRule] = field(default_factory=list)
    ask: list[PermissionRule] = field(default_factory=list)

    def check(self, call: "ToolCall") -> Literal["allow", "deny", "ask"]: ...
```

加载：`~/.config/phoenix/permissions.toml`，与 Claude Code 的 `alwaysAllowRules / alwaysDenyRules / alwaysAskRules` 一一对齐，支持直接 import。

---

## 12. Hook 协议（与 Claude Code 兼容）

### 12.1 事件类型
```python
HookEvent = Literal[
    "PreToolUse", "PostToolUse",
    "PrePlan", "PostPlan",
    "PreSubagent", "PostSubagent",
    "OnError",
]
```

### 12.2 Hook 进程协议
- 输入：JSONL stdin，一行一个 `HookInput`：
  ```json
  {"event":"PreToolUse","tool":"coding.multi_file_edit","args":{...},"task_id":"..."}
  ```
- 输出：JSONL stdout，一行一个 `HookOutput`：
  ```json
  {"decision":"allow"}
  {"decision":"modify","modified_args":{...}}
  {"decision":"deny","reason":"path blacklisted"}
  ```
- 超时：默认 3s，超时视为 `deny`。

### 12.3 默认 Hook
- `tools/hooks/deny-rm-rf.sh`：禁止 `rm -rf` 到 workspace 外路径。
- `tools/hooks/worktree-enforce.sh`：`requires_worktree=True` 的工具强制检查。

---

## 13. 日志与指标

### 13.1 StructuredLogger
- 输出：`logs/<session_id>.jsonl`；每行一个 `AgentEvent`（§1）。
- 字段统一含 `ts`、`session_id`、`task_id`、`kind`、`payload`。

### 13.2 MetricsSink
- 本地实现：SQLite `phoenix_metrics` 表，列：`ts`, `session_id`, `task_id`, `metric`, `value`, `tags(JSON)`。
- 必记指标：`tokens_in`、`tokens_out`、`tool_latency_ms`、`permission_denials`、`cost_usd`、`benchmark_resolved`。

### 13.3 Dashboard
- `phoenix dashboard --since 7d`：渲染 Markdown 总览（Resolved Rate 曲线、Token 成本、Permission 拒绝次数）。

---

## 14. CLI 契约

```
phoenix doctor
phoenix run       --task "..." [--runtime=claude|self|openai] [--model=<profile>] [--interactive/--no-interactive]
phoenix execute   --plan-id <ulid>
phoenix status    [--task-id <ulid>]
phoenix tasks     list|show|cancel
phoenix eval      --benchmark=<family> [--subset=N] [--runtime=...] [--model=<profile>]
phoenix research  --rounds=N --benchmark=<family> [--generator-model=...] [--evaluator-model=...]
phoenix memory    ingest|query|digest|import|graph|lint|tier
phoenix teach     build --milestone=M1.2 | publish [--dry-run]
phoenix dashboard [--since 7d]
```

- 所有子命令支持 `--json`，输出机器可读结构。
- 退出码：0 成功；1 用户错误；2 依赖不可达；3 评测不达标；10 权限拒绝；11 记忆写入失败。

---

## 15. 目录结构（权威）

```
PhoenixAgent/
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   ├── RnD-Analysis.md
│   ├── SPEC.md
│   ├── milestones/
│   │   ├── M0-plan.md
│   │   ├── M1-plan.md
│   │   └── M2-plan.md
│   └── teaching/
│       ├── templates/
│       │   ├── README-teaching.md.j2
│       │   ├── walkthrough.ipynb.j2
│       │   └── experiment-report.md.j2
│       ├── M0/ M1/ M2/...
├── src/phoenix/
│   ├── bootstrap.py
│   ├── cli.py
│   ├── context.py                # PhoenixContext
│   ├── runtime/
│   │   ├── base.py
│   │   ├── claude.py
│   │   ├── core.py
│   │   └── openai.py
│   ├── model/
│   │   ├── client.py
│   │   └── profiles.py
│   ├── harness/
│   │   ├── flags.py
│   │   ├── loop.py
│   │   ├── dispatch.py
│   │   ├── planning.py
│   │   ├── compression.py
│   │   ├── persistence.py
│   │   ├── subagent.py
│   │   ├── worktree.py
│   │   └── ...
│   ├── plugins/
│   │   ├── registry.py
│   │   ├── coding/
│   │   │   ├── git_worktree.py
│   │   │   ├── multi_file_edit.py
│   │   │   ├── test_runner.py
│   │   │   └── harness_validator.py
│   │   └── mcp/
│   ├── memory/
│   │   ├── backend.py
│   │   ├── akllmwiki.py
│   │   └── digest_rules/
│   ├── evaluation/
│   │   ├── runner.py
│   │   ├── swebench.py
│   │   ├── sweevo.py
│   │   ├── slopcodebench.py
│   │   └── phoenix_custom/
│   ├── research/
│   │   ├── loop.py
│   │   └── patching.py
│   └── teaching/
│       ├── emitter.py
│       └── templates.py
├── evaluation/
│   ├── tasks/phoenix-custom/
│   └── prompts/evaluator.v1.md
├── tools/
│   ├── phoenix-doctor.sh
│   ├── hooks/
│   ├── teaching-templates/
│   └── ci-check-teaching.py
├── logs/
├── tests/
├── pyproject.toml
└── README.md
```

---

## 16. 最小可运行骨架交付物（M0 Day-5 验收）

1. `src/phoenix/runtime/base.py`：`AgentRuntime` Protocol + 空实现。
2. `src/phoenix/runtime/claude.py`：`ClaudeAgentSDKRuntime` 跑通 hello task。
3. `src/phoenix/model/client.py`：Codex + Kimi 两种 profile 均能 chat。
4. `src/phoenix/memory/akllmwiki.py`：`ingest/query` 可运行。
5. `src/phoenix/plugins/registry.py`：可注册一个 dummy tool。
6. `src/phoenix/cli.py`：`phoenix doctor` + `phoenix run` 两条命令。
7. `tools/phoenix-doctor.sh`：检查 Python、Docker、Anthropic / OpenAI / Kimi 可达性。
8. `docs/milestones/M0-plan.md`：按日任务清单。

---

## 17. 接受标准交叉索引

| 模块 | PRD 编号 | TRD 章节 | 不变量 |
|---|---|---|---|
| Runtime Layer | FR-01 | §2 | INV-RT-1/2/3 |
| Model Layer | FR-02 | §3 | INV-ML-1/2/3/4 |
| Harness Layer | FR-03 | §4 | 验证链 5 步 |
| Plugin Layer | FR-04 | §5 | INV-PL-1/2/3 |
| Memory Layer | FR-05 | §6 | INV-MM-1/2/3 |
| Evaluation Layer | FR-06 | §7 | INV-EV-1/2/3 |
| Auto-Research | FR-07 | §8 | INV-AR-1/2/3 |
| Teaching Layer | FR-08 | §9 | INV-TL-1/2 |

---

## 18. 变更流程

- 任何 SPEC 变更必须：
  1. PR 描述写明动机 + 受影响的 PRD / TRD 编号。
  2. 若影响不变量（INV-*），必须同步更新 RnD-Analysis §4 风险矩阵。
  3. 合并后重新 `wiki-ingest` 最新 SPEC.md，版本号 +1。
- SPEC 不接受"只改实现不改文档"的 PR；文档先行硬约束。

---

## 19. 变更日志

| 版本 | 日期 | 变更 | 触发 ADR |
|---|---|---|---|
| v1.0 | 2026-04-18 | 首版；锁定八层接口契约、HarnessFlags s01~s12 清单与 default、5 步验证链、PhoenixContext / ToolSpec / ToolCall 骨架。 | — |
| v1.1 | 2026-04-19 | §5.1 `HarnessFlags` 装饰器从 `@dataclass` 改为 `@dataclass(frozen=True)`，对齐 `harness-flags-policy` HF-IMPL-1；Minor 向后兼容（字段集 / 默认值 / 类型不变，仅强化不可变语义）。 | ADR-0001 |
