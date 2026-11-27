from dataclasses import dataclass

from fastapi import Request

from app.config import ROOT, Settings
from app.services.embeddings import VectorIndex
from app.services.openai_client import AI
from app.services.storage import Storage


@dataclass
class Services:
    settings: Settings
    storage: Storage
    demo_storage: Storage
    ai: AI
    index: VectorIndex


def build_services(settings):
    ai = AI(settings)
    return Services(settings, Storage(settings.knowledge_path), Storage(ROOT / 'data/demo_knowledge.json'), ai, VectorIndex(settings, ai))


def get_services(request: Request) -> Services:
    return request.app.state.services
