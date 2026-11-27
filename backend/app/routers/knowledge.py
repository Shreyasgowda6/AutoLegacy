from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.dependencies import Services, get_services
from app.schemas import InterviewRequest, KnowledgeInput, KnowledgeRecord
from app.services.extraction import extract

router = APIRouter(prefix='/api/knowledge', tags=['Knowledge'])
Service = Annotated[Services, Depends(get_services)]


@router.post('/extract', response_model=KnowledgeRecord)
def extract_knowledge(request: InterviewRequest, services: Service):
    return extract(services.ai, request)


@router.post('', response_model=KnowledgeRecord, status_code=201)
def create(data: KnowledgeInput, services: Service):
    record = KnowledgeRecord(**data.model_dump(), verification_status='unverified' if data.source_type == 'synthetic' else 'pending')
    return services.storage.put(record)


@router.get('', response_model=list[KnowledgeRecord])
def list_records(services: Service):
    return services.storage.all()


@router.get('/{record_id}', response_model=KnowledgeRecord)
def get(record_id: str, services: Service):
    return services.storage.get(record_id)


@router.put('/{record_id}', response_model=KnowledgeRecord)
def update(record_id: str, data: KnowledgeInput, services: Service):
    with services.storage.lock:
        old = services.storage.get(record_id)
        if data.source_type != old.source_type:
            raise HTTPException(422, 'source_type cannot be changed')
        if data.model_dump() == KnowledgeInput.model_validate(old.model_dump(include=set(KnowledgeInput.model_fields))).model_dump():
            return old
        record = KnowledgeRecord(**data.model_dump(), id=old.id, created_at=old.created_at,
                                 verification_status='unverified' if old.source_type == 'synthetic' else 'pending')
        # Invalidate in authoritative storage first, so failures cannot leave changed knowledge approved.
        services.storage.put(record)
        services.index.delete(record_id)
        return record


@router.delete('/{record_id}', status_code=204)
def delete(record_id: str, services: Service):
    with services.storage.lock:
        services.storage.get(record_id)
        services.index.delete(record_id)
        services.storage.delete(record_id)
    return Response(status_code=204)


@router.post('/{record_id}/approve', response_model=KnowledgeRecord)
def approve(record_id: str, services: Service):
    with services.storage.lock:
        record = services.storage.get(record_id)
        if record.source_type != 'expert_interview':
            raise HTTPException(422, 'Synthetic records cannot be approved as expert knowledge')
        approved = record.model_copy(update={'verification_status': 'approved'})
        services.index.upsert(approved)
        return services.storage.put(approved)
