from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_client
from backend.models.patent import PatentCreate, PatentRecord
from backend.services import patent_tracker

router = APIRouter(prefix="/patents", tags=["patents"])


@router.post("/search", response_model=list[PatentRecord])
def search_and_store(
    assignee: str | None = Query(default=None),
    cpc_class: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(50, le=200),
):
    """Search USPTO patents and persist results."""
    try:
        records = patent_tracker.search_patents(
            assignee=assignee,
            cpc_class=cpc_class,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = get_client()
    stored: list[dict] = []
    for r in records:
        payload = PatentCreate(
            patent_number=r.patent_number,
            title=r.title,
            abstract=r.abstract,
            assignee=r.assignee,
            inventors=r.inventors,
            filing_date=r.filing_date,
            grant_date=r.grant_date,
            cpc_class=r.cpc_class,
            source=r.source,
            url=r.url,
        ).model_dump(mode="json")
        result = (
            db.table("patents")
            .upsert(payload, on_conflict="patent_number")
            .execute()
        )
        if result.data:
            stored.extend(result.data)

    return stored


@router.get("/", response_model=list[PatentRecord])
def list_patents(limit: int = Query(50, le=200)):
    db = get_client()
    result = db.table("patents").select("*").order("grant_date", desc=True).limit(limit).execute()
    return result.data
