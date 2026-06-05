from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def _load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class AppConfig(BaseModel):
    name: str = ""
    version: str = ""


class LLMConfig(BaseModel):
    model: str = ""
    temperature: float = 0.7
    api_key: str = ""
    base_url: str = ""

class ZhipuConfig(BaseModel):
    api_key: str = ""

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 9000
    cors_origins: List[str] = ["*"]


class WorkerConfig(BaseModel):
    redis_url: str = "redis://127.0.0.1:6379/0"
    queue_name: str = "cv-processing"


class Config(BaseModel):
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    zhipu: ZhipuConfig = ZhipuConfig()
    server: ServerConfig = ServerConfig()
    worker: WorkerConfig = WorkerConfig()


appConfig = Config(**_load_config())
