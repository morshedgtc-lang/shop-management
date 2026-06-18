from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.part import Part
from app.models.user import User
from app.schemas.part import PartCreate, PartUpdate, PartResponse
from app.utils.auth import get_current_user, require_admin, require_manager_or_admin

router = APIRouter(prefix="/api/parts", tags=["parts"])


def generate_sku(db: Session) -> str:
    last = db.query(Part).order_by(Part.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"PART-{num:03d}"


@router.get("", response_model=dict)
def list_parts(
    search: Optional[str] = Query(None),
    brand_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    part_type_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Part)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Part.name.ilike(term)) | (Part.model.ilike(term)) |
            (Part.sku.ilike(term)) | (Part.supplier_barcode.ilike(term))
        )
    if brand_id:
        query = query.filter(Part.brand_id == brand_id)
    if model_id:
        query = query.filter(Part.model_id == model_id)
    if part_type_id:
        query = query.filter(Part.part_type_id == part_type_id)
    total = query.count()
    parts = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [PartResponse.model_validate(p) for p in parts],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/low-stock", response_model=list[PartResponse])
def list_low_stock_parts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parts = db.query(Part).filter(Part.stock_qty <= Part.min_stock_alert).all()
    return parts


@router.get("/scan/{barcode}", response_model=PartResponse)
def scan_barcode(barcode: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = db.query(Part).filter(
        (Part.supplier_barcode == barcode) | (Part.sku == barcode)
    ).first()
    if not part:
        raise HTTPException(status_code=404, detail="No part found with this barcode")
    return part


@router.post("", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
def create_part(
    data: PartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    sku = data.sku
    if not sku:
        sku = generate_sku(db)
    else:
        existing = db.query(Part).filter(Part.sku == sku).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{sku}' already exists")
    part = Part(**data.model_dump())
    part.sku = sku
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.put("/{part_id}", response_model=PartResponse)
def update_part(
    part_id: int,
    data: PartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    update_data = data.model_dump(exclude_unset=True)
    if "sku" in update_data and update_data["sku"] and update_data["sku"] != part.sku:
        existing = db.query(Part).filter(Part.sku == update_data["sku"]).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"SKU '{update_data['sku']}' already exists")
    for key, value in update_data.items():
        setattr(part, key, value)
    db.commit()
    db.refresh(part)
    return part


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(part)
    db.commit()
