import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
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

    def start(self, tool: str, **fields: Any) -> "ToolCallContext":
        self.before(tool, **fields)
        return ToolCallContext(runtime=self, tool=tool, base_fields=dict(fields))

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


@dataclass
class ToolCallContext:
    runtime: ToolRuntime
    tool: str
    base_fields: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.perf_counter)

    def policy_before(self, **fields: Any) -> None:
        merged = dict(self.base_fields)
        merged.update(fields)
        self.runtime.policy_before(self.tool, **merged)

    def ok(self, output: str, *, level: int = logging.INFO, **fields: Any) -> str:
        merged = dict(self.base_fields)
        merged.update(fields)
        self.runtime.after(
            level,
            self.tool,
            status="ok",
            elapsed_ms=round((time.perf_counter() - self.started) * 1000, 2),
            output_chars=len(output),
            **merged,
        )
        return output

    def error(
        self,
        message: str,
        *,
        reason: str = "tool_error",
        level: int = logging.ERROR,
        **fields: Any,
    ) -> str:
        merged = dict(self.base_fields)
        merged.update(fields)
        self.runtime.after(
            level,
            self.tool,
            status="error",
            reason=reason,
            error=message,
            elapsed_ms=round((time.perf_counter() - self.started) * 1000, 2),
            **merged,
        )
        return message

    def deny(
        self,
        reason: str,
        *,
        message: str | None = None,
        level: int = logging.WARNING,
        **fields: Any,
    ) -> str:
        merged = dict(self.base_fields)
        merged.update(fields)
        self.runtime.policy_deny(self.tool, reason, **merged)
        if message is None:
            message = f"ERROR: denied_by_policy reason={reason}"
        return self.error(message, reason=reason, level=level, **merged)


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
