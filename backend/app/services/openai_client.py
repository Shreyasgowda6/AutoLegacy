from functools import cached_property

from fastapi import HTTPException
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.config import Settings


class AI:
    def __init__(self, settings: Settings):
        self.settings = settings

    @cached_property
    def client(self):
        if not self.settings.api_key:
            raise HTTPException(503, 'OPENAI_API_KEY is not configured on the backend')
        return OpenAI(api_key=self.settings.api_key, timeout=45, max_retries=1)

    def structured(self, schema, instruction: str, payload: str):
        try:
            result = self.client.responses.parse(
                model=self.settings.chat_model,
                input=[{'role': 'system', 'content': instruction}, {'role': 'user', 'content': payload}],
                text_format=schema,
            )
            if result.output_parsed is None:
                raise HTTPException(502, 'The AI could not produce a structured response. Please try again.')
            return result.output_parsed
        except (OpenAIError, ValidationError) as exc:
            raise HTTPException(502, 'AI service failed. Check server configuration or retry.') from exc

    def embed(self, text: str) -> list[float]:
        try:
            return self.client.embeddings.create(model=self.settings.embedding_model, input=text).data[0].embedding
        except OpenAIError as exc:
            raise HTTPException(502, 'Embedding service failed. Please retry.') from exc

    def transcribe(self, filename: str, content: bytes, content_type: str) -> str:
        try:
            result = self.client.audio.transcriptions.create(
                model=self.settings.transcription_model, file=(filename, content, content_type),
            )
            if not result.text.strip():
                raise HTTPException(422, 'No speech was detected in the audio')
            return result.text.strip()
        except OpenAIError as exc:
            raise HTTPException(502, 'Transcription service failed. Check the audio and retry.') from exc
