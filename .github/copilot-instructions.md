# Copilot instructions for PhoenixAgent

## Build, test, and validation commands

This repository is currently **governance-first**: the active surface is `docs/`, `tools/`, and `.github/`. There is no runnable `src/phoenix/**` or `tests/**` tree yet, so the practical feedback loop today is the doctor script plus the repo validators.

```bash
# Environment preflight (run with bash, even on Windows)
bash tools/phoenix-doctor.sh --strict
bash tools/phoenix-doctor.sh --json

# Core validators
py -3 tools/ci-check-spec.py
py -3 tools/ci-check-adr.py
py -3 tools/ci-check-flags.py

# Conditional validators
py -3 tools/ci-check-teaching.py       # when touching docs/teaching/**
py -3 tools/ci-check-milestone-dod.py  # when touching docs/milestones/**
```

For the closest current equivalent of a **single test**, run only the validator for the surface you changed, for example:

```bash
py -3 tools/ci-check-flags.py   # HarnessFlags / SPEC v1.1 §5.1 changes
py -3 tools/ci-check-adr.py     # docs/adr/** changes
py -3 tools/ci-check-spec.py    # Tier-0 / cross-document reference changes
```

`docs/quality/test-strategy.md` defines a future `pytest` / coverage workflow for M1+, but do not assume those commands exist until `src/phoenix/**` and `tests/**` are introduced.

## High-level architecture

- **Current repo state:** this repo is the governance layer for PhoenixAgent. `docs/` is the canonical source of truth, `tools/` turns governance rules into machine checks, and `.github/PULL_REQUEST_TEMPLATE.md` mirrors the evidence reviewers expect.
- **Planned product architecture:** PhoenixAgent is specified as an eight-layer coding-agent stack: **Runtime, Model, Harness, Plugin, Memory, Evaluation, Auto-Research, Teaching**.
- **Composition root:** `docs/SPEC.md` defines `PhoenixContext` as the object that wires runtime, model profile, memory backend, plugin registry, permission rules, harness flags, evaluation, teaching, logger, and metrics together.
- **Operational core:** the Harness Layer is the control plane. Every tool call must follow the 5-step safety path: `validateInput -> PreToolUse Hook -> checkPermissions -> worktree enforcement -> mapToolResultToAPI`.
- **Plugin and memory boundaries are explicit:** tools are modeled as `ToolSpec`s in the Plugin Layer; MCP servers are planned as first-class plugin adapters via `~/.config/phoenix/mcp.json`; memory access goes through `MemoryBackend` rather than ad hoc file reads.
- **Evaluation, Auto-Research, and Teaching are first-class layers:** the design expects code changes to eventually feed reproducible evaluation runs and ingested teaching artifacts, not just runtime behavior.

## Key conventions

- Start by reading `docs/README.md` and `AGENTS.md`, then only the 1-2 task-specific docs you need. Do **not** load the whole `docs/` tree by default.
- Preserve the document role split:
  - `PRD.md`, `TRD.md`, `RnD-Analysis.md`, `SPEC.md` = canonical contract
  - `docs/rules/**` = process and policy
  - `docs/quality/**` = acceptance and review criteria
  - `docs/adr/**` = why a decision was made
- Cross-document references are strict. Use stable IDs (`FR-*`, `D-*`, `INV-*`, `R-*`, `ADR-NNNN`, `sNN`) and always cite SPEC with a version, e.g. `SPEC v1.1 §5.1`.
- Do not add random Markdown files under `docs/`; the root of `docs/` is tightly controlled by `documentation-rules.md`.
- Treat `HarnessFlags` as immutable. In spec and implementation they are `@dataclass(frozen=True)`, and changes must use `dataclasses.replace(...)`, not attribute assignment. Safety-critical defaults `s01`, `s02`, and `s12` must stay `True`.
- Use `py -3` for Python commands. `tools/phoenix-doctor.sh` is a bash script even in this Windows repo. New Python scripts should keep UTF-8 console output because Windows encoding issues are a known trap.
- The repo is still pre-implementation: unless the milestone docs explicitly say otherwise, expect work to land in `docs/`, `tools/`, or `.github/`, not `src/phoenix/**`.
- If a task changes SPEC, a rule, DoD thresholds, HarnessFlags defaults, or other governance contracts, check whether it triggers an ADR instead of silently editing the rule to fit the change.
