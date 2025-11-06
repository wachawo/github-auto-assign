#!/usr/bin/env python3
"""
Auto-assign GitHub Action entrypoint.
- Assigns assignees for both Issues and Pull Requests.
- Requests reviewers for Pull Requests.

Inputs (as env):
  INPUT_REPO_TOKEN   - required
  INPUT_ASSIGNEES    - optional, comma-separated
  INPUT_REVIEWERS    - optional, comma-separated (PR only)

This script uses GITHUB_EVENT_NAME and GITHUB_EVENT_PATH provided by the runner.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from github import Github
from github.GithubException import GithubException

LOGGING: dict[str, Any] = {
    "handlers": [
        logging.StreamHandler(),
    ],
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s.%(funcName)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)  # type: ignore[arg-type]
logger = logging.getLogger(__name__)


def get_input(name: str, default: str = "") -> str:
    # Support both dash and underscore variants just in case
    candidates = [
        f"INPUT_{name}",
        f"INPUT_{name.replace('-', '_')}",
        f"INPUT_{name.replace('_', '-')}",
    ]
    for key in candidates:
        val = os.getenv(key)
        if val is not None:
            return val
    return default


def split_list(raw: str) -> list[str]:
    if not raw:
        return []
    # Split by comma or whitespace, strip @ and spaces, keep unique while preserving order
    seen = set()
    result: list[str] = []
    for token in [
        t.strip().lstrip("@") for part in raw.split(",") for t in part.split()
    ]:
        if token and token not in seen:
            result.append(token)
            seen.add(token)
    return result


def load_event() -> dict[str, Any]:
    path = os.getenv("GITHUB_EVENT_PATH")
    if not path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set")
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def main() -> int:
    token = get_input("REPO_TOKEN") or get_input("REPO-TOKEN")
    if not token:
        logger.error(
            "::error title=Missing token::INPUT_REPO_TOKEN (repo-token) is required"
        )
        return 1

    assignees = split_list(get_input("ASSIGNEES"))
    reviewers = split_list(get_input("REVIEWERS"))

    event_name = os.getenv("GITHUB_EVENT_NAME", "").lower()
    repo_slug = os.getenv("GITHUB_REPOSITORY")
    if not repo_slug:
        logger.error("::error title=Missing context::GITHUB_REPOSITORY is not set")
        return 1

    gh = Github(token)
    repo = gh.get_repo(repo_slug)
    payload = load_event()

    try:
        if event_name in {"issues"} and "issue" in payload:
            number = payload["issue"]["number"]
            issue = repo.get_issue(number=number)
            if assignees:
                logger.info(f"Assigning to issue #{number}: {assignees}")
                issue.add_to_assignees(*assignees)
            else:
                logger.info("No assignees provided; skipping")
            # Reviewers do not apply to issues
            return 0

        if (
            event_name in {"pull_request", "pull_request_target"}
            and "pull_request" in payload
        ):
            number = payload["pull_request"]["number"]
            pr = repo.get_pull(number)

            if assignees:
                logger.info(f"Assigning to PR #{number}: {assignees}")
                pr.as_issue().add_to_assignees(*assignees)
            else:
                logger.info("No assignees provided; skipping")

            if reviewers:
                # You cannot request a review from the PR author; filter to avoid API errors
                author = payload["pull_request"].get("user", {}).get("login")
                logger.info(f"PR author: {author}, requested reviewers: {reviewers}")
                filtered = [r for r in reviewers if r != author]
                if filtered:
                    logger.info(f"Requesting reviewers for PR #{number}: {filtered}")
                    pr.create_review_request(reviewers=filtered)
                else:
                    logger.info(
                        f"All reviewers matched the PR author ({author}); cannot request review from yourself"
                    )
            else:
                logger.info("No reviewers provided; skipping")
            return 0

        logger.info(
            f"Unsupported event: {event_name}. This action handles issues and pull_request events."
        )
        return 0

    except GithubException as e:
        # Surface a proper annotation
        msg = getattr(e, "data", None) or str(e)
        logger.error(f"::error title=GitHub API error::{msg}")
        return 1
    except Exception as e:
        logger.error(f"::error title=Unhandled error::{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
