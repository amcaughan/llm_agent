import logging
import time
from pathlib import Path

from strands.tools import tool

from .core import ToolPolicy, ToolRuntime, ToolSpec


class ListDirPolicy(ToolPolicy):
    pass


def tool_constructor(repo_root: Path, _policy: ToolPolicy, rt: ToolRuntime):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and folders at a path (relative to repo root unless absolute)."""
        start = time.perf_counter()
        rt.before("list_dir", path=path)
        p = _resolve_path(path)
        if not p.exists():
            rt.after(
                logging.WARNING,
                "list_dir",
                status="error",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                error="path_not_found",
            )
            return f"ERROR: path not found: {p}"
        if not p.is_dir():
            rt.after(
                logging.WARNING,
                "list_dir",
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
        rt.after(
            logging.INFO,
            "list_dir",
            status="ok",
            elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
            output_chars=len(out),
        )
        return out

    return list_dir


SPEC = ToolSpec("list_dir", ListDirPolicy, tool_constructor)
