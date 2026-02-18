# llm_agent

Local-first AI agent wrapper built on AWS Strands, with pluggable model backends.

## Why this exists

The goal is to keep agent behavior and tooling stable while model providers change over time.

- Keep your core logic in one place: prompts, tools, orchestration.
- Swap model backends through config (Bedrock, local Ollama, future providers).
- Use AWS as the default cloud control plane, without hard-coding one model vendor.

## Current status

This repository is in an early but working stage.

- A CLI agent runs from `src/agent/main.py`.
- Backend selection is config-driven (`bedrock` or `ollama`).
- Two basic tools are implemented (`read_file`, `list_dir`).
- Infra modules currently provision:
  - SNS alert topic
  - Budget alerts
  - Bedrock invoke IAM policy/role
- Planned but not yet implemented: EC2 GPU runtime orchestration via Lambda + SSM.

## Repository layout

- `src/agent/`
  - `main.py`: agent startup, config loading, backend/model selection, tool registration
  - `__main__.py`: allows `python -m agent`
- `config/agent.yml`
  - active backend and model IDs
  - system prompt text
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
2. Agent loads `config/agent.yml`.
3. Backend is selected:
   - `ollama`: health-check `GET /api/tags`, then init `OllamaModel`
   - `bedrock`: init `BedrockModel` with region + model ID
4. Agent is created with system prompt + local tools.
5. Prompt executes, result is printed to stdout.

## Quick start

## 1) Install dependencies

```bash
cd /home/aaron/repos/llm_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Configure backend

Edit `config/agent.yml`:

- set `backend: bedrock` or `backend: ollama`
- set model IDs for the chosen backend

For Bedrock, ensure AWS credentials/profile are available in your shell.

## 3) Run the agent

```bash
python -m agent "Summarize this repository in 5 bullets."
```

or:

```bash
echo "List likely next implementation steps." | python -m agent
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
- Tooling is minimal and currently read-only.
- Error handling/config validation is functional but not strict/typed.

## Near-term direction

See `IMPLEMENTATION_PLAN.md` for a phased build plan with acceptance criteria.
