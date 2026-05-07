from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommitCreate(BaseModel):
    repo_full_name: str
    sha: str
    author: str | None = None
    message: str | None = None
    keywords_matched: list[str] = Field(default_factory=list)
    raw_diff: str | None = None
    committed_at: datetime | None = None


class CommitRecord(CommitCreate):
    id: UUID
    created_at: datetime
