from pathlib import Path
from typing import Any

from agent.config import LoggingConfig
from agent.observability import Observer

from .core import build_tools as build_tools_with_specs
from .registry import TOOL_SPECS


def build_tools(
    repo_root: Path,
    tool_configs: dict[str, dict[str, Any]],
    observer: Observer,
    log_cfg: LoggingConfig,
):
    return build_tools_with_specs(
        repo_root=repo_root,
        tool_configs=tool_configs,
        observer=observer,
        log_cfg=log_cfg,
        specs=TOOL_SPECS,
    )
