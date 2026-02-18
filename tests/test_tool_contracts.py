import os
import subprocess
from pathlib import Path

from agent.config import LoggingConfig
from agent.tools import build_tools


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def event(self, _level: int, name: str, **fields: object) -> None:
        payload = {"event": name}
        payload.update(fields)
        self.events.append(payload)


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
    (repo / "a.txt").write_text("v1\n", encoding="utf-8")
    _run(["git", "add", "a.txt"], cwd=repo)
    _run(["git", "commit", "-m", "first"], cwd=repo)
    return repo


def _build_single_tool(repo_root: Path, tool_name: str, cfg: dict):
    observer = RecordingObserver()
    tools = build_tools(
        repo_root=repo_root,
        tool_configs={tool_name: cfg},
        observer=observer,  # type: ignore[arg-type]
        log_cfg=LoggingConfig(level="INFO", log_tool_calls=True, log_tool_results=True),
    )
    return tools[0], observer


def _events(observer: RecordingObserver, event_name: str) -> list[dict]:
    return [e for e in observer.events if e["event"] == event_name]


def test_list_dir_contract_success(tmp_path: Path) -> None:
    list_dir, obs = _build_single_tool(tmp_path, "list_dir", {})
    out = list_dir(".")
    assert isinstance(out, str)

    before = _events(obs, "hook.tool.before")
    after = _events(obs, "hook.tool.after")
    assert before and before[0]["tool"] == "list_dir"
    assert after and after[0]["tool"] == "list_dir"
    assert after[0]["status"] == "ok"


def test_list_dir_contract_error(tmp_path: Path) -> None:
    list_dir, obs = _build_single_tool(tmp_path, "list_dir", {})
    out = list_dir("does-not-exist")
    assert out.startswith("ERROR:")

    after = _events(obs, "hook.tool.after")
    assert after and after[0]["status"] == "error"
    assert after[0]["reason"] == "path_not_found"


def test_git_contract_deny_emits_policy_and_after(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    git_tool, obs = _build_single_tool(repo, "git", {"allowed_actions": ["status"]})
    out = git_tool("diff_since", "1 hour ago")
    assert "denied_by_policy" in out
    assert "action_not_allowed" in out

    names = [e["event"] for e in obs.events]
    assert "hook.tool.before" in names
    assert "hook.policy.before" in names
    assert "hook.policy.deny" in names
    assert "hook.tool.after" in names

    deny = _events(obs, "hook.policy.deny")[0]
    after = _events(obs, "hook.tool.after")[0]
    assert deny["reason"] == "action_not_allowed"
    assert after["status"] == "error"
    assert after["reason"] == "action_not_allowed"

