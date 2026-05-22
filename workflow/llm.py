from langchain_openai import ChatOpenAI

from config.app import appConfig

llm = ChatOpenAI(**appConfig.llm.model_dump())