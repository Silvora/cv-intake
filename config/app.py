from typing import List

import yaml
from pydantic import BaseModel
# 读取并解析YAML
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)


class AppConfig(BaseModel):
    name: str = ""
    version: str = ""


class LLMConfig(BaseModel):
    model: str = ""
    temperature: float = 0.7
    api_key: str = ""
    base_url: str = ""


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 9000
    cors_origins: List[str] = ["*"]


class Config(BaseModel):
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    server: ServerConfig = ServerConfig()



appConfig = Config(**config)