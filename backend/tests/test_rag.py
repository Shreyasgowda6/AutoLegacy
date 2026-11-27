import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.ollama import Ollama, OllamaError
from app.rag import RAG, cosine_distance
from app.schemas import ChatRequest, GroundedAnswer


class FakeOllama:
    def __init__(self):
        self.embedded = []
        self.answered = []
        self.citation = None

    def embed(self, text):
        self.embedded.append(text)
        return [1.0, 0.0] if 'overheat' in text.lower() else [0.0, 1.0]

    def answer(self, payload):
        data = json.loads(payload)
        self.answered.append(data)
        source_id = self.citation or data['records'][0]['id']
        return GroundedAnswer(answer=f'Possible coolant loss [{source_id}]', source_ids=[source_id], insufficient_evidence=False)


@pytest.fixture
def rag(tmp_path):
    settings = Settings(knowledge_path=tmp_path / 'knowledge.json', index_path=tmp_path / 'embeddings.json')
    settings.knowledge_path.write_text(json.dumps([
        {'id': 'overheating', 'problem': 'Engine overheating', 'possible_causes': ['Coolant loss']},
        {'id': 'starting', 'problem': 'Intermittent starting issue'},
    ]))
    return RAG(settings, FakeOllama())


def test_full_json_rag_pipeline(rag):
    response = rag.ask(ChatRequest(question='Why is it overheating?'))
    assert not response.insufficient_evidence
    assert [s.id for s in response.sources] == ['overheating']
    assert response.sources[0].possible_causes == ['Coolant loss']
    assert response.sources[0].source_type == 'synthetic'
    assert len(rag.ollama.embedded) == 3
    assert len(rag.ollama.answered[0]['records']) == 1
    assert 'demo_mode' not in response.model_dump()


def test_index_cache_reused_across_instances(rag):
    rag.index()
    other = RAG(rag.settings, FakeOllama())
    other.index()
    assert other.ollama.embedded == []


def test_json_edits_and_model_change_rebuild_cache(rag):
    rag.index()
    rag.settings.knowledge_path.write_text(json.dumps([{'id': 'new', 'problem': 'New overheating knowledge'}]))
    records, vectors = rag.index()
    assert records[0].id == 'new'
    assert len(vectors) == 1
    rag.settings.embedding_model = 'another-model'
    before = len(rag.ollama.embedded)
    rag.index()
    assert len(rag.ollama.embedded) == before + 1


def test_deleted_records_cannot_be_retrieved(rag):
    rag.index()
    rag.settings.knowledge_path.write_text('[]')
    response = rag.ask(ChatRequest(question='overheating'))
    assert response.insufficient_evidence and response.sources == []
    assert rag.ollama.answered == []


def test_no_relevant_match_does_not_generate(rag):
    rag.settings.knowledge_path.write_text(json.dumps([{'id': 'one', 'problem': 'Overheating'}]))
    response = rag.ask(ChatRequest(question='unrelated starting issue'))
    assert response.insufficient_evidence
    assert rag.ollama.answered == []


def test_fabricated_citations_are_rejected(rag):
    rag.ollama.citation = 'invented'
    response = rag.ask(ChatRequest(question='overheating'))
    assert response.insufficient_evidence and response.sources == []


def test_corrupt_cache_is_rebuilt(rag):
    rag.settings.index_path.write_text('not json')
    assert len(rag.index()[0]) == 2
    cached = json.loads(rag.settings.index_path.read_text())
    cached['embeddings'] = [[0, 0], [0, 0]]
    rag.settings.index_path.write_text(json.dumps(cached))
    assert rag.index()[1] == [[1.0, 0.0], [0.0, 1.0]]


def test_bad_knowledge_is_not_silently_ignored(rag):
    rag.settings.knowledge_path.write_text('[{"id":"duplicate","problem":"A"},{"id":"duplicate","problem":"B"}]')
    with pytest.raises(ValueError, match='unique'):
        rag.index()
    rag.settings.knowledge_path.write_text('invalid JSON')
    with pytest.raises(ValueError):
        rag.index()


def test_api_without_mode_or_approval(rag):
    with TestClient(create_app(rag.settings, rag)) as client:
        assert client.get('/api/health').status_code == 200
        assert len(client.get('/api/knowledge').json()) == 2
        response = client.post('/api/chat', json={'question': 'overheating'})
        assert response.status_code == 200
        assert response.json()['sources'][0]['id'] == 'overheating'
        assert client.post('/api/chat', json={'question': 'overheating', 'demo_mode': True}).status_code == 422
        assert client.post('/api/chat', json={'question': ' '}).status_code == 422
        assert client.post('/api/chat', json={'question': 'test', 'top_k': 0}).status_code == 422
        assert client.post('/api/knowledge/one/approve').status_code == 404
        assert len(client.get('/openapi.json').json()['paths']) == 3


def test_cosine_distance():
    assert cosine_distance([1, 0], [1, 0]) == 0
    assert cosine_distance([1, 0], [0, 1]) == 1
    with pytest.raises(ValueError):
        cosine_distance([0, 0], [1, 0])
    with pytest.raises(ValueError):
        cosine_distance([1], [1, 0])


def test_ollama_payloads_and_validation(monkeypatch):
    ai = Ollama(Settings())
    calls = []
    def request(path, payload):
        calls.append((path, payload))
        if path == 'embed':
            return {'embeddings': [[1.0, 0.5]]}
        return {'message': {'content': json.dumps({'answer': 'Known fact', 'source_ids': ['one'], 'insufficient_evidence': False})}}
    monkeypatch.setattr(ai, 'request', request)
    assert ai.embed('text') == [1.0, 0.5]
    assert ai.answer('{}').source_ids == ['one']
    assert calls[1][1]['think'] is False
    assert calls[1][1]['format']['additionalProperties'] is False
    monkeypatch.setattr(ai, 'request', lambda *args: {'embeddings': [[]]})
    with pytest.raises(OllamaError):
        ai.embed('text')


def test_missing_model_error_is_actionable(monkeypatch):
    request = httpx.Request('POST', 'http://localhost:11434/api/embed')
    def fail(*args, **kwargs):
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError('missing model', request=request, response=response)
    monkeypatch.setattr(httpx.Client, 'post', fail)
    with pytest.raises(OllamaError, match='Model not installed'):
        Ollama(Settings()).embed('text')
