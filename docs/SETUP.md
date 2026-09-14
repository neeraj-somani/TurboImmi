# TurboImmi — Setup checklist (Day 0)

> Complete before Day 2 AWS deploy.  
> Region for P0: **`us-east-2`**. Resource prefix: **`turboimmi-dev`**.  
> Record account IDs, model IDs, Cognito prefix, personal emails, and CloudFront URL in **local** `.env` and `docs/SETUP.local.md` only (gitignored). Never put those values in this file or in git. Public docs may name variables (e.g. `BUDGET_ALERT_EMAIL`).

## Accounts & CLI

- [x] AWS console login works
- [x] Daily work uses IAM Identity Center (SSO) or least-privilege IAM user (not root)
- [x] AWS CLI v2 installed
- [x] `aws sts get-caller-identity` returns the expected account/ARN
- [x] CLI default/region set to `us-east-2`
- [x] Credentials only in `~/.aws/` — never committed
- [x] **`cdk bootstrap aws://<account>/us-east-2`** succeeded (`CDKToolkit` CREATE_COMPLETE)

## Agent Toolkit for AWS (local AI assist)

The AWS [Agent Toolkit](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html) is **local Day 0 tooling** (Cursor MCP + skills). It is not a runtime dependency of TurboImmi.

- [x] AWS CLI `configure agent-toolkit` completed (skills + `aws-mcp`)
- [x] Cursor MCP `aws-mcp` points at CLI profile `default` via `AWS_MCP_PROXY_PROFILES`
- [x] Restart Cursor after MCP changes so the new server loads (MCP calls succeed)
- Note: the Agent Toolkit **control plane** is `us-east-1` (AWS constraint). App resources stay in **`us-east-2`**.

## Local tooling (Windows notes)

This project is commonly developed on Windows 10/11 + PowerShell.

- [x] Node.js 20+ (`node -v`)
- [x] npm available (`npm -v`)
- [x] Local Python: **3.12 not required**. Machine uses 3.13 (CDK/tests) and 3.11. Lambda **runtime** stays 3.12
- [x] AWS CDK available via `npx aws-cdk` (activate `infra/.venv` first so `python` sees `aws-cdk-lib`)
- [x] Git + GitHub SSH/HTTPS push works
- [ ] **Docker Desktop** — not required for Day 2 Lambda bundle (local pip manylinux wheels). Start Docker only if that bundler fails
- [x] Local loop: Vite `localhost:5173` + FastAPI `localhost:8000` `/health` (Day 1). Day 3 `/me` and `/cases`, Day 5 `/prefill`, then `/attorneys`, `/consults`, `/admin`, `/chat`, and `/alerts` proxy to FastAPI. Real Cognito/DDB when `USERS_TABLE` / `USER_POOL_ID` are set in local `.env`. Optional `DOCS_BUCKET`, `PREFILL_TABLE`, `AUDIT_TABLE`, `ATTORNEYS_TABLE`, `CONSULTS_TABLE`, `ALERTS_TABLE` for real uploads, jobs, directory, consults, and news cards (tables default to `turboimmi-dev-*` if unset). Optional empty `ADMIN_ALLOWLIST_EMAIL=` for the unused Admin grant address (never commit the value). Empty `GITHUB_REPO=` (`owner/name`) so a local CDK deploy trusts the same GitHub repo as Actions. No LocalStack.

From repo root (two terminals):

```text
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd frontend
npm run dev
```

`pytest` from `backend/` (activate `backend/.venv`). `cdk synth` from `infra/` (activate `infra/.venv`).

## AWS enablement

- [x] Billing/budget alarm (**$10 / month**, `turboimmi-dev-monthly`) — CLI-created, then **recreated by CDK** (local ADR 013; CloudFormation cannot import `AWS::Budgets::Budget`)
- [x] Day 0: `infra/` CDK app + `.env.example`; copy to `.env` and set `BUDGET_ALERT_EMAIL` locally (never commit `.env`)
- [x] Bedrock model access enabled in `us-east-2` (Amazon Nova chat + vision + Titan embeddings)
- [x] Record chosen model IDs in **`SETUP.local.md`** (IDs change over time)
- [x] Tiny Bedrock **Converse** / InvokeModel “hello” succeeds (Nova Lite text + vision; Titan Embeddings V2)
- [x] **Converse-first:** 15-minute AgentCore probe in `us-east-2` — **skipped for P0** (control-plane APIs work; `agentcore` CLI not installed; no harness created). Note in `SETUP.local.md`
- [x] **RAG:** in-Lambda embeddings + cosine (no OpenSearch Serverless; no Bedrock KB in P0). Note in `SETUP.local.md`
- [x] Can create Cognito User Pool, S3, CloudFront, API Gateway, Lambda, DynamoDB (no SCP blocks observed; CDK stack already deployed)
- [x] IAM can pass roles to Lambda / CloudFront (confirmed Day 2 deploy)

## Auth planning

- [x] Cognito Hosted UI domain prefix planned as **`turboimmi-dev`** (available; add a suffix if taken on Day 2); record the final value in `SETUP.local.md`
- [x] Plan Cognito callback + sign-out URLs for:
  - `http://localhost:5173` (Vite dev)
  - CloudFront URL (fill in `SETUP.local.md` after first Day 2 deploy)
- [x] Plan CORS allowlist for the same origins
- [x] Role assignment = in-app chooser after first login → `POST /me/role` → `AdminAddUserToGroup` → token refresh; **no self-switch** after first choose. Admin is **not** on the chooser — set `ADMIN_ALLOWLIST_EMAIL` and Sign up with that unused address; `GET /me` promotes. Do not create the user in the Cognito console
- [x] Cognito **default email** (no SES) for verification; watch the daily send cap

## Data protection

- [x] Prefill uploads bucket: private, SSE, **lifecycle expiry 14 days**
- [x] DynamoDB **PITR** enabled on every P0 table
- [x] Placeholder ToS + Privacy Policy pages drafted (`/terms`, `/privacy`, marked “draft — counsel review”) — counsel review before public launch

## Secrets & CI

- [x] No long-lived keys, personal emails, account IDs, or PII in git or frontend
- [x] Real setup values only in `.env` and `SETUP.local.md`; commit `.env.example` with **empty keys** only (`BUDGET_ALERT_EMAIL=`, `BEDROCK_*_MODEL_ID=`, `DOCS_BUCKET=`, `ADMIN_ALLOWLIST_EMAIL=`, `GITHUB_REPO=`)
- [x] Plan SSM paths later: `/turboimmi/dev/...`
- [x] GitHub Actions auth = **OIDC to AWS** (Day 13). CDK creates provider `token.actions.githubusercontent.com` and role `turboimmi-dev-github-deploy`, trusted by this repo’s `main` under both GitHub OIDC `sub` shapes (name-only and `owner@id/repo@id` for repos created after 2026-07-15). After the first local `cdk deploy`, set Actions **variable** `AWS_DEPLOY_ROLE_ARN` to stack output `GitHubDeployRoleArn`. Add Actions **repository Secrets** (the repo-level list, not Environment secrets and not Variables) named `BUDGET_ALERT_EMAIL`, `ADMIN_ALLOWLIST_EMAIL`, `BEDROCK_CHAT_MODEL_ID`, `BEDROCK_VISION_MODEL_ID`, `BEDROCK_EMBED_MODEL_ID`. The deploy job has no `environment:`, so Environment secrets never reach it. Never put those values in the workflow file. The GitHub role is not the account root and must not rewrite the `$10` budget; change that email from a laptop deploy. Protect `main` (PR + green `checks` required).
- [x] Read [GIT_AND_CICD.md](GIT_AND_CICD.md): feature branches → PR → `main`; CI checks from Day 2; CD from Day 13; IaC-first (no lasting click-ops)

## Repo hygiene

- [ ] Public starter files on `main` when the owner asks to commit (never commit local planning files)

## Day 0 exit (all required)

- [x] STS OK in us-east-2
- [x] `cdk bootstrap` done
- [x] Bedrock Converse works; model IDs recorded in `SETUP.local.md`
- [x] Billing alarm set; CDK construct in `infra/`; **CDK-owned** after one-time delete + `cdk deploy` (local ADR 013)
- [x] Node / CDK (`npx aws-cdk`) OK; local Python 3.12 not required (3.13 venv for CDK synth; Lambda runtime stays 3.12)
- [x] RAG approach decided: in-Lambda retrieval (ADR 009)
- [x] AgentCore skipped for P0 (noted in `SETUP.local.md`)

**Days 5–11 are deployed.** After Day 0, do **not** create more AWS resources with the CLI except Bedrock model access.
