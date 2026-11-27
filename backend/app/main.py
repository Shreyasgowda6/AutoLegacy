import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.dependencies import build_services
from app.routers import chat, interview, knowledge, transcription
from app.schemas import HealthResponse, StatsResponse

logger = logging.getLogger(__name__)


def create_app(settings=None, services=None):
    settings = settings or load_settings()
    app = FastAPI(title='AutoLegacy API', version='0.1.0', description='Capture, review and retrieve automotive expert knowledge.')
    app.state.services = services or build_services(settings)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])

    @app.exception_handler(KeyError)
    async def missing_record(request: Request, exc: KeyError):
        return JSONResponse(status_code=404, content={'detail': 'Knowledge record not found'})

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        logger.exception('Request failed: %s', request.url.path)
        return JSONResponse(status_code=500, content={'detail': 'Server operation failed. Check the backend logs.'})

    @app.get('/api/health', tags=['Status'], response_model=HealthResponse)
    def health():
        return {'status': 'ok', 'ai_configured': bool(settings.api_key)}

    @app.get('/api/stats', tags=['Status'], response_model=StatsResponse)
    def stats():
        records = app.state.services.storage.all()
        return {
            'total_records': len(records),
            'approved_records': sum(r.verification_status == 'approved' for r in records),
            'pending_records': sum(r.verification_status == 'pending' for r in records),
            'synthetic_records': sum(r.source_type == 'synthetic' for r in records),
            'expert_insights': sum(bool(r.expert_insight) and r.source_type == 'expert_interview' for r in records),
            'recent_activity': [r.model_dump(mode='json') for r in sorted(records, key=lambda r: r.created_at, reverse=True)[:5]],
        }

    for router in (knowledge.router, interview.router, transcription.router, chat.router):
        app.include_router(router)
    return app


app = create_app()
