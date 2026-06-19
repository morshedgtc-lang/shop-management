from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.payment import Payment
from app.models.repair import Repair
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.auth import get_current_user, require_reseller_or_admin

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=dict)
async def list_payments(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    repair_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Payment)
    if date_from:
        query = query.where(Payment.paid_at >= date_from)
    if date_to:
        query = query.where(Payment.paid_at <= date_to + " 23:59:59")
    if method:
        query = query.where(Payment.method == method)
    if repair_id:
        query = query.where(Payment.repair_id == repair_id)

    count_stmt = select(sqlfunc.count(Payment.id))
    if date_from:
        count_stmt = count_stmt.where(Payment.paid_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(Payment.paid_at <= date_to + " 23:59:59")
    if method:
        count_stmt = count_stmt.where(Payment.method == method)
    if repair_id:
        count_stmt = count_stmt.where(Payment.repair_id == repair_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    list_query = select(Payment)
    if date_from:
        list_query = list_query.where(Payment.paid_at >= date_from)
    if date_to:
        list_query = list_query.where(Payment.paid_at <= date_to + " 23:59:59")
    if method:
        list_query = list_query.where(Payment.method == method)
    if repair_id:
        list_query = list_query.where(Payment.repair_id == repair_id)
    rows = (
        (await db.execute(list_query.order_by(Payment.paid_at.desc()).offset((page - 1) * limit).limit(limit)))
        .scalars()
        .all()
    )
    return {
        "items": [PaymentResponse.model_validate(p) for p in rows],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    repair = (await db.execute(select(Repair).where(Repair.id == data.repair_id))).scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")

    payment = Payment(
        repair_id=data.repair_id, amount=data.amount,
        currency=data.currency, method=data.method,
        notes=data.notes, created_by=current_user.id,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/repair/{repair_id}", response_model=list[PaymentResponse])
async def get_payments_by_repair(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (
        (await db.execute(select(Payment).where(Payment.repair_id == repair_id)))
        .scalars()
        .all()
    )
    return rows


@router.get("/summary")
async def payment_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Payment)
    if date_from:
        query = query.where(Payment.paid_at >= date_from)
    if date_to:
        query = query.where(Payment.paid_at <= date_to + " 23:59:59")
    payments = (await db.execute(query)).scalars().all()

    by_method = {}
    by_date = {}
    for p in payments:
        by_method[p.method] = by_method.get(p.method, 0) + p.amount
        day = p.paid_at.strftime("%Y-%m-%d") if p.paid_at else "unknown"
        by_date[day] = by_date.get(day, 0) + p.amount

    return {
        "total": sum(p.amount for p in payments),
        "by_method": by_method,
        "by_date": by_date,
        "count": len(payments),
    }


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    db=Depends(get_db),
    current_user=Depends(require_reseller_or_admin),
):
    payment = (await db.execute(select(Payment).where(Payment.id == payment_id))).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    await db.delete(payment)
    await db.commit()
