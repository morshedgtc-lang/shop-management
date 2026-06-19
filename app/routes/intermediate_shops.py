import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.intermediate_shop import IntermediateShop
from app.schemas.intermediate_shop import (
    IntermediateShopCreate, IntermediateShopUpdate, IntermediateShopResponse,
)
from app.utils.auth import get_current_user
from app.utils.permissions import require_warehouse_or_admin

router = APIRouter(prefix="/api/intermediate-shops", tags=["intermediate-shops"])


@router.get("", response_model=list[IntermediateShopResponse])
async def list_shops(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (await db.execute(select(IntermediateShop).order_by(IntermediateShop.name))).scalars().all()
    return rows


@router.get("/{shop_id}", response_model=IntermediateShopResponse)
async def get_shop(
    shop_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    shop = await db.get(IntermediateShop, shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")
    return shop


@router.post("", response_model=IntermediateShopResponse, status_code=201)
async def create_shop(
    data: IntermediateShopCreate,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = IntermediateShop(**data.model_dump())
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    return shop


@router.put("/{shop_id}", response_model=IntermediateShopResponse)
async def update_shop(
    shop_id: int,
    data: IntermediateShopUpdate,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = await db.get(IntermediateShop, shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(shop, key, value)
    await db.commit()
    await db.refresh(shop)
    return shop


@router.delete("/{shop_id}", status_code=204)
async def delete_shop(
    shop_id: int,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = await db.get(IntermediateShop, shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")
    await db.delete(shop)
    await db.commit()


@router.post("/{shop_id}/photo", response_model=IntermediateShopResponse)
async def upload_shop_photo(
    shop_id: int,
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = await db.get(IntermediateShop, shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")
    upload_dir = os.path.join("static", "uploads", "shops")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or ".jpg")[1]
    filename = f"shop_{shop_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    shop.photo_url = f"/static/uploads/shops/{filename}"
    await db.commit()
    await db.refresh(shop)
    return shop
