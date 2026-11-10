from tests.conftest import (
    add_member,
    fact_payload,
    login,
    register,
    switch_user,
)


async def _setup_org_with_roles(client):
    admin = await register(client, "admin@orga.example.com", "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, "creator@orga.example.com", "Carl Creator")
    await register(client, "reviewer@orga.example.com", "Rita Reviewer")
    await switch_user(client, "admin@orga.example.com")
    await add_member(client, org_id, "creator@orga.example.com", "creator")
    await add_member(client, org_id, "reviewer@orga.example.com", "reviewer")
    return org_id


async def test_creator_cannot_edit_confirm_or_delete_facts(client):
    org_id = await _setup_org_with_roles(client)
    await switch_user(client, "creator@orga.example.com")
    headers = {"X-Org-Id": str(org_id)}

    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    assert created.status_code == 201
    assert created.json()["approval_status"] == "pending"
    fact_pk = created.json()["id"]

    res = await client.put(f"/api/brand/facts/{fact_pk}", json={"approved_value": "6,000"}, headers=headers)
    assert res.status_code == 403

    res = await client.post(f"/api/brand/facts/{fact_pk}/confirm", headers=headers)
    assert res.status_code == 403

    res = await client.delete(f"/api/brand/facts/{fact_pk}", headers=headers)
    assert res.status_code == 403


async def test_reviewer_is_read_only_for_facts(client):
    org_id = await _setup_org_with_roles(client)
    await switch_user(client, "admin@orga.example.com")
    headers = {"X-Org-Id": str(org_id)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    fact_pk = created.json()["id"]

    await switch_user(client, "reviewer@orga.example.com")
    res = await client.post("/api/brand/facts", json=fact_payload(fact_id="NC-FR-009"), headers=headers)
    assert res.status_code == 403

    res = await client.post(f"/api/brand/facts/{fact_pk}/confirm", headers=headers)
    assert res.status_code == 403

    listing = await client.get("/api/brand/facts", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_admin_confirms_fact(client):
    org_id = await _setup_org_with_roles(client)
    headers = {"X-Org-Id": str(org_id)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    fact_pk = created.json()["id"]

    res = await client.post(f"/api/brand/facts/{fact_pk}/confirm", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["approval_status"] == "approved"
    assert body["confirmed_at"] is not None


async def test_only_admin_manages_members(client):
    org_id = await _setup_org_with_roles(client)
    await register(client, "outsider@orga.example.com", "Owen Outsider")
    await switch_user(client, "creator@orga.example.com")
    res = await client.post(
        f"/api/organisations/{org_id}/members",
        json={"email": "outsider@orga.example.com", "role": "creator"},
    )
    assert res.status_code == 403


async def test_creator_cannot_edit_brand_profile(client):
    org_id = await _setup_org_with_roles(client)
    await switch_user(client, "creator@orga.example.com")
    res = await client.put(
        "/api/brand/profile",
        json={"name": "X", "tone": "warm"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert res.status_code == 403


async def test_creator_cannot_view_audit(client):
    org_id = await _setup_org_with_roles(client)
    await switch_user(client, "creator@orga.example.com")
    res = await client.get("/api/audit", headers={"X-Org-Id": str(org_id)})
    assert res.status_code == 403
