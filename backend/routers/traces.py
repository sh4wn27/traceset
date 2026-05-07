from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_client
from backend.models.trace import TraceCreate, TraceResult
from backend.services import trace_engine
from backend.services.github_watcher import CommitRecord as SvcCommit
from backend.services.scholar_sync import PaperRecord as SvcPaper

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("/analyze", response_model=TraceResult)
def analyze_pair(commit_id: UUID, paper_id: UUID):
    """Run the forensic analyst on a stored commit/paper pair."""
    db = get_client()

    commit_row = db.table("commits").select("*").eq("id", str(commit_id)).single().execute()
    if not commit_row.data:
        raise HTTPException(status_code=404, detail="Commit not found.")

    paper_row = db.table("papers").select("*").eq("id", str(paper_id)).single().execute()
    if not paper_row.data:
        raise HTTPException(status_code=404, detail="Paper not found.")

    commit = _row_to_commit(commit_row.data)
    paper = _row_to_paper(paper_row.data)

    try:
        result = trace_engine.analyze(commit, paper)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    payload = TraceCreate(
        commit_id=commit_id,
        paper_id=paper_id,
        trace_type="commit_paper",
        confidence_score=result.confidence_score,
        reasoning=result.reasoning,
        model_version=result.model_version,
        prompt_version=result.prompt_version,
    ).model_dump(mode="json")

    stored = db.table("traces").insert(payload).execute()
    return stored.data[0]


@router.get("/", response_model=list[TraceResult])
def list_traces(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, le=200),
):
    db = get_client()
    result = (
        db.table("traces")
        .select("*")
        .gte("confidence_score", min_confidence)
        .order("confidence_score", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def _row_to_commit(row: dict) -> SvcCommit:
    committed_at = row.get("committed_at")
    if committed_at and isinstance(committed_at, str):
        committed_at = datetime.fromisoformat(committed_at)
    return SvcCommit(
        repo_full_name=row["repo_full_name"],
        sha=row["sha"],
        author=row.get("author"),
        message=row.get("message"),
        keywords_matched=row.get("keywords_matched") or [],
        raw_diff=row.get("raw_diff"),
        committed_at=committed_at,
    )


def _row_to_paper(row: dict) -> SvcPaper:
    pub = row.get("published_at")
    if pub and isinstance(pub, str):
        pub = date.fromisoformat(pub)
    return SvcPaper(
        title=row["title"],
        abstract=row.get("abstract"),
        authors=row.get("authors") or [],
        published_at=pub,
        url=row.get("url"),
        categories=row.get("categories") or [],
        arxiv_id=row.get("arxiv_id"),
        semantic_scholar_id=row.get("semantic_scholar_id"),
    )
