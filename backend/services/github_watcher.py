"""GitHubWatcher sentinel: fetches commits matching keyword filters via PyGitHub."""

from dataclasses import dataclass
from datetime import datetime

from github import Github
from github.GithubException import GithubException

from backend.config import get_settings


@dataclass
class CommitRecord:
    repo_full_name: str
    sha: str
    author: str | None
    message: str | None
    keywords_matched: list[str]
    raw_diff: str | None
    committed_at: datetime | None


def watch_repo(
    repo_full_name: str,
    keywords: list[str] | None = None,
    since: datetime | None = None,
) -> list[CommitRecord]:
    """Return commits from *repo_full_name* whose message or diff contains any keyword."""
    cfg = get_settings()
    kws = [k.lower() for k in (keywords or cfg.github_keywords)]
    gh = Github(cfg.github_token)

    try:
        repo = gh.get_repo(repo_full_name)
    except GithubException as exc:
        raise ValueError(f"Cannot access repo {repo_full_name!r}: {exc}") from exc

    kwargs: dict = {}
    if since:
        kwargs["since"] = since

    results: list[CommitRecord] = []
    for commit in repo.get_commits(**kwargs):
        msg = (commit.commit.message or "").lower()
        diff_text = _collect_diff(commit)
        haystack = msg + " " + diff_text.lower()
        matched = [k for k in kws if k in haystack]
        if not matched:
            continue

        author_login: str | None = None
        if commit.author:
            author_login = commit.author.login
        elif commit.commit.author:
            author_login = commit.commit.author.name

        results.append(
            CommitRecord(
                repo_full_name=repo_full_name,
                sha=commit.sha,
                author=author_login,
                message=commit.commit.message,
                keywords_matched=matched,
                raw_diff=diff_text or None,
                committed_at=commit.commit.author.date if commit.commit.author else None,
            )
        )

    return results


def _collect_diff(commit) -> str:
    parts: list[str] = []
    for f in commit.files:
        if f.patch:
            parts.append(f.patch)
    return "\n".join(parts)
