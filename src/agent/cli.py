import argparse
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from strands import Agent

from agent.backends import build_model
from agent.config import load_profile_config
from agent.tools import build_tools


def find_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find repo root (pyproject.toml not found)")


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(prog="agent")
    parser.add_argument(
        "--profile",
        default="default",
        help="Profile name under config/profiles (default: default)",
    )
    parser.add_argument("prompt", nargs="*", help="Prompt text")
    return parser.parse_args(argv)


def get_prompt(prompt_tokens: list[str]) -> str:
    # Usage:
    #   uv run agent --profile default "hello"
    #   echo "hello" | uv run agent --profile default
    if prompt_tokens:
        return " ".join(prompt_tokens).strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    print("Enter prompt, then press Ctrl-D:")
    return sys.stdin.read().strip()


def run(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    args = parse_args(argv[1:])
    repo_root = find_repo_root()
    config_path = repo_root / "config" / "profiles" / f"{args.profile}.yml"
    try:
        cfg = load_profile_config(config_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValidationError as e:
        print(f"ERROR: invalid config/profiles/{args.profile}.yml", file=sys.stderr)
        print(e, file=sys.stderr)
        return 2

    try:
        model = build_model(cfg)
        tools = build_tools(repo_root, cfg.tools)
    except (KeyError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    agent = Agent(
        model=model,
        system_prompt=cfg.system_prompt,
        tools=tools,
    )

    prompt = get_prompt(args.prompt)
    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr)
        return 2

    out = agent(prompt)
    if os.getenv("AGENT_SUPPRESS_FINAL_PRINT") != "1":
        print(out)
    return 0
