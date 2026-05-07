from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PatentCreate(BaseModel):
    patent_number: str | None = None
    title: str
    abstract: str | None = None
    assignee: str | None = None
    inventors: list[str] = Field(default_factory=list)
    filing_date: date | None = None
    grant_date: date | None = None
    cpc_class: str | None = None
    source: Literal["USPTO", "WIPO"] = "USPTO"
    url: str | None = None


class PatentRecord(PatentCreate):
    id: UUID
    created_at: datetime
