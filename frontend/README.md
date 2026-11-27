# AutoLegacy frontend

Imported from [Shreyasgowda6/AutoLegacy, frontend branch](https://github.com/Shreyasgowda6/AutoLegacy/tree/frontend), source commit `e5e3de2`. The original Garage Handbook layout, logo, initial sample answer, related documents, helpfulness buttons and feedback form design are retained. Search, feedback and expert interview capture are connected to the local backend. The expert directory and interview page extend the same visual style; there is no mode toggle or separate knowledge-source sidebar.

The original Garage Handbook style and related documents remain. The expert section now lists ten synthetic profiles and each can be selected for an interview. Feedback reports are saved through the backend; a no-information answer automatically opens the gap report. The sticky header and Explore navigation let you return to the page top.

## Expert Interview

Choose Expert Interview in the header or Interview this expert in the directory. Select an expert, paste text or record/upload audio, extract the structured knowledge, review/edit it, and choose Add to knowledge base. The next search includes the new JSON record automatically.

Recording requires browser microphone permission. Install the updated backend requirements before using local audio transcription; the first use downloads a small Whisper model. Text capture does not need Whisper. Audio is temporarily processed on the backend and then deleted.

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

API shapes are defined in [API_CONTRACT.md](../API_CONTRACT.md). There is one demo knowledge base. Missing information returns the canonical no-information message and opens feedback; failed requests preserve the question for retry. Generated answers appear in the original answer card and contributors are resolved through the expert directory. Captured interviews remain synthetic demonstration records.
