# AutoLegacy — Demo RAG

A basic local RAG pipeline for synthetic automotive knowledge:

**JSON records → Ollama embeddings → cosine similarity retrieval → Ollama answer with sources**

The backend uses `qwen3:1.7b` for answers and `bge-m3:latest` for embeddings. No API key, approval workflow, mode toggle, or external vector database is required. The ten bundled records are synthetic demonstration examples.

In an activated Python environment:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m app.cli
```

Type questions in the terminal; type `exit` to stop. Ollama must be running with both configured models installed.

See [backend instructions](backend/README.md) and [the small HTTP API contract](API_CONTRACT.md). `frontend/` remains available for the separately developed UI.
