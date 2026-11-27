from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from threading import Lock
from uuid import uuid4
import tempfile

from fastapi import HTTPException

from app.schemas import Expert, Knowledge
from app.storage import read_json, write_json
from app.rag import topic_terms


class Capture:
    def __init__(self, engine):
        self.engine = engine

    def experts(self):
        return [Expert.model_validate(row) for row in read_json(self.engine.settings.experts_path)]

    def expert(self, expert_id):
        for expert in self.experts():
            if expert.id == expert_id:
                return expert
        raise HTTPException(404, 'Expert not found')

    def draft(self, request):
        expert = self.expert(request.expert_id)
        extracted = self.engine.ollama.extract(request.transcript)
        # Small local models can add plausible facts. Conservatively remove details
        # whose substantive terms are not supported by the actual interview text.
        evidence = topic_terms(request.transcript)
        def supported(text):
            words = topic_terms(text)
            return bool(words) and len(words & evidence) / len(words) >= 0.7
        fields = extracted.model_dump()
        if not supported(extracted.problem):
            fields['problem'] = 'Not specified'
        for key, value in fields.items():
            if isinstance(value, list):
                fields[key] = [item for item in value if supported(item)]
            elif key != 'problem' and isinstance(value, str) and not supported(value):
                fields[key] = None
        extracted = type(extracted).model_validate(fields)
        if extracted.problem.strip().lower() == 'not specified':
            raise HTTPException(422, 'Describe an automotive problem and what the expert observed before extracting knowledge.')
        return Knowledge(id=str(uuid4()), expert_id=expert.id, expert_name=expert.name,
                         experience_years=expert.experience_years, original_transcript=request.transcript,
                         domain='Automotive', category=expert.specialty, **extracted.model_dump())

    def save(self, request):
        expert = self.expert(request.expert_id)
        if request.knowledge.problem.strip().lower() == 'not specified':
            raise HTTPException(422, 'A meaningful automotive problem is required')
        record = Knowledge(id=str(uuid4()), expert_id=expert.id, expert_name=expert.name,
                           experience_years=expert.experience_years, original_transcript=request.transcript,
                           domain='Automotive', category=expert.specialty, **request.knowledge.model_dump())
        with self.engine.lock:
            records = self.engine.records()
            records.append(record)
            write_json(self.engine.settings.knowledge_path, [r.model_dump() for r in records])
        return record

    def feedback(self, request):
        receipt = {'id': str(uuid4()), **request.model_dump(), 'created_at': datetime.now(timezone.utc).isoformat()}
        with self.engine.lock:
            records = read_json(self.engine.settings.feedback_path)
            records.append(receipt)
            write_json(self.engine.settings.feedback_path, records)
        return {'id': receipt['id'], 'status': 'saved'}


class Transcriber:
    def __init__(self, settings):
        self.settings = settings
        self.lock = Lock()

    @cached_property
    def model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise HTTPException(503, 'Audio transcription needs faster-whisper. Run: python -m pip install -r requirements.txt') from exc
        try:
            return WhisperModel(self.settings.whisper_model, device='cpu', compute_type='int8',
                                cpu_threads=4, download_root=str(self.settings.whisper_cache))
        except Exception as exc:
            raise HTTPException(503, 'Could not load the local Whisper model. The first run requires a model download.') from exc

    def transcribe(self, file):
        try:
            suffix = Path(file.filename or '').suffix.lower()
            if suffix not in {'.wav', '.mp3', '.m4a', '.webm', '.ogg', '.mp4'}:
                raise HTTPException(415, 'Use WAV, MP3, M4A, WebM or Ogg audio')
            content = file.file.read(25_000_001)
            if not content:
                raise HTTPException(422, 'The audio file is empty')
            if len(content) > 25_000_000:
                raise HTTPException(413, 'Audio must be smaller than 25 MB')
            # Close the temporary file before Whisper opens it (required on Windows).
            with tempfile.TemporaryDirectory(prefix='autolegacy-audio-') as directory:
                path = Path(directory) / ('recording' + suffix)
                path.write_bytes(content)
                with self.lock:
                    model = self.model
                    try:
                        from faster_whisper.audio import decode_audio
                        audio = decode_audio(str(path), sampling_rate=16000)
                        if len(audio) > 16000 * 300:
                            raise HTTPException(413, 'Recordings are limited to five minutes')
                        segments, _ = model.transcribe(audio, beam_size=1, vad_filter=True)
                        text = ' '.join(segment.text.strip() for segment in segments).strip()
                    except HTTPException:
                        raise
                    except Exception as exc:
                        raise HTTPException(422, 'Could not decode or transcribe the audio. Try a clearer recording or enter text.') from exc
                if not text:
                    raise HTTPException(422, 'No speech detected. Try a clearer recording or enter text.')
                return {'text': text}
        finally:
            file.file.close()
