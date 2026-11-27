# AutoLegacy backend

FastAPI MVP for capturing automotive interviews, extracting draft knowledge, expert review and approval, and retrieval with cited sources. Python 3.10+ is supported; this workspace uses Python 3.12.

## Start on Windows

From the repository root, create the environment if it does not already exist:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `backend/.env`, then start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

No environment activation is required. If `python` opens the Microsoft Store, use an installed interpreter's absolute path when creating the virtual environment. The existing workspace environment has already been created with Python 3.12.

Swagger: <http://localhost:8000/docs>. OpenAPI: <http://localhost:8000/openapi.json>. Health: <http://localhost:8000/api/health>.

Storage, health, stats, and an empty-knowledge response work without an API key. Interviewing, extraction, approval/embedding, transcription, and answers based on indexed records require a funded OpenAI API key. `ai_configured` indicates that a key is present; it does not check validity or credits.

## Text workflow

1. Send expert details and `messages` to `/api/interview/next`. Append each question as `assistant` and answer as `user`; keep the entire history. The backend stops after three assistant questions. This is a stateless MVP; restarting the history restarts the limit.
2. Send the completed history to `/api/knowledge/extract`. This returns a pending draft without saving it.
3. Show the draft for expert review. Remove `id`, `created_at`, and `verification_status` before POSTing the reviewed fields to `/api/knowledge`; the backend owns those fields.
4. Call `/api/knowledge/{id}/approve`. Only successful embedding/indexing results in persisted approval. Approval represents the reviewer's explicit action; there is no authentication in this MVP.
5. Ask `/api/chat` with `demo_mode: false`. Sources include IDs and full stored records. Changes to any content field reset approval and remove vectors. An identical PUT preserves approval.

See [the shared contract](../API_CONTRACT.md) for all request and response shapes.

## Synthetic demonstration data

Ten explicitly synthetic, unverified examples live in `data/demo_knowledge.json`. They contain possible causes, not confirmed repairs or real expert experience. Index them separately:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_database
```

Seeding uses paid embeddings and is repeatable without duplicate vectors. Synthetic records are only retrieved when chat explicitly enables `demo_mode`. They cannot be approved as expert knowledge. The bundled demo file is separate from the editable expert knowledge list and statistics. Creating a synthetic record through CRUD does not automatically index it; the seed script indexes the bundled demonstration file.

## Configuration and persistence

- `.env.example` lists configuration; paths are relative to `backend/`, independent of the shell's current directory.
- `RELEVANCE_THRESHOLD` is maximum cosine distance (0–2); smaller means stricter. Default 0.65 is a starting point to tune with real interviews.
- `MAX_AUDIO_BYTES` defaults to 25,000,000; WAV, MP3, M4A and WebM headers are checked. The provider validates the full audio encoding. Upload parsing happens before the application checks size; use a request body limit at a reverse proxy if deploying publicly.
- JSON writes use an atomic file replacement and an in-process lock. Run one Uvicorn worker and one server instance against a given data directory. Multi-process storage coordination is outside this MVP.
- Chroma uses separate persistent cosine collections for approved expert and synthetic data. Retrieval checks the authoritative JSON status and content fingerprint, so stale vectors cannot expose edited or unapproved records. A failed edit cleanup leaves the record pending; retry the edit or reapprove after the service recovers.
- Changing the embedding model requires rebuilding `chroma_db/` and reapproving expert records/reseeding demos. Do this only with the server stopped and after backing up data.
- Keep `.env`, real `data/knowledge.json`, audio and `chroma_db/` out of Git. Back up your JSON and Chroma directory together.
- There is no authentication or deployment configuration; this implementation is for a local demonstration.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests mock OpenAI and use temporary JSON plus real persistent Chroma collections. They cover the full text workflow, approval failures, reapproval, CRUD, atomic persistence, retrieval thresholds, stale vectors, synthetic separation, interview limits, and audio validation. No tests require a key or API credits.
