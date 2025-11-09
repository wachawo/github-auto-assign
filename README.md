## GitHub Auto-assign

Automatically assign Issues and Pull Requests.

### Usage

Create a workflow file `.github/workflows/auto-assign.yml`:

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
      - name: Auto-assign and request reviewers
        if:  github.event_name == 'issue' || github.event_name == 'pull_request'
        uses: wachawo/github-auto-assign@v1
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          assignees: wachawo
          reviewers: gvanrossum,torvalds,wachawo
```

Don't forget change `assignees` and `reviewers`. You can specify multiple assignees/reviewers by comma separation.

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
