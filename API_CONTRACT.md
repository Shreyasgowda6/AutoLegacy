# AutoLegacy Demo RAG API — v0.2

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
  "answer": "The JSON knowledge base does not contain sufficient information to answer this question.",
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

The previous interview, extraction, audio, approval, statistics and knowledge-write endpoints have been removed. The frontend should use this contract.
