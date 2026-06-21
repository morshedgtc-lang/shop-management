from httpx import AsyncClient


class TestRepairs:
    async def test_create_repair(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/repairs", json={
            "customer_name": "John Doe",
            "customer_phone": "+1234567890",
            "model": "iPhone 13",
            "issues": "Screen cracked",
            "order_type": "OR",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["model"] == "iPhone 13"
        assert data["order_type"] == "OR"
        assert data["customer_name"] == "John Doe"
        assert "id" in data

    async def test_create_repair_ir(self, client: AsyncClient, auth_headers: dict):
        shop_resp = await client.post("/api/intermediate-shops", json={
            "name": "Test Shop",
            "phone": "+9876543210",
        }, headers=auth_headers)
        assert shop_resp.status_code == 201
        shop_id = shop_resp.json()["id"]

        response = await client.post("/api/repairs", json={
            "model": "Samsung Galaxy S24",
            "issues": "Battery draining",
            "order_type": "IR",
            "intermediate_shop_id": shop_id,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["order_type"] == "IR"
        assert data["intermediate_shop_id"] == shop_id

    async def test_get_repair(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post("/api/repairs", json={
            "customer_name": "Jane Smith",
            "customer_phone": "+1987654321",
            "model": "Google Pixel 8",
            "issues": "No power",
            "order_type": "OR",
        }, headers=auth_headers)
        repair_id = create_resp.json()["id"]

        response = await client.get(f"/api/repairs/{repair_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == repair_id
        assert data["model"] == "Google Pixel 8"

    async def test_update_repair_status(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post("/api/repairs", json={
            "customer_name": "Status Tester",
            "customer_phone": "+1112223333",
            "model": "OnePlus 12",
            "issues": "Overheating",
            "order_type": "OR",
        }, headers=auth_headers)
        repair_id = create_resp.json()["id"]

        response = await client.put(f"/api/repairs/{repair_id}/status", json={
            "status": "ESTIMATE_GIVEN",
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ESTIMATE_GIVEN"

    async def test_cancel_repair(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post("/api/repairs", json={
            "customer_name": "Cancel Tester",
            "customer_phone": "+4445556666",
            "model": "Xiaomi 14",
            "issues": "Water damage",
            "order_type": "OR",
        }, headers=auth_headers)
        repair_id = create_resp.json()["id"]

        response = await client.post(f"/api/repairs/{repair_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["repair_id"] == repair_id
        assert data["status"] == "COMPLETED"
