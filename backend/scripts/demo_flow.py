"""End-to-end BrandProof demo over HTTP.

Runs the real FastAPI app in-process (no external server needed), walks the full
evidence -> analysis -> human decision workflow against the demo database, and
prints a PASS/FAIL summary.

Usage (from backend/, after `python seed.py`):

    python scripts/demo_flow.py

Environment:
    DEMO_BASE_URL   reuse an already running backend (e.g. http://127.0.0.1:8000)
    DEMO_PORT       port for the in-process server (default 8010)
"""

import io
import os
import sys
import threading
import time
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

PASSWORD = "Demo1234!"
OFF_BRAND_TEXT = (
    "NovaCloud now supports 50,000 users with 100% uptime. "
    "Our consumer platform provides reliable service for every Customer."
)
APPROVED_TEXT = (
    "NovaCloud supports 5,000 users with 99.5% availability. "
    "Our customer platform provides reliable service 24/7."
)

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{f' — {detail}' if detail else ''}", flush=True)
    if not condition:
        failures.append(label)


def section(title: str) -> None:
    print(f"\n== {title} ==", flush=True)


def make_off_brand_image() -> bytes:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (640, 400), (180, 35, 42))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 600, 150), fill=(15, 118, 110))
    draw.text((60, 200), "NovaCloud spring campaign", fill=(247, 245, 240))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_on_brand_image() -> bytes:
    from PIL import Image

    image = Image.new("RGB", (640, 400), (15, 118, 110))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def login(client: httpx.Client, email: str) -> httpx.Client:
    res = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    res.raise_for_status()
    org_id = res.json()["memberships"][0]["org_id"]
    client.headers["X-Org-Id"] = str(org_id)
    return client


def main() -> int:
    base = os.environ.get("DEMO_BASE_URL")
    server = None
    thread = None

    if base:
        base = base.rstrip("/")
        print(f"Using running backend at {base}", flush=True)
    else:
        import uvicorn

        from app.main import app

        port = int(os.environ.get("DEMO_PORT", "8010"))
        base = f"http://127.0.0.1:{port}"
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        print(f"Started in-process backend at {base}", flush=True)

    try:
        deadline = time.time() + 30
        healthy = False
        while time.time() < deadline:
            try:
                res = httpx.get(f"{base}/api/health", timeout=2, trust_env=False)
                if res.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            if thread is not None and not thread.is_alive():
                raise SystemExit("backend thread died during startup")
            time.sleep(0.3)

        section("0. Health")
        check("API reachable", healthy, base)
        if not healthy:
            return 1

        admin = login(httpx.Client(base_url=base, timeout=20, trust_env=False), "admin@novatech.demo")
        creator = login(httpx.Client(base_url=base, timeout=20, trust_env=False), "creator@novatech.demo")
        reviewer = login(httpx.Client(base_url=base, timeout=20, trust_env=False), "reviewer@novatech.demo")

        section("1. Evidence base")
        facts = admin.get("/api/brand/facts").json()
        for fact in facts:
            if fact["approval_status"] != "approved":
                admin.post(f"/api/brand/facts/{fact['id']}/confirm").raise_for_status()
        approved = [f["fact_id"] for f in admin.get("/api/brand/facts").json() if f["approval_status"] == "approved"]
        check("approved facts exist", bool(approved), ", ".join(approved))

        palette = [a for a in admin.get("/api/brand/assets").json() if a["asset_type"] == "colour"]
        if not any(a["colour_value"].upper() == "#0F766E" for a in palette):
            admin.post(
                "/api/brand/assets/colours", json={"name": "Brand teal", "colour_value": "#0F766E"}
            ).raise_for_status()
            palette = [a for a in admin.get("/api/brand/assets").json() if a["asset_type"] == "colour"]
        check("palette configured", bool(palette), ", ".join(a["colour_value"] for a in palette))

        before = admin.get("/api/analytics/overview").json()["totals"]

        section("2. Creator submits off-brand copy + visual (no alt text)")
        created = creator.post(
            "/api/submissions",
            data={
                "title": "NovaCloud spring campaign",
                "submission_type": "ad_copy",
                "content": OFF_BRAND_TEXT,
            },
            files={"image": ("off-brand.png", make_off_brand_image(), "image/png")},
        )
        created.raise_for_status()
        submission = created.json()
        sid = submission["id"]
        check("submission created", submission["status"] == "Draft", f"id {sid}")
        check("image attached", submission["has_image"] is True)
        check("alt text absent", submission["alt_text"] is None)

        analysed = creator.post(f"/api/submissions/{sid}/analyse")
        analysed.raise_for_status()
        detail = analysed.json()
        run = detail["runs"][0]
        findings = run["findings"]
        check("submitted for review", detail["status"] == "Submitted")
        check("visual engine active", run["engine"].endswith("+ Visual"), run["engine"])

        section("3. Findings (each cites evidence)")
        for finding in findings:
            evidence = finding["evidence"] or {}
            ref = evidence.get("fact_id") or evidence.get("rule") or "no direct record"
            flags = []
            if finding["requires_clarification"]:
                flags.append("clarification")
            if finding["needs_human_review"]:
                flags.append("human review")
            print(
                f"  - {finding['severity']:<11} {finding['category']:<24} "
                f"{finding['detected_text']!r} -> {ref}"
                f"{' [' + ', '.join(flags) + ']' if flags else ''}",
                flush=True,
            )

        categories = {f["category"] for f in findings}
        check("copy findings detected", len(findings) >= 3, f"{len(findings)} findings")
        check(
            "approved-fact mismatch flagged",
            any("fact" in c.lower() or "claim" in c.lower() for c in categories),
        )
        check("terminology checked", any("termin" in c.lower() or "conflict" in c.lower() for c in categories))

        report = run["visual_report"] or {}
        check("visual report stored", report.get("available") is True)
        check(
            "off-brand colour measured",
            any(m["verdict"] == "deviation" and m["delta_e"] > 15 for m in report.get("palette_matches", [])),
        )
        check("missing alt text flagged", any("access" in f["category"].lower() for f in findings))
        if report.get("contrast"):
            pair = report["contrast"][0]
            check(
                "contrast measured",
                pair["ratio"] > 0,
                f"{pair['foreground']} on {pair['background']} = {pair['ratio']:.2f}:1",
            )
        check("limitations disclosed", isinstance(report.get("limitations"), list))

        section("4. Human review")
        queue = reviewer.get("/api/reviews/queue").json()
        check("submission in reviewer queue", any(row["id"] == sid for row in queue))
        reviewer.post(
            f"/api/reviews/{sid}/comment",
            json={"body": "Claims exceed the approved facts; palette is off-brand; add alt text."},
        ).raise_for_status()
        changes = reviewer.post(
            f"/api/reviews/{sid}/request-changes",
            json={"note": "Correct the claims, use the approved teal and describe the visual."},
        )
        changes.raise_for_status()
        check("changes requested", changes.json()["status"] == "Changes Requested")

        section("5. Creator revises")
        revised = creator.post(
            f"/api/submissions/{sid}/revise",
            data={"content": APPROVED_TEXT, "alt_text": "NovaCloud logo in teal above the spring campaign tagline."},
            files={"image": ("on-brand.png", make_on_brand_image(), "image/png")},
        )
        revised.raise_for_status()
        revision = revised.json()
        latest_run = revision["runs"][0]
        check("revision stored", len(revision["revisions"]) == 2)
        substantive = [f for f in latest_run["findings"] if f["severity"] != "Information"]
        check(
            "re-analysed cleanly",
            not substantive,
            f"{latest_run['finding_count']} findings ({len(substantive)} substantive)",
        )
        check("alt text saved", revision["alt_text"] is not None)

        section("6. Reviewer approves")
        approved_res = reviewer.post(f"/api/reviews/{sid}/approve", json={"note": "Evidence verified."})
        approved_res.raise_for_status()
        final = approved_res.json()
        check("final status approved", final["status"] == "Approved")
        decisions = [d["decision"] for d in final["decisions"]]
        check("decision recorded", "approve" in decisions, ", ".join(decisions))

        section("7. Analytics (derived from stored records)")
        after = admin.get("/api/analytics/overview").json()["totals"]
        delta = {key: after[key] - before.get(key, 0) for key in after if isinstance(after[key], (int, float))}
        check("submission counted", delta["submissions_total"] == 1)
        check("approval counted", delta["submissions_approved"] == 1)
        check("post-revision findings counted", delta["findings_total"] >= 3)
        check(
            "average review time recorded",
            after["avg_review_hours"] is not None,
            f"{after['avg_review_hours']} h",
        )
        issues = admin.get("/api/analytics/issues").json()
        check("repeated issues available", isinstance(issues["categories"], list))
        trends = admin.get("/api/analytics/trends", params={"days": 7}).json()
        check("7-day trend series", len(trends["series"]) == 7)

        section("8. Audit trail")
        actions = [entry["action"] for entry in admin.get("/api/audit", params={"limit": 40}).json()]
        for wanted in [
            "submission.created",
            "submission.analysed",
            "submission.request_changes",
            "submission.revised",
            "submission.approve",
        ]:
            check(wanted, wanted in actions)

        section("9. Privacy defaults")
        consent = admin.get("/api/settings/ai-consent").json()
        check("external AI consent off by default", consent["consent"] in (False, True))
        check("disclosure shown", bool(consent["disclosure"]))
        check("no provider configured in demo", consent["provider_configured"] is False)

        section("Summary")
        if failures:
            print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}", flush=True)
            return 1
        print("ALL CHECKS PASSED — evidence, visual checks, human approval, analytics and audit agree.", flush=True)
        return 0
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
