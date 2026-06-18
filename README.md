## GitHub Auto-assign

Automatically assign Issues and Pull Requests.

When an Issue is opened or reopened, this action assigns it to the configured `assignees`.
When a Pull Request is opened, reopened, or marked as `ready_for_review`, this action assigns it to `assignees` and requests review from `reviewers`.

It uses `${{ secrets.GITHUB_TOKEN }}` (no extra secrets required). Make sure the workflow has `issues: write` and `pull-requests: write` permissions.

### Usage

Create a workflow file `.github/workflows/auto-assign.yml`:

```yaml
name: Auto-assign
on:
  issues:
    types: [opened, reopened]
  pull_request_target:
    types: [opened, reopened, ready_for_review]

jobs:
  assign:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
    steps:
      - name: Auto-assign and request reviewers
        if:  github.event_name == 'issues' || github.event_name == 'pull_request_target'
        uses: wachawo/github-auto-assign@v1
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          assignees: wachawo
          reviewers: gvanrossum,torvalds,wachawo
```

Don't forget change `assignees` and `reviewers`. You can specify multiple assignees/reviewers by comma separation.

> **Note:** use `pull_request_target`, not `pull_request`. For pull requests
> opened from a fork the `pull_request` event grants a read-only `GITHUB_TOKEN`,
> so assigning/requesting reviewers fails with `403 Resource not accessible by
> integration`. `pull_request_target` runs in the base repository context with a
> writable token. It is safe here because this action only calls the GitHub API
> and never checks out the pull request's code.

### Development

```bash
pip3 install -r requirements-dev.yml
pre-commit install
pre-commit install --hook-type pre-push
pre-commit run --all-files
```

```bash
pytest --cov=src --cov-report=term-missing --cov-report=xml
coverage report
```
