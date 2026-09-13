# TurboImmi — Git & CI/CD (DevOps)

> **Status: LOCKED** (2026-09-07; IaC-first + no secrets/PII in git, local ADR 012; CD Day 13 per ADR 016; GitHub OIDC `sub` formats per local ADR 018)  
> Solo P0 practices. **CI checks from Day 2; CD (deploy) from Day 13.**  
> **Auth:** GitHub OIDC → AWS (no long-lived keys).

## Local planning vs this repo

This clone is a **clean starter**. The author's day-by-day plan, ADRs, changelog, Cursor rules, and `SETUP.local.md` stay on their machine (see `.gitignore` and [AGENTS.md](../AGENTS.md)). Never commit those paths.

## Branching model

**Trunk-based / short-lived feature branches.** Do **not** use one long-lived branch per implementation day.

```text
main                 ← always deployable; what CloudFront / API run
 └─ feature/...      ← hours to a few days, then PR → merge
 └─ fix/...
 └─ chore/...
```

| Practice | Rule |
|----------|------|
| Default branch | `main` only for P0 (no `develop` yet) |
| Branch names | `feature/d5-prefill-confirm`, `fix/cognito-callback`, `chore/ci-oidc` |
| Lifetime | Prefer &lt; 3 days open; merge often |
| Day numbers | Optional in branch name for traceability — not permanent day-branches |
| Direct commits to `main` | Avoid once CI exists; use PRs |

### Why not day-branches?

Day-1…Day-14 branches go stale, cause merge pain, and don’t match shippable units. **Features** are the unit of merge; days live in the author's local implementation plan.

## Pull requests (even solo)

1. Create branch from latest `main`
2. Implement + test locally
3. Open PR → fill the **PR template** (`.github/pull_request_template.md`) incl. the **public** docs-sync checklist → CI must pass (pytest, frontend build, `cdk synth`)
4. Merge (squash OK for solo)
5. Deploy from `main` (manual `cdk deploy` + `s3 sync` until Day 13; Actions after)
6. Smoke-test CloudFront + API

Protect `main`: require PR + green **`checks`** before merge (enable in the GitHub repo: Settings → Branches). The Day 13 `deploy` job runs only after a push to `main`.

## CI/CD pipeline

| Trigger | Actions |
|---------|---------|
| PR → `main` (**Day 2+**) | `pytest`, `npm run build`, `cdk synth` — **block merge on failure** |
| Push/merge to `main` (**Day 13+**) | After `checks`: assume `AWS_DEPLOY_ROLE_ARN` (OIDC) → CDK deploy → `s3 sync` (keep `config.json`) → CloudFront invalidation. Workflow file uses secret **names** only. The deploy role trusts this repo’s `main` under both GitHub OIDC `sub` shapes (name-only and `owner@id/repo@id`; local ADR 018) |
| Secrets | **GitHub OIDC → AWS**; no long-lived keys in repo |
| Environments | One env P0 (`dev`); add `prod` later with same branch rules |

**Rule:** Broken work may exist on a feature branch. **`main` must stay demo-safe.**

Infra changes ship like app changes: `feature/*` → PR → `cdk synth` in CI → merge to `main` → deploy from `main` (manual `cdk deploy` until Day 13). **Do not** create Cognito, buckets, tables, APIs, budgets, or alarms in the console and leave them unmanaged. Emergency CLI/console changes must be imported or recreated in CDK the same work day.

**Secrets / PII:** never commit `.env`, personal emails, account IDs, or keys. CI/CD uses **OIDC** (and repo secrets only if the owner adds them). Never bake personal emails into workflow files. Public docs may name variables (`BUDGET_ALERT_EMAIL`); values stay in local `.env` / `SETUP.local.md`.

## Rollback (if something breaks)

1. **Prefer `git revert`** of the bad merge on `main` (new commit; no history rewrite) → redeploy
2. **Redeploy last known-good tag** (e.g. `p0-d2-hello`, `p0-mvp`) while fixing on a branch
3. **Avoid** `git push --force` to `main`
4. Prefer additive DynamoDB/CDK changes; don’t destroy tables casually; budget uses `RemovalPolicy.RETAIN`
5. Keep prior frontend artifacts or S3 versioning so static assets can roll back

## Tags & milestones

Tag after major green deploys:

| Tag example | When |
|-------------|------|
| `p0-d2-hello` | Cognito + CF + JWT health works |
| `p0-d8-score` | Validation score path works |
| `p0-d13-ci` | CD pipeline deploys from `main` |
| `p0-mvp` | P0 Definition of Done met |

Note tags in the author's local changelog (not in this repo).

## Local workflow cheat sheet

```bash
git checkout main
git pull
git checkout -b feature/d3-profile-api
# ... work ...
git push -u origin HEAD
# open PR, wait for CI, merge
```

Undo bad merge on `main`:

```bash
git revert -m 1 <merge-commit-sha>
git push
# redeploy
```

## Anti-patterns

- Fourteen open day-branches merging at the end
- Force-push / hard reset as normal undo on `main`
- Deploying WIP feature branches to the only demo URL
- Committing AWS keys, `.env` secrets, personal emails, account IDs, or **local planning files**
- Creating AWS resources in the console/CLI and leaving them out of CDK
- Merging a PR with the public docs-sync checklist unticked and no “N/A” reason

## Docs stay in sync (anti-staleness)

1. **[AGENTS.md](../AGENTS.md)** — public docs-sync and local-vs-GitHub contract (author `.cursor/rules/` are local-only)
2. **PR template** — public-docs checklist only; tick the local plan on disk, do not include it in the PR
3. **Daily ritual** (author machine): tick local plan checkboxes, add local changelog bullet

Optional later (P1): a CI job that fails when `backend/` or `infra/` changes without a public `docs/` change in the same PR unless labelled `docs-na`.

## Related

- Setup: [SETUP.md](SETUP.md)
- PR template: `.github/pull_request_template.md`
