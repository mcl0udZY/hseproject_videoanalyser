from datetime import datetime
from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    id: str
    status: str
    progress: int


class HighlightItem(BaseModel):
    rank: int
    start: float
    end: float
    score: float
    text: str
    analysis: str | None = None
    file: str | None = None


class ResultPayload(BaseModel):
    summary_text: str | None = None
    transcript_preview: str | None = None
    highlights: list[HighlightItem] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class JobDetailResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    progress: int
    asr_model: str
    language: str
    summary_mode: str
    error_message: str | None = None
    result_payload: ResultPayload | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobDetailResponse]
