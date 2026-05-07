from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_client
from backend.models.commit import CommitCreate, CommitRecord
from backend.services import github_watcher

router = APIRouter(prefix="/commits", tags=["commits"])


@router.post("/watch", response_model=list[CommitRecord])
def watch_and_store(
    repo: str = Query(..., description="owner/repo format"),
    keywords: list[str] = Query(default=None),
    since: datetime | None = Query(default=None),
):
    """Fetch matching commits from GitHub and persist them."""
    try:
        records = github_watcher.watch_repo(repo, keywords=keywords, since=since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = get_client()
    stored: list[dict] = []
    for r in records:
        payload = CommitCreate(
            repo_full_name=r.repo_full_name,
            sha=r.sha,
            author=r.author,
            message=r.message,
            keywords_matched=r.keywords_matched,
            raw_diff=r.raw_diff,
            committed_at=r.committed_at,
        ).model_dump(mode="json")
        result = db.table("commits").upsert(payload, on_conflict="sha").execute()
        if result.data:
            stored.extend(result.data)

    return stored


@router.get("/", response_model=list[CommitRecord])
def list_commits(limit: int = Query(50, le=200)):
    db = get_client()
    result = db.table("commits").select("*").order("committed_at", desc=True).limit(limit).execute()
    return result.data
