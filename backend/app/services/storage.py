import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from app.schemas import KnowledgeRecord


class Storage:
    """One process, thread-safe JSON store; run Uvicorn with one worker."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()

    def all(self) -> list[KnowledgeRecord]:
        with self.lock:
            if not self.path.exists():
                return []
            return [KnowledgeRecord.model_validate(x) for x in json.loads(self.path.read_text(encoding='utf-8'))]

    def get(self, record_id: str) -> KnowledgeRecord:
        for record in self.all():
            if record.id == record_id:
                return record
        raise KeyError(record_id)

    def write(self, records: list[KnowledgeRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, delete=False) as stream:
                temporary = stream.name
                json.dump([x.model_dump(mode='json') for x in records], stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def put(self, record: KnowledgeRecord) -> KnowledgeRecord:
        with self.lock:
            records = self.all()
            records = [x for x in records if x.id != record.id] + [record]
            self.write(records)
            return record

    def delete(self, record_id: str):
        with self.lock:
            self.get(record_id)
            self.write([x for x in self.all() if x.id != record_id])
