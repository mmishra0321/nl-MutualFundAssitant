# Runbook: GitHub Actions refresh failures

## Workflow

`.github/workflows/refresh-corpus-index.yml` — daily **10:00 IST** (04:30 UTC) + manual dispatch.

## On failure

1. Open **Actions** → failed run → expand **Phase 1.5** or **Phase 2.5** step logs.
2. Download artifact `corpus-index-<run_id>` if upload succeeded partially.
3. Fix root cause (see `crawl-failure.md` for corpus issues).
4. Re-run via **Run workflow** (workflow_dispatch).

## Optional notifications

Enable GitHub **Settings → Notifications → Actions** for the repository, or add a future step:

```yaml
- uses: actions/github-script@v7
  if: failure()
  with:
    script: |
      // post to issue / Slack webhook
```

## Phase 5 quality gate

After fixing ingestion, run locally:

```bash
./phases/quality/scripts/run_quality_gates.sh
```

CI: `.github/workflows/quality-gates.yml` on push/PR.
