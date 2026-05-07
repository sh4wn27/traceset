"""Agent 2: Competitor Mapper.

Given a CompanyProfile, uses Claude to identify the top competitors and
return structured profiles for each: their repos, researchers, and patents.
"""

import json
from dataclasses import dataclass, field

import anthropic

from agents.base import BaseAgent
from agents.company_researcher import CompanyProfile
from backend.config import get_settings

_SYSTEM = """\
You are a competitive intelligence analyst. Given a company profile, identify
its top 3-5 direct competitors in the same technology space.

For each competitor return structured data that can be used to monitor them:
- Their actual GitHub organization slugs (what you'd find at github.com/<slug>)
- Names of their known researchers or engineers who publish papers
- The company name as it appears on USPTO patents (assignee name)
- Relevant CPC patent classification codes for their tech (e.g. G06N3/04)

Respond ONLY with a JSON array:
[
  {
    "name": "<company name>",
    "description": "<1-2 sentence summary>",
    "github_repos": ["<org/repo>", ...],
    "researcher_names": ["<Full Name>", ...],
    "patent_assignee": "<name as on USPTO>",
    "cpc_classes": ["<code>", ...]
  },
  ...
]
"""


@dataclass
class CompetitorProfile:
    name: str
    description: str
    github_repos: list[str] = field(default_factory=list)
    researcher_names: list[str] = field(default_factory=list)
    patent_assignee: str | None = None
    cpc_classes: list[str] = field(default_factory=list)


class CompetitorMapper(BaseAgent):
    name = "competitor_mapper"

    def run(self, company: CompanyProfile) -> list[CompetitorProfile]:
        self._start_timer()
        self._log(f"Mapping competitors for '{company.name}'...")

        cfg = get_settings()
        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

        user_msg = (
            f"Company: {company.name}\n"
            f"Description: {company.description}\n"
            f"Tech focus: {', '.join(company.tech_focus)}\n\n"
            "Identify the top 3-5 direct competitors."
        )

        response = client.messages.create(
            model=cfg.anthropic_model,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text.strip()
        items = _parse_json(raw)

        competitors = [
            CompetitorProfile(
                name=c.get("name", ""),
                description=c.get("description", ""),
                github_repos=c.get("github_repos", []),
                researcher_names=c.get("researcher_names", []),
                patent_assignee=c.get("patent_assignee"),
                cpc_classes=c.get("cpc_classes", []),
            )
            for c in items
        ]

        self._log(f"Done in {self._elapsed()}s — identified {len(competitors)} competitors")
        return competitors


def _parse_json(text: str) -> list:
    if "```" in text:
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.strip().startswith("```"))
    return json.loads(text.strip())
