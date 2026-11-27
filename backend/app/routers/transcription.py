from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import Services, get_services
from app.schemas import TranscriptionResponse
from app.services.transcription import transcribe

router = APIRouter(tags=['Transcription'])


@router.post('/api/transcribe', response_model=TranscriptionResponse)
def transcription(services: Annotated[Services, Depends(get_services)], file: UploadFile = File(...)):
    return transcribe(services, file)
