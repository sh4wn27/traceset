"""Agent 5: Strategic Analyst.

Synthesizes all collected intelligence into a final markdown report
with concrete recommendations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

from agents.base import BaseAgent
from agents.company_researcher import CompanyProfile
from agents.competitor_mapper import CompetitorProfile
from agents.sentinel_agent import SentinelData
from agents.trace_engine_agent import Trace
from backend.config import get_settings

_SYSTEM = """\
You are a senior technology strategist and competitive intelligence analyst.
You have been given raw intelligence data collected about a company's competitors:
commit activity, research papers, patents, and linked "traces" showing where
code and research converge.

Write a comprehensive intelligence report in markdown. Structure it as:

# Intelligence Report: <Company>
## Executive Summary
## What Competitors Are Building Right Now
## Key Research Signals (notable papers + patent activity)
## Traced Technical Connections (code ↔ research links)
## Strategic Recommendations (what our company should do)
## Risk Factors & Watch List

Be specific, cite actual paper titles, repo names, and patent numbers where available.
Recommendations must be actionable. Risks must be concrete.
"""


@dataclass
class IntelligenceReport:
    company: str
    competitors: list[str]
    markdown: str
    generated_at: datetime = field(default_factory=datetime.utcnow)


class StrategicAnalyst(BaseAgent):
    name = "strategic_analyst"

    def run(
        self,
        company: CompanyProfile,
        competitors: list[CompetitorProfile],
        data: SentinelData,
        traces: list[Trace],
    ) -> IntelligenceReport:
        self._start_timer()
        self._log(f"Synthesizing intelligence report for '{company.name}'...")

        cfg = get_settings()
        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

        context = _build_context(company, competitors, data, traces)

        response = client.messages.create(
            model=cfg.anthropic_model,
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": context}],
        )

        markdown = response.content[0].text.strip()

        self._log(f"Done in {self._elapsed()}s — report generated ({len(markdown)} chars)")

        return IntelligenceReport(
            company=company.name,
            competitors=[c.name for c in competitors],
            markdown=markdown,
        )


def _build_context(
    company: CompanyProfile,
    competitors: list[CompetitorProfile],
    data: SentinelData,
    traces: list[Trace],
) -> str:
    lines: list[str] = []

    lines.append(f"## Target Company\n{company.name}: {company.description}")
    lines.append(f"Tech focus: {', '.join(company.tech_focus)}")

    lines.append("\n## Competitors Identified")
    for c in competitors:
        lines.append(f"- **{c.name}**: {c.description}")

    lines.append(f"\n## Commit Activity ({len(data.commits)} commits)")
    for commit in data.commits[:15]:
        lines.append(
            f"- [{commit.repo_full_name}] {commit.sha[:7]}: "
            f"{(commit.message or '').splitlines()[0][:100]}"
        )

    lines.append(f"\n## Research Papers ({len(data.papers)} papers)")
    for paper in data.papers[:15]:
        authors = ", ".join(paper.authors[:3])
        lines.append(f"- \"{paper.title}\" — {authors} ({paper.published_at})")

    lines.append(f"\n## Patents ({len(data.patents)} patents)")
    for patent in data.patents[:10]:
        lines.append(
            f"- {patent.patent_number}: \"{patent.title}\" "
            f"[{patent.assignee}] ({patent.grant_date})"
        )

    lines.append(f"\n## Traced Connections ({len(traces)} traces)")
    for trace in traces[:10]:
        lines.append(
            f"- {trace.confidence_score:.0%} confidence: "
            f"commit {trace.commit.sha[:7]} ↔ \"{trace.paper.title[:60]}\"\n"
            f"  {trace.reasoning[:200]}"
        )

    return "\n".join(lines)
