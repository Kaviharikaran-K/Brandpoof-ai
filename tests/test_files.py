from tests.conftest import add_member, register, switch_user


async def test_upload_txt_guideline_and_download(client):
    admin = await register(client, "admin@file.example.com", "Ann Admin")
    content = b"NovaCloud brand guidelines: fictional demo data."
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Style guide"},
        files={"file": ("guide.txt", content, "text/plain")},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["file_name"] == "guide.txt"
    assert body["size_bytes"] == len(content)

    download = await client.get(f"/api/brand/guidelines/{body['id']}/download")
    assert download.status_code == 200
    assert download.content == content


async def test_upload_rejects_disallowed_type(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Bad file"},
        files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
    )
    assert res.status_code == 415


async def test_upload_rejects_extension_mismatch(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Mismatch"},
        files={"file": ("notes.txt", b"fake pdf", "application/pdf")},
    )
    assert res.status_code == 415


async def test_upload_rejects_oversize(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    big = b"x" * (10 * 1024 * 1024 + 100)
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Too big"},
        files={"file": ("big.txt", big, "text/plain")},
    )
    assert res.status_code == 413


async def test_upload_rejects_empty_file(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Empty"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert res.status_code == 422


async def test_creator_can_upload_but_reviewer_cannot(client):
    admin = await register(client, "admin@file.example.com", "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, "creator@file.example.com", "Carl Creator")
    await register(client, "reviewer@file.example.com", "Rita Reviewer")
    await switch_user(client, "admin@file.example.com")
    await add_member(client, org_id, "creator@file.example.com", "creator")
    await add_member(client, org_id, "reviewer@file.example.com", "reviewer")
    headers = {"X-Org-Id": str(org_id)}

    await switch_user(client, "creator@file.example.com")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Creator guide"},
        files={"file": ("creator.txt", b"creator content", "text/plain")},
        headers=headers,
    )
    assert res.status_code == 201

    await switch_user(client, "reviewer@file.example.com")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Reviewer guide"},
        files={"file": ("reviewer.txt", b"reviewer content", "text/plain")},
        headers=headers,
    )
    assert res.status_code == 403


async def test_filename_is_sanitised(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    res = await client.post(
        "/api/brand/guidelines",
        data={"title": "Weird name"},
        files={"file": ("..\\..\\evil<>:name.txt", b"content", "text/plain")},
    )
    assert res.status_code == 201
    assert ".." not in res.json()["file_name"]
    assert "<" not in res.json()["file_name"]


async def test_colour_and_logo_assets(client):
    await register(client, "admin@file.example.com", "Ann Admin")
    colour = await client.post(
        "/api/brand/assets/colours",
        json={"name": "Nova Teal", "colour_value": "#0f766e"},
    )
    assert colour.status_code == 201
    assert colour.json()["colour_value"] == "#0F766E"

    invalid = await client.post(
        "/api/brand/assets/colours",
        json={"name": "Bad", "colour_value": "teal"},
    )
    assert invalid.status_code == 422

    logo = await client.post(
        "/api/brand/assets/logos",
        data={"name": "Primary logo"},
        files={"file": ("logo.png", b"\x89PNG fake", "image/png")},
    )
    assert logo.status_code == 201

    file = await client.get(f"/api/brand/assets/logos/{logo.json()['id']}/file")
    assert file.status_code == 200
