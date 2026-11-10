from tests.conftest import PASSWORD, login, register


async def test_register_login_me_flow(client):
    data = await register(client, "alice@example.com", "Alice Ray")
    assert data["user"]["email"] == "alice@example.com"
    assert len(data["memberships"]) == 1
    assert data["memberships"][0]["role"] == "admin"

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["full_name"] == "Alice Ray"


async def test_login_wrong_password(client):
    await register(client, "bob@example.com", "Bob Marsh")
    res = await client.post("/api/auth/login", json={"email": "bob@example.com", "password": "WrongPass1!"})
    assert res.status_code == 401


async def test_register_duplicate_email(client):
    await register(client, "carol@example.com", "Carol Diaz")
    res = await client.post(
        "/api/auth/register",
        json={"email": "carol@example.com", "password": PASSWORD, "full_name": "Carol Again"},
    )
    assert res.status_code == 409


async def test_me_requires_auth(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


async def test_logout_clears_session(client):
    await register(client, "dave@example.com", "Dave Cole")
    res = await client.post("/api/auth/logout")
    assert res.status_code == 200
    me = await client.get("/api/auth/me")
    assert me.status_code == 401


async def test_register_validates_password(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "eve@example.com", "password": "short", "full_name": "Eve Shaw"},
    )
    assert res.status_code == 422
