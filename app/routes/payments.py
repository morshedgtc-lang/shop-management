from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.payment import Payment
from app.models.repair import Repair
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/", response_model=dict)
def list_payments(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    repair_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Payment)
    if date_from:
        query = query.filter(Payment.paid_at >= date_from)
    if date_to:
        query = query.filter(Payment.paid_at <= date_to + " 23:59:59")
    if method:
        query = query.filter(Payment.method == method)
    if repair_id:
        query = query.filter(Payment.repair_id == repair_id)
    total = query.count()
    payments = (
        query.order_by(Payment.paid_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "items": [PaymentResponse.model_validate(p) for p in payments],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == data.repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    payment = Payment(
        repair_id=data.repair_id,
        amount=data.amount,
        currency=data.currency,
        method=data.method,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(payment)
    total_paid = (
        db.query(sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0))
        .filter(Payment.repair_id == data.repair_id)
        .scalar()
    )
    repair.actual_cost = total_paid + data.amount
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/repair/{repair_id}", response_model=list[PaymentResponse])
def get_payments_by_repair(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payments = db.query(Payment).filter(Payment.repair_id == repair_id).all()
    return payments


@router.get("/summary")
def payment_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Payment)
    if date_from:
        query = query.filter(Payment.paid_at >= date_from)
    if date_to:
        query = query.filter(Payment.paid_at <= date_to + " 23:59:59")

    payments = query.all()

    by_method = {}
    for p in payments:
        if p.method not in by_method:
            by_method[p.method] = 0
        by_method[p.method] += p.amount

    by_date = {}
    for p in payments:
        day = p.paid_at.strftime("%Y-%m-%d") if p.paid_at else "unknown"
        if day not in by_date:
            by_date[day] = 0
        by_date[day] += p.amount

    total = sum(p.amount for p in payments)

    return {
        "total": total,
        "by_method": by_method,
        "by_date": by_date,
        "count": len(payments),
    }
