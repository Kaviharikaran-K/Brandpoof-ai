from tests.conftest import add_member, fact_payload, login, register, switch_user


async def test_org_b_cannot_see_org_a_facts(client):
    admin_a = await register(client, "admin@orga.example.com", "Ann Admin")
    org_a = admin_a["memberships"][0]["org_id"]
    headers_a = {"X-Org-Id": str(org_a)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers_a)
    fact_pk = created.json()["id"]

    user_b = await register(client, "admin@orgb.example.com", "Ben Admin")
    org_b = user_b["memberships"][0]["org_id"]
    headers_b = {"X-Org-Id": str(org_b)}

    listing = await client.get("/api/brand/facts", headers=headers_b)
    assert listing.status_code == 200
    assert listing.json() == []

    detail = await client.get(f"/api/brand/facts/{fact_pk}", headers=headers_b)
    assert detail.status_code == 404

    update = await client.put(
        f"/api/brand/facts/{fact_pk}", json={"approved_value": "9,999"}, headers=headers_b
    )
    assert update.status_code == 404


async def test_non_member_cannot_use_org_header(client):
    admin_a = await register(client, "admin@orga.example.com", "Ann Admin")
    org_a = admin_a["memberships"][0]["org_id"]
    await client.post("/api/brand/facts", json=fact_payload(), headers={"X-Org-Id": str(org_a)})

    await register(client, "admin@orgb.example.com", "Ben Admin")
    res = await client.get("/api/brand/facts", headers={"X-Org-Id": str(org_a)})
    assert res.status_code == 403


async def test_audit_is_org_scoped(client):
    admin_a = await register(client, "admin@orga.example.com", "Ann Admin")
    org_a = admin_a["memberships"][0]["org_id"]
    await client.post("/api/brand/facts", json=fact_payload(), headers={"X-Org-Id": str(org_a)})

    audit_a = await client.get("/api/audit", headers={"X-Org-Id": str(org_a)})
    assert audit_a.status_code == 200
    actions_a = [row["action"] for row in audit_a.json()]
    assert "fact.created" in actions_a

    user_b = await register(client, "admin@orgb.example.com", "Ben Admin")
    org_b = user_b["memberships"][0]["org_id"]

    audit_b = await client.get("/api/audit", headers={"X-Org-Id": str(org_b)})
    assert audit_b.status_code == 200
    actions_b = [row["action"] for row in audit_b.json()]
    assert "fact.created" not in actions_b

    foreign = await client.get("/api/audit", headers={"X-Org-Id": str(org_a)})
    assert foreign.status_code == 403


async def test_members_endpoint_isolation(client):
    admin_a = await register(client, "admin@orga.example.com", "Ann Admin")
    org_a = admin_a["memberships"][0]["org_id"]
    await register(client, "creator@orga.example.com", "Carl Creator")
    await switch_user(client, "admin@orga.example.com")
    await add_member(client, org_a, "creator@orga.example.com", "creator")

    user_b = await register(client, "admin@orgb.example.com", "Ben Admin")

    await switch_user(client, "admin@orga.example.com")
    res = await client.get(f"/api/organisations/{org_a}/members")
    assert res.status_code == 200
    emails = {m["email"] for m in res.json()}
    assert "creator@orga.example.com" in emails

    await switch_user(client, "admin@orgb.example.com")
    res = await client.get(f"/api/organisations/{org_a}/members")
    assert res.status_code == 403
