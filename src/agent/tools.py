from pathlib import Path
from typing import Any, Callable

from strands.tools import tool


ToolBuilder = Callable[[Path, dict[str, Any]], Any]


def _build_read_file_tool(repo_root: Path, _cfg: dict[str, Any]):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the repo and return its contents."""
        p = _resolve_path(path)
        if not p.exists():
            return f"ERROR: file not found: {p}"
        if p.is_dir():
            return f"ERROR: path is a directory: {p}"
        try:
            return p.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR: failed to read {p}: {e}"

    return read_file


def _build_list_dir_tool(repo_root: Path, _cfg: dict[str, Any]):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and folders at a path (relative to repo root unless absolute)."""
        p = _resolve_path(path)
        if not p.exists():
            return f"ERROR: path not found: {p}"
        if not p.is_dir():
            return f"ERROR: not a directory: {p}"
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for x in items:
            suffix = "/" if x.is_dir() else ""
            lines.append(f"{x.name}{suffix}")
        return "\n".join(lines) if lines else "(empty)"

    return list_dir


TOOL_REGISTRY: dict[str, ToolBuilder] = {
    "read_file": _build_read_file_tool,
    "list_dir": _build_list_dir_tool,
}


def build_tools(repo_root: Path, tool_configs: dict[str, dict[str, Any]]):
    tools = []
    for tool_name, tool_cfg in tool_configs.items():
        builder = TOOL_REGISTRY.get(tool_name)
        if builder is None:
            raise ValueError(f"Unknown tool configured: {tool_name}")
        tools.append(builder(repo_root, tool_cfg or {}))
    return tools
