import hashlib
import json
import math
import os
import re
import tempfile
import logging
from threading import RLock

from app.ollama import Ollama
from app.schemas import ChatResponse, Knowledge, Source

INSUFFICIENT = 'No information available.'

STOP_WORDS = set('a an the i my me we our you your it its is are was were be been do does did can could would should will may might have has had to of for in on at and or with from about as when why what how which please want need new get engine car vehicle information knowledge issue problem help tell explain investigate diagnose'.split())
ALIASES = {
    'overheating': 'heat', 'overheat': 'heat', 'overheats': 'heat', 'temperature': 'heat', 'hot': 'heat',
    'starting': 'start', 'starts': 'start', 'crank': 'start', 'cranking': 'start',
    'knocking': 'noise', 'knock': 'noise', 'rattle': 'noise', 'rattling': 'noise',
    'vibrating': 'vibration', 'shaking': 'vibration', 'vibrates': 'vibration',
    'leaking': 'leak', 'leakage': 'leak', 'leaks': 'leak', 'idling': 'idle',
    'tyres': 'tyre', 'tires': 'tyre', 'tire': 'tyre', 'smoking': 'smoke',
    'stalls': 'shutdown', 'stalling': 'shutdown', 'stall': 'shutdown',
}


def topic_terms(text):
    return {ALIASES.get(word, word) for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP_WORDS}


def matches_topic(question, record):
    # Incidental mentions in a diagnosis or transcript do not establish topic coverage.
    focus = ' '.join([record.problem, *record.symptoms, *record.operating_conditions])
    if not topic_terms(question) & topic_terms(focus):
        return False
    if re.search(r'\b(buy|purchase|prices?|costs?|shopping)\b|\bhow much\b', question.lower()):
        return bool(re.search(r'\b(buy|purchase|price|cost|shopping)\b', focus.lower()))
    return True


def vehicle_matches(question, records):
    """Honor vehicle names in a question before ranking the eligible records."""
    query = question.lower()
    def mentioned(value):
        return bool(value and re.search(r'(?<!\w)' + re.escape(value.lower()) + r'(?!\w)', query))
    def model(record):
        return (record.vehicle_model or '').split('(')[0].strip().lower()
    makes = {(r.vehicle_make or '').lower() for r in records if mentioned(r.vehicle_make)}
    models = {model(r) for r in records if mentioned(model(r))}
    return [r for r in records if (not makes or (r.vehicle_make or '').lower() in makes)
            and (not models or model(r) in models)]


def supported_positive_answer(answer, sources):
    """Resolve a small model's contradictory flag only for source-grounded text."""
    plain = re.sub(r'\[[^\[\]]+\]', '', answer).strip()
    if re.search(r'no information|insufficient|not enough|does not (?:contain|provide)|cannot (?:answer|determine)|not available', plain, re.I):
        return False
    terms = topic_terms(plain)
    evidence = topic_terms(' '.join(source.model_dump_json(exclude={'id', 'original_transcript'}) for source in sources))
    return len(terms & evidence) >= 3 and len(terms & evidence) / max(1, len(terms)) >= 0.65


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
        candidates = vehicle_matches(request.question, self.records())
        eligible = {record.id for record in candidates if matches_topic(request.question, record)}
        if not eligible:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        records, vectors = self.index()
        if not records:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        query = self.ollama.embed(request.question)
        matches = sorted([(cosine_distance(query, vector), record) for record, vector in zip(records, vectors)
                          if record.id in eligible], key=lambda x: x[0])
        sources = [Source(**record.model_dump(), distance=distance) for distance, record in matches[:request.top_k]
                   if distance <= self.settings.max_distance and matches_topic(request.question, record)]
        if not sources:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        result = self.ollama.answer(json.dumps({'question': request.question, 'records': [s.model_dump(exclude={
            'original_transcript', 'expert_id', 'expert_name', 'experience_years', 'domain', 'category', 'distance',
        }) for s in sources]}))
        allowed = {s.id for s in sources}
        def citation_id(value):
            # Local models sometimes format a valid ID as "record-id: UUID".
            return re.sub(r'^(?:record[-_ ]?id|source|id)\s*:\s*', '', value.strip(), flags=re.I).strip()
        cited = {citation_id(value) for value in result.source_ids}
        answer = re.sub(r'\[([^\[\]]+)\]', lambda match: '[' + citation_id(match.group(1)) + ']', result.answer)
        inline = set(re.findall(r'\[([^\[\]]+)\]', answer))
        if not cited or not cited <= allowed or not inline <= cited:
            return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
        cited_sources = [source for source in sources if source.id in cited]
        if result.insufficient_evidence:
            if not supported_positive_answer(answer, cited_sources):
                return ChatResponse(answer=INSUFFICIENT, sources=[], insufficient_evidence=True)
            logging.getLogger(__name__).warning('Corrected contradictory insufficient-evidence flag for cited records: %s', sorted(cited))
        text = answer
        if not inline:
            text += '\n\nSources: ' + ' '.join(f'[{s.id}]' for s in sources if s.id in cited)
        return ChatResponse(answer=text, sources=cited_sources, insufficient_evidence=False)
