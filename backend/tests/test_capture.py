import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.capture import Transcriber, Capture
from app.main import create_app
from app.schemas import ChatRequest, ExtractedKnowledge, GroundedAnswer, InterviewInput, SaveKnowledge, FeedbackInput
from app.rag import INSUFFICIENT

# Reuse the temporary knowledge/index fixture and fake model from the pipeline tests.
from test_rag import rag  # noqa: F401


def extracted():
    return ExtractedKnowledge(problem='Tyre pressure warning after wheel change', vehicle_make=None,
        vehicle_model=None, engine_type=None, symptoms=['Tyre pressure warning'], operating_conditions=['After wheel change'],
        possible_causes=[], diagnostic_steps=['Record the warning and consult vehicle documentation'],
        confirmed_cause=None, solution=None, expert_insight='Record when the warning first appeared',
        common_mistakes=[], safety_precautions=['Arrange qualified inspection if pressure is dropping'])


def test_incidental_tyre_mention_is_not_purchase_advice(rag):
    rag.settings.knowledge_path.write_text(json.dumps([{
        'id': 'fuel', 'problem': 'Excessive fuel consumption', 'diagnostic_steps': ['Check tyre pressure'],
    }]))
    response = rag.ask(ChatRequest(question='i want to buy new tyre'))
    assert response.answer == 'No information available.'
    assert response.sources == [] and response.insufficient_evidence
    assert rag.ollama.answered == []


def test_model_insufficient_flag_discards_unrelated_answer(rag, monkeypatch):
    monkeypatch.setattr(rag.ollama, 'answer', lambda payload: GroundedAnswer(
        answer='An unrelated answer [overheating]', source_ids=['overheating'], insufficient_evidence=True))
    response = rag.ask(ChatRequest(question='overheating'))
    assert response.answer == INSUFFICIENT and response.sources == []


def test_all_synthetic_experts_are_available(rag):
    with TestClient(create_app(rag.settings, rag)) as client:
        response = client.get('/api/experts')
        assert response.status_code == 200
        experts = response.json()
        assert len(experts) == 10
        assert len({e['id'] for e in experts}) == 10
        assert all(e['synthetic'] for e in experts)
        assert experts[0]['name'] == 'James Miller'


def test_feedback_is_persisted_and_validated(rag):
    with TestClient(create_app(rag.settings, rag)) as client:
        response = client.post('/api/feedback', json={'question': 'buy new tyre', 'topic': 'Knowledge gap', 'details': 'Please add tyre selection knowledge'})
        assert response.status_code == 201
        records = json.loads(rag.settings.feedback_path.read_text())
        assert records[0]['id'] == response.json()['id']
        assert records[0]['question'] == 'buy new tyre'
        assert client.post('/api/feedback', json={'topic': 'Gap', 'details': ' '}).status_code == 422


def test_text_interview_extract_review_save_and_retrieve(rag, monkeypatch):
    monkeypatch.setattr(rag.ollama, 'extract', lambda transcript: extracted(), raising=False)
    with TestClient(create_app(rag.settings, rag)) as client:
        interview = {'expert_id': 'expert-01', 'transcript': 'A tyre pressure warning appeared after a wheel change. Record when the warning appeared.'}
        draft = client.post('/api/interview/extract', json=interview)
        assert draft.status_code == 200, draft.text
        assert len(rag.records()) == 2  # Extraction does not write before review.
        assert draft.json()['expert_name'] == 'James Miller'
        assert draft.json()['original_transcript'] == interview['transcript']
        rag.index()  # Existing cache must refresh after saving.
        reviewed = extracted().model_dump()
        reviewed['expert_insight'] = 'Reviewed lesson about recording the warning'
        saved = client.post('/api/knowledge', json={**interview, 'knowledge': reviewed})
        assert saved.status_code == 201, saved.text
        assert saved.json()['expert_insight'] == reviewed['expert_insight']
        assert len(rag.records()) == 3
        assert saved.json()['id'] != draft.json()['id']
        result = client.post('/api/chat', json={'question': 'What causes a tyre pressure warning after a wheel change?'})
        assert result.status_code == 200
        assert result.json()['sources'][0]['id'] == saved.json()['id']
        assert result.json()['sources'][0]['expert_id'] == 'expert-01'
        assert client.post('/api/interview/extract', json={**interview, 'expert_id': 'missing'}).status_code == 404


@pytest.mark.parametrize('filename,data,expected', [('recording.txt', b'test', 415), ('recording.wav', b'', 422), ('recording.wav', b'x' * 25_000_001, 413)])
def test_audio_validation_before_model_loading(rag, filename, data, expected):
    with TestClient(create_app(rag.settings, rag)) as client:
        assert client.post('/api/transcribe', files={'file': (filename, data)}).status_code == expected


def test_transcription_dependency_error_is_actionable(rag, monkeypatch):
    def missing(self):
        raise HTTPException(503, 'Audio transcription needs faster-whisper. Run: python -m pip install -r requirements.txt')
    monkeypatch.setattr(Transcriber, 'model', property(missing))
    with TestClient(create_app(rag.settings, rag)) as client:
        response = client.post('/api/transcribe', files={'file': ('recording.wav', b'RIFF0000WAVEpayload')})
        assert response.status_code == 503
        assert 'pip install' in response.json()['detail']


def test_unsupported_interview_is_not_saved(rag, monkeypatch):
    result = extracted().model_copy(update={'problem': 'Not specified'})
    monkeypatch.setattr(rag.ollama, 'extract', lambda transcript: result, raising=False)
    with TestClient(create_app(rag.settings, rag)) as client:
        response = client.post('/api/interview/extract', json={'expert_id': 'expert-01', 'transcript': 'Hello there'})
        assert response.status_code == 422
        assert len(rag.records()) == 2


def test_capture_service_saves_reviewed_text_and_refreshes_index(rag, monkeypatch):
    monkeypatch.setattr(rag.ollama, 'extract', lambda text: extracted(), raising=False)
    capture = Capture(rag)
    request = InterviewInput(expert_id='expert-01', transcript='Tyre pressure warning appeared after a wheel change.')
    draft = capture.draft(request)
    assert len(rag.records()) == 2 and draft.original_transcript == request.transcript
    rag.index()
    record = capture.save(SaveKnowledge(**request.model_dump(), knowledge=extracted()))
    assert len(rag.records()) == 3 and record.expert_name == 'James Miller'
    answer = rag.ask(ChatRequest(question='Tyre pressure warning after a wheel change'))
    assert answer.sources[0].id == record.id


def test_feedback_service_atomic_persistence(rag):
    receipt = Capture(rag).feedback(FeedbackInput(topic='Knowledge gap', details='Please add tyre purchasing knowledge', question='buy new tyre'))
    data = json.loads(rag.settings.feedback_path.read_text())
    assert receipt['id'] == data[0]['id']
    assert data[0]['question'] == 'buy new tyre'


def test_expert_profiles_and_empty_interview_service(rag, monkeypatch):
    capture = Capture(rag)
    assert len(capture.experts()) == 10
    assert all(expert.synthetic for expert in capture.experts())
    with pytest.raises(HTTPException) as exc:
        capture.expert('missing')
    assert exc.value.status_code == 404
    monkeypatch.setattr(rag.ollama, 'extract', lambda text: extracted().model_copy(update={'problem': 'Not specified'}), raising=False)
    with pytest.raises(HTTPException) as exc:
        capture.draft(InterviewInput(expert_id='expert-01', transcript='hello'))
    assert exc.value.status_code == 422 and len(rag.records()) == 2


def test_transcriber_pipeline_with_local_decoder_stub(rag, monkeypatch):
    import io
    import sys
    import types
    from fastapi import UploadFile
    package = types.ModuleType('faster_whisper')
    package.__path__ = []
    decoder = types.ModuleType('faster_whisper.audio')
    decoder.decode_audio = lambda *args, **kwargs: [0.1] * 16000
    monkeypatch.setitem(sys.modules, 'faster_whisper', package)
    monkeypatch.setitem(sys.modules, 'faster_whisper.audio', decoder)
    transcriber = Transcriber(rag.settings)
    transcriber.__dict__['model'] = SimpleNamespace(transcribe=lambda *args, **kwargs: (iter([SimpleNamespace(text=' The engine overheats. ')]), None))
    upload = UploadFile(filename='recording.wav', file=io.BytesIO(b'RIFF0000WAVEpayload'))
    assert transcriber.transcribe(upload) == {'text': 'The engine overheats.'}
    assert upload.file.closed


def test_extraction_removes_unsupported_details(rag, monkeypatch):
    result = extracted().model_copy(update={'engine_type': 'Unknown', 'common_mistakes': ['Replacing the alternator or starter without diagnosis']})
    monkeypatch.setattr(rag.ollama, 'extract', lambda text: result, raising=False)
    draft = Capture(rag).draft(InterviewInput(expert_id='expert-01', transcript='A tyre pressure warning appeared after a wheel change.'))
    assert draft.engine_type is None
    assert draft.common_mistakes == []


@pytest.mark.parametrize('filename,data,status', [('recording.txt', b'x', 415), ('recording.wav', b'', 422), ('recording.wav', b'x' * 25_000_001, 413)])
def test_transcriber_service_validation(rag, filename, data, status):
    import io
    from fastapi import UploadFile
    upload = UploadFile(filename=filename, file=io.BytesIO(data))
    with pytest.raises(HTTPException) as exc:
        Transcriber(rag.settings).transcribe(upload)
    assert exc.value.status_code == status
    assert upload.file.closed


def test_failed_knowledge_write_preserves_original(rag, monkeypatch):
    import app.storage as storage
    def fail(*args):
        raise OSError('Mock disk failure')
    monkeypatch.setattr(storage.os, 'replace', fail)
    with pytest.raises(OSError):
        Capture(rag).save(SaveKnowledge(expert_id='expert-01', transcript='Tyre pressure warning after wheel change', knowledge=extracted()))
    assert len(rag.records()) == 2
