import requests
from strands.models.bedrock import BedrockModel
from strands.models.ollama import OllamaModel

from agent.config import ProfileConfig


def build_model(cfg: ProfileConfig):
    if cfg.backend == "ollama":
        host = cfg.model.ollama.host
        model_id = cfg.model.ollama.model_id
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        return OllamaModel(host=host, model_id=model_id)

    region = cfg.model.bedrock.region
    model_id = cfg.model.bedrock.model_id
    return BedrockModel(model_id=model_id, region_name=region)
