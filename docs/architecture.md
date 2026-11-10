# Architecture

## Overview

```
Next.js UI  ──HTTP──▶  FastAPI routers  ──▶  services  ──▶  SQLAlchemy (async)  ──▶  PostgreSQL / SQLite
   │                        │                 │
   │                        │                 ├─ analysis/  deterministic text engine
   │                        │                 ├─ visual/    image measurements
   │                        │                 └─ analytics  read-only aggregates
   │                        ├─ deps: JWT cookie auth, org context, RBAC
   │                        └─ audit: append-only audit rows
   └─ httpOnly cookie + X-Org-Id header
```

The backend is the only writer. The frontend never computes findings, verdicts or analytics; it
renders what the API returns and sends human decisions back.

## Authentication and organisation context

1. `POST /api/auth/login` verifies a bcrypt hash and issues a signed JWT in an `httpOnly` cookie
   (`SameSite=Lax`, `Secure` when configured or in production).
2. Every request resolves the user from the cookie and the active organisation from the `X-Org-Id`
   header, then checks membership and role (`deps.OrgContext`).
3. All queries filter by `org_id`; cross-organisation IDs return 404 rather than leaking existence.

## Data model (Phase 3 state)

| Table | Purpose | Notable columns |
| --- | --- | --- |
| `users` | accounts | `password_hash`, `name` |
| `organisations` | tenant | `name`, `slug`, `llm_consent` |
| `memberships` | user↔org | `role` (admin/creator/reviewer) |
| `brand_profiles` | identity | `name`, `product_name`, `tagline`, `tone`, `description` |
| `brand_facts` | evidence | `fact_id`, `value`, `approval_status`, `version`, `source_ref`, `effective_date`, `expiry_date` |
| `terminology_rules` | language rules | `term`, `rule_type` (required/prohibited), `notes` |
| `guidelines` / `sources` | documents | validated uploads, `original_name`, `stored_name` |
| `approved_assets` | palette/logos | `asset_type`, `colour_value`, stored logo file |
| `content_submissions` | work items | `status`, `created_by_id`, `has_image`, `image_name`, `alt_text` |
| `submission_revisions` | immutable copy | `revision_number`, `content` |
| `analysis_runs` | engine output | `engine`, `finding_count`, `visual_report` (JSON) |
| `findings` | explainable issues | `category`, `severity`, `start_offset`, `end_offset`, `evidence` (JSON), `requires_clarification`, `needs_human_review` |
| `review_comments` | discussion | `author_id`, `body` |
| `approval_decisions` | human verdicts | `decision`, `from_status`, `to_status`, `note`, `decided_by_id` |
| `audit_events` | traceability | `action`, `entity_type`, `entity_id`, `details` (JSON) |

Uploads are stored by randomised name under `UPLOAD_DIR` (`assets/logos` for logo assets);
original names are metadata only.

## Text analysis pipeline

`services/analysis/pipeline.py::analyse_text(db, org_id, text, llm_consent, extra_text)`:

1. **Normalise** — whitespace, quotes/dashes, character offsets preserved for highlighting.
2. **Terminology** — required/prohibited phrase matching with word boundaries.
3. **Tone** — deterministic checks (excess capitalisation, exclamation density, long sentences).
   With admin consent *and* a provider key, an advisory LLM provider can be used instead; it never
   auto-applies changes.
4. **Claim extraction** — numbers, percentages, timeframes, superlatives and comparative phrases.
5. **Verification** — each claim is matched to an approved fact:
   - matching approved value → no finding;
   - approved fact conflicts → Critical/Major factual mismatch with evidence citation;
   - only pending/expired/conflicting facts → clarification finding (human routing), never an
     invented correction.
6. **Guidelines** — simple rule checks derived from stored guideline text.
7. **OCR merge** — text extracted from an attached image is analysed with the same rules, its
   findings marked offsets `0/0`, `source="image_ocr"` and `needs_human_review=True`.

Engine labels: `Rule-based` or `LLM-assisted (experimental)`; ` + Visual` is appended when pixel
measurements succeeded.

## Visual inspection

`services/visual/inspector.py::inspect_image` returns a JSON `visual_report` plus findings:

- **Dominant colours** — alpha-composited, quantised to 24-step RGB bins, then averaged per bin
  for accurate hex values; up to five colours with share.
- **Palette deviation** — nearest approved colour by CIE76 ΔE in CIELAB:
  `≤10` match, `≤15` close, `≤25` deviation, `>25` clear deviation. Report rows always include the
  measurement; findings require ≥8% share and chroma ≥12 (maximum two findings).
- **Contrast** — WCAG relative luminance for the two most common colours; below 4.5:1 is Major
  (below 3.0:1 stays Major as well, but always `needs_human_review=True` because automated
  colour pairs cannot know which pixels are text).
- **Logo match** — masked normalised cross-correlation over scales 0.12–0.35 (step 2 px).
  `≥0.55` detected, `0.30–0.55` uncertain (Information + human review), below is not detected.
- **Alt text** — missing → Minor accessibility finding; shorter than 8 characters → Information.
- **OCR** — optional Tesseract; when unavailable the limitation is stated as an Information
  finding instead of failing the run.
- **Limits** — pixels downscaled to 160 px on the long edge for scoring; SVG is skipped with an
  explicit limitation; unsupported/corrupt files produce an unavailable report, not a crash.

## Analytics

`services/analytics.py` derives everything from stored rows with a latest-run-per-submission
subquery and Python date bucketing (portable across SQLite/PostgreSQL):

- totals, status/category/severity counts;
- repeated terminology, top factual mismatches, clarification claims;
- daily submission/finding/decision series and per-category series;
- average hours from creation to first decision; average revisions per submission;
- creator scoping applied in SQL, capped at 20,000 findings per query.

## Workflow state machine

```
Draft ──analyse──▶ Submitted ──approve──▶ Approved
  ▲                    │  └──reject───▶ Rejected
  │                    ├──request-changes──▶ Changes Requested
  │                    └──request-clarification──▶ Clarification Required
  └──────────────── revise ◀───────────────┘          │
                       └──────────────────────────────┘
```

Rules enforced server-side: only admin/reviewer decide; from **Changes Requested** the only
allowed decision is *request clarification*; from **Clarification Required** the reviewer may
approve, reject or request changes; terminal states cannot be revised. Each decision writes the
decision row, updates the submission, and appends an audit event in one transaction.

## Audit

`audit.log_audit` is called inside the same transaction as the mutation. Recorded actions include
fact confirmation, asset/document changes, submission lifecycle, consent changes and membership
changes, with actor, org, entity and structured details.
