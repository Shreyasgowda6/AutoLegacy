import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def local_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


@dataclass
class Settings:
    ollama_url: str = field(default_factory=lambda: os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
    chat_model: str = field(default_factory=lambda: os.getenv('OLLAMA_CHAT_MODEL', 'qwen3:1.7b'))
    embedding_model: str = field(default_factory=lambda: os.getenv('OLLAMA_EMBEDDING_MODEL', 'bge-m3:latest'))
    knowledge_path: Path = field(default_factory=lambda: local_path(os.getenv('KNOWLEDGE_PATH', './data/knowledge_base.json')))
    index_path: Path = field(default_factory=lambda: local_path(os.getenv('INDEX_PATH', './data/embeddings.json')))
    max_distance: float = field(default_factory=lambda: float(os.getenv('RELEVANCE_THRESHOLD', '0.65')))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(','))

    def __post_init__(self):
        if not 0 <= self.max_distance <= 2:
            raise ValueError('RELEVANCE_THRESHOLD must be between 0 and 2')


def load_settings():
    load_dotenv(ROOT / '.env')
    return Settings()
