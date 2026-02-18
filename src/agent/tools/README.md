# Tools Architecture

This directory defines a tool framework for the agent runtime.

Key files:

- `core.py`: shared contracts/runtime (`ToolPolicy`, `ToolSpec`, `ToolRuntime`, `ToolCallContext`)
- `<tool>.py`: one file per concrete tool (policy + constructor + `SPEC`)
- `registry.py`: the available tool specs
- `__init__.py`: `build_tools(...)` entrypoint used by the runtime

## Why This Pattern Exists

The tool system is intentionally split into:

- broad, reusable tool capabilities (for example, `git`)
- profile-specific restrictions (policy in config)

This is meant to support different agent profiles with different risk/cost envelopes, without rewriting tool code per profile.

Main motivations:

1. Keep tools reusable:
- One `git` tool can serve many profiles (`read-only reviewer`, `branching fixer`, `release helper`) by changing the policy used for particular agents.

2. Put safety in enforceable code paths:
- Guardrails are checked in tool code and reflected in policy models, not only implied by prompts. An agent should literally be unable to `rm -rf` everything, not just be asked "pretty please be safe" in the prompt

3. Make failures diagnosable:
- Every tool call emits consistent lifecycle events. CI failures become traceable from logs.

4. Reduce accidental inconsistency:
- A shared call context (`ToolCallContext`) standardizes timing, success/error fields, and deny behavior.

5. Make growth manageable:
- New tools can follow one template and inherit observability and policy conventions.

## Design Principles

1. Policy is configuration, behavior is implementation:
- Policy: allowlists, limits, branch controls, write permissions. Safety stuff mostly.
- Implementation: how the tool actually executes an operation.

2. Denials are first-class, not generic errors:
- A denied action should carry a stable reason (`action_not_allowed`, `branch_prefix_required`, etc.).

3. Logging is a contract:
- Every call should produce predictable event shapes so humans and automation can consume them.

4. Tool modules should be small and local:
- Keep each tool in its own file to avoid a single large, hard-to-change tools blob.

## How a Tool Is Wired

Each tool module does three things:

1. Define a policy model:
- Subclass `ToolPolicy`
- Add security and operational knobs

2. Define `tool_constructor(repo_root, policy, rt)`:
- Build and return a Strands `@tool` callable
- Use `ToolCallContext` for lifecycle logging
- Takes in a tool pattern (ex: git operations) and a policy (ex: this agent's git tool should be read only)
- The callable function it returns (the actual tool given to the agent) should have whatever custom safety profile you configured that agent to have

3. Export `SPEC`:
- `SPEC = ToolSpec("<name>", <PolicyClass>, tool_constructor)`

Then add the spec to `registry.py`.

## Call Lifecycle (Standardized)

Inside a tool call:

1. `ctx = rt.start("tool_name", ...)`
- Emits `hook.tool.before`
- Captures start time and base fields

2. `ctx.policy_before(...)` before policy checks
- Emits `hook.policy.before`

3. Exit through one path:
- `ctx.ok(output, ...)`:
  - Emits `hook.tool.after status=ok`
- `ctx.error(message, reason=..., ...)`:
  - Emits `hook.tool.after status=error`
- `ctx.deny(reason, message=..., ...)`:
  - Emits `hook.policy.deny`
  - Then emits `hook.tool.after status=error`

This keeps observability consistent regardless of tool type.

## Guardrail Model

Guardrails should be represented explicitly in the policy model and enforced in code.

Typical policy fields:

- action allowlists (`allowed_actions`)
- payload limits (`max_output_chars`, max files, max input length)
- write controls (`allow_push`, `allow_worktree_dirty`)
- scope controls (`managed_branch_prefix`, ref patterns)

Reason strings should be short and stable (examples):

- `action_not_allowed`
- `invalid_ref`
- `invalid_since_format`
- `branch_prefix_required`
- `too_many_files`
- `dirty_worktree`

Stable reason keys matter for:

- CI policy assertions
- future dashboards/alerting
- clean incident triage

## Minimal Tool Template

```python
from pathlib import Path
from strands.tools import tool

from .core import ToolPolicy, ToolRuntime, ToolSpec


class ExamplePolicy(ToolPolicy): # This has whatever safety knobs you want
    allowed_actions: list[str] = ["read"]
    max_output_chars: int = 5000


def tool_constructor(repo_root: Path, policy: ToolPolicy, rt: ToolRuntime):
    # Runtime guard to keep constructor and policy types aligned.
    assert isinstance(policy, ExamplePolicy)

    # Normalize allowlist
    allowed = {a.strip().lower() for a in policy.allowed_actions if a.strip()}

    @tool
    def example(action: str, arg1: str = "") -> str:
        action = (action or "").strip().lower() # Normalize caller input.
        ctx = rt.start("example", action=action, arg1=arg1) # Start standardized tool lifecycle logging + timer.
        ctx.policy_before() # Mark the beginning of policy checks in logs.

        if action not in allowed:
            # Policy denial: emits deny + error lifecycle events.
            return ctx.deny("action_not_allowed")

        try:
            # Domain behavior for this tool goes here.
            out = f"example output for {arg1}"
        except Exception as e:
            # Runtime failure with structured reason for debugging/metrics.
            return ctx.error(f"ERROR: {e}", reason="unexpected_failure")

        if len(out) > policy.max_output_chars:
            # Enforce output budget before returning to the model.
            out = out[: policy.max_output_chars]
        # Success path: emits a standardized "ok" lifecycle event.
        return ctx.ok(out)

    return example


# Registry metadata: name + policy schema + constructor function.
SPEC = ToolSpec("example", ExamplePolicy, tool_constructor)
```

## Adding a New Tool (Checklist)

- Add `<tool>.py` with:
  - `Policy` model
  - `tool_constructor`
  - exported `SPEC`
- Register `SPEC` in `registry.py`
- Add tests for:
  - happy path
  - deny path (`action_not_allowed` etc.)
  - validation errors
  - guardrail limit behavior
- Add/adjust profile config examples in `config/profiles/*.yml`

## Future Direction

This pattern is designed to scale toward:

- profile families with different trust levels
- “broad tool + narrow policy” across CI and local runs
- stronger automated policy verification in tests
- richer observability (structured logs, per-tool metrics, deny-rate tracking)
