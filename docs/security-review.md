# Security review

Scope: the BrandProof AI backend and its Next.js frontend as implemented for Phases 1–3.
This is a self-review of the demo codebase, not a third-party audit.

## Authentication and sessions

- Passwords are hashed with bcrypt (`security.py`); hashes never leave the database and are never
  returned by the API.
- Login issues a time-limited JWT stored in an `httpOnly`, `SameSite=Lax` cookie. JavaScript cannot
  read it, which removes the common token-theft path through XSS.
- `Secure` is set when `COOKIE_SECURE=true` **or** `ENVIRONMENT=production`, so HTTPS deployments
  cannot silently issue plaintext cookies.
- Logout clears the cookie; a missing/invalid/expired token yields 401 from the auth dependency.
- Session resolution is centralised in `deps.py`; routers do not parse tokens themselves.

## Authorisation and tenant isolation

- Every protected route depends on `OrgContext`, which resolves the membership for the `X-Org-Id`
  header and exposes the caller's role.
- All data queries include `org_id` filters. Accessing a foreign record by ID returns 404, not a
  permission error, so existence is not disclosed.
- Role checks are enforced server-side, not only in the UI:

| Action | admin | creator | reviewer |
| --- | --- | --- | --- |
| Confirm/edit facts, terminology, guidelines, assets | yes | no (pending facts only) | no |
| Manage members, edit brand profile | yes | no | no |
| Create/revise own submissions | yes | yes | no |
| See all submissions in org | yes | own only | yes |
| Approve/reject/request changes | yes | no | yes |
| Read audit history | yes | no | yes |
| Toggle external AI consent | yes | no | no |

- Decision transitions are validated against an explicit state machine; illegal decisions (for
  example approving from **Changes Requested**) return 400. The engine itself has no approval path.

## Uploads

- Only images (PNG/JPEG/SVG/WebP) and documents (TXT/PDF/DOCX) are accepted, checked by extension,
  declared MIME type and size (`MAX_UPLOAD_MB`).
- Files are stored under randomised names inside `UPLOAD_DIR`; user-supplied names are metadata
  only, preventing path traversal and overwrite attacks.
- Image bytes are decoded by Pillow for measurement, never executed; SVGs are not rendered as
  documents by the backend and are skipped by pixel analysis. Document text extraction is not
  implemented yet.
- Uploads are served through authenticated, org-checked endpoints rather than a static directory.

## Input handling and output

- All request bodies are Pydantic-validated with explicit length limits (content 50,000 chars,
  alt text 500 chars, comments/notes bounded).
- Highlight offsets are numbers, not HTML; the frontend renders text through React (escaped by
  default) and does not use `dangerouslySetInnerHTML`.
- Date ranges on analytics are validated (`date_from <= date_to`, 422 otherwise). Query result
  sizes are capped (20,000 findings; 500 assets/rows where relevant) to bound work.
- The analytics service computes aggregates with SQLAlchemy parameter binding; no raw SQL string
  interpolation.

## External AI and privacy

- Deterministic analysis is entirely local. The optional LLM tone provider activates only when
  **both** an organisation admin has enabled consent (`organisations.llm_consent`) **and** a
  provider key is configured. Consent changes are audited.
- With no key configured (the demo default), consent toggling is harmless: the deterministic
  provider remains in use and the UI reports "provider not configured".
- The disclosure text returned by `/api/settings/ai-consent` states what is sent, why, and that
  output is advisory.

## Transport and browser hardening

- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` and a
  restrictive `Permissions-Policy` are applied to every response in `main.py`.
- CORS allows only configured origins with credentials; the default list is the local frontend.
- Cookies are `httpOnly` + `SameSite=Lax`, so cross-site POST requests do not carry the session
  cookie. State-changing APIs accept JSON or multipart form data and are not reachable via simple
  cross-site form submissions with credentials.

## Audit and observability

- Mutations write an audit row in the same transaction (actor, org, action, entity, details,
  timestamp). Failed authorisation attempts are rejected before mutation.
- Passwords, tokens and provider keys are never written to audit details or application logs.

## Verification performed

- `pytest`: 79 tests covering auth, RBAC, tenant isolation, fact workflow, uploads, analysis engine,
  submissions/reviews, visual inspection, analytics and settings consent.
- `scripts/demo_flow.py`: end-to-end HTTP run asserting evidence citations, visual measurements,
  human-only approval, analytics deltas, audit events, consent defaults and the `nosniff` header.
- Frontend production build (`npm run build`) passes type checking and linting.

## Residual risks / not yet implemented

- No rate limiting, account lockout or CAPTCHA on login/register; add a reverse-proxy limiter or
  application middleware before public exposure.
- No password reset, email verification or session revocation list; JWTs remain valid until
  expiry after logout on a stolen device.
- Uploads are validated but not virus-scanned; deploy behind a scanning gateway if untrusted users
  can upload.
- SVG uploads are accepted for storage but skipped by analysis; treat them as untrusted documents
  if any future feature renders them inline.
- Logo matching is a heuristic; low-confidence results are surfaced for human review rather than
  trusted. OCR quality depends on the local Tesseract binary.
- The LLM provider in this repository is an advisory stub; enabling a real provider should add an
  outbound allow-list, timeout, retry and redaction policy.
- SQLite is suitable for the demo only; production should use PostgreSQL (Docker Compose is
  provided) with backups and least-privilege credentials.
- Demo credentials (`Demo1234!`) are intentionally weak and must never be seeded in production.
