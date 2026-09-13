# TurboImmi — API and data (P0)

> **Status:** Day 3–13 **deployed:** profile through Admin, cited `POST /chat`, `GET /alerts` (manual USCIS cards). `ci.yml` has a `main` CD job; first Actions run still needs GitHub `AWS_DEPLOY_ROLE_ARN` + named secrets. Do not sprawl past this list.  
> Region: **`us-east-2`**. Table prefix: **`turboimmi-dev-`**.  
> Educational only; not a law firm; not legal advice. Attorney review is mandatory before filing.

Shared copy: [`shared/disclaimer.json`](../shared/disclaimer.json) (frontend UI + every Bedrock system prompt).

---

## Auth

| Rule | Detail |
|------|--------|
| Identity | Cognito User Pool JWT (PKCE public app client). Hosted UI prefix planned `turboimmi-dev`. |
| Groups | `Applicant`, `Attorney`, `Admin` |
| Role choose | After first login, if JWT has no group → in-app chooser (**Applicant / Attorney only**) → `POST /me/role` → Lambda `AdminAddUserToGroup` → **force token refresh** |
| Admin grant | `ADMIN_ALLOWLIST_EMAIL` (`.env` / Lambda env). Hosted UI Sign up is a normal user. `GET /me` compares JWT `email` (case-insensitive) and then `AdminAddUserToGroup(Admin)`. Never a chooser button. Do not create the user in the Cognito console. An address that already chose Applicant/Attorney is **not** promoted. |
| Role lock | After the first successful choose, reject further `POST /me/role`. No self-switch Applicant ↔ Attorney. Admin is not choosable. |
| Directory | Attorney directory is **authenticated-only**. Self-created attorneys `published=false`, `verified=false`, UI badge **Unverified**. Seeded demo attorneys start `published=true`. Admin publishes, unlists, flags, or marks verified after basic field checks. |
| Profiles | Three surfaces, same tables: applicant immigration fields on Users (`GET/PUT /me/profile`); attorney card on Attorneys (`PUT /attorneys/me`); admin stub on Users `admin` map (`GET/PUT /admin/me`). Admin never reads applicant cases or prefill. |
| Email | Cognito **default email** (no SES). Watch daily send cap. |

Public (no JWT): `GET /health`, `GET /disclaimer`. All other P0 routes require JWT.

---

## Rate and cost caps

| Cap | P0 value |
|-----|----------|
| API Gateway HTTP API | Throttle **50** req/s, burst **100** (whole API, Day 2) |
| Extract (vision) | **3** successful extract jobs per user per UTC day |
| Chat | **15** chat turns per user per UTC day |
| Uploads | jpeg / png / pdf; **max 8 MB** each; **max 2 files** per user at a time |
| Prefill object lifecycle | **14 days** then expire; also delete-after-confirm and a “Delete my uploads” action |
| Bedrock | Always set `maxTokens`; account `$10/month` budget `turboimmi-dev-monthly` (CDK). Optional Bedrock-specific alarm later. |

Exceeding per-user caps returns **429** with a stable `code` (see Errors).

---

## DynamoDB (few tables)

On-demand. **PITR on** every table. Attribute names `pk` / `sk`. Do not add tables in P0 without updating this doc.

### Users (`turboimmi-dev-users`)

Profile JSON + role flag. Journey stage enums live here even if UI is H-1B-only.

| | |
|--|--|
| PK | `USER#{cognitoSub}` |
| SK | `PROFILE` |
| Attrs | `roleChosen` (bool), `role` (`Applicant` \| `Attorney` \| `Admin` \| absent), `profile` (map), `admin` (map; `{ displayName }`), `chatDay` (UTC `YYYY-MM-DD`), `chatCount` (int; 15 turns / UTC day), `createdAt`, `updatedAt` |

First `GET /me` creates this item if missing (email from the token). `POST /me/role` with `Applicant` also seeds one draft H-1B case when the user has none.

**Profile sketch**

| Field | Notes |
|-------|--------|
| `legalName` | given / family |
| `dateOfBirth` | ISO date |
| `countryOfBirth` | |
| `countryOfCitizenship` | |
| `passportNumber`, `passportExpiry` | PII |
| `alienNumber` | optional |
| `email` | from Cognito; do not treat as verified filing email |
| `currentStatus` | e.g. F-1, H-1B, other |
| `journeyStage` | enum: `f1` \| `cpt` \| `opt` \| `stem_opt` \| `h1b` \| `h4` \| `h4_ead` \| `perm` \| `i140` \| `aos` |
| `employerLegalName`, `employerFein` | petitioner-side |
| `jobTitle`, `socCode`, `wageAmount`, `wageUnit`, `worksiteAddress` | |
| `dependents[]` | H-4 names only in P0; no I-539 packet |
| `confirmedPrefillAt` | set only by confirm-prefill |

Manual `PUT /me/profile` may write these fields. **OCR/extract never writes profile** except via `POST /prefill/confirm` after the user confirms.

---

### Cases (`turboimmi-dev-cases`)

One active H-1B case per applicant in P0 is enough; still key by case id.

| | |
|--|--|
| PK | `USER#{cognitoSub}` |
| SK | `CASE#{caseId}` |
| Attrs | `visaClass` (`H-1B`), interview, `formFields`, `score`, `attestation`, `status`, timestamps |

**Case sketch**

| Field | Notes |
|-------|--------|
| `intent` | `cap` \| `transfer` \| `extension` |
| `entryPath` | `change_of_status` \| `consular` |
| `capExemptClaim` | bool; default false |
| `requestedStart`, `requestedEnd` | ISO dates |
| `lcaEtaNumber` | optional until Day 7 |
| `formFields` | I-129 / H-style map (see inventory below) |
| `score` | `{ completeness, consistency, deductions[] }` — **not** approval odds |
| `attestationAcceptedAt` | required before `status=ready_to_file` |
| `status` | `draft` \| `in_progress` \| `ready_to_file` |

`ready_to_file` in P0 requires attestation checkbox **and** a visible “Request consult” CTA. Linked attorney review is P1.

**Day 6 interview (writes the case, not the profile).** Cap vs transfer vs extension and COS vs consular cannot be inferred from passport/offer letter. Optional `capExemptClaim` and requested start/end. Journey map is a UI stub over `profile.journeyStage` (no extra table).

---

### PrefillJobs (`turboimmi-dev-prefill-jobs`)

Extract **suggestions** only. TTL on `expiresAt`.

| | |
|--|--|
| PK | `USER#{cognitoSub}` |
| SK | `JOB#{jobId}` |
| Attrs | `status` (`uploaded` \| `extracted` \| `confirmed` \| `deleted`), `docType` (`passport` \| `offer_letter`), `s3Key`, `suggestions` (structured fields, **never raw OCR text**), `source` (`bedrock` \| `fixture`), `extractDay` (UTC `YYYY-MM-DD` for the daily cap), `expiresAt` (unix TTL) |

**Confirm-prefill is the only profile write from OCR.** Skip-upload / manual entry must work without a job. Extract is capped at **3 successful extracts per user per UTC day** (`429 RATE_LIMIT`); later delete/confirm does not reset the day count. If `DOCS_BUCKET` is unset, `uploadUrl` is null and `skipUpload: true` (tests and local without S3).

**Bodies (Day 5)**

| Path | Body / response |
|------|-----------------|
| `POST /prefill/upload-url` | `{ docType, contentType, contentLength }` → `{ jobId, uploadUrl, headers, skipUpload, docType }` |
| `POST /prefill/extract` | `{ jobId }` → job with `suggestions` |
| `POST /prefill/confirm` | `{ jobId, fields }` → profile (`confirmedPrefillAt` set; S3 object deleted) |
| `DELETE /prefill/uploads` | → `{ deleted }` |

---

### Attorneys (`turboimmi-dev-attorneys`)

| | |
|--|--|
| PK | `ATTORNEY#{attorneyId}` |
| SK | `PROFILE` |
| GSI1 | attrs `gsi1pk` = `STATE#{usState}`, `gsi1sk` = `SPEC#{specialty}#{attorneyId}` |

**Attorney sketch**

| Field | Notes |
|-------|--------|
| `cognitoSub` | owner |
| `displayName`, `firmName` | |
| `usState`, `specialties[]` | filter keys |
| `bio` | short |
| `published` | default **false**; only Admin or seeds set true |
| `verified` | default **false** (P0: basic field checks, not a bar lookup) |
| `flag` | `none` \| `incomplete` \| `mismatch` \| `other` |
| `flagNote` | short; Admin only |
| `createdAt` | |

UI: if `verified=false`, show **Unverified**. Browse lists `published=true` only. Seeded demo cards (`demo-chen`, `demo-okonkwo`) are written on first directory read. Self-created cards stay `published=false` until Admin publishes them. `ATTORNEY_DEMO_SUB` is **retired**.

---

### Consults (`turboimmi-dev-consults`)

In-app only. **No SES.**

| | |
|--|--|
| PK | `ATTORNEY#{attorneyId}` |
| SK | `CONSULT#{consultId}` |
| GSI1 | attrs `gsi1pk` = `USER#{applicantSub}`, `gsi1sk` = `CONSULT#{consultId}` |

**Consult sketch**

| Field | Notes |
|-------|--------|
| `applicantSub`, `attorneyId` | |
| `caseId` | optional |
| `message` | short; no PII dumps |
| `status` | `requested` \| `seen` \| `closed` |
| `createdAt` | |

Marketplace = **referral / discovery**. Do not “assign counsel.”

---

### Alerts (`turboimmi-dev-alerts`)

Manual H-1B news cards (Day 13). No X ingest.

| | |
|--|--|
| PK | `ALERT` |
| SK | `DATE#{yyyy-mm-dd}#{alertId}` |

Attrs: `title`, `sourceUrl` (USCIS.gov), `publishedOn`, `summary`, `tag` (`policy_alert` \| `news_release` \| `fee_change`).

---

### PolicyChunks (`turboimmi-dev-policy-chunks`)

Tiny H-1B corpus. Embeddings + cosine **in Lambda** (local ADR 009). No OpenSearch.

| | |
|--|--|
| PK | `CHUNK#{chunkId}` |
| SK | `META` |

**Provenance (required on every chunk)**

| Field | Notes |
|-------|--------|
| `source_url` | Canonical USCIS.gov deep link |
| `title` | Section / page title |
| `retrieved_at` | ISO timestamp when fetched |
| `content_hash` | Hash of stored text |
| `text` | Public USCIS text with attribution |
| `embedding` | Titan V2 vector (store as list; dim recorded in item) |

Chat: **citation-or-silence**. Show as-of / retrieved date. No USCIS/DHS seals or implied endorsement.

---

### AiAudit (`turboimmi-dev-ai-audit`)

| | |
|--|--|
| PK | `USER#{cognitoSub}` |
| SK | `TS#{isoTimestamp}#{auditId}` |
| TTL | `expiresAt` (unix, ~90 days) |

Attrs: `kind` (`extract` \| `chat` \| `explain_score`), `modelId`, `inputTokens`, `outputTokens`, `citationUrls[]`. **Never store OCR text, images, or full chat transcripts of passport data.**

---

## P0 HTTP routes

Base: HTTP API → FastAPI + Mangum. Local: `http://localhost:8000`.

| Method | Path | Auth | Day | Notes |
|--------|------|------|-----|--------|
| GET | `/health` | public | 1 | `{ "status": "ok" }` |
| GET | `/disclaimer` | public | 1 | `shared/disclaimer.json` |
| GET | `/health/auth` | JWT | 2 | Hello-path proof JWT is accepted |
| GET | `/me` | JWT | 3 / 11 | sub, groups, `roleChosen`. Allowlisted unused email is promoted to Admin here |
| POST | `/me/role` | JWT | 3 | `{ "role": "Applicant" \| "Attorney" }`; lock after first success. Admin is not a valid body |
| GET | `/me/profile` | JWT | 3 | |
| PUT | `/me/profile` | JWT | 3 | Manual edits only |
| GET | `/cases` | JWT Applicant | 3 | Each case includes derived `packet` (Day 7) |
| POST | `/cases` | JWT Applicant | 3 | Create H-1B case |
| GET | `/cases/{caseId}` | JWT owner | 3 | Includes derived `packet` (Day 7) |
| PATCH | `/cases/{caseId}` | JWT owner | 3 / 6 / 7 | Interview + `formFields` packet overrides. Completing intent + entry path sets `status=in_progress` |
| POST | `/prefill/upload-url` | JWT Applicant | 5 | Presigned PUT; type/size checks |
| POST | `/prefill/extract` | JWT Applicant | 5 | Bedrock vision or fixture JSON |
| POST | `/prefill/confirm` | JWT Applicant | 5 | **Only** OCR path that writes profile |
| DELETE | `/prefill/uploads` | JWT Applicant | 5 | Delete my uploads |
| POST | `/cases/{caseId}/score` | JWT Applicant | 8 | Body `{ explain?: bool }`. Rules engine; optional Bedrock explain of **rule hits only** (no PII). Persists `score` on the case |
| POST | `/cases/{caseId}/attestation` | JWT Applicant | 8 | Body `{ accepted: true, text }` must match `disclaimer.attestation`. Sets `attestationAcceptedAt` and `status=ready_to_file`. Does not file. `PATCH` cannot set `ready_to_file` |
| GET | `/attorneys` | JWT | 9 | Query `state`, `specialty`. `published=true` only. Auth-only |
| GET | `/attorneys/{attorneyId}` | JWT | 9 | Published listings, or the owner’s unpublished card. Else 404 |
| PUT | `/attorneys/me` | JWT Attorney | 9 | Self profile. Cannot set `published`/`verified`/`flag`. Stays unpublished until Admin publishes |
| GET | `/admin/me` | JWT Admin | 11 | Users `admin` map (`displayName`) |
| PUT | `/admin/me` | JWT Admin | 11 | `{ displayName }` |
| GET | `/admin/attorneys` | JWT Admin | 11 | All cards including unpublished. Query `published`, `verified`, `flagged`. Includes basic `checks` |
| PATCH | `/admin/attorneys/{id}` | JWT Admin | 11 | `{ published?, verified?, flag?, flagNote? }`. Not a bar lookup |
| POST | `/consults` | JWT Applicant | 10 | `{ attorneyId, caseId?, message }`. Published attorneys only. No SES. Max 8 open |
| GET | `/consults` | JWT | 10 | Applicant: mine. Attorney: inbox (marks `requested` → `seen`) plus own `attorney` card |
| GET | `/alerts` | JWT | 13 | Seeded manual H-1B cards (`uscis.gov` only). Add cards by PR, not a CMS. Follow-links to official X / newsroom live in the SPA |
| POST | `/chat` | JWT | 12 | Body `{ message }` (max 400). In-Lambda retrieve + Converse (or fixture). Citation-or-silence. 15 turns / UTC day → `RATE_LIMIT`. Audit stores citation URLs only, never the transcript |

No SES. No “assign attorney” route.

---

## I-129 / H-supplement field inventory (P0 ceiling)

Day 7 maps profile + interview → this set. **Do not add essays, extra supplements, or I-539 in P0.** GET/list case responses include a derived `packet` (profile + interview). Saved `formFields` override derived values. Unknown keys are dropped. Evidence items are **presence flags**, not stored files. No PDF in P0.

| Group | Fields |
|-------|--------|
| Petitioner | legal name, US address, FEIN (optional), org type |
| Beneficiary | family name, given name, DOB, country of birth, citizenship, passport number/expiry, A-number (optional) |
| Classification | `intent` (cap / transfer / extension), `entryPath` (COS / consular), cap-exempt flag |
| Employment | job title, SOC (optional), wage amount + unit, hours/week (optional), worksite address |
| LCA | ETA case number (optional; checklist item if missing) |
| Dates | requested start, requested end |
| H supplement (data only) | off-site / itinerary flag (bool); **no** specialty-occupation legal narrative auto-draft in P0 |
| Evidence checklist | passport biographic page, offer letter, LCA (if any) — presence flags, not file vault |

PDF polish is a cut-order item. Structured JSON + review UI is enough.

---

## Validation rule catalog (sketch)

Rules engine is **Python**, completeness + consistency only. Completeness % uses C-01–C-09. Consistency % uses X-01–X-04 blockers; X-05 is a warning only. C-10 is a data-integrity deduction if `ready_to_file` lacks attestation. X-03 compares saved packet `petitionerLegalName` to `profile.employerLegalName` when both are set. Bedrock may explain **which rules hit**, never invent odds. Starter attributed excerpts: [`shared/policy/h1b_excerpts.json`](../shared/policy/h1b_excerpts.json) (`source_url`, `title`, `retrieved_at`, `content_hash`). Day 12 chat embeds those chunks (Titan when `BEDROCK_EMBED_MODEL_ID` is set; hashed bag-of-words in tests) and retrieves with cosine, then a lexical fallback.

**Completeness (C-)** — missing required data

| Id | Trigger |
|----|---------|
| C-01 | Missing legal name |
| C-02 | Missing date of birth |
| C-03 | Missing passport number |
| C-04 | Missing employer legal name |
| C-05 | Missing job title |
| C-06 | Missing wage |
| C-07 | Missing worksite |
| C-08 | Missing `intent` |
| C-09 | Missing `entryPath` |
| C-10 | `ready_to_file` without attestation |

**Consistency (X-)** — fields disagree

| Id | Trigger |
|----|---------|
| X-01 | Passport expiry before requested start |
| X-02 | Requested end before start |
| X-03 | Confirmed offer-letter employer ≠ profile employer (if both set) |
| X-04 | Wage present without wage unit |
| X-05 | Dependents listed but no H-4 note on profile (warning, not blocker) |

Score UI must say completeness/consistency, **not** “chance of approval.”

---

## Uploads (PII)

| Rule | Value |
|------|--------|
| Bucket | Private, SSE, block public access (Day 2) |
| Types | `image/jpeg`, `image/png`, `application/pdf` |
| Size | 8 MB max per file |
| Count | Max 2 objects per user |
| Lifecycle | Expire after **14 days** |
| Delete | After confirm **or** `DELETE /prefill/uploads` |
| Logging | Never log OCR text or image bytes |

---

## Errors

JSON `{ "detail": { "code": "ROLE_LOCKED", "message": "..." } }` (FastAPI envelope). Stable codes: `ROLE_LOCKED`, `RATE_LIMIT`, `CONFIRM_REQUIRED`, `NOT_FOUND`, `FORBIDDEN`, `VALIDATION`, `UNAUTHORIZED`.

---

## Out of scope (do not add in P0)

RDS, OpenSearch, SES, payments, public attorney SEO pages, AgentCore, USCIS e-filing, approval-odds fields, X ingest, extra DynamoDB tables.
