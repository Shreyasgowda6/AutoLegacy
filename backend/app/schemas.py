from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Knowledge(Model):
    id: Text
    problem: Text
    expert_name: str | None = None
    expert_id: str | None = None
    experience_years: int | None = Field(default=None, ge=0)
    domain: str | None = None
    category: str | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    engine_type: str | None = None
    original_transcript: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    operating_conditions: list[str] = Field(default_factory=list)
    possible_causes: list[str] = Field(default_factory=list)
    diagnostic_steps: list[str] = Field(default_factory=list)
    confirmed_cause: str | None = None
    solution: str | None = None
    expert_insight: str | None = None
    common_mistakes: list[str] = Field(default_factory=list)
    safety_precautions: list[str] = Field(default_factory=list)
    source_type: Literal['synthetic'] = 'synthetic'


class ChatRequest(Model):
    question: Text
    top_k: int = Field(default=3, ge=1, le=10)


class Source(Knowledge):
    distance: float


class GroundedAnswer(Model):
    answer: Text
    source_ids: list[str]
    insufficient_evidence: bool


class ChatResponse(Model):
    answer: str
    sources: list[Source]
    insufficient_evidence: bool


class Expert(Model):
    id: str
    name: str
    specialty: str
    experience_years: int
    bio: str
    synthetic: bool = True


class FeedbackInput(Model):
    kind: Literal['gap', 'expert'] = 'gap'
    question: str = Field(default='', max_length=20000)
    topic: Text
    details: Text
    email: str = Field(default='', max_length=320)


class FeedbackReceipt(Model):
    id: str
    status: Literal['saved'] = 'saved'


class InterviewInput(Model):
    expert_id: Text
    transcript: Text


class ExtractedKnowledge(Model):
    problem: Text
    vehicle_make: str | None
    vehicle_model: str | None
    engine_type: str | None
    symptoms: list[str]
    operating_conditions: list[str]
    possible_causes: list[str]
    diagnostic_steps: list[str]
    confirmed_cause: str | None
    solution: str | None
    expert_insight: str | None
    common_mistakes: list[str]
    safety_precautions: list[str]

    @field_validator('vehicle_make', 'vehicle_model', 'engine_type', 'confirmed_cause', 'solution', 'expert_insight')
    @classmethod
    def missing_values(cls, value):
        if value is None or value.strip().lower() in {'', 'unknown', 'not specified', 'n/a', 'null'}:
            return None
        return value.strip()

    @field_validator('symptoms', 'operating_conditions', 'possible_causes', 'diagnostic_steps', 'common_mistakes', 'safety_precautions')
    @classmethod
    def clean_lists(cls, values):
        return [value.strip() for value in values if value.strip()]


class SaveKnowledge(InterviewInput):
    knowledge: ExtractedKnowledge
