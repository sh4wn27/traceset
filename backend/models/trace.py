from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


TraceType = Literal["commit_paper", "commit_patent", "paper_patent", "trilinear"]


class TraceCreate(BaseModel):
    commit_id: UUID | None = None
    paper_id: UUID | None = None
    patent_id: UUID | None = None
    trace_type: TraceType
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    model_version: str
    prompt_version: int = 1

    @field_validator("patent_id", mode="after")
    @classmethod
    def at_least_two_artifacts(cls, v: UUID | None, info) -> UUID | None:
        data = info.data
        filled = sum(
            x is not None
            for x in (data.get("commit_id"), data.get("paper_id"), v)
        )
        if filled < 2:
            raise ValueError("A trace must link at least two artifacts.")
        return v


class TraceResult(TraceCreate):
    id: UUID
    created_at: datetime
