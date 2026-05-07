from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaperCreate(BaseModel):
    arxiv_id: str | None = None
    semantic_scholar_id: str | None = None
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_at: date | None = None
    url: str | None = None
    categories: list[str] = Field(default_factory=list)


class PaperRecord(PaperCreate):
    id: UUID
    created_at: datetime
