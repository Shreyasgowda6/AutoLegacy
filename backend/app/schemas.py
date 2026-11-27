from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Knowledge(Model):
    id: Text
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
