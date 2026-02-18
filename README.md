# llm_agent

Local-first AI agent wrapper built on AWS Strands, with pluggable model backends.

## Why this exists

The goal is to keep agent behavior and tooling stable while model providers change over time.

- Keep your core logic in one place: prompts, tools, orchestration.
- Swap model backends through config (Bedrock, local Ollama, future providers).
- Use AWS as the default cloud control plane, without hard-coding one model vendor.

## Current status

This repository is in an early but working stage.

- A CLI agent runs through `src/agent/cli.py` (entrypoint exposed as `agent`).
- Backend selection is config-driven (`bedrock` or `ollama`).
- Two basic tools are implemented (`read_file`, `list_dir`).
- Infra modules currently provision:
  - SNS alert topic
  - Budget alerts
  - Bedrock invoke IAM policy/role
- Planned but not yet implemented: EC2 GPU runtime orchestration via Lambda + SSM.

## Repository layout

- `src/agent/`
  - `config.py`: typed config + env overrides
  - `backends.py`: backend model construction (Ollama/Bedrock)
  - `tools.py`: tool library + profile-based tool selection
  - `cli.py`: orchestration and runtime flow
  - `main.py`: compatibility wrapper that delegates to CLI run
  - `__main__.py`: supports module execution (`python -m agent`)
- `config/profiles/`
  - one YAML profile per agent (`default.yml` currently)
- `docker/ollama/`
  - scripts to run local Ollama in Docker and manage model cache
- `docker/dev/`
  - dev container with AWS CLI, Terraform, Terragrunt
- `infra/terragrunt/`
  - `modules/`: reusable Terraform modules
  - `live/prod/`: environment-specific Terragrunt stacks
- `scripts/`
  - local bootstrap script and planned operational wrappers

## Runtime architecture (today)

1. CLI receives prompt from argv or stdin.
2. Agent loads `config/profiles/<profile>.yml` (default: `default`).
3. Backend/model is selected from profile config:
   - `ollama`: health-check `GET /api/tags`, then init `OllamaModel`
   - `bedrock`: init `BedrockModel` with region + model ID
4. Agent is created with profile system prompt + only configured tools.
5. Prompt executes, result is printed to stdout.

## Quick start

## 1) Install dependencies

```bash
cd /home/aaron/repos/llm_agent
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
uv sync
```

## 2) Configure backend

Edit `config/profiles/default.yml`:

- set `backend: bedrock` or `backend: ollama`
- set model IDs in nested backend maps:
  - `model.ollama.*`
  - `model.bedrock.*`

For Bedrock, ensure AWS credentials/profile are available in your shell.

## 3) Run the agent

```bash
uv run agent "Summarize this repository in 5 bullets."
uv run agent --profile default "Summarize this repository in 5 bullets."
```

or:

```bash
echo "List likely next implementation steps." | uv run agent
echo "List likely next implementation steps." | uv run agent --profile default
```

You can also override backend/model settings without editing config:

```bash
AGENT_BACKEND=ollama uv run agent "Reply with exactly HI"
AGENT_BACKEND=bedrock uv run agent "Reply with exactly HI"
```

## Local Ollama workflow

Bring up local Ollama container:

```bash
./docker/ollama/up.sh cpu
```

Verify:

```bash
./docker/ollama/image-test.sh
```

Stop:

```bash
./docker/ollama/down.sh
```

Purge downloaded models:

```bash
./docker/ollama/purge-models.sh
```

## Smoke tests

Single command (recommended after refactors):

```bash
./scripts/e2e_smoke.sh all
```

The smoke scripts run the agent with `uv run`, so run `uv sync` once first.

Run one backend at a time:

```bash
./scripts/smoke_ollama.sh
./scripts/smoke_bedrock.sh
```

Pytest wrappers (safe by default; run only when explicitly enabled):

```bash
RUN_OLLAMA_SMOKE=1 uv run pytest -m smoke_ollama -q
RUN_BEDROCK_SMOKE=1 uv run pytest -m smoke_bedrock -q
```

Behavior:

- `smoke_ollama.sh` is now fully end-to-end: starts container, runs agent check, tears down.
- `smoke_bedrock.sh` runs the equivalent Bedrock check.
- `e2e_smoke.sh all` runs both in sequence.
- Set `KEEP_OLLAMA_UP=1` if you want to keep the container running after the Ollama smoke test.

## Infra workflow (Terragrunt)

Current infra stacks are under:

- `infra/terragrunt/live/prod/alerts-sns`
- `infra/terragrunt/live/prod/budget`
- `infra/terragrunt/live/prod/bedrock-iam`

Run via your local toolchain or `docker/dev/dev-container.sh`.

## Known gaps and caveats

- No formal tests yet (unit/integration/e2e).
- No provider abstraction layer yet beyond `if/elif` backend switch.
- No remote Ollama (EC2 + SSM tunnel) implementation yet.
- Profiles are currently treated as trusted inputs.
- Tool-level access control/policy hooks are planned but not enforced yet.
- Tooling is minimal and currently read-only.
- Error handling/config validation is functional but not strict/typed.

## Near-term direction

See `IMPLEMENTATION_PLAN.md` for a phased build plan with acceptance criteria.
