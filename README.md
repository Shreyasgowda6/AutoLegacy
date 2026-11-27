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

The integrated React frontend lives in `frontend/`. Run the backend HTTP server in one terminal and Vite in another:

```powershell
# Terminal 1, from the repository root
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2, from the repository root
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the Vite URL (normally http://localhost:5173). The original frontend design and presentation content are retained. Search retrieves from the same JSON knowledge base used by the CLI and updates the existing answer card. Expert profiles, related documents and feedback forms remain as originally designed; feedback backend integration is deferred.

See [backend instructions](backend/README.md), [frontend instructions](frontend/README.md), and [the shared HTTP API contract](API_CONTRACT.md).
