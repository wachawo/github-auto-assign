# GitHub Auto-assign

Automatically assign Issues and Pull Requests and request reviewers.

## Usage

```yaml
name: Auto-assign
on:
  issues:
    types: [opened, reopened]
  pull_request:
    types: [opened, reopened, ready_for_review]

jobs:
  assign:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
    steps:
      - uses: wachawo/github-auto-assign@v0.0.1
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          assignees: wachawo
          reviewers: wachawo
```

## Inputs

- `assignees` – comma/space-separated usernames
- `reviewers` – comma/space-separated usernames (PRs only)

## Dev

```bash
pip3 install -r requirements-dev.yml
pre-commit install
pre-commit install --hook-type pre-push
pre-commit run --all-files
```
