from tests.conftest import add_member, fact_payload, register, switch_user

ADMIN = "admin@consent.example.com"
CREATOR = "creator@consent.example.com"


async def _setup(client):
    admin = await register(client, ADMIN, "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, CREATOR, "Carl Creator")
    await switch_user(client, ADMIN)
    await add_member(client, org_id, CREATOR, "creator")
    headers = {"X-Org-Id": str(org_id)}
    created = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    assert created.status_code == 201
    await client.post(f"/api/brand/facts/{created.json()['id']}/confirm", headers=headers)
    return org_id, headers


async def _analyse_engine(client, headers, monkeypatch):
    await switch_user(client, CREATOR)
    created = await client.post(
        "/api/submissions",
        data={
            "title": "Consent copy",
            "submission_type": "ad_copy",
            "content": "NovaCloud supports 5,000 users.",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    analysed = await client.post(f"/api/submissions/{created.json()['id']}/analyse", headers=headers)
    assert analysed.status_code == 200, analysed.text
    return analysed.json()["runs"][0]["engine"]


async def test_consent_defaults_off_and_requires_admin(client, monkeypatch):
    monkeypatch.delenv("BRANDPROOF_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    org_id, headers = await _setup(client)

    res = await client.get("/api/settings/ai-consent", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["consent"] is False
    assert body["provider_configured"] is False
    assert "never executed" in body["disclosure"]

    await switch_user(client, CREATOR)
    forbidden = await client.patch(
        "/api/settings/ai-consent", json={"consent": True}, headers=headers
    )
    assert forbidden.status_code == 403

    await switch_user(client, ADMIN)
    enabled = await client.patch(
        "/api/settings/ai-consent", json={"consent": True}, headers=headers
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["consent"] is True

    audit = await client.get("/api/audit", params={"limit": 50}, headers=headers)
    actions = [row["action"] for row in audit.json()]
    assert "settings.ai_consent_changed" in actions


async def test_llm_requires_both_provider_and_consent(client, monkeypatch):
    org_id, headers = await _setup(client)
    monkeypatch.delenv("BRANDPROOF_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert await _analyse_engine(client, headers, monkeypatch) == "Rule-based"

    await switch_user(client, ADMIN)
    await client.patch("/api/settings/ai-consent", json={"consent": True}, headers=headers)

    monkeypatch.setenv("BRANDPROOF_LLM_API_KEY", "test-key-not-used")
    engine = await _analyse_engine(client, headers, monkeypatch)
    assert engine == "LLM-assisted (experimental)"

    await switch_user(client, ADMIN)
    await client.patch("/api/settings/ai-consent", json={"consent": False}, headers=headers)
    engine_off = await _analyse_engine(client, headers, monkeypatch)
    assert engine_off == "Rule-based"
