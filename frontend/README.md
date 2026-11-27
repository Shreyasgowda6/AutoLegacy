# AutoLegacy frontend

Imported from [Shreyasgowda6/AutoLegacy, frontend branch](https://github.com/Shreyasgowda6/AutoLegacy/tree/frontend), source commit `e5e3de2`. The original layout, stylesheet, logo, initial sample answer, expert profile, related documents, helpfulness buttons and feedback forms are retained. Only search is connected to the local RAG backend: submitting a question updates the existing question-and-answer card. No knowledge-source sidebar, new navigation items, or mode toggle is added.

The expert profile and related documents remain the original presentation content; they are not returned by RAG or evidence of authorship of a generated answer. Feedback forms retain their original demo behavior. Their backend integration is deferred.

## Run locally

Keep Ollama running. In terminal 1:

```powershell
cd C:\Users\suhai\Desktop\AutoLegacy\backend
python -m uvicorn app.main:app --reload --port 8000
```

In terminal 2:

```powershell
cd C:\Users\suhai\Desktop\AutoLegacy\frontend
npm.cmd ci
npm.cmd run dev
```

Open the URL printed by Vite (normally <http://localhost:5173>). Type a question and press Enter; the original mobile layout also exposes the search button. Initial model loading may take longer. Both the terminal CLI and frontend use the same JSON knowledge base and RAG backend.

Vite proxies `/api` to `http://127.0.0.1:8000`, so no frontend configuration is needed for local development. To use another backend, copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to its origin, then restart Vite. The backend must allow that frontend origin through CORS when using a direct cross-origin URL.

## Verify/build

```powershell
npx.cmd tsc --noEmit
npm.cmd run build
```

The production files are written to `dist/`. Production hosting must forward `/api` to FastAPI or build with `VITE_API_BASE_URL` set to the backend origin; the Vite dev proxy is only for local development. This task does not deploy the site.

API shapes are defined in [API_CONTRACT.md](../API_CONTRACT.md). There is one demo knowledge base and no mode toggle. A loading notice appears while searching; errors are shown without losing the question so it can be retried. Generated answers are displayed in the original answer card; the rest of the original content remains intact.
