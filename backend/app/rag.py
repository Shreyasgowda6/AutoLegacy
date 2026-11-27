import hashlib
import json
import math
import os
import re
import tempfile
from threading import RLock

from app.ollama import Ollama
from app.schemas import ChatResponse, Knowledge, Source

INSUFFICIENT = 'The JSON knowledge base does not contain sufficient information to answer this question.'


def cosine_distance(left, right):
    if len(left) != len(right):
        raise ValueError('Embedding dimensions differ. Rebuild the index.')
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    if denominator == 0:
        raise ValueError('Embedding vector cannot be zero')
    return max(0.0, min(2.0, 1 - sum(x * y for x, y in zip(left, right)) / denominator))


class RAG:
    """JSON -> cached embeddings -> cosine retrieval -> grounded Ollama answer."""

    def __init__(self, settings, ollama=None):
        self.settings = settings
        self.ollama = ollama or Ollama(settings)
        self.lock = RLock()

    def records(self):
        records = [Knowledge.model_validate(row) for row in json.loads(self.settings.knowledge_path.read_text(encoding='utf-8'))]
        if len({r.id for r in records}) != len(records):
            raise ValueError('Knowledge record IDs must be unique')
        return records

    def index(self, force=False):
        with self.lock:
            records = self.records()
            documents = [r.model_dump_json() for r in records]
            signature = hashlib.sha256(json.dumps([self.settings.embedding_model, documents]).encode()).hexdigest()
            if not force and self.settings.index_path.exists():
                try:
                    cached = json.loads(self.settings.index_path.read_text(encoding='utf-8'))
                    vectors = cached['embeddings']
                    if (cached['signature'] == signature and len(vectors) == len(records)
                            and all(isinstance(v, list) and v and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v) and any(v) for v in vectors)
                            and len({len(v) for v in vectors}) <= 1):
                        return records, vectors
                except (ValueError, KeyError, TypeError):
                    pass  # A corrupt cache is rebuilt from the authoritative JSON.
            vectors = [self.ollama.embed(text) for text in documents]
            path = self.settings.index_path
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
                    temporary = stream.name
                    json.dump({'signature': signature, 'embeddings': vectors}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            return records, vectors

    def ask(self, request):
        records, vectors = self.index()
        if not records:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        query = self.ollama.embed(request.question)
        matches = sorted([(cosine_distance(query, vector), record) for record, vector in zip(records, vectors)], key=lambda x: x[0])
        sources = [Source(**record.model_dump(), distance=distance) for distance, record in matches[:request.top_k]
                   if distance <= self.settings.max_distance]
        if not sources:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        result = self.ollama.answer(json.dumps({'question': request.question, 'records': [s.model_dump() for s in sources]}))
        allowed = {s.id for s in sources}
        cited = set(result.source_ids)
        inline = set(re.findall(r'\[([^\[\]]+)\]', result.answer))
        if not cited or not cited <= allowed or not inline <= cited:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        text = result.answer
        if not inline:
            text += '\n\nSources: ' + ' '.join(f'[{s.id}]' for s in sources if s.id in cited)
        return ChatResponse(answer=text, sources=[s for s in sources if s.id in cited],
                            insufficient_evidence=result.insufficient_evidence)
