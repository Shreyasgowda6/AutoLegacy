# Basic demo RAG

This project answers questions from a prepared, extracted JSON knowledge base. All bundled knowledge is synthetic demonstration data.

## Run in the terminal

From your current activated virtual environment:

```powershell
cd C:\Users\suhai\Desktop\AutoLegacy\backend
python -m app.cli
```

Enter a question such as `Why might an engine overheat?`. Type `exit` to quit. The CLI directly runs the RAG pipeline; no browser or HTTP server is required. The first question builds the embedding cache automatically. If an HTTP server is already running, you can stop it with Ctrl+C before using the CLI.

One question at a time:

```powershell
python -m app.cli ask "Why might an engine overheat?"
```

To explicitly rebuild embeddings:

```powershell
python -m app.cli index
```

## First-time setup on another machine

Install Python 3.10+ and Ollama, then:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen3:1.7b
ollama pull bge-m3:latest
.\.venv\Scripts\python.exe -m app.cli
```

Ollama and both models are already installed on this workstation. No OpenAI key is used.

## Structure

```text
backend/
  app/
    config.py       # Paths and Ollama model names
    schemas.py      # Knowledge, question and answer shapes
    ollama.py       # Local embeddings and generation
    rag.py          # JSON loading, embedding cache and cosine retrieval
    cli.py          # Interactive terminal chat
    main.py         # Optional FastAPI wrapper
  data/
    knowledge_base.json  # The only knowledge source; edit this file
    embeddings.json      # Generated cache, ignored by Git
  tests/test_rag.py
  .env.example
  requirements.txt
```

## How it works

1. Read `data/knowledge_base.json` and validate records and unique IDs.
2. Embed each structured JSON record with local `bge-m3` and cache vectors in `data/embeddings.json`.
3. Embed the question and calculate cosine distances against the cached vectors.
4. Retrieve up to three relevant JSON records (maximum distance 0.65 by default).
5. Give only those records to `qwen3:1.7b`; return an answer and source records.

The JSON file is authoritative. Changing it or the embedding model automatically rebuilds the cache on the next question. A corrupt cache is also rebuilt. No Chroma, database service, indexing approval, or knowledge-status fields are needed for this small dataset. An unrelated question returns an insufficient-information response when no records meet the threshold. Citation IDs are checked against retrieved records.

Edit the JSON directly to replace or add examples. Each record needs unique `id` and nonempty `problem`; the other supported fields are shown in the bundled file. Keep records and retrieved context concise for the local model's 8192-token context window. Small models may produce imperfect summaries; this is a demonstration, not vehicle repair guidance.

`.env` controls paths, models, and the distance threshold. Paths are relative to `backend/`. Old `chroma_db/` and `data/knowledge.json` files, if present, are no longer used and have been left intact.

## Optional HTTP server

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
$result = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -ContentType 'application/json' `
  -Body '{"question":"Why might an engine overheat?"}'
$result.answer
```

See [API_CONTRACT.md](../API_CONTRACT.md). This replaces the previous larger backend API; interview, extraction, transcription, approval and CRUD endpoints are removed. The frontend should use the three endpoints in the new contract.

## Tests

```powershell
python -m pytest -q
```

Tests use fake Ollama responses and temporary JSON/cache files, so they require no model or network connection.
