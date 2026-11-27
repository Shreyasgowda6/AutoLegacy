import logging

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.ollama import OllamaError
from app.rag import RAG
from app.capture import Capture, Transcriber
from app.schemas import ChatRequest, ChatResponse, Knowledge, Expert, FeedbackInput, FeedbackReceipt, InterviewInput, SaveKnowledge


def create_app(settings=None, rag=None):
    settings = settings or load_settings()
    engine = rag or RAG(settings)
    capture = Capture(engine)
    audio = Transcriber(settings)
    app = FastAPI(title='AutoLegacy Demo RAG', version='0.3.0', description='Capture expert knowledge and retrieve grounded answers from JSON.')
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

    @app.get('/api/experts', response_model=list[Expert])
    def experts():
        return capture.experts()

    @app.post('/api/feedback', response_model=FeedbackReceipt, status_code=201)
    def feedback(request: FeedbackInput):
        return capture.feedback(request)

    @app.post('/api/interview/extract', response_model=Knowledge)
    def extract(request: InterviewInput):
        return capture.draft(request)

    @app.post('/api/knowledge', response_model=Knowledge, status_code=201)
    def save(request: SaveKnowledge):
        return capture.save(request)

    @app.post('/api/transcribe')
    def transcribe(file: UploadFile = File(...)):
        return audio.transcribe(file)

    return app


app = create_app()
