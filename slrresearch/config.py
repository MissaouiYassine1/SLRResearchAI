from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    provider: str = getenv("LLM_PROVIDER", "ollama").strip().lower()
    ollama_model: str = getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_base_url: str = getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    groq_api_key: str = getenv("GROQ_API_KEY", "")
    groq_model: str = getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def build_model(settings: Settings):
    if settings.provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY manque dans .env")
        from langchain_groq import ChatGroq

        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )
    if settings.provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    raise ValueError("LLM_PROVIDER doit valoir groq ou ollama")

