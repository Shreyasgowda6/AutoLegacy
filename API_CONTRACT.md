# AutoLegacy Demo RAG API — v0.3

Base URL: `http://localhost:8000`. This demo always searches the prepared JSON knowledge base. There is no mode parameter or approval status. Unknown request fields are rejected. No API key is required.

## POST /api/chat

Request:

```json
{"question": "Why might an engine overheat?", "top_k": 3}
```

`question` is required and nonempty (maximum 20,000 characters). `top_k` is optional, defaults to 3, and supports 1–10.

Response **200**:

```json
{
  "answer": "No information available.",
  "sources": [],
  "insufficient_evidence": true
}
```

When relevant evidence exists, `answer` summarizes the retrieved records and `sources` contains the cited JSON records plus numeric cosine `distance` (lower is closer). Each source includes `id`, `problem`, `symptoms`, `operating_conditions`, `possible_causes`, `diagnostic_steps`, `confirmed_cause`, `solution`, `expert_insight`, `common_mistakes`, `safety_precautions` and `source_type: "synthetic"`. Answers cite `[record-id]`. All records are demonstration examples.

Records can also include nullable `expert_name`, `experience_years`, `domain`, `category`, `vehicle_make`, `vehicle_model`, `engine_type` and `original_transcript`. These details are preserved for retrieval and answer generation.

The embedding cache is created automatically on the first question and rebuilt when the JSON or embedding model changes. No approval or seed endpoint is required.

PowerShell:

```powershell
$result = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -ContentType 'application/json' `
  -Body '{"question":"Why might an engine overheat?"}'
$result.answer
$result.sources | Select-Object id, problem, distance
```

## GET /api/knowledge

No body. **200**: array of the records in `backend/data/knowledge_base.json`, with defaults filled for omitted optional fields. Edit this JSON file directly to update the knowledge base.

```powershell
Invoke-RestMethod http://localhost:8000/api/knowledge
```

## GET /api/health

No body. **200**:

```json
{"status":"ok","chat_model":"qwen3:1.7b","embedding_model":"bge-m3:latest"}
```

This confirms the HTTP process and configured model names, not Ollama connectivity.

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Errors

- **422**: invalid request; FastAPI `detail` array describes field errors.
- **503**: Ollama is unavailable, a model is missing, or its output is invalid; `detail` is an actionable string.
- **500**: JSON knowledge or cache cannot be read/indexed; `detail` is a generic string and server logs provide details.

## GET /api/experts

Returns all ten synthetic profiles from `data/experts.json`. Each has `id`, `name`, `specialty`, `experience_years`, `bio`, and `synthetic: true`.

## POST /api/feedback

Body: `{"kind":"gap","question":"buy new tyre","topic":"Knowledge gap","details":"Please add tyre selection knowledge","email":""}`. `kind` supports `gap` and `expert`; `topic` and `details` are required. Returns **201** `{"id":"uuid","status":"saved"}` after atomic persistence in ignored `data/feedback.json`.

## POST /api/interview/extract

Body: `{"expert_id":"expert-01","transcript":"Expert interview text"}` (nonempty, at most 20,000 characters). Returns a full Knowledge draft without saving. Only explicitly supplied facts are extracted; missing fields stay null/empty. **404** unknown expert, **422** no useful automotive problem.

## POST /api/knowledge

Body: `{"expert_id":"expert-01","transcript":"Original text","knowledge":{...}}`. The reviewed `knowledge` object requires `problem`, `vehicle_make`, `vehicle_model`, `engine_type`, `symptoms`, `operating_conditions`, `possible_causes`, `diagnostic_steps`, `confirmed_cause`, `solution`, `expert_insight`, `common_mistakes`, `safety_precautions`. Missing scalar facts can be null, lists can be empty. Returns **201** with backend-generated ID and expert metadata. Writes atomically to `knowledge_base.json`; the next chat reindexes automatically. Captured records remain labelled synthetic for this demonstration.

## POST /api/transcribe

Multipart `file`. WAV, MP3, M4A, WebM, Ogg and MP4 supported; maximum 25 MB and five minutes. Returns `{"text":"Interview transcription"}`. Uses faster-whisper locally on CPU; first use downloads the configured model. Temporary audio is deleted after processing. **413** size/duration, **415** unsupported format, **422** invalid/empty/no-speech audio, **503** missing dependency/model failure.

The frontend opens a prefilled feedback form when `insufficient_evidence` is true. Unsupported topics and incidental mentions in unrelated records return exactly `No information available.` with no sources. Records also include `expert_id` for contributor lookup.

Run one backend process per data directory; writes use an in-process lock. This remains a local demo without authentication. Feedback and capture endpoints are connected; approval/statistics endpoints are not included.
