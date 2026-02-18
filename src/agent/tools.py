import logging
import time
from pathlib import Path
from typing import Any, Callable

from strands.tools import tool

from agent.config import LoggingConfig
from agent.observability import Observer


ToolBuilder = Callable[[Path, dict[str, Any], Observer, LoggingConfig], Any]


def _build_read_file_tool(repo_root: Path, _cfg: dict[str, Any], observer: Observer, log_cfg):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the repo and return its contents."""
        start = time.perf_counter()
        if log_cfg.log_tool_calls:
            observer.event(logging.INFO, "hook.tool.before", tool="read_file", path=path)
        p = _resolve_path(path)
        if not p.exists():
            if log_cfg.log_tool_results:
                observer.event(
                    logging.WARNING,
                    "hook.tool.after",
                    tool="read_file",
                    status="error",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    error="file_not_found",
                )
            return f"ERROR: file not found: {p}"
        if p.is_dir():
            if log_cfg.log_tool_results:
                observer.event(
                    logging.WARNING,
                    "hook.tool.after",
                    tool="read_file",
                    status="error",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    error="is_directory",
                )
            return f"ERROR: path is a directory: {p}"
        try:
            out = p.read_text(encoding="utf-8")
            if log_cfg.log_tool_results:
                observer.event(
                    logging.INFO,
                    "hook.tool.after",
                    tool="read_file",
                    status="ok",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    output_chars=len(out),
                )
            return out
        except Exception as e:
            if log_cfg.log_tool_results:
                observer.event(
                    logging.ERROR,
                    "hook.tool.after",
                    tool="read_file",
                    status="error",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    error=str(e),
                )
            return f"ERROR: failed to read {p}: {e}"

    return read_file


def _build_list_dir_tool(repo_root: Path, _cfg: dict[str, Any], observer: Observer, log_cfg):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and folders at a path (relative to repo root unless absolute)."""
        start = time.perf_counter()
        if log_cfg.log_tool_calls:
            observer.event(logging.INFO, "hook.tool.before", tool="list_dir", path=path)
        p = _resolve_path(path)
        if not p.exists():
            if log_cfg.log_tool_results:
                observer.event(
                    logging.WARNING,
                    "hook.tool.after",
                    tool="list_dir",
                    status="error",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    error="path_not_found",
                )
            return f"ERROR: path not found: {p}"
        if not p.is_dir():
            if log_cfg.log_tool_results:
                observer.event(
                    logging.WARNING,
                    "hook.tool.after",
                    tool="list_dir",
                    status="error",
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    error="not_directory",
                )
            return f"ERROR: not a directory: {p}"
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for x in items:
            suffix = "/" if x.is_dir() else ""
            lines.append(f"{x.name}{suffix}")
        out = "\n".join(lines) if lines else "(empty)"
        if log_cfg.log_tool_results:
            observer.event(
                logging.INFO,
                "hook.tool.after",
                tool="list_dir",
                status="ok",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                output_chars=len(out),
            )
        return out

    return list_dir


TOOL_REGISTRY: dict[str, ToolBuilder] = {
    "read_file": _build_read_file_tool,
    "list_dir": _build_list_dir_tool,
}


def build_tools(repo_root: Path, tool_configs: dict[str, dict[str, Any]], observer: Observer, log_cfg):
    # Current security model: profiles are trusted. Tool-level access controls
    # (before/after hooks, path policies, command restrictions) are planned.
    tools = []
    for tool_name, tool_cfg in tool_configs.items():
        builder = TOOL_REGISTRY.get(tool_name)
        if builder is None:
            raise ValueError(f"Unknown tool configured: {tool_name}")
        tools.append(builder(repo_root, tool_cfg or {}, observer, log_cfg))
    return tools
