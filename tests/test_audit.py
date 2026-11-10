from tests.conftest import add_member, fact_payload, login, register, switch_user


async def test_audit_rows_created_for_fact_lifecycle(client):
    admin = await register(client, "admin@audit.example.com", "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]

    created = await client.post("/api/brand/facts", json=fact_payload())
    fact_pk = created.json()["id"]
    await client.post(f"/api/brand/facts/{fact_pk}/confirm")
    await client.put(f"/api/brand/facts/{fact_pk}", json={"approved_value": "6,000"})
    await client.post("/api/brand/terminology", json={"rule_type": "prohibited", "term": "Consumer"})
    await client.delete(f"/api/brand/facts/{fact_pk}")

    res = await client.get("/api/audit?limit=50")
    assert res.status_code == 200
    actions = [row["action"] for row in res.json()]
    for expected in [
        "fact.created",
        "fact.confirmed",
        "fact.updated",
        "terminology.created",
        "fact.deleted",
    ]:
        assert expected in actions, f"missing audit action {expected}"


async def test_audit_entries_reference_entities_and_users(client):
    admin = await register(client, "admin@audit.example.com", "Ann Admin")
    created = await client.post("/api/brand/facts", json=fact_payload())
    fact_pk = created.json()["id"]

    res = await client.get("/api/audit?entity_type=approved_fact&limit=10")
    rows = res.json()
    assert len(rows) >= 1
    row = rows[0]
    assert row["user_email"] == "admin@audit.example.com"
    assert row["entity_id"] == str(fact_pk)
    assert row["details"].get("fact_id") == "NC-FR-001"


async def test_upload_actions_are_audited(client):
    admin = await register(client, "admin@audit.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Style guide"},
        files={"file": ("guide.txt", b"hello guideline", "text/plain")},
    )
    assert res.status_code == 201, res.text
    guideline_id = res.json()["id"]

    audit = await client.get("/api/audit?entity_type=brand_guideline")
    actions = [r["action"] for r in audit.json()]
    assert "guideline.uploaded" in actions

    await client.delete(f"/api/brand/guidelines/{guideline_id}")
    audit = await client.get("/api/audit?entity_type=brand_guideline")
    actions = [r["action"] for r in audit.json()]
    assert "guideline.deleted" in actions
