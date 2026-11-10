from tests.conftest import add_member, fact_payload, register, switch_user

ADMIN = "admin@analytics.example.com"
CREATOR = "creator@analytics.example.com"
REVIEWER = "reviewer@analytics.example.com"


async def _setup(client):
    admin = await register(client, ADMIN, "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, CREATOR, "Carl Creator")
    await register(client, REVIEWER, "Rita Reviewer")
    await switch_user(client, ADMIN)
    await add_member(client, org_id, CREATOR, "creator")
    await add_member(client, org_id, REVIEWER, "reviewer")
    headers = {"X-Org-Id": str(org_id)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    assert created.status_code == 201
    await client.post(f"/api/brand/facts/{created.json()['id']}/confirm", headers=headers)
    return org_id, headers


async def _create(client, headers, content, title="Copy"):
    res = await client.post(
        "/api/submissions",
        data={"title": title, "submission_type": "ad_copy", "content": content},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _seed_workflow(client):
    org_id, headers = await _setup(client)

    await switch_user(client, CREATOR)
    first = await _create(client, headers, "NovaCloud now supports 50,000 users.", "First")
    analysed = await client.post(f"/api/submissions/{first['id']}/analyse", headers=headers)
    assert analysed.status_code == 200, analysed.text

    await switch_user(client, REVIEWER)
    await client.post(
        f"/api/reviews/{first['id']}/request-changes",
        json={"note": "Capacity claim exceeds the approved fact."},
        headers=headers,
    )

    await switch_user(client, CREATOR)
    revised = await client.post(
        f"/api/submissions/{first['id']}/revise",
        data={"content": "NovaCloud supports 5,000 users."},
        headers=headers,
    )
    assert revised.status_code == 200, revised.text

    await switch_user(client, REVIEWER)
    approved = await client.post(
        f"/api/reviews/{first['id']}/approve", json={"note": "Fixed."}, headers=headers
    )
    assert approved.status_code == 200, approved.text

    await switch_user(client, CREATOR)
    second = await _create(client, headers, "NovaCloud now supports 50,000 users.", "Second")
    analysed_second = await client.post(
        f"/api/submissions/{second['id']}/analyse", headers=headers
    )
    assert analysed_second.status_code == 200, analysed_second.text
    return org_id, headers, first, second


async def test_overview_computes_totals_from_stored_data(client):
    org_id, headers, first, second = await _seed_workflow(client)
    await switch_user(client, ADMIN)

    res = await client.get("/api/analytics/overview", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    totals = body["totals"]
    assert totals["submissions_total"] == 2
    assert totals["submissions_approved"] == 1
    assert totals["submissions_pending"] == 1
    assert totals["findings_total"] == 2
    assert totals["findings_latest"] == 1
    assert totals["decided_total"] == 1
    assert totals["avg_review_hours"] is not None
    assert totals["avg_revision_cycles"] == 1.5
    categories = {row["category"] for row in body["categories"]}
    assert "Factual mismatch" in categories
    severities = {row["severity"]: row["count"] for row in body["severities"]}
    assert severities.get("Critical") == 1
    issue_texts = {row["detected_text"]: row["count"] for row in body["top_issues"]}
    assert issue_texts.get("50,000 users") == 2


async def test_issues_show_repeated_mistakes_and_human_review(client):
    org_id, headers, first, second = await _seed_workflow(client)
    await switch_user(client, ADMIN)

    res = await client.get(
        "/api/analytics/issues", params={"category": "Factual mismatch"}, headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert [row["category"] for row in body["categories"]] == ["Factual mismatch"]
    assert body["repeated_terminology"] == []
    mismatches = {row["detected_text"]: row["count"] for row in body["top_factual_mismatches"]}
    assert mismatches.get("50,000 users") == 2
    assert body["needs_human_review"] == 0


async def test_trends_series_covers_range_and_counts_events(client):
    org_id, headers, first, second = await _seed_workflow(client)
    await switch_user(client, ADMIN)

    res = await client.get("/api/analytics/trends", params={"days": 7}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["series"]) == 7
    assert sum(point["submissions"] for point in body["series"]) == 2
    assert sum(point["findings"] for point in body["series"]) == 2
    assert sum(point["decisions"] for point in body["series"]) == 2
    assert {row["category"] for row in body["by_category"]} == {"Factual mismatch"}

    filtered = await client.get(
        "/api/analytics/trends",
        params={"days": 7, "category": "Terminology violation"},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert sum(point["findings"] for point in filtered.json()["series"]) == 0


async def test_creator_sees_only_own_analytics(client):
    org_id, headers, first, second = await _seed_workflow(client)
    await switch_user(client, ADMIN)
    await _create(client, headers, "Admin copy with 50,000 users.", "Admin copy")

    await switch_user(client, CREATOR)
    res = await client.get("/api/analytics/overview", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["totals"]["submissions_total"] == 2

    await switch_user(client, ADMIN)
    res = await client.get("/api/analytics/overview", headers=headers)
    assert res.json()["totals"]["submissions_total"] == 3


async def test_future_date_filter_returns_empty_state(client):
    org_id, headers, first, second = await _seed_workflow(client)
    await switch_user(client, ADMIN)

    res = await client.get(
        "/api/analytics/overview",
        params={"date_from": "2099-01-01", "date_to": "2099-01-31"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["totals"]["submissions_total"] == 0
    assert body["totals"]["findings_total"] == 0
    assert body["categories"] == []

    invalid = await client.get(
        "/api/analytics/overview",
        params={"date_from": "2099-02-01", "date_to": "2099-01-01"},
        headers=headers,
    )
    assert invalid.status_code == 422
