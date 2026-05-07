"""TraceEngine: Claude-powered Technical Forensic Analyst."""

import json
from dataclasses import dataclass

import anthropic

from backend.config import get_settings
from backend.services.github_watcher import CommitRecord
from backend.services.scholar_sync import PaperRecord

_SYSTEM_PROMPT = """\
You are a Technical Forensic Analyst. Your job is to determine whether a GitHub \
commit and a research paper abstract describe the same underlying technical idea \
— that is, whether the code change was likely inspired by, or implements, the \
concepts in the paper.

Evaluate based on:
- Shared terminology and algorithmic concepts
- Temporal plausibility (commit should postdate or overlap with paper)
- Specificity of overlap (generic words like "optimization" score low)

Respond with a JSON object and nothing else:
{"confidence": <float 0.0-1.0>, "reasoning": "<one concise paragraph>"}
"""

_USER_TEMPLATE = """\
## GitHub Commit

Repository: {repo}
SHA: {sha}
Author: {author}
Message: {message}

Diff excerpt (first 2000 chars):
{diff}

---

## Paper Abstract

Title: {title}
Authors: {authors}
Published: {published}
ArXiv ID: {arxiv_id}

Abstract:
{abstract}
"""


@dataclass
class TraceResult:
    confidence_score: float
    reasoning: str
    model_version: str
    prompt_version: int


def analyze(commit: CommitRecord, paper: PaperRecord) -> TraceResult:
    """Run the forensic analyst prompt against a commit/paper pair."""
    cfg = get_settings()
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    user_message = _USER_TEMPLATE.format(
        repo=commit.repo_full_name,
        sha=commit.sha,
        author=commit.author or "unknown",
        message=commit.message or "",
        diff=(commit.raw_diff or "")[:2000],
        title=paper.title,
        authors=", ".join(paper.authors),
        published=str(paper.published_at or "unknown"),
        arxiv_id=paper.arxiv_id or "N/A",
        abstract=paper.abstract or "",
    )

    response = client.messages.create(
        model=cfg.anthropic_model,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()
    payload = _parse_json(raw_text)

    confidence = float(payload.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    return TraceResult(
        confidence_score=confidence,
        reasoning=payload.get("reasoning", ""),
        model_version=response.model,
        prompt_version=cfg.trace_prompt_version,
    )


def _parse_json(text: str) -> dict:
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {text!r}") from exc
