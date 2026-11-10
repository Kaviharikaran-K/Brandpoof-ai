# BrandProof AI

Evidence-based brand governance platform.

**Verify. Explain. Improve. Human approval.**

BrandProof AI keeps every claim in marketing copy tied to approved evidence: confirmed facts,
terminology rules, guidelines and brand assets. Content is analysed against that evidence base,
every finding cites the record that produced it, and only a human reviewer can approve or reject.

> All demo data is fictional (NovaTech Solutions / NovaCloud).

## Principles

1. **No evidence, no claim.** Pending, expired or conflicting facts never count as proof — the
   finding is routed to a human instead.
2. **Explainable by default.** Each finding contains the rule or fact, the detected text, offsets
   and a recommended correction where one is derivable.
3. **Measurement, not taste.** Visual checks report dominant colours, CIE76 ΔE palette deviation,
   WCAG contrast ratios and logo-match scores. Subjective quality is always flagged for humans.
4. **Human approval only.** The engine never approves content; decisions are stored with author,
   note and timestamp.
5. **Local-first privacy.** Deterministic checks run on your server. Optional external AI language
   review requires explicit admin consent and a configured provider key.

## Features

- **Evidence base** — approved facts with confirmation workflow, versioning, sources and
  effective/expiry dates; required/prohibited terminology; guidelines and document uploads;
  logo and colour assets.
- **Analysis engine** — deterministic pipeline for factual claims, terminology, guidelines and
  tone, with evidence citations, severity, suggested corrections and clarification routing.
- **Visual inspection** — dominant-colour extraction, palette deviation (CIE76 ΔE), WCAG contrast,
  masked normalised cross-correlation logo matching, alt-text checks and optional OCR.
- **Human workflow** — draft → submitted → changes requested / clarification required →
  resubmitted → approved / rejected, with review queue, comments, decisions and audit trail.
- **Analytics** — stored-data-only KPIs, status/severity/category breakdowns, repeated-issue
  tables and daily trends; creator scoping is enforced in SQL.
- **Security** — bcrypt + JWT in httpOnly cookies, RBAC, strict organisation isolation, upload
  validation with randomised storage names, security headers, audit logging.

## Stack

- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind CSS + Recharts
- **Backend**: FastAPI + Pydantic v2 + SQLAlchemy 2 (async) + Alembic
- **Database**: PostgreSQL 16 via Docker Compose, or SQLite for a quick local run
- **Analysis**: numpy, Pillow, optional Tesseract (`pytesseract`)

## Repository layout

```
brandproof-ai/
  frontend/                 Next.js app ("proofing desk" UI)
    src/app/dashboard/      overview, submissions, reviews, analytics,
                            facts, terminology, guidelines, assets,
                            brand profile, members, audit
    src/components/         findings, submission detail, visual report, UI kit
  backend/
    app/
      routers/              auth, organisations, profile, facts, terminology,
                            guidelines, sources, assets, submissions, reviews,
                            analytics, settings, audit
      services/
        analysis/           textprep, terminology, claims, verification,
                            tone, pipeline
        visual/             colour maths, image inspector
        analytics.py        SQL-derived aggregates
        files.py            safe upload storage
      models.py             SQLAlchemy tables
      schemas.py            Pydantic contracts
      main.py               app wiring + security headers
    alembic/                migrations
    scripts/demo_flow.py    scripted end-to-end demo over HTTP
    seed.py                 fictional NovaTech demo data
  docs/                     architecture, demo script, security review
  tests/                    pytest suite (79 tests)
  docker-compose.yml        PostgreSQL 16
```

## Quick start (Windows / VS Code)

### 1. Backend

```powershell
cd brandproof-ai\backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
python seed.py
python -m uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

With Docker Desktop running, `docker compose up -d` in `brandproof-ai\` provides PostgreSQL and
`.env.example` already points at it. Without Docker, switch `DATABASE_URL` to
`sqlite+aiosqlite:///./brandproof.db` — every other step is identical.

### 2. Frontend

```powershell
cd brandproof-ai\frontend
npm install
npm run dev
```

Open http://localhost:3000. API calls are proxied to the backend on port 8000.

### 3. Tests

```powershell
cd brandproof-ai
backend\.venv\Scripts\python.exe -m pytest
```

Tests use an in-memory SQLite database, temporary upload folders and a fixed secret key, so they
never touch the demo database.

### 4. Scripted demo

```powershell
cd brandproof-ai\backend
.venv\Scripts\python.exe scripts\demo_flow.py
```

The script starts the real app in-process, confirms facts, submits off-brand copy with an
off-brand visual, prints every finding, requests changes, revises with an on-brand visual and
alt text, approves, and verifies analytics and audit. Exit code 0 means every check passed.
See `docs/demo.md` for the expected narrative.

## Configuration

| Variable                | Purpose                                                    |
| ----------------------- | ---------------------------------------------------------- |
| `SECRET_KEY`            | JWT signing key (required, long random string)             |
| `DATABASE_URL`          | `postgresql+asyncpg://…` or `sqlite+aiosqlite:///./…`      |
| `UPLOAD_DIR`            | Where attachments, logos and documents are stored          |
| `MAX_UPLOAD_MB`         | Upload size limit (default 10)                             |
| `CORS_ORIGINS`          | Comma-separated allowed frontend origins                   |
| `COOKIE_SECURE`         | Force `Secure` cookies; always on when `ENVIRONMENT=production` |
| `BRANDPROOF_LLM_API_KEY`| Optional external tone provider; consent still required    |

Optional: install the Tesseract binary to enable OCR of text embedded in images. Without it, the
inspector reports that limitation as an Information finding instead of failing.

## Demo accounts

Seeded by `python seed.py`; password `Demo1234!` for all.

| Email                     | Role     | Can do                                             |
| ------------------------- | -------- | -------------------------------------------------- |
| `admin@novatech.demo`     | admin    | confirm facts, manage members, configure consent    |
| `creator@novatech.demo`   | creator  | create/revise submissions, add pending facts        |
| `reviewer@novatech.demo`  | reviewer | review queue, comments, approve/reject, audit       |

Three NovaCloud facts start **pending**. Confirm them as admin to activate the evidence base.

### Suggested demo text (exactly three copy findings)

```
NovaCloud now supports 50,000 users with 100% uptime. Our consumer platform provides reliable service for every Customer.
```

- `50,000 users` — Critical, contradicts approved fact NC-FR-001 (5,000)
- `100% uptime` — Major, contradicts NC-FR-002 (99.5%)
- `consumer` — Major, prohibited term (required: Customer)

Add an off-brand image without alt text to demonstrate palette deviation, contrast measurement
and accessibility findings.

## Workflow

```
Draft → Submitted → Changes Requested → Resubmitted → Approved
                 ↘ Clarification Required ↗         ↘ Rejected
```

Only admin/reviewer roles decide. From **Changes Requested** the reviewer may only request
clarification; the creator must revise before a decision. Every transition writes a decision row
and an audit event.

## API overview

| Area          | Endpoints                                                        |
| ------------- | ---------------------------------------------------------------- |
| Auth          | `/api/auth/{register,login,logout,me}`                            |
| Organisations | `/api/organisations`, members, invitations                       |
| Brand data    | `/api/brand/{profile,facts,terminology,guidelines,sources,assets}`|
| Submissions   | `/api/submissions` (+ `/{id}/{analyse,revise,image,comments}`)    |
| Reviews       | `/api/reviews/{queue,decided,{id}/{comment,approve,reject,request-changes,request-clarification}}` |
| Analytics     | `/api/analytics/{overview,issues,trends}`                        |
| Settings      | `/api/settings/ai-consent`                                       |
| Audit         | `/api/audit`                                                     |

## Analytics definitions

- **Findings (latest)** counts findings from the most recent analysis run per submission.
- **Findings (all runs)** counts every stored finding, including superseded revisions.
- **Needs human** counts findings explicitly flagged for human review (OCR, subjective visual
  checks, uncertain logo matches).
- **Avg review time** is mean hours from submission creation to the first human decision.
- **Avg revision cycles** is mean revision count per submission.
- Creators only see their own submissions; admins and reviewers see the whole organisation.

## Security and limitations

See `docs/security-review.md` for the full review. Highlights: httpOnly cookie sessions,
bcrypt hashing, org-scoped queries, reviewer-only decisions, upload extension/MIME/size checks,
randomised stored filenames, `nosniff`/`DENY`/`Referrer-Policy` headers, and external AI gated by
admin consent.

Known limitations: visual logo matching is a heuristic that flags low-confidence matches for
humans; OCR depends on a local Tesseract binary; the external LLM provider is an advisory stub;
there is no password-reset or email-verification flow.
