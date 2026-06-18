from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.daily_sale import DailySale
from app.models.user import User
from app.schemas.daily_sale import DailySaleCreate, DailySaleUpdate, DailySaleResponse
from app.utils.auth import get_current_user, require_admin, require_manager_or_admin

router = APIRouter(prefix="/api/daily-sales", tags=["daily_sales"])


@router.get("/", response_model=dict)
def list_daily_sales(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DailySale)
    if date_from:
        query = query.filter(DailySale.date >= date_from)
    if date_to:
        query = query.filter(DailySale.date <= date_to)
    total = query.count()
    sales = (
        query.order_by(DailySale.date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "items": [DailySaleResponse.model_validate(s) for s in sales],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post(
    "/", response_model=DailySaleResponse, status_code=status.HTTP_201_CREATED
)
def create_daily_sale(
    data: DailySaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    sale_date = data.date or date.today().isoformat()
    sale = DailySale(
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        note=data.note,
        date=sale_date,
        created_by=current_user.id,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.put("/{sale_id}", response_model=DailySaleResponse)
def update_daily_sale(
    sale_id: int,
    data: DailySaleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    sale = db.query(DailySale).filter(DailySale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Daily sale not found"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sale, key, value)
    db.commit()
    db.refresh(sale)
    return sale


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    sale = db.query(DailySale).filter(DailySale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Daily sale not found"
        )
    db.delete(sale)
    db.commit()
