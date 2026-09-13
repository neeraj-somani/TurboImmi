# TurboImmi

AI-assisted immigration platform (TurboTax-style) for people navigating U.S. processes such as H-1B — educational tooling with attorney marketplace referral. **Not a law firm; not legal advice.** A licensed immigration attorney must review forms and strategy before filing.

## Docs (in this repo)

| Doc | Purpose |
|-----|---------|
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | **Locked** P0 tech stack |
| [docs/SETUP.md](docs/SETUP.md) | Day 0 AWS / tooling checklist (no secrets) |
| [docs/GIT_AND_CICD.md](docs/GIT_AND_CICD.md) | **Locked** Git branching + CI/CD + rollback |
| [docs/API_AND_DATA.md](docs/API_AND_DATA.md) | P0 routes + DynamoDB keys (created on Day 1) |
| [AGENTS.md](AGENTS.md) | Guide for AI coding agents |

Day-by-day plans, ADRs, and account/model IDs are kept by the author locally and are **not** in this clone.

Cursor users: follow [AGENTS.md](AGENTS.md). Author `.cursor/rules/` are local and not in this clone.

## Status

P0 stack and Git/CI/CD **locked**. Days 5–13 are live in `us-east-2`: prefill through Admin, cited policy chat, manual USCIS news cards, and a GitHub OIDC deploy role. Local loop remains Vite (`localhost:5173`) + FastAPI (`localhost:8000`).

**Next:** Day 14 E2E demo. First Actions deploy still needs GitHub `AWS_DEPLOY_ROLE_ARN` + named secrets (see [SETUP.md](docs/SETUP.md)).

## Stack (P0)

React 18 + TypeScript + Vite + Tailwind on S3 + CloudFront; Cognito; API Gateway HTTP API + Python 3.12 Lambda (FastAPI + Mangum); DynamoDB (few tables); Bedrock Converse; CDK Python. **Region: `us-east-2`.** MIT licensed.

## Stack outputs (Day 11)

- CloudFront URL: https://dbez90hle5qkw.cloudfront.net
- Cognito User Pool ID: `us-east-2_C31ugmbVD`
- Hosted UI: https://turboimmi-dev.auth.us-east-2.amazoncognito.com
- API URL: https://abifpzun5a.execute-api.us-east-2.amazonaws.com
