import sys
from pathlib import Path
import yaml
from strands.tools import tool
import requests
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.models.bedrock import BedrockModel

def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find repo root (pyproject.toml not found)")


def get_prompt(argv: list[str]) -> str:
    # Usage:
    #   python -m agent "hello"
    #   echo "hello" | python -m agent
    if len(argv) > 1:
        return " ".join(argv[1:]).strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    print("Enter prompt, then press Ctrl-D:")
    return sys.stdin.read().strip()


def main() -> int:
    repo_root = find_repo_root()
    cfg = load_config(repo_root / "config" / "agent.yml")
    backend = (cfg.get("backend") or "").strip().lower()
    if backend not in ("ollama", "bedrock"):
        raise ValueError(f"Error: Unsupported backend: {backend}. Only 'bedrock' and 'ollama' supported")

    if backend == 'ollama':
        ollama_cfg = cfg["ollama"]
        host = ollama_cfg["host"]
        model_id = ollama_cfg["model_id"]    
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        model = OllamaModel(host=host, model_id=model_id)
    elif backend == 'bedrock':
        bedrock_cfg = cfg["bedrock"]
        region = bedrock_cfg["region"]
        model_id = bedrock_cfg["model_id"]
        model = BedrockModel(model_id=model_id, region_name=region)
    else:
        raise Exception("Backend model loading error")

    # ---- Tools ----
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

    tools = [read_file, list_dir]

    
    agent = Agent(
        model=model,
        system_prompt=cfg["agent"]["system_prompt"],
        tools=tools,
    )

    prompt = get_prompt(sys.argv)
    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr)
        return 2

    out = agent(prompt)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
