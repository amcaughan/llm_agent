import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from agent.config import LoggingConfig
from agent.observability import Observer


class ToolPolicy(BaseModel):
    """Base class for policy models consumed by tool builders."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    policy_model: type[ToolPolicy]
    build: Callable[[Path, ToolPolicy, "ToolRuntime"], Any]


@dataclass(frozen=True)
class ToolRuntime:
    observer: Observer
    log_cfg: LoggingConfig

    def before(self, tool: str, **fields: Any) -> None:
        if self.log_cfg.log_tool_calls:
            self.observer.event(logging.INFO, "hook.tool.before", tool=tool, **fields)

    def policy_before(self, tool: str, **fields: Any) -> None:
        if self.log_cfg.log_tool_calls:
            self.observer.event(logging.INFO, "hook.policy.before", tool=tool, **fields)

    def after(self, level: int, tool: str, **fields: Any) -> None:
        if self.log_cfg.log_tool_results:
            self.observer.event(level, "hook.tool.after", tool=tool, **fields)

    def policy_deny(self, tool: str, reason: str, **fields: Any) -> None:
        if self.log_cfg.log_tool_results:
            self.observer.event(logging.WARNING, "hook.policy.deny", tool=tool, reason=reason, **fields)


def run_git(repo_root: Path, args: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    env["GIT_PAGER"] = "cat"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def build_tools(
    repo_root: Path,
    tool_configs: dict[str, dict[str, Any]],
    observer: Observer,
    log_cfg: LoggingConfig,
    specs: dict[str, ToolSpec],
):
    rt = ToolRuntime(observer=observer, log_cfg=log_cfg)
    tools = []
    for tool_name, raw_cfg in tool_configs.items():
        spec = specs.get(tool_name)
        if spec is None:
            raise ValueError(f"Unknown tool configured: {tool_name}")
        try:
            policy = spec.policy_model.model_validate(raw_cfg or {})
        except ValidationError as e:
            raise ValueError(f"Invalid policy for tool {tool_name!r}: {e}") from e
        tools.append(spec.build(repo_root, policy, rt))
    return tools
