"""Agent 4: Trace Engine Agent.

Pairs commits with papers and runs Claude forensic analysis IN PARALLEL
across all pairs using a ThreadPoolExecutor.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from agents.base import BaseAgent
from agents.sentinel_agent import SentinelData
from backend.services.github_watcher import CommitRecord
from backend.services.scholar_sync import PaperRecord
from backend.services.trace_engine import TraceResult, analyze


@dataclass
class Trace:
    commit: CommitRecord
    paper: PaperRecord
    confidence_score: float
    reasoning: str
    model_version: str


class TraceEngineAgent(BaseAgent):
    name = "trace_engine"

    def __init__(self, min_confidence: float = 0.4, max_pairs: int = 20, verbose: bool = True):
        super().__init__(verbose)
        self.min_confidence = min_confidence
        self.max_pairs = max_pairs

    def run(self, data: SentinelData) -> list[Trace]:
        self._start_timer()

        pairs = self._select_pairs(data.commits, data.papers)
        self._log(f"Analyzing {len(pairs)} commit×paper pairs in parallel...")

        traces: list[Trace] = []

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(self._analyze_pair, commit, paper): (commit, paper)
                for commit, paper in pairs
            }
            for future in as_completed(futures):
                commit, paper = futures[future]
                try:
                    result: TraceResult = future.result()
                    if result.confidence_score >= self.min_confidence:
                        traces.append(Trace(
                            commit=commit,
                            paper=paper,
                            confidence_score=result.confidence_score,
                            reasoning=result.reasoning,
                            model_version=result.model_version,
                        ))
                        self._log(
                            f"  TRACE {result.confidence_score:.0%} — "
                            f"{commit.sha[:7]} × '{paper.title[:50]}'"
                        )
                except Exception as exc:
                    self._log(f"  Pair failed: {exc}")

        traces.sort(key=lambda t: t.confidence_score, reverse=True)
        self._log(f"Done in {self._elapsed()}s — {len(traces)} traces above {self.min_confidence:.0%}")
        return traces

    def _select_pairs(
        self,
        commits: list[CommitRecord],
        papers: list[PaperRecord],
    ) -> list[tuple[CommitRecord, PaperRecord]]:
        """Pick the most promising commit×paper pairs to analyze.

        Strategy: pair commits that have keyword-matched content with papers
        that share at least one keyword in the title. Cap at max_pairs to
        control API costs.
        """
        pairs: list[tuple[CommitRecord, PaperRecord]] = []

        for commit in commits:
            kws = {k.lower() for k in (commit.keywords_matched or [])}
            for paper in papers:
                title_words = set(paper.title.lower().split())
                if kws & title_words:
                    pairs.append((commit, paper))
                    if len(pairs) >= self.max_pairs:
                        return pairs

        # If not enough keyword-overlapping pairs, fill up to max with any pairs
        if len(pairs) < self.max_pairs:
            for commit in commits:
                for paper in papers:
                    if (commit, paper) not in pairs:
                        pairs.append((commit, paper))
                    if len(pairs) >= self.max_pairs:
                        return pairs

        return pairs

    def _analyze_pair(self, commit: CommitRecord, paper: PaperRecord) -> TraceResult:
        return analyze(commit, paper)
