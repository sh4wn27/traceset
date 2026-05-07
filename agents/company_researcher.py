"""Agent 1: Company Researcher.

Given a company name, uses Claude to produce a structured profile:
what they build, their tech stack, key people, and known GitHub presence.
"""

import json
from dataclasses import dataclass, field

import anthropic

from agents.base import BaseAgent
from backend.config import get_settings

_SYSTEM = """\
You are a technology industry analyst. Given a company name, produce a structured
research profile based on your knowledge. Be specific and factual. If unsure, omit
rather than guess.

Respond ONLY with a JSON object matching this exact shape:
{
  "name": "<official company name>",
  "description": "<2-3 sentence overview of what they do>",
  "tech_focus": ["<area1>", "<area2>", ...],
  "key_people": ["<Name, Role>", ...],
  "github_orgs": ["<org-slug>", ...],
  "founded": "<year or null>",
  "hq": "<city, country or null>"
}
"""


@dataclass
class CompanyProfile:
    name: str
    description: str
    tech_focus: list[str] = field(default_factory=list)
    key_people: list[str] = field(default_factory=list)
    github_orgs: list[str] = field(default_factory=list)
    founded: str | None = None
    hq: str | None = None


class CompanyResearcher(BaseAgent):
    name = "company_researcher"

    def run(self, company_name: str) -> CompanyProfile:
        self._start_timer()
        self._log(f"Researching '{company_name}'...")

        cfg = get_settings()
        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

        response = client.messages.create(
            model=cfg.anthropic_model,
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Research this company: {company_name}"}],
        )

        raw = response.content[0].text.strip()
        data = _parse_json(raw)

        profile = CompanyProfile(
            name=data.get("name", company_name),
            description=data.get("description", ""),
            tech_focus=data.get("tech_focus", []),
            key_people=data.get("key_people", []),
            github_orgs=data.get("github_orgs", []),
            founded=data.get("founded"),
            hq=data.get("hq"),
        )

        self._log(f"Done in {self._elapsed()}s — found {len(profile.tech_focus)} focus areas, "
                  f"{len(profile.github_orgs)} GitHub orgs")
        return profile


def _parse_json(text: str) -> dict:
    if "```" in text:
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        )
    return json.loads(text.strip())
