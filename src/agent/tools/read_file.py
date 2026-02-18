import logging
import time
from pathlib import Path

from strands.tools import tool

from .core import ToolPolicy, ToolRuntime, ToolSpec


class ReadFilePolicy(ToolPolicy):
    pass


def tool_constructor(repo_root: Path, _policy: ToolPolicy, rt: ToolRuntime):
    def _resolve_path(p: str) -> Path:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        return path

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the repo and return its contents."""
        start = time.perf_counter()
        rt.before("read_file", path=path)
        p = _resolve_path(path)
        if not p.exists():
            rt.after(
                logging.WARNING,
                "read_file",
                status="error",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                error="file_not_found",
            )
            return f"ERROR: file not found: {p}"
        if p.is_dir():
            rt.after(
                logging.WARNING,
                "read_file",
                status="error",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                error="is_directory",
            )
            return f"ERROR: path is a directory: {p}"
        try:
            out = p.read_text(encoding="utf-8")
            rt.after(
                logging.INFO,
                "read_file",
                status="ok",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                output_chars=len(out),
            )
            return out
        except Exception as e:
            rt.after(
                logging.ERROR,
                "read_file",
                status="error",
                elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                error=str(e),
            )
            return f"ERROR: failed to read {p}: {e}"

    return read_file


SPEC = ToolSpec("read_file", ReadFilePolicy, tool_constructor)
