from httpx import AsyncClient


class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        response = await client.post("/api/auth/login", json={
            "email": "admin@shop.com",
            "password": "admin123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient):
        response = await client.post("/api/auth/login", json={
            "email": "admin@shop.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    async def test_protected_route_no_token(self, client: AsyncClient):
        response = await client.get("/api/repairs")
        assert response.status_code == 401

    async def test_protected_route_with_token(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/repairs", headers=auth_headers)
        assert response.status_code == 200
