"""Tests for GitHubWatcher sentinel (all GitHub API calls mocked)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.github_watcher import CommitRecord, watch_repo


def _make_mock_commit(sha: str, message: str, patch_text: str = "") -> MagicMock:
    commit = MagicMock()
    commit.sha = sha
    commit.commit.message = message
    commit.commit.author.date = datetime(2024, 6, 1)
    commit.author.login = "dev_user"

    mock_file = MagicMock()
    mock_file.patch = patch_text
    commit.files = [mock_file]
    return commit


@pytest.fixture
def mock_repo():
    commits = [
        _make_mock_commit("abc123", "refactor: split encoder module", "- old\n+ new"),
        _make_mock_commit("def456", "fix: correct dtype cast"),
        _make_mock_commit("ghi789", "experimental: flash-attention kernel", "kernel code"),
    ]

    repo = MagicMock()
    repo.get_commits.return_value = iter(commits)

    with patch("backend.services.github_watcher.Github") as MockGH:
        MockGH.return_value.get_repo.return_value = repo
        yield repo


def test_keyword_match_returns_correct_commits(mock_repo):
    results = watch_repo("owner/repo", keywords=["refactor", "experimental"])
    shas = [r.sha for r in results]
    assert "abc123" in shas
    assert "ghi789" in shas


def test_non_matching_commit_excluded(mock_repo):
    results = watch_repo("owner/repo", keywords=["refactor", "experimental"])
    shas = [r.sha for r in results]
    assert "def456" not in shas


def test_keywords_matched_field_populated(mock_repo):
    results = watch_repo("owner/repo", keywords=["refactor"])
    assert results[0].keywords_matched == ["refactor"]


def test_returns_commit_record_dataclass(mock_repo):
    results = watch_repo("owner/repo", keywords=["refactor"])
    assert isinstance(results[0], CommitRecord)


def test_diff_in_haystack(mock_repo):
    results = watch_repo("owner/repo", keywords=["experimental"])
    exp = next(r for r in results if r.sha == "ghi789")
    assert "kernel" in (exp.raw_diff or "")


def test_since_parameter_passed_through(mock_repo):
    since = datetime(2024, 1, 1)
    watch_repo("owner/repo", since=since)
    mock_repo.get_commits.assert_called_once_with(since=since)


def test_invalid_repo_raises_value_error():
    from github.GithubException import GithubException

    with patch("backend.services.github_watcher.Github") as MockGH:
        MockGH.return_value.get_repo.side_effect = GithubException(404, "Not Found")
        with pytest.raises(ValueError, match="Cannot access repo"):
            watch_repo("bad/repo")
