import os
import pytest
import asyncio
from typing import AsyncGenerator

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import app.main
from app.database import Base, engine, AsyncSessionLocal, ROLE_ADMIN
from app.models.user import User
from app.utils.auth import hash_password

import app.models.user
import app.models.customer
import app.models.repair
import app.models.service
import app.models.part
import app.models.repair_part
import app.models.payment
import app.models.daily_sale
import app.models.expense
import app.models.expense_category
import app.models.setting
import app.models.brand
import app.models.device_model
import app.models.part_category
import app.models.part_type
import app.models.supplier
import app.models.purchase_order
import app.models.supplier_payment
import app.models.part_request
import app.models.intermediate_shop
import app.models.collection_run
import app.models.collection_item

fastapi_app = app.main.app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@shop.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                name="Admin",
                email="admin@shop.com",
                password_hash=hash_password("admin123"),
                phone="",
                role=ROLE_ADMIN,
                active=True,
            ))
            await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("test.db"):
        for _ in range(5):
            try:
                os.remove("test.db")
                break
            except PermissionError:
                await asyncio.sleep(0.1)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    response = await client.post("/api/auth/login", json={
        "email": "admin@shop.com",
        "password": "admin123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
