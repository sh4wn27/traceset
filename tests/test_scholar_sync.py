"""Tests for ScholarSync sentinel (ArXiv and Semantic Scholar mocked)."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from backend.services.scholar_sync import PaperRecord, fetch_papers_by_authors


def _mock_arxiv_result(title: str, arxiv_id: str) -> MagicMock:
    r = MagicMock()
    r.title = title
    r.summary = "An abstract about " + title
    r.authors = [MagicMock(__str__=lambda s: "Author A")]
    r.published = MagicMock(date=lambda: date(2024, 3, 15))
    r.entry_id = f"https://arxiv.org/abs/{arxiv_id}"
    r.categories = ["cs.LG"]
    r.get_short_id = lambda: arxiv_id
    return r


@pytest.fixture
def mock_arxiv():
    with patch("backend.services.scholar_sync.arxiv.Search") as MockSearch:
        MockSearch.return_value.results.return_value = iter([
            _mock_arxiv_result("Flash Attention Revisited", "2401.00001"),
            _mock_arxiv_result("Sparse Transformers", "2401.00002"),
        ])
        yield MockSearch


@pytest.fixture
def mock_s2():
    with patch("backend.services.scholar_sync.SemanticScholar") as MockS2:
        paper = MagicMock()
        paper.title = "S2-Only Paper"
        paper.abstract = "Abstract from S2."
        paper.year = 2023
        paper.paperId = "s2-id-999"
        paper.url = "https://semanticscholar.org/paper/s2-id-999"
        paper.authors = [{"name": "Author B"}]
        MockS2.return_value.search_paper.return_value = [paper]
        yield MockS2


def test_fetch_returns_paper_records(mock_arxiv, mock_s2):
    results = fetch_papers_by_authors(["Dao"])
    assert all(isinstance(r, PaperRecord) for r in results)


def test_arxiv_papers_captured(mock_arxiv, mock_s2):
    results = fetch_papers_by_authors(["Dao"])
    arxiv_ids = {r.arxiv_id for r in results}
    assert "2401.00001" in arxiv_ids
    assert "2401.00002" in arxiv_ids


def test_s2_papers_captured(mock_arxiv, mock_s2):
    results = fetch_papers_by_authors(["Dao"])
    s2_ids = {r.semantic_scholar_id for r in results}
    assert "s2-id-999" in s2_ids


def test_deduplication_by_title(mock_arxiv, mock_s2):
    with patch("backend.services.scholar_sync.SemanticScholar") as MockS2:
        dup = MagicMock()
        dup.title = "Flash Attention Revisited"
        dup.abstract = "Duplicate."
        dup.year = 2024
        dup.paperId = "s2-dup"
        dup.url = None
        dup.authors = []
        MockS2.return_value.search_paper.return_value = [dup]

        results = fetch_papers_by_authors(["Dao"])
        titles = [r.title for r in results]
        assert titles.count("Flash Attention Revisited") == 1


def test_s2_error_returns_partial_results(mock_arxiv):
    with patch("backend.services.scholar_sync.SemanticScholar") as MockS2:
        MockS2.return_value.search_paper.side_effect = RuntimeError("network error")
        results = fetch_papers_by_authors(["Dao"])
        assert len(results) >= 2
