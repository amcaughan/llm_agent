import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ValidationError


class TemplateInputConfig(BaseModel):
    required: bool = True
    default: Any | None = None
    description: str = ""


class TaskTemplateConfig(BaseModel):
    description: str = ""
    inputs: dict[str, TemplateInputConfig] = {}
    template: str


class ProfileConfig(BaseModel):
    name: str
    description: str = ""
    backend: Literal["ollama", "bedrock"]
    model: dict[str, Any]
    system_prompt: str
    token_budget: dict[str, Any] = {}
    tools: dict[str, dict[str, Any]] = {}
    task_templates: dict[str, TaskTemplateConfig] = {}


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_model_map(cfg: dict, backend: str) -> dict:
    model = cfg.get("model")
    if isinstance(model, dict):
        nested = model.get(backend)
        if isinstance(nested, dict):
            return nested
        return model
    cfg["model"] = {}
    return cfg["model"]


def apply_env_overrides(cfg: dict) -> dict:
    """Allow simple backend/model overrides without editing profile config files."""
    merged = dict(cfg)
    merged["model"] = dict(cfg.get("model") or {})

    backend = os.getenv("AGENT_BACKEND")
    if backend:
        merged["backend"] = backend

    active_backend = merged.get("backend", "bedrock")
    model_map = _get_model_map(merged, active_backend)

    ollama_host = os.getenv("AGENT_OLLAMA_HOST")
    if ollama_host:
        if isinstance(merged.get("model", {}).get("ollama"), dict):
            merged["model"]["ollama"]["host"] = ollama_host
        else:
            model_map["host"] = ollama_host

    ollama_model_id = os.getenv("AGENT_OLLAMA_MODEL_ID")
    if ollama_model_id:
        if isinstance(merged.get("model", {}).get("ollama"), dict):
            merged["model"]["ollama"]["model_id"] = ollama_model_id
        else:
            model_map["model_id"] = ollama_model_id

    bedrock_region = os.getenv("AGENT_BEDROCK_REGION")
    if bedrock_region:
        if isinstance(merged.get("model", {}).get("bedrock"), dict):
            merged["model"]["bedrock"]["region"] = bedrock_region
        else:
            model_map["region"] = bedrock_region

    bedrock_model_id = os.getenv("AGENT_BEDROCK_MODEL_ID")
    if bedrock_model_id:
        if isinstance(merged.get("model", {}).get("bedrock"), dict):
            merged["model"]["bedrock"]["model_id"] = bedrock_model_id
        else:
            model_map["model_id"] = bedrock_model_id

    return merged


def load_profile_config(path: Path) -> ProfileConfig:
    try:
        raw = load_config(path)
        return ProfileConfig.model_validate(apply_env_overrides(raw))
    except ValidationError:
        raise
