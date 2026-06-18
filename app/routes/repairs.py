from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.repair import Repair
from app.models.customer import Customer
from app.models.user import User
from app.models.part import Part
from app.models.repair_part import RepairPart
from app.models.payment import Payment
from app.schemas.repair import (
    RepairCreate,
    RepairUpdate,
    RepairStatusUpdate,
    RepairResponse,
    RepairPartResponse,
    RepairPaymentResponse,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/repairs", tags=["repairs"])

VALID_STATUSES = [
    "received",
    "diagnosed",
    "waiting_parts",
    "repairing",
    "testing",
    "delivered",
]


def build_repair_response(r: Repair, db: Session) -> RepairResponse:
    customer_name = r.customer.name if r.customer else ""
    assigned_name = r.assigned_user.name if r.assigned_user else ""
    creator_name = r.creator.name if r.creator else ""

    total_parts_cost = sum(rp.qty * rp.unit_price for rp in r.repair_parts)
    total_payments = (
        db.query(Payment)
        .filter(Payment.repair_id == r.id)
        .with_entities(Payment.amount)
        .all()
    )
    total_payments = sum(p[0] for p in total_payments)

    parts = [
        RepairPartResponse(
            id=rp.id,
            part_id=rp.part_id,
            qty=rp.qty,
            unit_price=rp.unit_price,
            part_name=rp.part.name if rp.part else "",
        )
        for rp in r.repair_parts
    ]

    payments = [
        RepairPaymentResponse(
            id=p.id,
            amount=p.amount,
            currency=p.currency,
            method=p.method,
            notes=p.notes,
            paid_at=p.paid_at,
        )
        for p in db.query(Payment).filter(Payment.repair_id == r.id).all()
    ]

    return RepairResponse(
        id=r.id,
        customer_id=r.customer_id,
        customer_name=customer_name,
        assigned_to=r.assigned_to,
        assigned_user_name=assigned_name,
        created_by=r.created_by,
        creator_name=creator_name,
        status=r.status,
        model=r.model,
        issues=r.issues,
        imei=r.imei,
        estimated_cost=r.estimated_cost,
        actual_cost=r.actual_cost,
        notes=r.notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
        parts=parts,
        payments=payments,
        total_parts_cost=total_parts_cost,
        total_payments=total_payments,
        balance=r.actual_cost - total_payments,
    )


@router.get("", response_model=dict)
def list_repairs(
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_to: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Repair)
    if status_filter:
        query = query.filter(Repair.status == status_filter)
    if assigned_to:
        query = query.filter(Repair.assigned_to == assigned_to)
    if date_from:
        query = query.filter(Repair.created_at >= date_from)
    if date_to:
        query = query.filter(Repair.created_at <= date_to + " 23:59:59")
    if search:
        search_term = f"%{search}%"
        query = query.join(Customer, Repair.customer_id == Customer.id).filter(
            (Customer.name.ilike(search_term))
            | (Repair.model.ilike(search_term))
            | (Repair.imei.ilike(search_term))
            | (Repair.issues.ilike(search_term))
        )
    total = query.count()
    repairs = (
        query.order_by(Repair.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    items = [build_repair_response(r, db) for r in repairs]
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=RepairResponse, status_code=status.HTTP_201_CREATED)
def create_repair(
    data: RepairCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    if data.assigned_to:
        assigned_user = db.query(User).filter(User.id == data.assigned_to).first()
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found"
            )
    repair = Repair(
        customer_id=data.customer_id,
        created_by=current_user.id,
        model=data.model,
        issues=data.issues,
        imei=data.imei,
        estimated_cost=data.estimated_cost,
        assigned_to=data.assigned_to,
        notes=data.notes,
    )
    db.add(repair)
    db.commit()
    db.refresh(repair)
    return build_repair_response(repair, db)


@router.get("/{repair_id}", response_model=RepairResponse)
def get_repair(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    return build_repair_response(repair, db)


@router.put("/{repair_id}", response_model=RepairResponse)
def update_repair(
    repair_id: int,
    data: RepairUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(repair, key, value)
    db.commit()
    db.refresh(repair)
    return build_repair_response(repair, db)


@router.put("/{repair_id}/status", response_model=RepairResponse)
def update_repair_status(
    repair_id: int,
    data: RepairStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}",
        )
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    repair.status = data.status
    db.commit()
    db.refresh(repair)
    return build_repair_response(repair, db)


@router.get("/{repair_id}/parts", response_model=list[RepairPartResponse])
def list_repair_parts(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    parts = (
        db.query(RepairPart)
        .filter(RepairPart.repair_id == repair_id)
        .all()
    )
    return [
        RepairPartResponse(
            id=rp.id,
            part_id=rp.part_id,
            qty=rp.qty,
            unit_price=rp.unit_price,
            part_name=rp.part.name if rp.part else "",
        )
        for rp in parts
    ]


@router.post(
    "/{repair_id}/parts", response_model=RepairPartResponse, status_code=status.HTTP_201_CREATED
)
def add_repair_part(
    repair_id: int,
    part_id: int = Query(...),
    qty: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Part not found"
        )
    if part.stock_qty < qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {part.stock_qty}",
        )
    part.stock_qty -= qty
    repair_part = RepairPart(
        repair_id=repair_id,
        part_id=part_id,
        qty=qty,
        unit_price=part.unit_price,
    )
    db.add(repair_part)
    db.commit()
    db.refresh(repair_part)
    return RepairPartResponse(
        id=repair_part.id,
        part_id=repair_part.part_id,
        qty=repair_part.qty,
        unit_price=repair_part.unit_price,
        part_name=part.name,
    )


@router.delete(
    "/{repair_id}/parts/{rp_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_repair_part(
    repair_id: int,
    rp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair_part = (
        db.query(RepairPart)
        .filter(RepairPart.id == rp_id, RepairPart.repair_id == repair_id)
        .first()
    )
    if not repair_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair part not found"
        )
    part = db.query(Part).filter(Part.id == repair_part.part_id).first()
    if part:
        part.stock_qty += repair_part.qty
    db.delete(repair_part)
    db.commit()


@router.get("/{repair_id}/payments", response_model=list[RepairPaymentResponse])
def list_repair_payments(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repair = db.query(Repair).filter(Repair.id == repair_id).first()
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found"
        )
    payments = db.query(Payment).filter(Payment.repair_id == repair_id).all()
    return [
        RepairPaymentResponse(
            id=p.id,
            amount=p.amount,
            currency=p.currency,
            method=p.method,
            notes=p.notes,
            paid_at=p.paid_at,
        )
        for p in payments
    ]
