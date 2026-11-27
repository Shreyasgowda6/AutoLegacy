from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import Services, get_services
from app.schemas import InterviewRequest, InterviewResponse
from app.services.interview import next_question

router = APIRouter(prefix='/api/interview', tags=['Interview'])


@router.post('/next', response_model=InterviewResponse)
def interview(request: InterviewRequest, services: Annotated[Services, Depends(get_services)]):
    return next_question(services.ai, request)
