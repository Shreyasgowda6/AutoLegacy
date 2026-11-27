from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class KnowledgeInput(Model):
    expert_name: Name
    experience_years: int = Field(ge=0, le=80)
    domain: str = 'Automotive'
    category: str = 'Engine diagnostics'
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    engine_type: str | None = None
    problem: Text
    symptoms: list[str] = Field(default_factory=list)
    operating_conditions: list[str] = Field(default_factory=list)
    possible_causes: list[str] = Field(default_factory=list)
    diagnostic_steps: list[str] = Field(default_factory=list)
    confirmed_cause: str | None = None
    solution: str | None = None
    expert_insight: str | None = None
    common_mistakes: list[str] = Field(default_factory=list)
    safety_precautions: list[str] = Field(default_factory=list)
    original_transcript: str = Field(default='', max_length=100000)
    source_type: Literal['expert_interview', 'synthetic'] = 'expert_interview'


class KnowledgeRecord(KnowledgeInput):
    id: str = Field(default_factory=lambda: str(uuid4()))
    verification_status: Literal['pending', 'approved', 'unverified'] = 'pending'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Expert(Model):
    name: Name
    experience_years: int = Field(ge=0, le=80)
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    engine_type: str | None = None


class Message(Model):
    role: Literal['user', 'assistant']
    content: Text


class InterviewRequest(Model):
    expert: Expert
    messages: list[Message] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def transcript_size(self):
        if len('\n'.join(f'{m.role}: {m.content}' for m in self.messages)) > 100000:
            raise ValueError('Complete interview transcript must not exceed 100000 characters')
        return self


class InterviewResponse(Model):
    next_question: str | None
    missing_information: list[str]
    interview_complete: bool


class ExtractedKnowledge(Model):
    # All model-generated fields are required for the strict OpenAI JSON schema.
    problem: Text
    symptoms: list[str]
    operating_conditions: list[str]
    possible_causes: list[str]
    diagnostic_steps: list[str]
    confirmed_cause: str | None
    solution: str | None
    expert_insight: str | None
    common_mistakes: list[str]
    safety_precautions: list[str]


class ChatRequest(Model):
    question: Text
    demo_mode: bool = False
    top_k: int = Field(default=3, ge=1, le=10)


class Source(KnowledgeRecord):
    distance: float


class GroundedAnswer(Model):
    answer: Text
    source_ids: list[str]
    insufficient_evidence: bool


class ChatResponse(Model):
    answer: str
    sources: list[Source]
    insufficient_evidence: bool
    demo_mode: bool


class TranscriptionResponse(Model):
    text: str


class HealthResponse(Model):
    status: Literal['ok'] = 'ok'
    ai_configured: bool


class StatsResponse(Model):
    total_records: int
    approved_records: int
    pending_records: int
    synthetic_records: int
    expert_insights: int
    recent_activity: list[KnowledgeRecord]
