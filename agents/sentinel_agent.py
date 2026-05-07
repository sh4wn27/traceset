"""Agent 3: Sentinel Agent.

Runs GitHubWatcher, ScholarSync, and PatentTracker IN PARALLEL
across all competitors using a ThreadPoolExecutor.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from agents.base import BaseAgent
from agents.competitor_mapper import CompetitorProfile
from backend.services.github_watcher import CommitRecord, watch_repo
from backend.services.scholar_sync import PaperRecord, fetch_papers_by_authors
from backend.services.patent_tracker import PatentRecord, search_patents


@dataclass
class SentinelData:
    commits: list[CommitRecord] = field(default_factory=list)
    papers: list[PaperRecord] = field(default_factory=list)
    patents: list[PatentRecord] = field(default_factory=list)


class SentinelAgent(BaseAgent):
    name = "sentinel"

    def __init__(self, lookback_days: int = 180, verbose: bool = True):
        super().__init__(verbose)
        self.lookback_days = lookback_days

    def run(self, competitors: list[CompetitorProfile]) -> SentinelData:
        self._start_timer()
        self._log(f"Running sentinels across {len(competitors)} competitors in parallel...")

        since = datetime.utcnow() - timedelta(days=self.lookback_days)
        result = SentinelData()

        # Build all jobs upfront
        jobs: list[tuple[str, callable, tuple]] = []

        for comp in competitors:
            for repo in comp.github_repos:
                jobs.append(("github", self._fetch_commits, (repo, since)))

            if comp.researcher_names:
                jobs.append(("papers", self._fetch_papers, (comp.researcher_names,)))

            if comp.patent_assignee:
                jobs.append(("patents", self._fetch_patents, (comp.patent_assignee, comp.cpc_classes)))

        self._log(f"Dispatching {len(jobs)} parallel sentinel jobs...")

        with ThreadPoolExecutor(max_workers=min(len(jobs), 10)) as pool:
            futures = {
                pool.submit(fn, *args): kind
                for kind, fn, args in jobs
            }
            for future in as_completed(futures):
                kind = futures[future]
                try:
                    data = future.result()
                    if kind == "github":
                        result.commits.extend(data)
                        self._log(f"  GitHub: +{len(data)} commits")
                    elif kind == "papers":
                        result.papers.extend(data)
                        self._log(f"  Papers: +{len(data)} papers")
                    elif kind == "patents":
                        result.patents.extend(data)
                        self._log(f"  Patents: +{len(data)} patents")
                except Exception as exc:
                    self._log(f"  [{kind}] job failed: {exc}")

        self._log(
            f"Done in {self._elapsed()}s — "
            f"{len(result.commits)} commits, "
            f"{len(result.papers)} papers, "
            f"{len(result.patents)} patents"
        )
        return result

    def _fetch_commits(self, repo: str, since: datetime) -> list[CommitRecord]:
        try:
            return watch_repo(repo, since=since)
        except Exception:
            return []

    def _fetch_papers(self, authors: list[str]) -> list[PaperRecord]:
        try:
            return fetch_papers_by_authors(authors)
        except Exception:
            return []

    def _fetch_patents(self, assignee: str, cpc_classes: list[str]) -> list[PatentRecord]:
        results: list[PatentRecord] = []
        try:
            results.extend(search_patents(assignee=assignee, limit=25))
        except Exception:
            pass
        for cpc in cpc_classes[:2]:
            try:
                results.extend(search_patents(cpc_class=cpc, limit=10))
            except Exception:
                pass
        return results
