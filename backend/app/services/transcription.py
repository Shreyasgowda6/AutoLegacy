from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.schemas import TranscriptionResponse

TYPES = {'.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.webm': 'audio/webm'}


def transcribe(services, file: UploadFile):
    try:
        suffix = Path(file.filename or '').suffix.lower()
        if suffix not in TYPES:
            raise HTTPException(415, 'Supported formats: WAV, MP3, M4A, WebM')
        content = file.file.read(services.settings.max_audio_bytes + 1)
        if len(content) > services.settings.max_audio_bytes:
            raise HTTPException(413, 'Audio exceeds the configured file size limit')
        if not content:
            raise HTTPException(422, 'Audio file is empty')
        valid = (
            suffix == '.wav' and content[:4] == b'RIFF' and content[8:12] == b'WAVE'
            or suffix == '.mp3' and (content[:3] == b'ID3' or len(content) >= 2 and content[0] == 255 and content[1] & 224 == 224)
            or suffix == '.m4a' and content[4:8] == b'ftyp'
            or suffix == '.webm' and content[:4] == b'\x1a\x45\xdf\xa3'
        )
        if not valid:
            raise HTTPException(422, 'File contents do not match the selected audio format')
        return TranscriptionResponse(text=services.ai.transcribe('recording' + suffix, content, TYPES[suffix]))
    finally:
        file.file.close()
