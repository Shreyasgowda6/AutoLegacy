import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import Services
from app.main import create_app
from app.schemas import ExtractedKnowledge, GroundedAnswer, InterviewResponse
from app.services.embeddings import VectorIndex
from app.services.storage import Storage


class FakeAI:
    def __init__(self):
        self.calls = []
        self.source_ids = None

    def embed(self, text):
        self.calls.append(('embed', text))
        # Deterministic local embeddings exercise the real Chroma index without API calls.
        return [1.0, 0.0, 0.0] if 'overheat' in text.lower() else [0.0, 1.0, 0.0]

    def structured(self, schema, instruction, payload):
        self.calls.append(('structured', payload))
        if schema is ExtractedKnowledge:
            return ExtractedKnowledge(problem='Engine overheating', symptoms=['High temperature'],
                operating_conditions=[], possible_causes=['Coolant leak'], diagnostic_steps=['Inspect when cool'],
                confirmed_cause=None, solution=None, expert_insight='Record when the temperature rises',
                common_mistakes=[], safety_precautions=['Never open a hot coolant reservoir'])
        if schema is InterviewResponse:
            return InterviewResponse(next_question='When does the overheating occur?',
                                     missing_information=['Operating conditions'], interview_complete=False)
        data = json.loads(payload)
        ids = self.source_ids if self.source_ids is not None else [r['id'] for r in data['records']]
        return GroundedAnswer(answer='Possible coolant leak. Seek qualified inspection. ' + ' '.join(f'[{i}]' for i in ids),
                              source_ids=ids, insufficient_evidence=False)

    def transcribe(self, filename, content, content_type):
        self.calls.append(('transcribe', filename))
        return 'The engine overheats.'


@pytest.fixture
def services(tmp_path):
    settings = Settings(api_key='', knowledge_path=tmp_path / 'knowledge.json', chroma_path=tmp_path / 'chroma')
    ai = FakeAI()
    return Services(settings, Storage(settings.knowledge_path), Storage(tmp_path / 'demo.json'), ai, VectorIndex(settings, ai))


@pytest.fixture
def client(services):
    with TestClient(create_app(settings=services.settings, services=services)) as client:
        yield client


@pytest.fixture
def knowledge():
    return {'expert_name': 'Test Mechanic', 'experience_years': 30, 'problem': 'Engine overheating',
            'symptoms': ['High temperature'], 'possible_causes': ['Coolant leak'],
            'expert_insight': 'Record when the temperature rises'}


@pytest.fixture
def interview():
    return {'expert': {'name': 'Test Mechanic', 'experience_years': 30},
            'messages': [{'role': 'user', 'content': 'The engine overheats after driving.'}]}
