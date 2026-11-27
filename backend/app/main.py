import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.ollama import OllamaError
from app.rag import RAG
from app.schemas import ChatRequest, ChatResponse, Knowledge


def create_app(settings=None, rag=None):
    settings = settings or load_settings()
    engine = rag or RAG(settings)
    app = FastAPI(title='AutoLegacy Demo RAG', version='0.2.0', description='Synthetic JSON knowledge → retrieval → local Ollama answer.')
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.exception_handler(OllamaError)
    async def ollama_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': str(exc)})

    @app.exception_handler(Exception)
    async def backend_error(request, exc):
        logging.getLogger(__name__).exception('RAG request failed')
        return JSONResponse(status_code=500, content={'detail': 'Could not read or index the JSON knowledge base. Check backend logs.'})

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'chat_model': settings.chat_model, 'embedding_model': settings.embedding_model}

    @app.get('/api/knowledge', response_model=list[Knowledge])
    def knowledge():
        return engine.records()

    @app.post('/api/chat', response_model=ChatResponse)
    def chat(request: ChatRequest):
        return engine.ask(request)

    return app


app = create_app()
