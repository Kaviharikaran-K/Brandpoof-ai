# Demo guide

Two ways to demo: the scripted flow (repeatable, exit code 0 = all checks pass) and the manual UI
walkthrough.

## Scripted demo

```powershell
cd brandproof-ai\backend
.venv\Scripts\python.exe scripts\demo_flow.py
```

The script starts the real FastAPI app in-process on port 8010 (override with `DEMO_PORT`, or
point at a running server with `DEMO_BASE_URL=http://127.0.0.1:8000`) and uses the seeded demo
database. It creates real records, so run it on the demo database, not production.

### What it proves

1. **Evidence** — approves the pending NovaCloud facts and ensures a teal palette colour exists.
2. **Submission** — creator submits off-brand copy plus an off-brand PNG with no alt text.
3. **Findings** — prints each finding with severity, category, detected text and cited record:
   - `50,000 users` — Critical factual mismatch (approved fact NC-FR-001 = 5,000)
   - `100% uptime` — Major factual mismatch (NC-FR-002 = 99.5%)
   - `consumer` — Major terminology violation (required: Customer)
   - missing alt text — Minor accessibility
   - `#B4232A` — Major palette deviation (ΔE ≈ 79 vs approved navy)
   - contrast — Major, flagged for human review (measured pair, text usage unknown)
   - OCR unavailable — Information, flagged for human review
4. **Human review** — the submission appears in the reviewer queue, receives a comment and
   *request changes*.
5. **Revision** — creator resubmits approved copy, an on-brand solid teal image and alt text;
   the only remaining finding is the OCR Information note.
6. **Approval** — reviewer approves; the decision history contains request-changes then approve.
7. **Analytics** — the overview delta shows one new submission, one approval, new findings and a
   recorded review time; 7-day trends return seven points.
8. **Audit** — created, analysed, request-changes, revised and approve events are present.
9. **Privacy** — external AI consent is off and no provider is configured in the demo.

## Manual UI walkthrough (fictional NovaCloud)

1. Sign in as `admin@novatech.demo` / `Demo1234!`.
2. **Approved facts** — confirm the three pending NovaCloud facts. Notice the evidence source and
   version shown on each row.
3. **Brand assets** — add a colour `#0F766E` named "Brand teal" (if not seeded).
4. Sign out, sign in as `creator@novatech.demo`.
5. **Submissions → New submission**, use:

   > NovaCloud now supports 50,000 users with 100% uptime. Our consumer platform provides
   > reliable service for every Customer.

   Attach any PNG without alt text and create + analyse.
6. Open the submission: highlights mark the three copy findings; hover a finding to see the linked
   fact or rule. The visual panel shows dominant colours, palette ΔE, contrast ratio, logo score
   and stated limitations. Findings that need judgement carry a "Requires human review" chip.
7. **Analytics** — set the range to "Last 30 days" and filter the category to `Factual mismatch`.
   KPIs are derived from the submission you just created.
8. Sign in as `reviewer@novatech.demo` → **Review queue** → open the item → comment, then
   **Request changes**.
9. Back as the creator, open the submission → **Revise**; replace the visual with an on-brand
   image, add alt text and use the approved copy:

   > NovaCloud supports 5,000 users with 99.5% availability. Our customer platform provides
   > reliable service 24/7.

   Saving re-runs the analysis immediately.
10. As the reviewer, **Approve** with a note. The status becomes Approved and the decision is
    visible on the detail page.
11. **Audit history** — filter by submission to see every action with actor and timestamp.
12. **Brand profile** — as admin, review the external AI disclosure and consent card. It starts
    disabled; enabling it is audited. With no provider key configured, the deterministic engine
    remains in use regardless.

## Notes for presenters

- The engine never auto-approves. Every decision in the demo is made by a reviewer account.
- Pending facts are deliberately not evidence — a claim that only matches a pending fact produces
  a clarification finding instead of a pass or a guessed correction.
- OCR findings appear only when the Tesseract binary is installed; otherwise the limitation is
  reported. Both behaviours are honest and visible in the UI.
- All analytics numbers come from the database you are browsing; refreshing after an action
  updates them without any external analytics service.
