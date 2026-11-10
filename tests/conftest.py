import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="bp-uploads-")
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app as main_app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_sessionmaker(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(db_sessionmaker):
    async def override_get_db():
        async with db_sessionmaker() as session:
            yield session

    main_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://testserver") as c:
        yield c
    main_app.dependency_overrides.clear()


PASSWORD = "Password123!"


async def register(client: AsyncClient, email: str, full_name: str = "Test User") -> dict:
    res = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
    assert res.status_code == 201, res.text
    return res.json()


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> dict:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


async def switch_user(client: AsyncClient, email: str, password: str = PASSWORD) -> dict:
    client.cookies.clear()
    return await login(client, email, password)


async def add_member(client: AsyncClient, org_id: int, email: str, role: str) -> dict:
    res = await client.post(f"/api/organisations/{org_id}/members", json={"email": email, "role": role})
    assert res.status_code == 201, res.text
    return res.json()


def fact_payload(**overrides) -> dict:
    payload = {
        "fact_id": "NC-FR-001",
        "name": "Maximum supported users",
        "approved_value": "5,000",
        "description": "NovaCloud supports up to 5,000 users per tenant.",
        "source_ref": "Product Handbook v2.1",
        "version": 1,
        "effective_date": "2025-01-01",
        "expiry_date": None,
    }
    payload.update(overrides)
    return payload
