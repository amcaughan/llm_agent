import logging
import re
import time
from pathlib import Path
from typing import Any

from pydantic import Field
from strands.tools import tool

from .core import ToolPolicy, ToolRuntime, ToolSpec, run_git


class GitToolPolicy(ToolPolicy):
    allowed_actions: list[str] = Field(default_factory=lambda: ["diff_since"])
    managed_branch_prefix: str = ""
    enforce_prefix_for_writes: bool = True
    allow_push: bool = False
    allow_worktree_dirty: bool = False
    max_output_chars: int = 60000
    max_files: int = 200
    max_since_chars: int = 64
    since_pattern: str = r"^[A-Za-z0-9_:+\-.,/ ]+$"
    allowed_ref_pattern: str = r"^[A-Za-z0-9_./\-~^:@]+$"
    context_lines: int = 3


def tool_constructor(repo_root: Path, policy: ToolPolicy, rt: ToolRuntime):
    assert isinstance(policy, GitToolPolicy)
    tool_name = "git"

    since_regex = re.compile(policy.since_pattern)
    ref_regex = re.compile(policy.allowed_ref_pattern)
    safe_branch_regex = re.compile(r"^[A-Za-z0-9._/\-]+$")
    context_lines = min(max(policy.context_lines, 0), 20)
    allowed_actions = {a.strip().lower() for a in policy.allowed_actions if a.strip()}
    write_actions = {"create_branch", "checkout", "commit"}
    write_like_actions = write_actions | {"push"}

    def _current_branch() -> str:
        rc, out, err = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
        if rc != 0:
            raise RuntimeError(err.strip() or "failed to resolve current branch")
        return out.strip()

    def _prefixed_branch(branch: str) -> str:
        if not policy.managed_branch_prefix:
            return branch
        if branch.startswith(policy.managed_branch_prefix):
            return branch
        return f"{policy.managed_branch_prefix}{branch}"

    def _is_branch_allowed(branch: str) -> bool:
        if not policy.managed_branch_prefix:
            return True
        return branch.startswith(policy.managed_branch_prefix)

    def _validate_ref(value: str, ref_name: str) -> str | None:
        value = (value or "").strip()
        if not value:
            return f"ERROR: {ref_name} cannot be empty."
        if not ref_regex.fullmatch(value):
            return f"ERROR: {ref_name} contains unsupported characters."
        return None

    def _policy_snapshot() -> str:
        snap = {
            "allowed_actions": sorted(allowed_actions),
            "managed_branch_prefix": policy.managed_branch_prefix,
            "enforce_prefix_for_writes": policy.enforce_prefix_for_writes,
            "allow_push": policy.allow_push,
            "allow_worktree_dirty": policy.allow_worktree_dirty,
        }
        return str(snap)

    def _deny(reason: str, **fields: Any) -> str:
        rt.policy_deny(tool_name, reason, **fields)
        return f"ERROR: denied_by_policy reason={reason} policy={_policy_snapshot()}"

    @tool
    def git(action: str, arg1: str = "", arg2: str = "") -> str:
        """
        Generic git tool with policy-gated actions.
        action/arg contract:
        - diff_since: arg1=since
        - log: arg1=ref (optional), arg2=max_count (optional)
        - diff: arg1=base_ref, arg2=head_ref(optional; default HEAD)
        - show: arg1=ref (optional; default HEAD)
        - rev_parse: arg1=ref (optional; default HEAD)
        - status: no args
        - create_branch: arg1=branch_name, arg2=base_ref(optional; default HEAD)
        - checkout: arg1=branch_name
        - commit: arg1=message
        - push: arg1=remote(optional; default origin), arg2=branch(optional; default current)
        """
        started = time.perf_counter()
        normalized_action = (action or "").strip().lower()
        rt.before(tool_name, action=normalized_action, arg1=arg1, arg2=arg2)
        rt.policy_before(tool_name, action=normalized_action)

        if normalized_action not in allowed_actions:
            return _deny("action_not_allowed", action=normalized_action)

        if normalized_action == "push" and not policy.allow_push:
            return _deny("push_not_allowed", action=normalized_action)

        if policy.enforce_prefix_for_writes and policy.managed_branch_prefix and normalized_action in write_like_actions:
            try:
                current = _current_branch()
            except RuntimeError as e:
                rt.after(
                    logging.ERROR,
                    tool_name,
                    status="error",
                    action=normalized_action,
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                    error=str(e),
                )
                return f"ERROR: {e}"
            if not _is_branch_allowed(current):
                return _deny(
                    "branch_prefix_required",
                    action=normalized_action,
                    current_branch=current,
                    required_prefix=policy.managed_branch_prefix,
                )

        if normalized_action in write_actions and not policy.allow_worktree_dirty:
            rc, out, err = run_git(repo_root, ["status", "--porcelain"])
            if rc != 0:
                return f"ERROR: failed to inspect worktree: {err.strip() or f'git exited {rc}'}"
            if out.strip():
                return _deny("dirty_worktree", action=normalized_action)

        if normalized_action == "diff_since":
            since = (arg1 or "").strip()
            if not since:
                return _deny("empty_since", action=normalized_action)
            if len(since) > policy.max_since_chars:
                return _deny("since_too_long", max_since_chars=policy.max_since_chars)
            if not since_regex.fullmatch(since):
                return _deny("since_pattern_mismatch")

            rc, base_commit, err = run_git(repo_root, ["rev-list", "-1", f"--before={since}", "HEAD"])
            if rc != 0:
                return f"ERROR: failed to resolve commit for since={since!r}: {err.strip() or f'git exited {rc}'}"
            base_commit = base_commit.strip()
            if not base_commit:
                return f"ERROR: no commit found before {since!r}."

            rc, files_out, err = run_git(repo_root, ["diff", "--name-only", "--no-color", f"{base_commit}..HEAD", "--", "."])
            if rc != 0:
                return f"ERROR: failed to list changed files: {err.strip() or f'git exited {rc}'}"
            changed_files = [line.strip() for line in files_out.splitlines() if line.strip()]
            if len(changed_files) > policy.max_files:
                return _deny("too_many_files", max_files=policy.max_files, file_count=len(changed_files))

            rc, diff_out, err = run_git(
                repo_root,
                [
                    "diff",
                    "--no-color",
                    "--no-ext-diff",
                    "--unified",
                    str(context_lines),
                    f"{base_commit}..HEAD",
                    "--",
                    ".",
                ],
            )
            if rc != 0:
                return f"ERROR: failed to compute diff: {err.strip() or f'git exited {rc}'}"

            out = (
                f"BASE_COMMIT: {base_commit}\n"
                f"RANGE: {base_commit}..HEAD\n"
                f"SINCE: {since}\n"
                f"CHANGED_FILES_COUNT: {len(changed_files)}\n"
                f"CHANGED_FILES:\n{chr(10).join(changed_files) if changed_files else '(none)'}\n"
                f"DIFF:\n{diff_out}"
            )
        elif normalized_action == "log":
            ref = (arg1 or "HEAD").strip()
            count = (arg2 or "20").strip()
            ref_err = _validate_ref(ref, "ref")
            if ref_err:
                return ref_err
            if not count.isdigit():
                return "ERROR: max_count must be numeric."
            rc, out, err = run_git(repo_root, ["log", "--oneline", f"-n{count}", ref])
            if rc != 0:
                return f"ERROR: git log failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "diff":
            base = (arg1 or "").strip()
            head = (arg2 or "HEAD").strip()
            for ref_name, ref in [("base_ref", base), ("head_ref", head)]:
                ref_err = _validate_ref(ref, ref_name)
                if ref_err:
                    return ref_err
            rc, out, err = run_git(repo_root, ["diff", "--no-color", "--no-ext-diff", f"{base}..{head}", "--", "."])
            if rc != 0:
                return f"ERROR: git diff failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "show":
            ref = (arg1 or "HEAD").strip()
            ref_err = _validate_ref(ref, "ref")
            if ref_err:
                return ref_err
            rc, out, err = run_git(repo_root, ["show", "--no-color", ref])
            if rc != 0:
                return f"ERROR: git show failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "rev_parse":
            ref = (arg1 or "HEAD").strip()
            ref_err = _validate_ref(ref, "ref")
            if ref_err:
                return ref_err
            rc, out, err = run_git(repo_root, ["rev-parse", ref])
            if rc != 0:
                return f"ERROR: git rev-parse failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "status":
            rc, out, err = run_git(repo_root, ["status", "--short", "--branch"])
            if rc != 0:
                return f"ERROR: git status failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "create_branch":
            branch = (arg1 or "").strip()
            base = (arg2 or "HEAD").strip()
            if not branch:
                return "ERROR: branch name cannot be empty."
            if not safe_branch_regex.fullmatch(branch):
                return "ERROR: branch contains unsupported characters."
            branch = _prefixed_branch(branch)
            ref_err = _validate_ref(base, "base_ref")
            if ref_err:
                return ref_err
            rc, out, err = run_git(repo_root, ["checkout", "-b", branch, base])
            if rc != 0:
                return f"ERROR: create_branch failed: {err.strip() or f'git exited {rc}'}"
            out = out or f"Switched to new branch {branch!r}"
        elif normalized_action == "checkout":
            branch = _prefixed_branch((arg1 or "").strip())
            if not branch:
                return "ERROR: branch cannot be empty."
            if not safe_branch_regex.fullmatch(branch):
                return "ERROR: branch contains unsupported characters."
            rc, out, err = run_git(repo_root, ["checkout", branch])
            if rc != 0:
                return f"ERROR: checkout failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "commit":
            msg = (arg1 or "").strip()
            if not msg:
                return "ERROR: commit message cannot be empty."
            rc, out, err = run_git(repo_root, ["commit", "-m", msg])
            if rc != 0:
                return f"ERROR: commit failed: {err.strip() or f'git exited {rc}'}"
        elif normalized_action == "push":
            remote = (arg1 or "origin").strip()
            branch = (arg2 or "").strip()
            if not remote:
                return "ERROR: remote cannot be empty."
            if branch:
                if not safe_branch_regex.fullmatch(branch):
                    return "ERROR: branch contains unsupported characters."
            else:
                try:
                    branch = _current_branch()
                except RuntimeError as e:
                    return f"ERROR: {e}"
            branch = _prefixed_branch(branch)
            if policy.managed_branch_prefix and not _is_branch_allowed(branch):
                return _deny("branch_prefix_required", action=normalized_action, branch=branch)
            rc, out, err = run_git(repo_root, ["push", remote, branch])
            if rc != 0:
                return f"ERROR: push failed: {err.strip() or f'git exited {rc}'}"
        else:
            return f"ERROR: unsupported action {normalized_action!r}."

        truncated = False
        if len(out) > policy.max_output_chars:
            out = out[: policy.max_output_chars]
            truncated = True

        rt.after(
            logging.INFO,
            tool_name,
            status="ok",
            action=normalized_action,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            output_chars=len(out),
            truncated=truncated,
        )
        return out

    return git


SPEC = ToolSpec("git", GitToolPolicy, tool_constructor)
