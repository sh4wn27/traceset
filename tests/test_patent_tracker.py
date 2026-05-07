"""Tests for PatentTracker sentinel (USPTO PatentsView API mocked via respx)."""

from datetime import date

import httpx
import pytest
import respx

from backend.services.patent_tracker import PatentRecord, _PATENTSVIEW_URL, search_patents


_MOCK_RESPONSE = {
    "patents": [
        {
            "patent_number": "11223344",
            "patent_title": "Neural Accelerator",
            "patent_abstract": "An invention about neural acceleration.",
            "patent_date": "2023-05-01",
            "inventors": [
                {"inventor_name_first": "Jane", "inventor_name_last": "Inventor"}
            ],
            "assignees": [{"assignee_organization": "TechCorp Inc."}],
        },
        {
            "patent_number": "99887766",
            "patent_title": "Quantum Cache",
            "patent_abstract": "An invention about quantum caching.",
            "patent_date": "2022-11-15",
            "inventors": [
                {"inventor_name_first": "Bob", "inventor_name_last": "Smith"}
            ],
            "assignees": [{"assignee_organization": "TechCorp Inc."}],
        },
    ]
}


@pytest.fixture
def mock_patentsview():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(_PATENTSVIEW_URL).mock(
            return_value=httpx.Response(200, json=_MOCK_RESPONSE)
        )
        yield mock


def test_returns_patent_records(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    assert all(isinstance(r, PatentRecord) for r in results)


def test_patent_numbers_captured(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    nums = {r.patent_number for r in results}
    assert "11223344" in nums
    assert "99887766" in nums


def test_source_is_uspto(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    assert all(r.source == "USPTO" for r in results)


def test_grant_date_parsed(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    r = next(x for x in results if x.patent_number == "11223344")
    assert r.grant_date == date(2023, 5, 1)


def test_inventors_captured(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    r = next(x for x in results if x.patent_number == "11223344")
    assert "Jane Inventor" in r.inventors


def test_url_constructed(mock_patentsview):
    results = search_patents(assignee="TechCorp")
    r = next(x for x in results if x.patent_number == "11223344")
    assert "11223344" in (r.url or "")


def test_requires_at_least_one_filter():
    with pytest.raises(ValueError, match="at least one"):
        search_patents()


def test_empty_response():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(_PATENTSVIEW_URL).mock(
            return_value=httpx.Response(200, json={"patents": []})
        )
        results = search_patents(assignee="Unknown Corp")
    assert results == []
