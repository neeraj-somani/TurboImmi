## What

<!-- 1–3 lines: what this PR ships. Reference the plan day, e.g. "Day 5 — prefill confirm". -->

## Checks

- [ ] CI green (pytest, frontend build, `cdk synth`)
- [ ] `main` stays demo-safe after merge
- [ ] No secrets, keys, or `.env` committed
- [ ] No local planning files (`IMPLEMENTATION_PLAN`, `PRODUCT_ROADMAP`, ADRs, changelog, `TRAJECTORY`, `SETUP.local.md`, `.cursor/rules/`)

## Docs sync (required — public files only)

See [AGENTS.md](../AGENTS.md) (public contract). Author Cursor rules are not in this clone.

- [ ] Stack / library change? → `docs/TECH_STACK.md`
- [ ] New API route or table key? → `docs/API_AND_DATA.md`
- [ ] Git / CI / deploy change? → `docs/GIT_AND_CICD.md`
- [ ] Setup prerequisite (no secrets)? → `docs/SETUP.md`
- [ ] New stack output (URL, pool ID)? → `README.md`
- [ ] Tick **local** `IMPLEMENTATION_PLAN.md` / changelog on disk — **do not include those files in this PR**
- [ ] N/A — docs unaffected (explain why)

## Compliance (AI / form surfaces only)

- [ ] Educational + attorney-review disclaimer present (`shared/disclaimer.json`)
- [ ] No profile write without user confirmation (prefill)
- [ ] USCIS citations include URL + as-of date; no seals/logos
