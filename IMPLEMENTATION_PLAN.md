# Implementation Plan

This plan is optimized for incremental progress: each phase should land as a small PR with tests and runnable docs.

## Principles

- Keep agent behavior provider-agnostic.
- Prefer config-driven backend/model switching.
- Keep local-first developer workflow simple.
- Add AWS controls for cost and safety before adding complexity.

## Phase 0: Baseline hardening (current code -> stable baseline)

## Goals

- Make current workflows reliable.
- Remove known friction points.

## Tasks

- Fix `docker/ollama/up.sh` repo-root/config path resolution.
- Add config validation using Pydantic models for `agent.yml`.
- Normalize CLI behavior and exit codes for common failures.
- Add structured logging (basic levels: info/warn/error).
- Add `.env.example` for expected environment variables.

## Acceptance criteria

- `python -m agent` works with both backends using documented steps.
- Invalid config produces clear, actionable error messages.
- Ollama helper scripts work from any current working directory.

## Phase 1: Code architecture for pluggable backends

## Goals

- Decouple backend selection from `main.py`.
- Make adding new providers low-risk.

## Tasks

- Introduce `src/agent/backends/` with a common interface:
  - `BaseBackend` (or protocol)
  - `BedrockBackend`
  - `OllamaBackend`
- Move backend initialization logic out of `main.py`.
- Add backend factory (`from_config`) and backend capability metadata.
- Refactor tool registration into `src/agent/tools/`.

## Acceptance criteria

- `main.py` mainly orchestrates config -> backend -> agent run.
- Adding a new backend requires a new class + config entry, not edits across core flow.
- Unit tests cover backend factory selection and error cases.

## Phase 2: Tooling model and safety

## Goals

- Move from demo tools to usable coding-agent tools safely.

## Tasks

- Expand toolset:
  - `read_file`, `list_dir` improvements (path constraints, limits)
  - `search_files` (ripgrep wrapper)
  - `write_file` with explicit safety rules
  - optional `run_command` with allowlist
- Add tool policy config (`enabled_tools`, max output sizes, write paths).
- Add audit logging for tool invocations.

## Acceptance criteria

- Tools are independently testable.
- Unsafe operations are blocked with explicit error messages.
- Agent can complete simple repo tasks end-to-end using tools.

## Phase 3: Local + remote Ollama operations

## Goals

- Support both laptop local Ollama and remote GPU Ollama through the same interface.

## Tasks

- Add scripts described in `scripts/README.md`:
  - `gpu_start.sh`
  - `gpu_stop.sh`
  - `ssm_shell.sh`
  - `ssm_tunnel_ollama.sh`
  - `run_agent.sh`
- Ensure remote Ollama still maps to local endpoint (`localhost:11434`) via SSM tunnel.
- Add health-check and reconnect behaviors for tunneled backend.

## Acceptance criteria

- Single documented workflow to start remote GPU, tunnel, run agent, stop instance.
- No inbound ports required on EC2.
- Failures are recoverable with clear operator instructions.

## Phase 4: AWS infra for safe GPU orchestration

## Goals

- Implement planned AWS control plane with cost guardrails.

## Tasks

- Add Terragrunt modules/stacks for:
  - GPU EC2 instance + IAM profile (`AmazonSSMManagedInstanceCore`)
  - Lambda: `StartGpuInstance`, `StopGpuInstance`
  - EventBridge Scheduler one-shot auto-stop jobs
  - IAM policy to prevent direct human `ec2:StartInstances`
- Integrate alerts with existing SNS + budget setup.

## Acceptance criteria

- Instance can only be started through approved workflow.
- Every start request includes bounded runtime with auto-stop.
- End-to-end infra plan/apply works cleanly in `live/prod`.

## Phase 5: Quality gates and CI

## Goals

- Make the repo maintainable and safe to evolve.

## Tasks

- Add test suites:
  - unit tests (config/backend/tools)
  - integration tests (mocked Bedrock/Ollama clients)
- Add lint/type checks (`ruff`, `mypy` or equivalent).
- Add GitHub Actions:
  - test + lint on PR
  - optional nightly smoke test against local mock backend

## Acceptance criteria

- CI blocks merges on failing checks.
- New backend/tool contributions have clear test patterns.
- Regressions are caught before deployment.

## Phase 6: Multi-provider expansion (optional, after stabilization)

## Goals

- Add optional direct provider adapters while keeping Bedrock as default cloud path.

## Tasks

- Add adapters for additional providers only through the backend interface.
- Add model routing policy (cost/performance tiers).
- Add provider-specific retry and quota handling.

## Acceptance criteria

- Swapping model/provider requires config changes, not architecture changes.
- Provider-specific failures degrade gracefully.

## Suggested next 3 PRs

1. PR-1: Baseline hardening
2. PR-2: Backend abstraction refactor
3. PR-3: Tool safety and expanded file/search tooling

## Definition of done for each PR

- Code + tests + docs updated together.
- `README.md` reflects new workflow.
- Commands shown in docs are verified in a clean environment.
