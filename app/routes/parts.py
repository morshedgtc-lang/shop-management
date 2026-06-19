from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc, update as sqlupdate
from typing import Optional

from app.database import get_db
from app.models.part import Part
from app.schemas.part import PartCreate, PartUpdate, PartResponse
from app.utils.auth import get_current_user, require_admin, require_reseller_or_admin
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/api/parts", tags=["parts"])


async def generate_sku(db) -> str:
    result = await db.execute(select(sqlfunc.max(Part.id)))
    max_id = result.scalar() or 0
    return f"PART-{max_id + 1:03d}"


@router.get("", response_model=dict)
async def list_parts(
    search: Optional[str] = Query(None),
    brand_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    part_type_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Part)
    if search:
        term = f"%{search}%"
        query = query.where(
            (Part.name.ilike(term)) | (Part.model.ilike(term))
            | (Part.sku.ilike(term)) | (Part.supplier_barcode.ilike(term))
        )
    if brand_id:
        query = query.where(Part.brand_id == brand_id)
    if model_id:
        query = query.where(Part.model_id == model_id)
    if part_type_id:
        query = query.where(Part.part_type_id == part_type_id)

    count_stmt = select(sqlfunc.count(Part.id))
    if search:
        term = f"%{search}%"
        count_stmt = count_stmt.where(
            (Part.name.ilike(term)) | (Part.model.ilike(term))
            | (Part.sku.ilike(term)) | (Part.supplier_barcode.ilike(term))
        )
    if brand_id:
        count_stmt = count_stmt.where(Part.brand_id == brand_id)
    if model_id:
        count_stmt = count_stmt.where(Part.model_id == model_id)
    if part_type_id:
        count_stmt = count_stmt.where(Part.part_type_id == part_type_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    list_query = select(Part)
    if search:
        list_query = list_query.where(
            (Part.name.ilike(term)) | (Part.model.ilike(term))
            | (Part.sku.ilike(term)) | (Part.supplier_barcode.ilike(term))
        )
    if brand_id:
        list_query = list_query.where(Part.brand_id == brand_id)
    if model_id:
        list_query = list_query.where(Part.model_id == model_id)
    if part_type_id:
        list_query = list_query.where(Part.part_type_id == part_type_id)
    parts = (
        (await db.execute(list_query.offset((page - 1) * limit).limit(limit)))
        .scalars()
        .all()
    )
    return {
        "items": [PartResponse.model_validate(p) for p in parts],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/low-stock", response_model=list[PartResponse])
async def list_low_stock_parts(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Part).where(Part.stock_qty <= Part.min_stock_alert)
        )
    ).scalars().all()
    return rows


@router.get("/scan/{barcode}", response_model=PartResponse)
async def scan_barcode(barcode: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(Part).where((Part.supplier_barcode == barcode) | (Part.sku == barcode))
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="No part found with this barcode")
    return part


@router.post("", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
async def create_part(
    data: PartCreate,
    db=Depends(get_db),
    current_user=Depends(require_reseller_or_admin),
):
    sku = data.sku
    if not sku:
        sku = await generate_sku(db)
    else:
        existing = (await db.execute(select(Part).where(Part.sku == sku))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{sku}' already exists")
    part = Part(**data.model_dump())
    part.sku = sku
    db.add(part)
    await db.commit()
    await db.refresh(part)
    return part


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: int,
    data: PartUpdate,
    db=Depends(get_db),
    current_user=Depends(require_reseller_or_admin),
):
    part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    update_data = data.model_dump(exclude_unset=True)
    if "sku" in update_data and update_data["sku"] and update_data["sku"] != part.sku:
        existing = (await db.execute(select(Part).where(Part.sku == update_data["sku"]))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{update_data['sku']}' already exists")
    for key, value in update_data.items():
        setattr(part, key, value)
    await db.commit()
    await db.refresh(part)
    await ws_manager.broadcast("part_created", {
        "part_id": part.id,
        "name": part.name,
        "sku": part.sku,
        "stock_qty": part.stock_qty,
        "created_by": current_user.id,
    })
    return part


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part(
    part_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    part = (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    await db.delete(part)
    await db.commit()
