import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError


class TemplateInputConfig(BaseModel):
    required: bool = True
    default: Any | None = None
    description: str = ""


class TaskTemplateConfig(BaseModel):
    description: str = ""
    inputs: dict[str, TemplateInputConfig] = {}
    template: str


class OllamaModelConfig(BaseModel):
    host: str
    model_id: str


class BedrockModelConfig(BaseModel):
    region: str
    model_id: str


class ModelConfig(BaseModel):
    ollama: OllamaModelConfig
    bedrock: BedrockModelConfig


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: Literal["text", "json"] = "text"
    max_field_chars: int = 400
    log_model_startup: bool = True
    log_prompt_metadata: bool = True
    log_tool_calls: bool = True
    log_tool_results: bool = True


class ProfileConfig(BaseModel):
    name: str
    description: str = ""
    backend: Literal["ollama", "bedrock"]
    model: ModelConfig
    system_prompt: str
    token_budget: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    task_templates: dict[str, TaskTemplateConfig] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_env_overrides(cfg: dict) -> dict:
    """Allow simple backend/model overrides without editing profile config files."""
    merged = dict(cfg or {})
    merged["model"] = dict(cfg.get("model") or {})
    merged["model"]["ollama"] = dict(merged["model"].get("ollama") or {})
    merged["model"]["bedrock"] = dict(merged["model"].get("bedrock") or {})

    backend = os.getenv("AGENT_BACKEND")
    if backend:
        merged["backend"] = backend

    ollama_host = os.getenv("AGENT_OLLAMA_HOST")
    if ollama_host:
        merged["model"]["ollama"]["host"] = ollama_host

    ollama_model_id = os.getenv("AGENT_OLLAMA_MODEL_ID")
    if ollama_model_id:
        merged["model"]["ollama"]["model_id"] = ollama_model_id

    bedrock_region = os.getenv("AGENT_BEDROCK_REGION")
    if bedrock_region:
        merged["model"]["bedrock"]["region"] = bedrock_region

    bedrock_model_id = os.getenv("AGENT_BEDROCK_MODEL_ID")
    if bedrock_model_id:
        merged["model"]["bedrock"]["model_id"] = bedrock_model_id

    log_level = os.getenv("AGENT_LOG_LEVEL")
    if log_level:
        merged["logging"] = dict(merged.get("logging") or {})
        merged["logging"]["level"] = log_level

    log_format = os.getenv("AGENT_LOG_FORMAT")
    if log_format:
        merged["logging"] = dict(merged.get("logging") or {})
        merged["logging"]["format"] = log_format

    return merged


def load_profile_config(path: Path) -> ProfileConfig:
    try:
        raw = load_config(path)
        return ProfileConfig.model_validate(apply_env_overrides(raw))
    except ValidationError:
        raise
