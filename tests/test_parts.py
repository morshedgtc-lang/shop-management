import pytest
from httpx import AsyncClient


class TestParts:
    async def test_create_part(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/parts", json={
            "name": "Test Battery",
            "model": "iPhone 13",
            "stock_qty": 50,
            "unit_price": 15.0,
            "selling_price": 35.0,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Battery"
        assert data["stock_qty"] == 50
        assert "sku" in data
        assert "id" in data

    async def test_get_parts_list(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/parts", json={
            "name": "Screen Assembly",
            "model": "Samsung S24",
            "stock_qty": 10,
            "unit_price": 80.0,
            "selling_price": 150.0,
        }, headers=auth_headers)

        response = await client.get("/api/parts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_update_part(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post("/api/parts", json={
            "name": "Charging Port",
            "model": "Pixel 8",
            "stock_qty": 20,
            "unit_price": 5.0,
            "selling_price": 12.0,
        }, headers=auth_headers)
        part_id = create_resp.json()["id"]

        response = await client.put(f"/api/parts/{part_id}", json={
            "stock_qty": 35,
            "selling_price": 15.0,
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["stock_qty"] == 35
        assert data["selling_price"] == 15.0

    async def test_bulk_commit(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/inventory/bulk/commit", json={
            "items": [
                {
                    "name": "USB Cable",
                    "model": "Universal",
                    "sku": "CBL-001",
                    "stock_qty": 100,
                    "unit_price": 1.5,
                    "selling_price": 5.0,
                },
                {
                    "name": "Tempered Glass",
                    "model": "iPhone 13",
                    "sku": "GLASS-001",
                    "stock_qty": 200,
                    "unit_price": 0.8,
                    "selling_price": 3.0,
                },
            ],
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert len(data["items"]) == 2
