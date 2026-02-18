import logging
import re
from pathlib import Path
from typing import Any

from pydantic import Field
from strands.tools import tool

from .core import ToolPolicy, ToolRuntime, ToolSpec, run_git


class GitToolPolicy(ToolPolicy):
    allowed_actions: list[str] = Field(
        default_factory=lambda: ["status", "log", "show", "rev_parse", "diff", "diff_since"]
    )
    managed_branch_prefix: str = ""
    enforce_prefix_for_writes: bool = True
    allow_push: bool = False
    allow_worktree_dirty: bool = False
    max_output_chars: int = 60000
    max_files: int = 200
    max_since_chars: int = 64
    allowed_ref_pattern: str = r"^[A-Za-z0-9_./\-~^:@]+$"
    context_lines: int = 3


def tool_constructor(repo_root: Path, policy: ToolPolicy, rt: ToolRuntime):
    assert isinstance(policy, GitToolPolicy)
    tool_name = "git"

    since_regex = re.compile(r"^[A-Za-z0-9_:+\-.,/ ]+$")
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
        normalized_action = (action or "").strip().lower()
        ctx = rt.start(tool_name, action=normalized_action, arg1=arg1, arg2=arg2)

        def _deny_action(reason: str, **fields: Any) -> str:
            return ctx.deny(
                reason,
                message=f"ERROR: denied_by_policy reason={reason} policy={_policy_snapshot()}",
                level=logging.WARNING,
                policy=_policy_snapshot(),
                **fields,
            )

        def _error(message: str, *, reason: str = "tool_error", level: int = logging.ERROR) -> str:
            return ctx.error(message, reason=reason, level=level)

        ctx.policy_before()

        try:
            if normalized_action not in allowed_actions:
                return _deny_action("action_not_allowed", action=normalized_action)

            if normalized_action == "push" and not policy.allow_push:
                return _deny_action("push_not_allowed", action=normalized_action)

            if policy.enforce_prefix_for_writes and policy.managed_branch_prefix and normalized_action in write_like_actions:
                try:
                    current = _current_branch()
                except RuntimeError as e:
                    return _error(f"ERROR: {e}", reason="branch_resolution_failed")
                if not _is_branch_allowed(current):
                    return _deny_action(
                        "branch_prefix_required",
                        action=normalized_action,
                        current_branch=current,
                        required_prefix=policy.managed_branch_prefix,
                    )

            if normalized_action in write_actions and not policy.allow_worktree_dirty:
                rc, out, err = run_git(repo_root, ["status", "--porcelain"])
                if rc != 0:
                    return _error(
                        f"ERROR: failed to inspect worktree: {err.strip() or f'git exited {rc}'}",
                        reason="worktree_inspection_failed",
                    )
                if out.strip():
                    return _deny_action("dirty_worktree", action=normalized_action)

            if normalized_action == "diff_since":
                since = (arg1 or "").strip()
                if not since:
                    return _deny_action("empty_since", action=normalized_action)
                if len(since) > policy.max_since_chars:
                    return _deny_action("since_too_long", max_since_chars=policy.max_since_chars)
                if not since_regex.fullmatch(since):
                    return _deny_action("invalid_since_format")

                rc, base_commit, err = run_git(repo_root, ["rev-list", "-1", f"--before={since}", "HEAD"])
                if rc != 0:
                    return _error(
                        f"ERROR: failed to resolve commit for since={since!r}: {err.strip() or f'git exited {rc}'}",
                        reason="base_commit_resolution_failed",
                    )
                base_commit = base_commit.strip()
                if not base_commit:
                    return _error(f"ERROR: no commit found before {since!r}.", reason="no_commit_before_since")

                rc, files_out, err = run_git(
                    repo_root, ["diff", "--name-only", "--no-color", f"{base_commit}..HEAD", "--", "."]
                )
                if rc != 0:
                    return _error(
                        f"ERROR: failed to list changed files: {err.strip() or f'git exited {rc}'}",
                        reason="changed_files_listing_failed",
                    )
                changed_files = [line.strip() for line in files_out.splitlines() if line.strip()]
                if len(changed_files) > policy.max_files:
                    return _deny_action("too_many_files", max_files=policy.max_files, file_count=len(changed_files))

                rc, diff_out, err = run_git(
                    repo_root,
                    [
                        "diff",
                        "--no-color",
                        "--no-ext-diff",
                        f"--unified={context_lines}",
                        f"{base_commit}..HEAD",
                        "--",
                        ".",
                    ],
                )
                if rc != 0:
                    return _error(
                        f"ERROR: failed to compute diff: {err.strip() or f'git exited {rc}'}",
                        reason="diff_generation_failed",
                    )

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
                    return _error(ref_err, reason="invalid_ref")
                if not count.isdigit():
                    return _error("ERROR: max_count must be numeric.", reason="invalid_max_count")
                rc, out, err = run_git(repo_root, ["log", "--oneline", f"-n{count}", ref])
                if rc != 0:
                    return _error(f"ERROR: git log failed: {err.strip() or f'git exited {rc}'}", reason="git_log_failed")
            elif normalized_action == "diff":
                base = (arg1 or "").strip()
                head = (arg2 or "HEAD").strip()
                for ref_name, ref in [("base_ref", base), ("head_ref", head)]:
                    ref_err = _validate_ref(ref, ref_name)
                    if ref_err:
                        return _error(ref_err, reason="invalid_ref")
                rc, out, err = run_git(repo_root, ["diff", "--no-color", "--no-ext-diff", f"{base}..{head}", "--", "."])
                if rc != 0:
                    return _error(f"ERROR: git diff failed: {err.strip() or f'git exited {rc}'}", reason="git_diff_failed")
            elif normalized_action == "show":
                ref = (arg1 or "HEAD").strip()
                ref_err = _validate_ref(ref, "ref")
                if ref_err:
                    return _error(ref_err, reason="invalid_ref")
                rc, out, err = run_git(repo_root, ["show", "--no-color", ref])
                if rc != 0:
                    return _error(f"ERROR: git show failed: {err.strip() or f'git exited {rc}'}", reason="git_show_failed")
            elif normalized_action == "rev_parse":
                ref = (arg1 or "HEAD").strip()
                ref_err = _validate_ref(ref, "ref")
                if ref_err:
                    return _error(ref_err, reason="invalid_ref")
                rc, out, err = run_git(repo_root, ["rev-parse", ref])
                if rc != 0:
                    return _error(
                        f"ERROR: git rev-parse failed: {err.strip() or f'git exited {rc}'}",
                        reason="git_rev_parse_failed",
                    )
            elif normalized_action == "status":
                rc, out, err = run_git(repo_root, ["status", "--short", "--branch"])
                if rc != 0:
                    return _error(
                        f"ERROR: git status failed: {err.strip() or f'git exited {rc}'}", reason="git_status_failed"
                    )
            elif normalized_action == "create_branch":
                branch = (arg1 or "").strip()
                base = (arg2 or "HEAD").strip()
                if not branch:
                    return _error("ERROR: branch name cannot be empty.", reason="empty_branch")
                if not safe_branch_regex.fullmatch(branch):
                    return _error("ERROR: branch contains unsupported characters.", reason="invalid_branch")
                branch = _prefixed_branch(branch)
                ref_err = _validate_ref(base, "base_ref")
                if ref_err:
                    return _error(ref_err, reason="invalid_ref")
                rc, out, err = run_git(repo_root, ["checkout", "-b", branch, base])
                if rc != 0:
                    return _error(
                        f"ERROR: create_branch failed: {err.strip() or f'git exited {rc}'}",
                        reason="git_create_branch_failed",
                    )
                out = out or f"Switched to new branch {branch!r}"
            elif normalized_action == "checkout":
                branch = _prefixed_branch((arg1 or "").strip())
                if not branch:
                    return _error("ERROR: branch cannot be empty.", reason="empty_branch")
                if not safe_branch_regex.fullmatch(branch):
                    return _error("ERROR: branch contains unsupported characters.", reason="invalid_branch")
                rc, out, err = run_git(repo_root, ["checkout", branch])
                if rc != 0:
                    return _error(
                        f"ERROR: checkout failed: {err.strip() or f'git exited {rc}'}", reason="git_checkout_failed"
                    )
            elif normalized_action == "commit":
                msg = (arg1 or "").strip()
                if not msg:
                    return _error("ERROR: commit message cannot be empty.", reason="empty_commit_message")
                rc, out, err = run_git(repo_root, ["commit", "-m", msg])
                if rc != 0:
                    return _error(f"ERROR: commit failed: {err.strip() or f'git exited {rc}'}", reason="git_commit_failed")
            elif normalized_action == "push":
                remote = (arg1 or "origin").strip()
                branch = (arg2 or "").strip()
                if not remote:
                    return _error("ERROR: remote cannot be empty.", reason="empty_remote")
                if branch:
                    if not safe_branch_regex.fullmatch(branch):
                        return _error("ERROR: branch contains unsupported characters.", reason="invalid_branch")
                else:
                    try:
                        branch = _current_branch()
                    except RuntimeError as e:
                        return _error(f"ERROR: {e}", reason="branch_resolution_failed")
                branch = _prefixed_branch(branch)
                if policy.managed_branch_prefix and not _is_branch_allowed(branch):
                    return _deny_action("branch_prefix_required", action=normalized_action, branch=branch)
                rc, out, err = run_git(repo_root, ["push", remote, branch])
                if rc != 0:
                    return _error(f"ERROR: push failed: {err.strip() or f'git exited {rc}'}", reason="git_push_failed")
            else:
                return _error(f"ERROR: unsupported action {normalized_action!r}.", reason="unsupported_action")
        except Exception as e:  # pragma: no cover - defensive logging path
            return _error(f"ERROR: unexpected git tool failure: {e}", reason="unexpected_exception")

        truncated = False
        if len(out) > policy.max_output_chars:
            out = out[: policy.max_output_chars]
            truncated = True

        return ctx.ok(out, truncated=truncated)

    return git


SPEC = ToolSpec("git", GitToolPolicy, tool_constructor)
