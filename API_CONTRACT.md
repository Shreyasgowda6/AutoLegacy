# AutoLegacy API contract — v0.1

Base URL: `http://localhost:8000`. JSON uses snake_case. Interactive documentation and complete generated JSON schemas: `/docs` and `/openapi.json`. CORS defaults to `http://localhost:5173` and `http://localhost:3000`. Dates are UTC ISO-8601. No authentication is implemented for this local MVP.

## Common models

`KnowledgeInput` is the body for create and update. Required fields are `expert_name` (nonempty), `experience_years` (0–80) and `problem` (nonempty). Other fields default as shown:

```json
{
  "expert_name": "Senior Mechanic",
  "experience_years": 30,
  "domain": "Automotive",
  "category": "Engine diagnostics",
  "vehicle_make": null,
  "vehicle_model": null,
  "engine_type": null,
  "problem": "Engine overheating",
  "symptoms": [],
  "operating_conditions": [],
  "possible_causes": [],
  "diagnostic_steps": [],
  "confirmed_cause": null,
  "solution": null,
  "expert_insight": null,
  "common_mistakes": [],
  "safety_precautions": [],
  "original_transcript": "",
  "source_type": "expert_interview"
}
```

`source_type` is `expert_interview` or `synthetic` and cannot be changed after creation. Synthetic data must never be represented as a real expert's knowledge. Unknown fields are rejected. `PUT` replaces all input fields, so send the full editable record.

`KnowledgeRecord` adds server-owned `id`, `verification_status` and `created_at`:

```json
{
  "id": "generated-uuid",
  "verification_status": "pending",
  "created_at": "2026-11-27T12:00:00Z"
}
```

The actual response includes **all** `KnowledgeInput` fields plus these metadata fields. Expert records start `pending` and become `approved` only through approval. Synthetic records remain `unverified`. Remove these three metadata fields before sending a record back to create/update.

`InterviewRequest` is shared by interviewing and extraction:

```json
{
  "expert": {
    "name": "Senior Mechanic",
    "experience_years": 30,
    "vehicle_make": "Volkswagen",
    "vehicle_model": "Golf",
    "engine_type": null
  },
  "messages": [
    {"role": "user", "content": "The engine overheats in slow traffic."},
    {"role": "assistant", "content": "What did you observe when it overheated?"},
    {"role": "user", "content": "The temperature warning appeared. The cause was not confirmed."}
  ]
}
```

Expert name and experience are required. Vehicle fields are optional. Messages must contain 1–30 entries with `role` equal to `user` (expert) or `assistant` (interviewer), and nonempty `content`. The complete transcript (including role labels) is limited to 100,000 characters. Include the full history on each request. The interview endpoint expects the last message to be `user` unless the three-question limit has already been reached.

The curl examples below use POSIX shell quoting. In PowerShell use `curl.exe` with request JSON saved in a UTF-8 file and `--data-binary @request.json`, or use `Invoke-RestMethod`.

## GET /api/health

No body. **200**:

```json
{"status": "ok", "ai_configured": false}
```

`ai_configured` checks key presence, not API access or credits.

```bash
curl http://localhost:8000/api/health
```

## POST /api/transcribe

Multipart form with one `file` field; supported extensions WAV, MP3, M4A and WebM. Default maximum file size is 25,000,000 bytes. File headers are checked and the provider validates decoding. **200**:

```json
{"text": "The engine overheats in slow traffic."}
```

```bash
curl -X POST http://localhost:8000/api/transcribe -F 'file=@recording.webm'
```

Errors: **413** oversized audio, **415** unsupported extension, **422** empty/invalid audio or missing file, **503** missing API key, **502** provider error or undetectable structured service failure. No audio is persisted by the application.

## POST /api/interview/next

Body: `InterviewRequest`. **200**:

```json
{
  "next_question": "What conditions made the temperature rise?",
  "missing_information": ["Operating conditions", "Diagnostic steps"],
  "interview_complete": false
}
```

After three `assistant` messages, or if sufficient knowledge is captured, `interview_complete` is true and `next_question` is null. The limit is based on supplied history; the server does not store interview sessions.

```bash
curl -X POST http://localhost:8000/api/interview/next -H 'Content-Type: application/json' -d '{"expert":{"name":"Senior Mechanic","experience_years":30},"messages":[{"role":"user","content":"The engine overheats in slow traffic."}]}'
```

## POST /api/knowledge/extract

Body: `InterviewRequest`. **200**: a full `KnowledgeRecord` draft with `verification_status: "pending"`, missing facts represented by null/empty arrays, original conversation in `original_transcript` and backend-generated metadata. Does **not** save or index the draft. Its ID is temporary; saving creates a new ID.

```bash
curl -X POST http://localhost:8000/api/knowledge/extract -H 'Content-Type: application/json' -d '{"expert":{"name":"Senior Mechanic","experience_years":30},"messages":[{"role":"user","content":"The engine overheats in slow traffic. The cause is not yet confirmed."}]}'
```

Frontend flow: show editable draft → remove server-owned metadata → POST reviewed `KnowledgeInput` → approve the returned saved record ID.

## POST /api/knowledge

Body: `KnowledgeInput`. **201**: complete saved `KnowledgeRecord`. Does not index or approve. `id`, `verification_status` and `created_at` must not be submitted.

```bash
curl -X POST http://localhost:8000/api/knowledge -H 'Content-Type: application/json' -d '{"expert_name":"Senior Mechanic","experience_years":30,"problem":"Engine overheating","possible_causes":["Coolant leak"]}'
```

## GET /api/knowledge

No body. **200**: array of complete `KnowledgeRecord` objects, or `[]`. Returns editable local records; the bundled synthetic demo dataset is separate. No pagination or server-side filters in this MVP.

```bash
curl http://localhost:8000/api/knowledge
```

## GET /api/knowledge/{id}

No body. **200**: complete `KnowledgeRecord`. **404** if absent.

```bash
curl http://localhost:8000/api/knowledge/RECORD_ID
```

## PUT /api/knowledge/{id}

Body: full `KnowledgeInput`. **200**: updated full `KnowledgeRecord`. Preserves ID and creation time. Any content change resets expert approval to `pending` and removes existing vectors. An identical body preserves approval. `source_type` is immutable. **404** absent; **422** invalid body/source type change.

```bash
curl -X PUT http://localhost:8000/api/knowledge/RECORD_ID -H 'Content-Type: application/json' -d '{"expert_name":"Senior Mechanic","experience_years":30,"problem":"Engine overheating","possible_causes":["Coolant leak"],"expert_insight":"Record the conditions when the warning appears."}'
```

If vector cleanup fails, the operation returns **500** but the edited record is already saved as pending. Refetch the record; reapproval will rebuild its vector. Retrieval will exclude the stale vector.

## DELETE /api/knowledge/{id}

No body. **204**, empty response. Removes the vector and JSON record. **404** absent. If vector cleanup fails, deletion returns **500** and the JSON record remains; retry after recovery.

```bash
curl -X DELETE http://localhost:8000/api/knowledge/RECORD_ID
```

## POST /api/knowledge/{id}/approve

No body. Call only after expert review. **200**: complete record with `verification_status: "approved"`. Generates an embedding, upserts into verified Chroma collection, then persists approval. Repeated calls do not duplicate vectors. A failed first approval leaves the record pending. **404** absent; **422** synthetic record; **503** missing key; **502** embedding provider failure.

```bash
curl -X POST http://localhost:8000/api/knowledge/RECORD_ID/approve
```

## POST /api/chat

Body:

```json
{"question": "What knowledge do we have about engine overheating?", "demo_mode": false, "top_k": 3}
```

`question` required and nonempty. `demo_mode` defaults to false; `top_k` defaults to 3 and supports 1–10. **200**:

```json
{
  "answer": "The knowledge base does not contain sufficient information to answer this question.",
  "sources": [],
  "insufficient_evidence": true,
  "demo_mode": false
}
```

For a grounded answer, `sources` contains full `KnowledgeRecord` objects with an additional numeric `distance` (cosine distance; lower is closer), including the requested `id`, `expert_name`, `problem`, `expert_insight`, `source_type` and `verification_status` fields. Answer citations use `[record-id]`. Only cited retrieved records are returned. Unknown source IDs in either structured references or bracketed answer citations cause an insufficient-evidence response.

With demo mode off, only current approved expert records are eligible. With demo mode on, both verified expert knowledge and separately indexed unverified synthetic examples are eligible. Display a prominent synthetic label whenever a source has `source_type: "synthetic"`. `demo_mode: true` indicates permission to include demo records, not that every returned source is synthetic.

No relevant results is a successful **200**, not an error. An empty verified knowledge base does not call OpenAI. Nonempty indexed queries require embeddings and, when relevant results exist, generation.

```bash
curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"question":"What knowledge do we have about engine overheating?","demo_mode":false}'
```

## GET /api/stats

No body. **200**:

```json
{
  "total_records": 0,
  "approved_records": 0,
  "pending_records": 0,
  "synthetic_records": 0,
  "expert_insights": 0,
  "recent_activity": []
}
```

Counts refer to editable local JSON knowledge records. `expert_insights` counts expert-interview records with nonempty insights, including pending records. `recent_activity` contains up to five complete records sorted by creation time, newest first; it is not an edit audit log. Bundled synthetic demo records are excluded from these counts.

```bash
curl http://localhost:8000/api/stats
```

## Errors and frontend handling

- **422**: FastAPI validation error as `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`, or a business validation string such as `{"detail":"Synthetic records cannot be approved as expert knowledge"}`.
- **404**: `{"detail":"Knowledge record not found"}`.
- **503**: `{"detail":"OPENAI_API_KEY is not configured on the backend"}`.
- **502**: sanitized provider/refusal/structured-output failure; `detail` is a string. A corrupt or undecodable audio provider error also returns 502.
- **500**: `{"detail":"Server operation failed. Check the backend logs."}` for storage/index errors; no internal paths or secrets are returned.

The UI should handle string and array `detail` values, show loading states during AI operations, and permit text input when audio fails. Never send an OpenAI key from the frontend. Do not automatically approve extracted drafts.
