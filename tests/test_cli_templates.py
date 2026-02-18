import argparse

import pytest

from agent.cli import get_template_prompt, resolve_prompt
from agent.config import ProfileConfig


def _cfg() -> ProfileConfig:
    return ProfileConfig.model_validate(
        {
            "name": "test",
            "backend": "ollama",
            "model": {
                "ollama": {"host": "http://127.0.0.1:11434", "model_id": "x"},
                "bedrock": {"region": "us-east-2", "model_id": "y"},
            },
            "system_prompt": "test",
            "task_templates": {
                "example": {
                    "inputs": {
                        "repo": {"required": True, "description": "repo"},
                        "issue": {"required": False, "default": "n/a", "description": "issue"},
                    },
                    "template": "repo={repo} issue={issue}",
                }
            },
        }
    )


def test_get_template_prompt_happy_path() -> None:
    cfg = _cfg()
    out = get_template_prompt(cfg, "example", [["repo", "llm_agent"]])
    assert out == "repo=llm_agent issue=n/a"


def test_get_template_prompt_unknown_input_fails() -> None:
    cfg = _cfg()
    with pytest.raises(ValueError, match="Unknown template input key"):
        get_template_prompt(cfg, "example", [["bad", "value"]])


def test_get_template_prompt_missing_required_fails() -> None:
    cfg = _cfg()
    with pytest.raises(ValueError, match="Missing required template input"):
        get_template_prompt(cfg, "example", [])


def test_resolve_prompt_template_rejects_raw_prompt() -> None:
    cfg = _cfg()
    args = argparse.Namespace(template="example", input=[["repo", "llm_agent"]], prompt=["raw"])
    with pytest.raises(ValueError, match="Do not pass a raw prompt"):
        resolve_prompt(cfg, args)

