from fastapi import APIRouter, HTTPException, Query

from backend.database import get_client
from backend.models.paper import PaperCreate, PaperRecord
from backend.services import scholar_sync

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/sync", response_model=list[PaperRecord])
def sync_and_store(
    authors: list[str] = Query(..., description="List of author names to search"),
    max_results: int = Query(20, le=100),
):
    """Fetch papers for given authors from ArXiv + Semantic Scholar and store them."""
    records = scholar_sync.fetch_papers_by_authors(authors, max_results=max_results)

    db = get_client()
    stored: list[dict] = []
    for r in records:
        payload = PaperCreate(
            arxiv_id=r.arxiv_id,
            semantic_scholar_id=r.semantic_scholar_id,
            title=r.title,
            abstract=r.abstract,
            authors=r.authors,
            published_at=r.published_at,
            url=r.url,
            categories=r.categories,
        ).model_dump(mode="json")
        result = (
            db.table("papers")
            .upsert(payload, on_conflict="arxiv_id")
            .execute()
        )
        if result.data:
            stored.extend(result.data)

    return stored


@router.get("/", response_model=list[PaperRecord])
def list_papers(limit: int = Query(50, le=200)):
    db = get_client()
    result = db.table("papers").select("*").order("published_at", desc=True).limit(limit).execute()
    return result.data
