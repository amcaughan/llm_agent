import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from strands import Agent

from agent.backends import build_model
from agent.config import ProfileConfig, TaskTemplateConfig, load_profile_config
from agent.observability import configure_observer
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
    parser.add_argument(
        "--template",
        help="Task template name from the selected profile",
    )
    parser.add_argument(
        "--input",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        default=[],
        help="Template input key/value pair (repeatable)",
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


def _coerce_template_inputs(pairs: list[list[str]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        key, value = pair
        values[key] = value
    return values


def _render_template(template_cfg: TaskTemplateConfig, values: dict[str, Any]) -> str:
    try:
        return template_cfg.template.format(**values).strip()
    except KeyError as e:
        missing = e.args[0]
        raise ValueError(f"Template references undefined input key {missing!r}") from e
    except ValueError as e:
        raise ValueError(f"Invalid template format string: {e}") from e


def get_template_prompt(cfg: ProfileConfig, template_name: str, input_pairs: list[list[str]]) -> str:
    template_cfg = cfg.task_templates.get(template_name)
    if template_cfg is None:
        available = ", ".join(sorted(cfg.task_templates.keys())) or "(none)"
        raise ValueError(f"Unknown template {template_name!r}. Available templates: {available}")

    provided = _coerce_template_inputs(input_pairs)
    unknown = sorted(set(provided.keys()) - set(template_cfg.inputs.keys()))
    if unknown:
        raise ValueError(f"Unknown template input key(s): {', '.join(unknown)}")

    resolved: dict[str, Any] = {}
    for key, input_cfg in template_cfg.inputs.items():
        if key in provided:
            resolved[key] = provided[key]
            continue
        if input_cfg.default is not None:
            resolved[key] = input_cfg.default
            continue
        if input_cfg.required:
            raise ValueError(f"Missing required template input {key!r}")
        resolved[key] = ""

    return _render_template(template_cfg, resolved)


def resolve_prompt(cfg: ProfileConfig, args: argparse.Namespace) -> tuple[str, str]:
    if args.template:
        if args.prompt:
            raise ValueError("Do not pass a raw prompt when --template is set")
        return get_template_prompt(cfg, args.template, args.input), "template"

    if args.input:
        raise ValueError("--input can only be used with --template")

    return get_prompt(args.prompt), "raw"


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

    observer = configure_observer(
        level_name=cfg.logging.level,
        log_format=cfg.logging.format,
        max_field_chars=cfg.logging.max_field_chars,
    )

    if cfg.logging.log_model_startup:
        model_id = cfg.model.ollama.model_id if cfg.backend == "ollama" else cfg.model.bedrock.model_id
        observer.event(
            logging.INFO,
            "agent.startup",
            profile=cfg.name,
            backend=cfg.backend,
            model_id=model_id,
            tool_count=len(cfg.tools),
        )

    try:
        build_start = time.perf_counter()
        model = build_model(cfg)
        tools = build_tools(repo_root, cfg.tools, observer, cfg.logging)
        if cfg.logging.log_model_startup:
            observer.event(
                logging.INFO,
                "agent.ready",
                profile=cfg.name,
                backend=cfg.backend,
                elapsed_ms=round((time.perf_counter() - build_start) * 1000, 2),
            )
    except (KeyError, ValueError) as e:
        observer.event(logging.ERROR, "agent.setup.error", profile=cfg.name, error=str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    agent = Agent(
        model=model,
        system_prompt=cfg.system_prompt,
        tools=tools,
    )

    try:
        prompt, prompt_source = resolve_prompt(cfg, args)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr)
        return 2

    if cfg.logging.log_prompt_metadata:
        observer.event(
            logging.INFO,
            "agent.prompt.received",
            profile=cfg.name,
            prompt_chars=len(prompt),
            from_stdin=(prompt_source == "raw" and len(args.prompt) == 0),
            prompt_source=prompt_source,
            template=args.template or "",
        )

    invoke_start = time.perf_counter()
    out = agent(prompt)
    observer.event(
        logging.INFO,
        "agent.run.complete",
        profile=cfg.name,
        elapsed_ms=round((time.perf_counter() - invoke_start) * 1000, 2),
        output_chars=len(str(out)),
    )
    if os.getenv("AGENT_SUPPRESS_FINAL_PRINT") != "1":
        print(out)
    return 0
