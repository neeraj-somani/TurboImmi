# TurboImmi — Agent Guide

TurboImmi is an AI-assisted, TurboTax-style immigration platform (H-1B MVP first). It is **not a law firm** and does **not provide legal advice**. Content is **educational**; **attorney review is mandatory before filing**.

## Local vs GitHub

GitHub is a **clean cloneable starter**. This file is the **public agent contract**. Author `.cursor/rules/` stay on the author's machine and are **not** in this clone — do not link to or require them.

Day-by-day plans, ADRs, changelog, Cursor rules, and AWS account notes stay local. Never commit those paths (see `.gitignore`). Do not ask whether to include them.

## Public docs (in this repo)

| Doc | Purpose |
|-----|---------|
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | **Locked** P0 stack |
| [docs/SETUP.md](docs/SETUP.md) | Day 0 AWS / tooling checklist (no secrets) |
| [docs/GIT_AND_CICD.md](docs/GIT_AND_CICD.md) | **Locked** branching, CI/CD, rollback |
| [docs/API_AND_DATA.md](docs/API_AND_DATA.md) | P0 routes + DynamoDB keys (created Day 1) |
| [AGENTS.md](AGENTS.md) | This guide |

When the user makes a product/tech decision in chat, **update the owning public doc and the local planning files in the same turn** (table below).

## Local planning (this machine only — do not commit)

| Doc | Purpose |
|-----|---------|
| `docs/PRODUCT_ROADMAP.md` | Product phases, P0/P1 use cases, compliance |
| `docs/IMPLEMENTATION_PLAN.md` | Locked day-by-day P0 plan |
| `docs/decisions/` | Architecture Decision Records |
| `docs/changelog/` | Weekly notes (`YYYY-MM-wN.md`) |
| `docs/TRAJECTORY.md` | High-level timeline of decisions |
| `docs/SETUP.local.md` | Account ID, model IDs, Cognito prefix, CloudFront URL, personal emails |
| `.env` | Runtime secrets/PII (gitignored); `.env.example` is public keys-only |
| `.cursor/rules/` | Author Cursor conventions |

## Docs-sync contract (prevents stale docs)

| Change | Update | GitHub? |
|--------|--------|---------|
| Scope / phase / use case | local `docs/PRODUCT_ROADMAP.md` | no |
| Stack, AWS service, library | `docs/TECH_STACK.md` (+ local ADR if alternatives rejected) | yes |
| Schedule, day content, cut order | local `docs/IMPLEMENTATION_PLAN.md` (tick shipped items) | no |
| API route, DynamoDB key, entity | `docs/API_AND_DATA.md` | yes |
| Git / CI / deploy process | `docs/GIT_AND_CICD.md` | yes |
| Setup prerequisite (no secrets) | `docs/SETUP.md` | yes |
| Account / model IDs | local `docs/SETUP.local.md` | no |
| Deployed stack output (URL, IDs) | `README.md` | yes |
| Any of the above | local changelog + TRAJECTORY | no |

Locked docs change only with a local ADR. End the reply by listing changed doc files. The PR template (`.github/pull_request_template.md`) checks **public** docs only.

## Locked P0 stack

- **Region:** **`us-east-2`** (all P0 AWS resources; do not use us-east-1)
- **Local AI assist (optional):** Agent Toolkit for AWS (Cursor `aws-mcp` + skills). Toolkit APIs are us-east-1; that does not move app resources.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind → **S3 + CloudFront** SPA
- **Auth:** Amazon Cognito (`Applicant`, `Attorney` groups); role lock after first choose
- **API:** API Gateway HTTP API + Python 3.12 Lambda (**FastAPI + Mangum**)
- **DB:** DynamoDB **few tables** (on-demand, PITR)
- **Files:** Private S3 + presigned URLs; jpeg/png/pdf; max 8 MB; max 2 files; **14-day** lifecycle + delete-after-confirm
- **AI:** Amazon Bedrock **Converse first**; Day 0 skipped AgentCore (not easy enough). Stay on Converse for P0.
- **RAG:** embeddings + in-Lambda cosine over tiny corpus (local ADR 009); no OpenSearch Serverless in P0
- **Disclaimer:** `shared/disclaimer.json` (frontend + backend)
- **IaC:** AWS CDK (Python), **IaC-first** — all P0 AWS resources in `infra/`; CDK-owned `$10` budget (local ADR 013; CloudFormation cannot import it); no lasting click-ops (local ADR 012)
- **Secrets / PII:** never in git. Real values only in `.env` and `docs/SETUP.local.md`. Public `.env.example` has empty keys (`BUDGET_ALERT_EMAIL=`, `BEDROCK_*_MODEL_ID=`). Do not ask whether to commit these.
- **CI/CD:** GitHub Actions with **OIDC → AWS** (see [docs/GIT_AND_CICD.md](docs/GIT_AND_CICD.md))

Do **not** introduce Next.js SSR, RDS, ECS/EKS, Spark/Databricks, or paid X API in P0 without a local ADR.

## Monorepo (target)

```text
frontend/   # Vite React SPA
backend/    # FastAPI / Lambda / agents
infra/      # AWS CDK (Python)
shared/     # disclaimer.json (imported by frontend + backend)
docs/       # public stack / setup / API / git docs only
```

Local loop: Vite `:5173` + FastAPI `:8000` → real Cognito / DynamoDB / S3 / Bedrock. No LocalStack.

## Hard rules

1. Educational + attorney-review framing on every AI/form surface.
2. Prefill: extract → **user confirms** → then write profile (never silent auto-write).
3. Validation score = completeness/consistency — **not** approval odds.
4. USCIS content: attribution, deep links, as-of dates; **no** seals/logos/endorsement.
5. Official news: USCIS newsroom / policy updates — **no** X scraping or paid X API in P0.
6. Secrets and setup PII never in frontend or git. Write emails, account IDs, keys, and names to `.env` and/or `SETUP.local.md` only. Public docs use variable names (`BUDGET_ALERT_EMAIL`), never values. CDK reads env at synth/deploy. If a real value lands in a public file, remove it the same turn. Never `git add` `.env` or `SETUP.local.md` — do not ask. Runtime secrets later: SSM/Secrets Manager.
7. Prefer deterministic Python for CRUD/validation; Bedrock for extract/explain/cited chat.
8. Git: short-lived `feature/*` → PR → `main`; no long-lived day-branches; revert/tags for rollback ([docs/GIT_AND_CICD.md](docs/GIT_AND_CICD.md)). AWS resources via CDK only after Day 0.
9. Roles: in-app chooser → `POST /me/role` → `AdminAddUserToGroup` → token refresh; **no self-switch** after first choose. Attorney directory auth-only; self-created attorneys `published=false` + "Unverified".
10. `ready_to_file` in P0 = attestation checkbox + consult CTA (linked attorney review is P1).
11. Uploaded PII: private SSE bucket, 14-day lifecycle, deletable; never log OCR text.
12. One shared `DISCLAIMER` in `shared/disclaimer.json` reused by frontend and backend prompts.

## MVP focus

H-1B path + thin AI prefill (passport + offer letter) + short intent interview + attorney marketplace (directory + consult request) + scoped policy chat. Journey model supports F-1→OPT→H-1B→H-4→EB later.

## Next implementation gate

1. Day 0–3 live (hello path + profile/case APIs + role chooser). Optional leftover: local Python 3.12. CI/tag wait on a public commit.
2. Day 4: landing polish, disclaimer gate, placeholder ToS + Privacy, dual dashboards.
3. Follow the **local** implementation plan (day-by-day) incl. its daily ritual.
