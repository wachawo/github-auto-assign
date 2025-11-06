# GitHub Auto-assign (Python)

Automatically assign Issues and Pull Requests and request reviewers.

## Inputs
- `assignees` *(optional)* – comma/space-separated usernames. Example: `alice,bob`.
- `reviewers` *(optional)* – comma/space-separated usernames (PRs only).

## Events
- Issues: assigns on `issues` events (e.g., `opened`, `reopened`).
- Pull Requests: assigns and requests reviewers on `pull_request` / `pull_request_target` events (`opened`, `reopened`, `ready_for_review`).

## Example workflow
```yaml
name: GitHub Auto-assign
on:
  issues:
    types: [opened, reopened]
  pull_request:
    types: [opened, reopened, ready_for_review]

jobs:
  auto_assign:
    runs-on: ubuntu-latest
    steps:
      - name: GitHub Auto-assign
        uses: wachawo/github-auto-assign@v1
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          assignees: wachawo
          reviewers: wachawo
```

## Notes

* Review requests cannot be made to the PR author; the action filters them out.
* Team reviewers are not supported in this minimal version; you can add `team_reviewers=[...]` to `create_review_request` if needed.


## Dev

```bash
pip3 install -r requirements-dev.yml
pre-commit install
pre-commit install --hook-type pre-push
pre-commit run --all-files
```
