"""PatentTracker sentinel: searches USPTO PatentsView API (no scraping)."""

import json
from dataclasses import dataclass
from datetime import date

import httpx

_PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"

_DEFAULT_FIELDS = (
    "patent_number,patent_title,patent_abstract,patent_date,"
    "inventors.inventor_name_first,inventors.inventor_name_last,"
    "assignees.assignee_organization,uspc_subclasses.subclass_id"
)


@dataclass
class PatentRecord:
    patent_number: str | None
    title: str
    abstract: str | None
    assignee: str | None
    inventors: list[str]
    filing_date: date | None
    grant_date: date | None
    cpc_class: str | None
    source: str
    url: str | None


def search_patents(
    assignee: str | None = None,
    cpc_class: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[PatentRecord]:
    """Search USPTO PatentsView for patents by assignee and/or CPC class.

    At least one of *assignee* or *cpc_class* must be provided.
    """
    if not assignee and not cpc_class:
        raise ValueError("Provide at least one of 'assignee' or 'cpc_class'.")

    query = _build_query(assignee, cpc_class, date_from, date_to)

    resp = httpx.get(
        _PATENTSVIEW_URL,
        params={"q": query, "f": _DEFAULT_FIELDS, "o": json.dumps({"per_page": min(limit, 100)})},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    return [_parse_patent(p, cpc_class) for p in data.get("patents") or []]


def _build_query(
    assignee: str | None,
    cpc_class: str | None,
    date_from: date | None,
    date_to: date | None,
) -> str:
    clauses: list[dict] = []
    if assignee:
        clauses.append({"_text_any": {"assignee_organization": assignee}})
    if cpc_class:
        clauses.append({"_begins": {"cpc_group_id": cpc_class}})
    if date_from:
        clauses.append({"_gte": {"patent_date": str(date_from)}})
    if date_to:
        clauses.append({"_lte": {"patent_date": str(date_to)}})

    if len(clauses) == 1:
        return json.dumps(clauses[0])
    return json.dumps({"_and": clauses})


def _parse_patent(raw: dict, cpc_class: str | None) -> PatentRecord:
    num = raw.get("patent_number")
    grant_dt = _to_date(raw.get("patent_date"))

    assignees = raw.get("assignees") or []
    assignee_name = assignees[0].get("assignee_organization") if assignees else None

    inventors: list[str] = []
    for inv in (raw.get("inventors") or []):
        first = inv.get("inventor_name_first") or ""
        last = inv.get("inventor_name_last") or ""
        name = f"{first} {last}".strip()
        if name:
            inventors.append(name)

    return PatentRecord(
        patent_number=num,
        title=raw.get("patent_title") or "",
        abstract=raw.get("patent_abstract"),
        assignee=assignee_name,
        inventors=inventors,
        filing_date=None,
        grant_date=grant_dt,
        cpc_class=cpc_class,
        source="USPTO",
        url=f"https://patents.google.com/patent/US{num}" if num else None,
    )


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None
