import requests
from strands.models.bedrock import BedrockModel
from strands.models.ollama import OllamaModel

from agent.config import ProfileConfig


def _resolve_model(cfg: ProfileConfig) -> dict:
    model = cfg.model
    nested = model.get(cfg.backend) if isinstance(model, dict) else None
    if isinstance(nested, dict):
        return nested
    return model


def build_model(cfg: ProfileConfig):
    model_cfg = _resolve_model(cfg)
    if cfg.backend == "ollama":
        host = model_cfg["host"]
        model_id = model_cfg["model_id"]
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        return OllamaModel(host=host, model_id=model_id)

    region = model_cfg["region"]
    model_id = model_cfg["model_id"]
    return BedrockModel(model_id=model_id, region_name=region)
