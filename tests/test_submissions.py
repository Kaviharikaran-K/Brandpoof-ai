from tests.conftest import (
    add_member,
    fact_payload,
    register,
    switch_user,
)

CREATOR = "creator@sub.example.com"
REVIEWER = "reviewer@sub.example.com"
ADMIN = "admin@sub.example.com"


async def _setup(client):
    admin = await register(client, ADMIN, "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, CREATOR, "Carl Creator")
    await register(client, REVIEWER, "Rita Reviewer")
    await switch_user(client, ADMIN)
    await add_member(client, org_id, CREATOR, "creator")
    await add_member(client, org_id, REVIEWER, "reviewer")
    return org_id


async def _approved_fact(client, headers, **overrides):
    payload = fact_payload(**overrides)
    created = await client.post("/api/brand/facts", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    confirmed = await client.post(
        f"/api/brand/facts/{created.json()['id']}/confirm", headers=headers
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


async def _create(client, headers, content, title="NovaCloud launch copy", submission_type="ad_copy"):
    res = await client.post(
        "/api/submissions",
        data={"title": title, "submission_type": submission_type, "content": content},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _analyse(client, headers, submission_id):
    res = await client.post(f"/api/submissions/{submission_id}/analyse", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


async def test_create_submission_starts_as_draft(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)

    body = await _create(client, headers, "NovaCloud is dependable cloud.")
    assert body["status"] == "Draft"
    assert len(body["revisions"]) == 1
    assert body["revisions"][0]["revision_number"] == 1
    assert body["has_image"] is False
    assert body["created_by_email"] == CREATOR
    assert body["runs"] == []


async def test_analyse_flags_capacity_mismatch_with_evidence(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud now supports 50,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Submitted"
    assert len(detail["runs"]) == 1
    run = detail["runs"][0]
    assert run["engine"] == "Rule-based"
    assert run["finding_count"] == 1
    finding = run["findings"][0]
    assert finding["category"] == "Factual mismatch"
    assert finding["severity"] == "Critical"
    assert finding["detected_text"] == "50,000 users"
    assert finding["suggested_correction"] == "5,000"
    assert finding["evidence"]["fact_id"] == "NC-FR-001"
    assert finding["requires_clarification"] is False


async def test_case_a_clean_claim_passes_without_findings(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Submitted"
    assert detail["runs"][0]["finding_count"] == 0


async def test_case_c_missing_evidence_requires_clarification(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Clarification Required"
    finding = detail["runs"][0]["findings"][0]
    assert finding["category"] == "Missing or conflicting guideline"
    assert finding["requires_clarification"] is True
    assert finding["suggested_correction"] is None
    assert finding["explanation"].startswith(
        "Clarification Required: No reliable approved evidence found."
    )


async def test_case_d_conflicting_facts_require_reviewer_resolution(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await _approved_fact(
        client,
        headers,
        fact_id="NC-FR-009",
        name="User capacity (current)",
        approved_value="10,000",
        description="NovaCloud now supports 10,000 users per tenant.",
    )
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Clarification Required"
    finding = detail["runs"][0]["findings"][0]
    assert finding["requires_clarification"] is True
    assert "conflict" in finding["explanation"].lower()


async def test_expired_fact_is_reported_as_outdated(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers, effective_date="2019-01-01", expiry_date="2020-01-01")
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Clarification Required"
    finding = detail["runs"][0]["findings"][0]
    assert finding["category"] == "Outdated information"
    assert finding["requires_clarification"] is True


async def test_pending_fact_is_not_treated_as_evidence(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    assert created.status_code == 201
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    detail = await _analyse(client, headers, submission["id"])

    assert detail["status"] == "Clarification Required"
    finding = detail["runs"][0]["findings"][0]
    assert "confirmed by an admin" in finding["explanation"]


async def test_revision_creates_new_content_and_reanalyses(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 50,000 users.")
    await _analyse(client, headers, submission["id"])

    res = await client.post(
        f"/api/submissions/{submission['id']}/revise",
        data={"content": "NovaCloud supports 5,000 users."},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    detail = res.json()
    assert detail["status"] == "Submitted"
    assert len(detail["revisions"]) == 2
    assert detail["revisions"][1]["revision_number"] == 2
    assert len(detail["runs"]) == 2
    assert detail["runs"][0]["finding_count"] == 0


async def test_only_reviewers_can_decide_and_terminal_states_lock(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)

    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    await _analyse(client, headers, submission["id"])

    res = await client.post(f"/api/reviews/{submission['id']}/approve", headers=headers)
    assert res.status_code == 403

    await switch_user(client, REVIEWER)
    res = await client.post(f"/api/reviews/{submission['id']}/approve", headers=headers)
    assert res.status_code == 200, res.text
    detail = res.json()
    assert detail["status"] == "Approved"
    assert detail["decided_at"] is not None
    assert detail["decisions"][0]["decision"] == "approve"
    assert detail["decisions"][0]["decided_by_email"] == REVIEWER

    await switch_user(client, CREATOR)
    res = await client.post(f"/api/submissions/{submission['id']}/analyse", headers=headers)
    assert res.status_code == 400
    res = await client.post(
        f"/api/submissions/{submission['id']}/revise",
        data={"content": "Late change."},
        headers=headers,
    )
    assert res.status_code == 400


async def test_reject_requires_a_note(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud is great.")
    await _analyse(client, headers, submission["id"])

    await switch_user(client, REVIEWER)
    res = await client.post(f"/api/reviews/{submission['id']}/reject", json={}, headers=headers)
    assert res.status_code == 422

    res = await client.post(
        f"/api/reviews/{submission['id']}/reject",
        json={"note": "Cannot substantiate the availability claim."},
        headers=headers,
    )
    assert res.status_code == 200
    detail = res.json()
    assert detail["status"] == "Rejected"
    assert detail["decisions"][0]["note"] == "Cannot substantiate the availability claim."


async def test_request_changes_then_creator_revises(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud supports 50,000 users.")
    await _analyse(client, headers, submission["id"])

    await switch_user(client, REVIEWER)
    res = await client.post(
        f"/api/reviews/{submission['id']}/request-changes",
        json={"note": "Correct the capacity figure."},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "Changes Requested"

    await switch_user(client, CREATOR)
    res = await client.post(
        f"/api/submissions/{submission['id']}/revise",
        data={"content": "NovaCloud supports 5,000 users."},
        headers=headers,
    )
    assert res.status_code == 200
    detail = res.json()
    assert detail["status"] == "Submitted"
    assert len(detail["revisions"]) == 2

    await switch_user(client, REVIEWER)
    res = await client.post(f"/api/reviews/{submission['id']}/approve", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "Approved"


async def test_review_queue_and_scoping(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud is dependable cloud.")

    await switch_user(client, REVIEWER)
    queue = await client.get("/api/reviews/queue", headers=headers)
    assert queue.status_code == 200
    assert queue.json() == []

    await switch_user(client, CREATOR)
    await _analyse(client, headers, submission["id"])

    await switch_user(client, REVIEWER)
    queue = await client.get("/api/reviews/queue", headers=headers)
    assert [item["id"] for item in queue.json()] == [submission["id"]]


async def test_creator_only_lists_own_submissions(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, ADMIN)
    admin_submission = await _create(client, headers, "Admin authored copy.", title="Admin draft")

    await switch_user(client, CREATOR)
    creator_submission = await _create(client, headers, "Creator authored copy.", title="Creator draft")

    mine = await client.get("/api/submissions", headers=headers)
    assert [item["id"] for item in mine.json()] == [creator_submission["id"]]

    await switch_user(client, ADMIN)
    everything = await client.get("/api/submissions", headers=headers)
    ids = {item["id"] for item in everything.json()}
    assert {admin_submission["id"], creator_submission["id"]} <= ids


async def test_reviewer_comment_appears_on_detail(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud is dependable cloud.")

    await switch_user(client, REVIEWER)
    res = await client.post(
        f"/api/reviews/{submission['id']}/comment",
        json={"body": "Please cite the source for this claim."},
        headers=headers,
    )
    assert res.status_code == 200
    comments = res.json()["comments"]
    assert comments[-1]["body"] == "Please cite the source for this claim."
    assert comments[-1]["author_email"] == REVIEWER


async def test_workflow_transitions_are_audited(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await _approved_fact(client, headers)
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")
    await _analyse(client, headers, submission["id"])

    await switch_user(client, REVIEWER)
    await client.post(f"/api/reviews/{submission['id']}/approve", headers=headers)

    await switch_user(client, ADMIN)
    audit = await client.get("/api/audit", headers=headers)
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()]
    assert "submission.created" in actions
    assert "submission.analysed" in actions
    assert "submission.approve" in actions


async def test_submission_image_upload_and_retrieval(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    res = await client.post(
        "/api/submissions",
        data={"title": "Visual check", "submission_type": "social", "content": "NovaCloud visual."},
        files={"image": ("mock.png", png, "image/png")},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    detail = res.json()
    assert detail["has_image"] is True
    assert detail["image_name"] == "mock.png"

    image = await client.get(f"/api/submissions/{detail['id']}/image", headers=headers)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"


async def test_submissions_are_isolated_between_organisations(client):
    org_id = await _setup(client)
    headers = {"X-Org-Id": str(org_id)}
    await switch_user(client, CREATOR)
    submission = await _create(client, headers, "NovaCloud supports 5,000 users.")

    outsider = await register(client, "outsider@other.example.com", "Owen Outsider")
    other_org = outsider["memberships"][0]["org_id"]
    other_headers = {"X-Org-Id": str(other_org)}

    res = await client.get(f"/api/submissions/{submission['id']}", headers=other_headers)
    assert res.status_code == 404
    res = await client.post(f"/api/submissions/{submission['id']}/analyse", headers=other_headers)
    assert res.status_code == 404
    listing = await client.get("/api/submissions", headers=other_headers)
    assert listing.json() == []
