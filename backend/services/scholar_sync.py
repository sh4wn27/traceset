"""ScholarSync sentinel: fetches papers by author from ArXiv and Semantic Scholar."""

from dataclasses import dataclass
from datetime import date

import arxiv
from semanticscholar import SemanticScholar


@dataclass
class PaperRecord:
    title: str
    abstract: str | None
    authors: list[str]
    published_at: date | None
    url: str | None
    categories: list[str]
    arxiv_id: str | None = None
    semantic_scholar_id: str | None = None


def fetch_papers_by_authors(
    author_names: list[str],
    max_results: int = 20,
) -> list[PaperRecord]:
    """Fetch recent papers for each author from ArXiv and Semantic Scholar.

    Deduplicates by arxiv_id then by title (case-insensitive).
    """
    seen_arxiv: set[str] = set()
    seen_titles: set[str] = set()
    results: list[PaperRecord] = []

    for name in author_names:
        results.extend(_fetch_arxiv(name, max_results, seen_arxiv, seen_titles))
        results.extend(_fetch_s2(name, max_results, seen_titles))

    return results


def _fetch_arxiv(
    author: str,
    max_results: int,
    seen_arxiv: set[str],
    seen_titles: set[str],
) -> list[PaperRecord]:
    search = arxiv.Search(
        query=f"au:{author}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    out: list[PaperRecord] = []
    for result in search.results():
        aid = result.get_short_id()
        title_key = result.title.lower()
        if aid in seen_arxiv or title_key in seen_titles:
            continue
        seen_arxiv.add(aid)
        seen_titles.add(title_key)
        out.append(
            PaperRecord(
                title=result.title,
                abstract=result.summary,
                authors=[str(a) for a in result.authors],
                published_at=result.published.date() if result.published else None,
                url=result.entry_id,
                categories=result.categories,
                arxiv_id=aid,
            )
        )
    return out


def _fetch_s2(
    author: str,
    max_results: int,
    seen_titles: set[str],
) -> list[PaperRecord]:
    sch = SemanticScholar()
    try:
        results = sch.search_paper(author, limit=max_results)
    except Exception:
        return []

    out: list[PaperRecord] = []
    for paper in results:
        title = getattr(paper, "title", None) or ""
        title_key = title.lower()
        if not title or title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        paper_id = getattr(paper, "paperId", None)
        pub_date: date | None = None
        raw_year = getattr(paper, "year", None)
        if raw_year:
            try:
                pub_date = date(int(raw_year), 1, 1)
            except (ValueError, TypeError):
                pass

        author_names = [
            (a.get("name") or "") for a in (getattr(paper, "authors", None) or [])
        ]
        out.append(
            PaperRecord(
                title=title,
                abstract=getattr(paper, "abstract", None),
                authors=author_names,
                published_at=pub_date,
                url=getattr(paper, "url", None),
                categories=[],
                semantic_scholar_id=paper_id,
            )
        )
    return out
