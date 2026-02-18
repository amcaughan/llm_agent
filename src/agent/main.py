import sys
from pathlib import Path
import yaml
from strands.tools import tool
import requests
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.models.bedrock import BedrockModel
import os
from typing import Literal
from pydantic import BaseModel, ValidationError


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class OllamaConfig(BaseModel):
    host: str
    model_id: str


class BedrockConfig(BaseModel):
    region: str
    model_id: str


class AgentConfig(BaseModel):
    system_prompt: str


class AppConfig(BaseModel):
    backend: Literal["ollama", "bedrock"]
    ollama: OllamaConfig
    bedrock: BedrockConfig
    agent: AgentConfig


def apply_env_overrides(cfg: dict) -> dict:
    """Allow simple backend/model overrides without editing config files."""
    merged = dict(cfg)
    merged["ollama"] = dict(cfg.get("ollama") or {})
    merged["bedrock"] = dict(cfg.get("bedrock") or {})

    backend = os.getenv("AGENT_BACKEND")
    if backend:
        merged["backend"] = backend

    ollama_host = os.getenv("AGENT_OLLAMA_HOST")
    if ollama_host:
        merged["ollama"]["host"] = ollama_host

    ollama_model_id = os.getenv("AGENT_OLLAMA_MODEL_ID")
    if ollama_model_id:
        merged["ollama"]["model_id"] = ollama_model_id

    bedrock_region = os.getenv("AGENT_BEDROCK_REGION")
    if bedrock_region:
        merged["bedrock"]["region"] = bedrock_region

    bedrock_model_id = os.getenv("AGENT_BEDROCK_MODEL_ID")
    if bedrock_model_id:
        merged["bedrock"]["model_id"] = bedrock_model_id

    return merged


def find_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find repo root (pyproject.toml not found)")


def get_prompt(argv: list[str]) -> str:
    # Usage:
    #   uv run -m agent "hello"
    #   echo "hello" | uv run -m agent
    if len(argv) > 1:
        return " ".join(argv[1:]).strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    print("Enter prompt, then press Ctrl-D:")
    return sys.stdin.read().strip()


def main() -> int:
    repo_root = find_repo_root()
    try:
        cfg = AppConfig.model_validate(
            apply_env_overrides(load_config(repo_root / "config" / "agent.yml"))
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValidationError as e:
        print("ERROR: invalid config/agent.yml", file=sys.stderr)
        print(e, file=sys.stderr)
        return 2

    backend = cfg.backend

    if backend == 'ollama':
        host = cfg.ollama.host
        model_id = cfg.ollama.model_id
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        model = OllamaModel(host=host, model_id=model_id)
    else:
        region = cfg.bedrock.region
        model_id = cfg.bedrock.model_id
        model = BedrockModel(model_id=model_id, region_name=region)

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
        system_prompt=cfg.agent.system_prompt,
        tools=tools,
    )

    prompt = get_prompt(sys.argv)
    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr)
        return 2

    out = agent(prompt)
    if os.getenv("AGENT_SUPPRESS_FINAL_PRINT") != "1":
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
