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
        ctx = rt.start("read_file", path=path)
        p = _resolve_path(path)
        if not p.exists():
            return ctx.error(f"ERROR: file not found: {p}", reason="file_not_found")
        if p.is_dir():
            return ctx.error(f"ERROR: path is a directory: {p}", reason="is_directory")
        try:
            out = p.read_text(encoding="utf-8")
            return ctx.ok(out)
        except Exception as e:
            return ctx.error(f"ERROR: failed to read {p}: {e}", reason="read_failure")

    return read_file


SPEC = ToolSpec("read_file", ReadFilePolicy, tool_constructor)
