import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas import KnowledgeInput, KnowledgeRecord
from app.services.openai_client import AI
from app.services.storage import Storage


def create(client, knowledge):
    response = client.post('/api/knowledge', json=knowledge)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_and_cors(client):
    assert client.get('/api/health').json() == {'status': 'ok', 'ai_configured': False}
    response = client.options('/api/chat', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert client.get('/openapi.json').status_code == 200


def test_validation_and_server_owned_fields(client, knowledge):
    for override in ({'experience_years': -1}, {'problem': ' '}, {'verification_status': 'approved'}, {'id': 'fake'}):
        assert client.post('/api/knowledge', json=knowledge | override).status_code == 422
    with pytest.raises(ValidationError):
        KnowledgeInput(**(knowledge | {'expert_name': ''}))


def test_crud_persistence_and_stats(client, services, knowledge):
    record = create(client, knowledge)
    assert record['verification_status'] == 'pending'
    assert Storage(services.settings.knowledge_path).get(record['id']).expert_name == knowledge['expert_name']
    assert client.get('/api/knowledge').json() == [record]
    assert client.get('/api/knowledge/' + record['id']).json() == record
    assert client.get('/api/stats').json()['pending_records'] == 1
    assert client.delete('/api/knowledge/' + record['id']).status_code == 204
    assert client.get('/api/knowledge/' + record['id']).status_code == 404
    assert client.get('/api/knowledge').json() == []


def test_complete_text_workflow(client, services, interview):
    assert client.post('/api/interview/next', json=interview).json()['next_question']
    draft = client.post('/api/knowledge/extract', json=interview)
    assert draft.status_code == 200, draft.text
    draft = draft.json()
    assert 'user: The engine overheats' in draft['original_transcript']
    assert draft['confirmed_cause'] is None
    assert client.get('/api/knowledge').json() == []
    data = KnowledgeInput.model_validate({k: v for k, v in draft.items() if k in KnowledgeInput.model_fields}).model_dump()
    record = create(client, data)
    assert record['id'] != draft['id']
    assert client.post('/api/chat', json={'question': 'overheating'}).json()['insufficient_evidence']
    approved = client.post(f"/api/knowledge/{record['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()['verification_status'] == 'approved'
    assert services.index.collection().count() == 1
    response = client.post('/api/chat', json={'question': 'overheating'})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer['sources'][0]['id'] == record['id']
    assert not answer['insufficient_evidence']
    assert answer['demo_mode'] is False
    assert client.get('/api/stats').json()['approved_records'] == 1


def test_approval_upsert_and_edits_require_reapproval(client, services, knowledge):
    record = create(client, knowledge)
    url = '/api/knowledge/' + record['id']
    assert client.post(url + '/approve').status_code == 200
    assert client.post(url + '/approve').status_code == 200
    assert services.index.collection().count() == 1
    assert client.put(url, json=knowledge).json()['verification_status'] == 'approved'
    changed = client.put(url, json=knowledge | {'solution': 'Expert reviewed repair'})
    assert changed.json()['verification_status'] == 'pending'
    assert changed.json()['created_at'] == record['created_at']
    assert services.index.collection().count() == 0
    assert client.post('/api/chat', json={'question': 'overheating'}).json()['sources'] == []
    assert client.post(url + '/approve').status_code == 200
    assert client.delete(url).status_code == 204
    assert services.index.collection().count() == 0


def test_synthetic_separation(client, services, knowledge):
    synthetic = KnowledgeRecord(**(knowledge | {'source_type': 'synthetic'}), verification_status='unverified')
    services.demo_storage.put(synthetic)
    services.index.upsert(synthetic)
    assert services.index.collection(True).count() == 1
    assert services.index.collection(False).count() == 0
    assert client.post('/api/chat', json={'question': 'overheating'}).json()['sources'] == []
    demo = client.post('/api/chat', json={'question': 'overheating', 'demo_mode': True}).json()
    assert demo['demo_mode'] is True
    assert demo['sources'][0]['source_type'] == 'synthetic'
    assert 'synthetic demonstration' in demo['answer']
    record = create(client, knowledge | {'source_type': 'synthetic'})
    assert record['verification_status'] == 'unverified'
    assert client.post(f"/api/knowledge/{record['id']}/approve").status_code == 422
    assert client.put('/api/knowledge/' + record['id'], json=knowledge).status_code == 422


def test_empty_and_irrelevant_knowledge(client, services, knowledge):
    response = client.post('/api/chat', json={'question': 'overheating'})
    assert response.json()['insufficient_evidence']
    assert services.ai.calls == []
    record = create(client, knowledge)
    client.post(f"/api/knowledge/{record['id']}/approve")
    assert client.post('/api/chat', json={'question': 'unrelated noise'}).json()['sources'] == []


def test_stale_index_and_invalid_citations_fail_closed(client, services, knowledge):
    record = create(client, knowledge)
    client.post(f"/api/knowledge/{record['id']}/approve")
    services.ai.source_ids = ['invented-id']
    assert client.post('/api/chat', json={'question': 'overheating'}).json()['insufficient_evidence']
    services.ai.source_ids = None
    current = services.storage.get(record['id'])
    services.storage.put(current.model_copy(update={'problem': 'Changed overheating record'}))
    assert client.post('/api/chat', json={'question': 'overheating'}).json()['sources'] == []


def test_failed_approval_stays_pending(client, services, knowledge, monkeypatch):
    record = create(client, knowledge)
    def fail(*args):
        raise HTTPException(502, 'Mock embedding outage')
    monkeypatch.setattr(services.ai, 'embed', fail)
    assert client.post(f"/api/knowledge/{record['id']}/approve").status_code == 502
    assert services.storage.get(record['id']).verification_status == 'pending'


def test_interview_limit(client, services, interview):
    for _ in range(3):
        interview['messages'] += [{'role': 'assistant', 'content': 'What happened next?'}, {'role': 'user', 'content': 'More context.'}]
    response = client.post('/api/interview/next', json=interview).json()
    assert response['interview_complete'] is True
    assert response['next_question'] is None
    assert services.ai.calls == []


@pytest.mark.parametrize('name,content,status', [
    ('audio.txt', b'hello', 415), ('audio.wav', b'', 422), ('audio.mp3', b'not audio', 422),
    ('audio.wav', b'RIFF0000WAVEpayload', 200),
])
def test_transcription_validation(client, name, content, status):
    response = client.post('/api/transcribe', files={'file': (name, content, 'audio/wav')})
    assert response.status_code == status
    if status == 200:
        assert response.json()['text'] == 'The engine overheats.'


def test_audio_size_limit(client, services):
    services.settings.max_audio_bytes = 4
    assert client.post('/api/transcribe', files={'file': ('audio.wav', b'RIFF0000WAVEpayload')}).status_code == 413


def test_missing_key_is_actionable(services):
    with pytest.raises(HTTPException) as exc:
        AI(services.settings).embed('test')
    assert exc.value.status_code == 503


def test_atomic_write_failure_preserves_original(services, knowledge, monkeypatch):
    record = KnowledgeRecord(**knowledge)
    services.storage.put(record)
    import app.services.storage as storage_module
    def fail(*args):
        raise OSError('Mock disk error')
    monkeypatch.setattr(storage_module.os, 'replace', fail)
    with pytest.raises(OSError):
        services.storage.put(record.model_copy(update={'problem': 'Changed'}))
    assert services.storage.get(record.id).problem == record.problem
    assert len(list(services.settings.knowledge_path.parent.glob('tmp*'))) == 0


def test_invalid_interview_history_and_size(client, interview):
    interview['messages'].append({'role': 'assistant', 'content': 'A question'})
    assert client.post('/api/interview/next', json=interview).status_code == 422
    interview['messages'] = [{'role': 'user', 'content': 'x' * 20000} for _ in range(6)]
    assert client.post('/api/knowledge/extract', json=interview).status_code == 422


def test_demo_dataset_is_explicitly_synthetic():
    from app.config import ROOT
    records = Storage(ROOT / 'data/demo_knowledge.json').all()
    assert len(records) == 10
    assert len({r.id for r in records}) == 10
    assert all(r.source_type == 'synthetic' and r.verification_status == 'unverified' for r in records)
    assert all(r.confirmed_cause is None and r.solution is None for r in records)


def test_provider_refusal_is_sanitized(services):
    from types import SimpleNamespace
    ai = AI(services.settings)
    ai.__dict__['client'] = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(output_parsed=None)))
    with pytest.raises(HTTPException) as exc:
        from app.schemas import InterviewResponse
        ai.structured(InterviewResponse, 'instructions', 'interview')
    assert exc.value.status_code == 502


def test_unknown_inline_citation_is_rejected(client, services, knowledge, monkeypatch):
    record = create(client, knowledge)
    client.post(f"/api/knowledge/{record['id']}/approve")
    original = services.ai.structured
    def fabricated_citation(*args):
        response = original(*args)
        response.answer += ' [invented-inline-id]'
        return response
    monkeypatch.setattr(services.ai, 'structured', fabricated_citation)
    response = client.post('/api/chat', json={'question': 'overheating'}).json()
    assert response['insufficient_evidence'] is True
    assert response['sources'] == []
