import json
import os
import tempfile


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def write_json(path, data):
    """Atomically replace a JSON file; the caller holds the application lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
