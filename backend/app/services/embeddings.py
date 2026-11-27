import hashlib
import json
from functools import cached_property

from app.schemas import KnowledgeRecord


def document(record: KnowledgeRecord) -> str:
    fields = record.model_dump(exclude={'id', 'created_at', 'verification_status', 'original_transcript'})
    return json.dumps(fields, ensure_ascii=False, sort_keys=True)


def fingerprint(record: KnowledgeRecord) -> str:
    return hashlib.sha256(document(record).encode()).hexdigest()


class VectorIndex:
    def __init__(self, settings, ai):
        self.settings = settings
        self.ai = ai

    @cached_property
    def client(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        return chromadb.PersistentClient(path=str(self.settings.chroma_path),
                                       settings=ChromaSettings(anonymized_telemetry=False))

    def collection(self, demo=False):
        return self.client.get_or_create_collection(
            name='synthetic_demo' if demo else 'verified_experts',
            embedding_function=None,
            metadata={'hnsw:space': 'cosine'},
        )

    def upsert(self, record: KnowledgeRecord):
        demo = record.source_type == 'synthetic'
        if not demo and record.verification_status != 'approved':
            raise ValueError('Only approved expert knowledge may be indexed')
        text = document(record)
        embedding = self.ai.embed(text)
        self.collection(demo).upsert(
            ids=[record.id], documents=[text], embeddings=[embedding],
            metadatas=[{'fingerprint': fingerprint(record), 'source_type': record.source_type,
                        'expert_name': record.expert_name, 'embedding_model': self.settings.embedding_model}],
        )

    def delete(self, record_id: str):
        if self.settings.chroma_path.exists():
            for demo in (False, True):
                self.collection(demo).delete(ids=[record_id])

    def search(self, question: str, demo_mode: bool, top_k: int):
        collections = [self.collection(False)]
        if demo_mode:
            collections.append(self.collection(True))
        if not any(c.count() for c in collections):
            return []
        embedding = self.ai.embed(question)
        hits = []
        for collection in collections:
            count = collection.count()
            if not count:
                continue
            result = collection.query(query_embeddings=[embedding], n_results=min(top_k, count),
                                      include=['distances', 'metadatas'])
            for record_id, distance, metadata in zip(result['ids'][0], result['distances'][0], result['metadatas'][0]):
                if distance <= self.settings.relevance_threshold and metadata.get('embedding_model') == self.settings.embedding_model:
                    hits.append((record_id, distance, metadata))
        return sorted(hits, key=lambda hit: hit[1])[:top_k]
