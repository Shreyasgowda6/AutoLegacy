import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def local_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


@dataclass
class Settings:
    api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    chat_model: str = field(default_factory=lambda: os.getenv('OPENAI_CHAT_MODEL', 'gpt-4.1-mini'))
    transcription_model: str = field(default_factory=lambda: os.getenv('OPENAI_TRANSCRIPTION_MODEL', 'whisper-1'))
    embedding_model: str = field(default_factory=lambda: os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'))
    chroma_path: Path = field(default_factory=lambda: local_path(os.getenv('CHROMA_PATH', './chroma_db')))
    knowledge_path: Path = field(default_factory=lambda: local_path(os.getenv('KNOWLEDGE_PATH', './data/knowledge.json')))
    cors_origins: list[str] = field(default_factory=lambda: [x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',') if x.strip()])
    relevance_threshold: float = field(default_factory=lambda: float(os.getenv('RELEVANCE_THRESHOLD', '0.65')))
    max_audio_bytes: int = field(default_factory=lambda: int(os.getenv('MAX_AUDIO_BYTES', '25000000')))

    def __post_init__(self):
        if not 0 <= self.relevance_threshold <= 2:
            raise ValueError('RELEVANCE_THRESHOLD must be a cosine distance between 0 and 2')
        if self.max_audio_bytes <= 0:
            raise ValueError('MAX_AUDIO_BYTES must be positive')


def load_settings() -> Settings:
    load_dotenv(ROOT / '.env')
    return Settings()
