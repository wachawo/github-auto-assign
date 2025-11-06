#!/usr/bin/env python3
"""Tests for main module in functional style."""

import importlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# --- Global state for functional fakes --------------------------------------

FAKE_STATE: dict[str, Any] = {"issues": {}, "prs": {}, "instance": None}


def reset_fake_state() -> None:
    """Reset all fake state between tests."""
    FAKE_STATE.clear()
    FAKE_STATE.update({"issues": {}, "prs": {}, "instance": None})


# --- Pure functions for issue management -------------------------------------


def create_issue(number: int = 1) -> dict[str, list[str]]:
    """Create an issue dict."""
    return {"assignees": []}


def add_assignees(issue: dict[str, list[str]], *users: str) -> None:
    """Add assignees to an issue (mutates)."""
    issue["assignees"].extend(users)


# --- Pure functions for PR management ----------------------------------------


def create_pr(number: int = 2, author: str = "author") -> dict[str, Any]:
    """Create a PR dict."""
    return {
        "number": number,
        "author": author,
        "issue": create_issue(number),
        "requested_reviewers": [],
    }


def pr_as_issue(pr: dict[str, Any]) -> dict[str, list[str]]:
    """Get issue from PR."""
    return pr["issue"]  # type: ignore[no-any-return]


def request_reviewers(pr: dict[str, Any], reviewers: list[str]) -> None:
    """Request reviewers on PR (mutates)."""
    pr["requested_reviewers"].extend(reviewers)


# --- Pure functions for repo management --------------------------------------


def create_repo(
    issue_num: int = 1, pr_num: int = 2, pr_author: str = "author"
) -> dict[str, Any]:
    """Create a repo dict with issues and PRs."""
    issue = create_issue(issue_num)
    pr = create_pr(pr_num, pr_author)
    FAKE_STATE["issues"][issue_num] = issue
    FAKE_STATE["prs"][pr_num] = pr
    return {"issues": FAKE_STATE["issues"], "prs": FAKE_STATE["prs"]}


def get_issue_from_repo(repo: dict[str, Any], number: int) -> dict[str, list[str]]:
    """Get issue from repo."""
    return repo["issues"][number]  # type: ignore[no-any-return]


def get_pr_from_repo(repo: dict[str, Any], number: int) -> dict[str, Any]:
    """Get PR from repo."""
    return repo["prs"][number]  # type: ignore[no-any-return]


# --- Wrapper classes (minimal OOP interface) ---------------------------------


class IssueWrapper:
    """Thin wrapper around issue dict for PyGithub API compatibility."""

    def __init__(self, issue_dict: dict[str, list[str]]) -> None:
        self._dict = issue_dict

    @property
    def assignees(self) -> list[str]:
        return self._dict["assignees"]

    def add_to_assignees(self, *users: str) -> None:
        add_assignees(self._dict, *users)


class PRWrapper:
    """Thin wrapper around PR dict for PyGithub API compatibility."""

    def __init__(self, pr_dict: dict[str, Any]) -> None:
        self._dict = pr_dict

    @property
    def number(self) -> int:
        return self._dict["number"]  # type: ignore[no-any-return]

    @property
    def requested_reviewers(self) -> list[str]:
        return self._dict["requested_reviewers"]  # type: ignore[no-any-return]

    def as_issue(self) -> IssueWrapper:
        return IssueWrapper(pr_as_issue(self._dict))

    def create_review_request(
        self,
        reviewers: list[str] | None = None,
        team_reviewers: list[str] | None = None,
    ) -> None:
        if reviewers:
            request_reviewers(self._dict, reviewers)


class RepoWrapper:
    """Thin wrapper around repo dict for PyGithub API compatibility."""

    def __init__(self, repo_dict: dict[str, Any]) -> None:
        self._dict = repo_dict

    def get_issue(self, number: int) -> IssueWrapper:
        return IssueWrapper(get_issue_from_repo(self._dict, number))

    def get_pull(self, number: int) -> PRWrapper:
        return PRWrapper(get_pr_from_repo(self._dict, number))


class FakeGithub:
    """Fake Github client (minimal state holder)."""

    @staticmethod
    def reset() -> None:
        """Reset global state."""
        reset_fake_state()

    def __init__(self, token: str) -> None:
        self.token = token
        if FAKE_STATE["instance"] is None:
            self.repo = RepoWrapper(create_repo())
            FAKE_STATE["instance"] = self
        else:
            self.repo = FAKE_STATE["instance"].repo

    def get_repo(self, slug: str) -> RepoWrapper:
        return self.repo


class FakeGithubException(Exception):
    """Fake GitHub exception."""

    def __init__(self, data: str = "boom") -> None:
        super().__init__(data)
        self.data = data


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture(autouse=True)
def ensure_entrypoint_on_path(tmp_path: Path, monkeypatch: Any) -> Any:
    """Import and patch src.main module."""
    FakeGithub.reset()

    repo_root = Path.cwd()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if "src.main" in sys.modules:
        del sys.modules["src.main"]
    module = importlib.import_module("src.main")

    monkeypatch.setattr(module, "Github", FakeGithub, raising=True)
    monkeypatch.setattr(module, "GithubException", FakeGithubException, raising=True)

    return module


@pytest.fixture
def event_file(tmp_path: Path, monkeypatch: Any) -> Callable[[dict[str, Any]], Path]:
    """Create event file fixture."""

    def write_event(payload: dict[str, Any]) -> Path:
        p = tmp_path / "event.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(p))
        return p

    return write_event


# --- Helper functions for tests ----------------------------------------------


def setup_base_env(
    monkeypatch: Any, token: str = "t0", repo: str = "owner/repo", event: str = "issues"
) -> None:
    """Set up base environment variables."""
    monkeypatch.setenv("INPUT_REPO_TOKEN", token)
    monkeypatch.setenv("GITHUB_REPOSITORY", repo)
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)


# --- Unit tests for pure helpers ---------------------------------------------


def test_split_list_normalization_and_uniqueness(
    ensure_entrypoint_on_path: Any,
) -> None:
    """Test split_list function with various inputs."""
    m = ensure_entrypoint_on_path
    test_cases = {
        "": [],
        "alice": ["alice"],
        "@alice": ["alice"],
        "alice, bob": ["alice", "bob"],
        "alice bob  alice": ["alice", "bob"],
        "alice,@bob,  @alice": ["alice", "bob"],
        "alice, bob,  \n  carol": ["alice", "bob", "carol"],
    }
    for raw, expected in test_cases.items():
        assert m.split_list(raw) == expected


def test_get_input_variants(ensure_entrypoint_on_path: Any, monkeypatch: Any) -> None:
    """Test get_input function with various environment variable formats."""
    m = ensure_entrypoint_on_path

    monkeypatch.setenv("INPUT_FOO_BAR", "v1")
    monkeypatch.setenv("INPUT_FOO-BAR", "v2")
    assert m.get_input("FOO_BAR") == "v1"

    monkeypatch.delenv("INPUT_FOO_BAR", raising=False)
    assert m.get_input("FOO-BAR") == "v2"

    monkeypatch.delenv("INPUT_FOO-BAR", raising=False)
    monkeypatch.setenv("INPUT_FOO-BAR", "v3")
    assert m.get_input("FOO_BAR") == "v3"

    monkeypatch.delenv("INPUT_FOO-BAR", raising=False)
    assert m.get_input("FOO_BAR", default="def") == "def"


def test_load_event_reads_json(
    ensure_entrypoint_on_path: Any, event_file: Callable[[dict[str, Any]], Path]
) -> None:
    """Test load_event function reads JSON correctly."""
    m = ensure_entrypoint_on_path
    payload: dict[str, Any] = {"ok": True, "n": 3}
    event_file(payload)
    assert m.load_event() == payload


# --- Main flow tests ---------------------------------------------------------


def test_missing_token_returns_error(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that missing token returns error code."""
    m = ensure_entrypoint_on_path
    monkeypatch.delenv("INPUT_REPO_TOKEN", raising=False)
    monkeypatch.delenv("INPUT_REPO-TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    event_file({"issue": {"number": 1}})
    assert m.main() == 1


def test_missing_repo_returns_error(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that missing repo returns error code."""
    m = ensure_entrypoint_on_path
    monkeypatch.setenv("INPUT_REPO_TOKEN", "t0")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    event_file({"issue": {"number": 1}})
    assert m.main() == 1


def test_issues_event_assigns_assignees(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test assigning users to issues."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="issues")
    monkeypatch.setenv("INPUT_ASSIGNEES", "alice, @bob  carol")
    event_file({"issue": {"number": 1}})

    rc = m.main()
    assert rc == 0

    repo = m.Github("x").get_repo("y")
    issue = repo.get_issue(1)
    assert issue.assignees == ["alice", "bob", "carol"]


def test_issues_event_no_assignees_ok(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that issues without assignees still succeed."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="issues")
    monkeypatch.delenv("INPUT_ASSIGNEES", raising=False)
    event_file({"issue": {"number": 1}})
    assert m.main() == 0


def test_pr_event_assigns_and_requests_reviewers(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test assigning users and requesting reviewers on PRs."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="pull_request")
    monkeypatch.setenv("INPUT_ASSIGNEES", "alice,bob")
    monkeypatch.setenv("INPUT_REVIEWERS", "bob,carol, dave")
    event_file({"pull_request": {"number": 2, "user": {"login": "author"}}})

    rc = m.main()
    assert rc == 0

    repo = m.Github("x").get_repo("y")
    pr = repo.get_pull(2)
    assert pr.as_issue().assignees == ["alice", "bob"]
    assert pr.requested_reviewers == ["bob", "carol", "dave"]


def test_pr_event_filters_author_from_reviewers(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that PR author is filtered from reviewers list."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="pull_request")
    monkeypatch.setenv("INPUT_REVIEWERS", "author, carol")
    event_file({"pull_request": {"number": 2, "user": {"login": "author"}}})

    rc = m.main()
    assert rc == 0

    repo = m.Github("x").get_repo("y")
    pr = repo.get_pull(2)
    assert pr.requested_reviewers == ["carol"]


def test_pr_event_no_assignees_or_reviewers_is_ok(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that PRs without assignees or reviewers still succeed."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="pull_request")
    monkeypatch.delenv("INPUT_ASSIGNEES", raising=False)
    monkeypatch.delenv("INPUT_REVIEWERS", raising=False)
    event_file({"pull_request": {"number": 2, "user": {"login": "author"}}})
    assert m.main() == 0


def test_unsupported_event_is_graceful(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that unsupported events are handled gracefully."""
    m = ensure_entrypoint_on_path
    setup_base_env(monkeypatch, event="schedule")
    event_file({"nothing": True})
    assert m.main() == 0


def test_github_exception_is_caught_and_returns_1(
    ensure_entrypoint_on_path: Any,
    monkeypatch: Any,
    event_file: Callable[[dict[str, Any]], Path],
) -> None:
    """Test that GitHub exceptions are caught and return error code."""
    m = ensure_entrypoint_on_path

    class BoomRepo(RepoWrapper):
        def get_issue(self, number: int) -> IssueWrapper:
            raise FakeGithubException("nope")

    class BoomGithub:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_repo(self, slug: str) -> BoomRepo:
            return BoomRepo(create_repo())

    monkeypatch.setattr(m, "Github", BoomGithub, raising=True)

    setup_base_env(monkeypatch, event="issues")
    event_file({"issue": {"number": 1}})
    assert m.main() == 1
