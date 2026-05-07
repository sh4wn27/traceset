"""Tests for TraceEngine (Claude API mocked — zero API credit burn)."""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.github_watcher import CommitRecord
from backend.services.scholar_sync import PaperRecord
from backend.services.trace_engine import TraceResult, _parse_json, analyze


@pytest.fixture
def sample_commit() -> CommitRecord:
    return CommitRecord(
        repo_full_name="triton-lang/triton",
        sha="deadbeef",
        author="ptillet",
        message="refactor: implement flash attention v2 kernel",
        keywords_matched=["refactor"],
        raw_diff="+ tl.load(q_ptrs)\n+ tl.store(out_ptrs, acc)",
        committed_at=datetime(2023, 9, 1),
    )


@pytest.fixture
def sample_paper() -> PaperRecord:
    return PaperRecord(
        title="FlashAttention-2: Faster Attention with Better Parallelism",
        abstract="We present FlashAttention-2, an efficient exact attention algorithm...",
        authors=["Tri Dao"],
        published_at=date(2023, 7, 17),
        url="https://arxiv.org/abs/2307.08691",
        categories=["cs.LG"],
        arxiv_id="2307.08691",
    )


def _mock_anthropic_response(confidence: float, reasoning: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = json.dumps({"confidence": confidence, "reasoning": reasoning})

    response = MagicMock()
    response.content = [content_block]
    response.model = "claude-sonnet-4-6"
    return response


@pytest.fixture
def mock_anthropic():
    with patch("backend.services.trace_engine.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            confidence=0.87,
            reasoning="The commit implements flash attention, which matches the paper exactly.",
        )
        yield MockClient


def test_analyze_returns_trace_result(mock_anthropic, sample_commit, sample_paper):
    result = analyze(sample_commit, sample_paper)
    assert isinstance(result, TraceResult)


def test_confidence_score_in_range(mock_anthropic, sample_commit, sample_paper):
    result = analyze(sample_commit, sample_paper)
    assert 0.0 <= result.confidence_score <= 1.0


def test_confidence_score_value(mock_anthropic, sample_commit, sample_paper):
    result = analyze(sample_commit, sample_paper)
    assert result.confidence_score == pytest.approx(0.87)


def test_reasoning_non_empty(mock_anthropic, sample_commit, sample_paper):
    result = analyze(sample_commit, sample_paper)
    assert len(result.reasoning) > 0


def test_model_version_captured(mock_anthropic, sample_commit, sample_paper):
    result = analyze(sample_commit, sample_paper)
    assert result.model_version == "claude-sonnet-4-6"


def test_prompt_contains_diff_and_abstract(mock_anthropic, sample_commit, sample_paper):
    analyze(sample_commit, sample_paper)
    call_args = mock_anthropic.return_value.messages.create.call_args
    user_content = call_args.kwargs["messages"][0]["content"]
    assert "tl.load" in user_content
    assert "FlashAttention" in user_content


def test_confidence_clamped_to_1(mock_anthropic, sample_commit, sample_paper):
    mock_anthropic.return_value.messages.create.return_value = _mock_anthropic_response(
        confidence=1.5, reasoning="Over-confident model."
    )
    result = analyze(sample_commit, sample_paper)
    assert result.confidence_score == 1.0


def test_confidence_clamped_to_0(mock_anthropic, sample_commit, sample_paper):
    mock_anthropic.return_value.messages.create.return_value = _mock_anthropic_response(
        confidence=-0.2, reasoning="Under-confident model."
    )
    result = analyze(sample_commit, sample_paper)
    assert result.confidence_score == 0.0


def test_parse_json_plain():
    assert _parse_json('{"confidence": 0.5, "reasoning": "ok"}') == {
        "confidence": 0.5, "reasoning": "ok",
    }


def test_parse_json_with_markdown_fence():
    text = '```json\n{"confidence": 0.7, "reasoning": "good"}\n```'
    assert _parse_json(text) == {"confidence": 0.7, "reasoning": "good"}


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError, match="non-JSON"):
        _parse_json("not json at all")
