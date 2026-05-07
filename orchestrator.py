"""Orchestrator: runs all 5 agents sequentially, with internal parallelism in agents 3 & 4."""

from dataclasses import dataclass
from datetime import datetime

from agents.company_researcher import CompanyProfile, CompanyResearcher
from agents.competitor_mapper import CompetitorProfile, CompetitorMapper
from agents.sentinel_agent import SentinelData, SentinelAgent
from agents.trace_engine_agent import Trace, TraceEngineAgent
from agents.strategic_analyst import IntelligenceReport, StrategicAnalyst


@dataclass
class PipelineStatus:
    company: str
    started_at: datetime
    agent_1_done: bool = False
    agent_2_done: bool = False
    agent_3_done: bool = False
    agent_4_done: bool = False
    agent_5_done: bool = False
    error: str | None = None
    report: IntelligenceReport | None = None


def run_pipeline(
    company_name: str,
    lookback_days: int = 180,
    min_confidence: float = 0.4,
    max_pairs: int = 20,
    on_progress: callable = None,
    verbose: bool = True,
) -> PipelineStatus:
    """Run the full 5-agent intelligence pipeline for a given company.

    Args:
        company_name:   The company to analyze competitors for.
        lookback_days:  How far back to look for GitHub commits.
        min_confidence: Minimum trace confidence to include in report.
        max_pairs:      Max commit×paper pairs to analyze (controls API cost).
        on_progress:    Optional callback(status) called after each agent.
        verbose:        Print agent logs to stdout.
    """
    status = PipelineStatus(company=company_name, started_at=datetime.utcnow())

    def _notify():
        if on_progress:
            on_progress(status)

    try:
        # ── Agent 1: Company Researcher ───────────────────────────────────────
        company: CompanyProfile = CompanyResearcher(verbose=verbose).run(company_name)
        status.agent_1_done = True
        _notify()

        # ── Agent 2: Competitor Mapper ────────────────────────────────────────
        competitors: list[CompetitorProfile] = CompetitorMapper(verbose=verbose).run(company)
        status.agent_2_done = True
        _notify()

        # ── Agent 3: Sentinel (parallel inside) ───────────────────────────────
        sentinel_data: SentinelData = SentinelAgent(
            lookback_days=lookback_days,
            verbose=verbose,
        ).run(competitors)
        status.agent_3_done = True
        _notify()

        # ── Agent 4: Trace Engine (parallel inside) ───────────────────────────
        traces: list[Trace] = TraceEngineAgent(
            min_confidence=min_confidence,
            max_pairs=max_pairs,
            verbose=verbose,
        ).run(sentinel_data)
        status.agent_4_done = True
        _notify()

        # ── Agent 5: Strategic Analyst ────────────────────────────────────────
        report: IntelligenceReport = StrategicAnalyst(verbose=verbose).run(
            company=company,
            competitors=competitors,
            data=sentinel_data,
            traces=traces,
        )
        status.agent_5_done = True
        status.report = report
        _notify()

    except Exception as exc:
        status.error = str(exc)
        _notify()

    return status
