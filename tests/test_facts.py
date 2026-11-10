from tests.conftest import fact_payload, register


async def test_create_fact_is_pending(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    res = await client.post("/api/brand/facts", json=fact_payload())
    assert res.status_code == 201
    body = res.json()
    assert body["approval_status"] == "pending"
    assert body["confirmed_at"] is None


async def test_duplicate_fact_id_rejected(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    first = await client.post("/api/brand/facts", json=fact_payload())
    assert first.status_code == 201
    second = await client.post("/api/brand/facts", json=fact_payload(name="Another name"))
    assert second.status_code == 409


async def test_editing_approved_fact_resets_to_pending_and_bumps_version(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    created = await client.post("/api/brand/facts", json=fact_payload())
    fact_pk = created.json()["id"]

    confirmed = await client.post(f"/api/brand/facts/{fact_pk}/confirm")
    assert confirmed.json()["approval_status"] == "approved"

    updated = await client.put(f"/api/brand/facts/{fact_pk}", json={"approved_value": "6,000"})
    assert updated.status_code == 200
    body = updated.json()
    assert body["approval_status"] == "pending"
    assert body["approved_value"] == "6,000"
    assert body["version"] == 2
    assert body["confirmed_at"] is None


async def test_fact_date_validation(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/facts",
        json=fact_payload(effective_date="2025-06-01", expiry_date="2025-01-01"),
    )
    assert res.status_code == 422


async def test_fact_status_filter(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    await client.post("/api/brand/facts", json=fact_payload())
    await client.post("/api/brand/facts", json=fact_payload(fact_id="NC-FR-002", name="Availability"))
    second = (await client.get("/api/brand/facts?status_filter=pending")).json()
    assert len(second) == 2
    first_pk = second[0]["id"] if second[0]["fact_id"] == "NC-FR-001" else second[1]["id"]
    await client.post(f"/api/brand/facts/{first_pk}/confirm")
    pending = await client.get("/api/brand/facts?status_filter=pending")
    approved = await client.get("/api/brand/facts?status_filter=approved")
    assert len(pending.json()) == 1
    assert len(approved.json()) == 1


async def test_terminology_crud_admin_only_flow(client):
    await register(client, "admin@fact.example.com", "Ann Admin")
    created = await client.post(
        "/api/brand/terminology",
        json={"rule_type": "required", "term": "Customer", "description": "Use customer."},
    )
    assert created.status_code == 201

    duplicate = await client.post(
        "/api/brand/terminology",
        json={"rule_type": "required", "term": "customer", "description": "dup"},
    )
    assert duplicate.status_code == 409

    updated = await client.put(
        f"/api/brand/terminology/{created.json()['id']}",
        json={"description": "Always use customer."},
    )
    assert updated.status_code == 200

    deleted = await client.delete(f"/api/brand/terminology/{created.json()['id']}")
    assert deleted.status_code == 200
    listing = await client.get("/api/brand/terminology")
    assert listing.json() == []
