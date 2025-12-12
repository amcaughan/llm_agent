from __future__ import annotations

import sys
from pathlib import Path
import yaml

def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r") as f:
        return yaml.safe_load(f)

def find_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()

    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("Could not find repo root (pyproject.toml not found)")


def main() -> int:
    cfg = load_config(find_repo_root() / "config" / "agent.yml")

    if cfg["backend"] != "ollama":
        raise ValueError("Smoke test expects backend=ollama")

    ollama_cfg = cfg["ollama"]
    host = ollama_cfg["host"]
    model_id = ollama_cfg["model_id"]

    import requests
    r = requests.get(f"{host}/api/tags", timeout=5)
    r.raise_for_status()

    print("[OK] Ollama reachable")

    from strands import Agent
    from strands.models.ollama import OllamaModel

    model = OllamaModel(host=host, model_id=model_id)

    agent = Agent(
        model=model,
        system_prompt=cfg["agent"]["system_prompt"],
    )

    out = agent("Reply with exactly: OK")
    print()
    print("Agent output:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
