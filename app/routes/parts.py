from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.part import Part
from app.models.user import User
from app.schemas.part import PartCreate, PartUpdate, PartResponse
from app.utils.auth import get_current_user, require_admin, require_manager_or_admin

router = APIRouter(prefix="/api/parts", tags=["parts"])


@router.get("/", response_model=dict)
def list_parts(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Part)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Part.name.ilike(search_term)) | (Part.model.ilike(search_term))
        )
    total = query.count()
    parts = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [PartResponse.model_validate(p) for p in parts],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/low-stock", response_model=list[PartResponse])
def list_low_stock_parts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parts = db.query(Part).filter(Part.stock_qty <= Part.min_stock_alert).all()
    return parts


@router.post("/", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
def create_part(
    data: PartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    part = Part(**data.model_dump())
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Part not found"
        )
    update_data = data.model_dump(exclude_unset=True)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Part not found"
        )
    db.delete(part)
    db.commit()
