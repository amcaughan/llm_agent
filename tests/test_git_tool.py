import subprocess
import os
from pathlib import Path

from agent.config import LoggingConfig
from agent.observability import configure_observer
from agent.tools import build_tools


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(cmd, cwd=cwd, check=True, env=merged_env)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)

    a = repo / "a.txt"
    a.write_text("v1\n", encoding="utf-8")
    _run(["git", "add", "a.txt"], cwd=repo)
    env1 = {
        "GIT_AUTHOR_DATE": "2024-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2024-01-01T00:00:00Z",
    }
    _run(["git", "commit", "-m", "first"], cwd=repo, env=env1)

    a.write_text("v2\n", encoding="utf-8")
    _run(["git", "add", "a.txt"], cwd=repo)
    env2 = {
        "GIT_AUTHOR_DATE": "2024-01-02T00:00:00Z",
        "GIT_COMMITTER_DATE": "2024-01-02T00:00:00Z",
    }
    _run(["git", "commit", "-m", "second"], cwd=repo, env=env2)
    return repo


def _build_git(repo_root: Path, cfg: dict | None = None):
    observer = configure_observer("ERROR", "text", 400)
    tools = build_tools(
        repo_root=repo_root,
        tool_configs={"git": cfg or {}},
        observer=observer,
        log_cfg=LoggingConfig(level="ERROR", log_tool_calls=False, log_tool_results=False),
    )
    return tools[0]


def test_git_diff_since_happy_path(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_tool = _build_git(repo)
    out = git_tool("diff_since", "2024-01-01 12:00")
    assert "BASE_COMMIT:" in out
    assert "CHANGED_FILES_COUNT: 1" in out
    assert "a.txt" in out
    assert "DIFF:" in out


def test_git_diff_since_rejects_bad_chars(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_tool = _build_git(repo)
    out = git_tool("diff_since", "1 day ago; rm -rf /")
    assert out.startswith("ERROR:")
    assert "denied_by_policy" in out
    assert "since_pattern_mismatch" in out


def test_git_diff_since_respects_max_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_tool = _build_git(repo, cfg={"max_files": 0})
    out = git_tool("diff_since", "2024-01-01 12:00")
    assert out.startswith("ERROR:")
    assert "denied_by_policy" in out
    assert "too_many_files" in out


def test_git_action_allowlist_is_enforced(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_tool = _build_git(repo, cfg={"allowed_actions": ["log"]})
    out = git_tool("diff_since", "2024-01-01 12:00")
    assert out.startswith("ERROR:")
    assert "denied_by_policy" in out
    assert "action_not_allowed" in out
