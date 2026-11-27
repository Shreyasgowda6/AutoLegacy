from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import Services, get_services
from app.schemas import ChatRequest, ChatResponse
from app.services.rag import answer

router = APIRouter(tags=['Assistant'])


@router.post('/api/chat', response_model=ChatResponse)
def chat(request: ChatRequest, services: Annotated[Services, Depends(get_services)]):
    return answer(services, request)
