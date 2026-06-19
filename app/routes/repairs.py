from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.repair import Repair
from app.models.customer import Customer
from app.models.user import User
from app.models.part import Part
from app.models.repair_part import RepairPart
from app.models.payment import Payment
from app.schemas.repair import (
    RepairCreate, RepairUpdate, RepairStatusUpdate, RepairResponse,
    RepairPartResponse, RepairPaymentResponse, VALID_TRANSITIONS,
    CANCELLABLE_STATUSES,
)
from app.utils.auth import get_current_user, require_reseller_or_admin
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/api/repairs", tags=["repairs"])


async def build_repair_response(r: Repair, db) -> RepairResponse:
    from app.models.customer import Customer
    from app.models.user import User
    from app.models.repair_part import RepairPart
    cust = await db.get(Customer, r.customer_id)
    customer_name = cust.name if cust else ""
    assigned_user = await db.get(User, r.assigned_to) if r.assigned_to else None
    assigned_name = assigned_user.name if assigned_user else ""
    creator = await db.get(User, r.created_by)
    creator_name = creator.name if creator else ""
    rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == r.id))).scalars().all()
    total_parts_cost = sum(rp.qty * rp.unit_price for rp in rps)

    pay_result = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0)).where(
            Payment.repair_id == r.id
        )
    )
    total_payments = float(pay_result.scalar() or 0)

    from app.models.part import Part
    part_ids = list(set(rp.part_id for rp in rps if rp.part_id))
    part_map = {}
    if part_ids:
        pr = await db.execute(select(Part).where(Part.id.in_(part_ids)))
        part_map = {p.id: p.name for p in pr.scalars().all()}
    parts = [
        RepairPartResponse(
            id=rp.id, part_id=rp.part_id, qty=rp.qty,
            unit_price=rp.unit_price, selling_price=rp.selling_price,
            returned_qty=rp.returned_qty,
            part_name=part_map.get(rp.part_id) or "",
        )
        for rp in rps
    ]

    pay_rows = (
        (await db.execute(select(Payment).where(Payment.repair_id == r.id)))
        .scalars()
        .all()
    )
    payments = [
        RepairPaymentResponse(
            id=p.id, amount=p.amount, currency=p.currency,
            method=p.method, notes=p.notes, paid_at=p.paid_at,
        )
        for p in pay_rows
    ]

    return RepairResponse(
        id=r.id, customer_id=r.customer_id, customer_name=customer_name,
        assigned_to=r.assigned_to, assigned_user_name=assigned_name,
        created_by=r.created_by, creator_name=creator_name,
        status=r.status, model=r.model, issues=r.issues,
        imei=r.imei, estimated_cost=r.estimated_cost,
        actual_cost=r.actual_cost, service_fee=r.service_fee or 0,
        notes=r.notes, created_at=r.created_at, updated_at=r.updated_at,
        parts=parts, payments=payments,
        total_parts_cost=total_parts_cost,
        total_payments=total_payments,
        balance=(total_parts_cost + (r.service_fee or 0)) - total_payments,
    )


@router.get("", response_model=dict)
async def list_repairs(
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_to: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Repair)
    if status_filter:
        query = query.where(Repair.status == status_filter)
    if assigned_to:
        query = query.where(Repair.assigned_to == assigned_to)
    if date_from:
        query = query.where(Repair.created_at >= date_from)
    if date_to:
        query = query.where(Repair.created_at <= date_to + " 23:59:59")
    if search:
        term = f"%{search}%"
        query = query.join(Customer, Repair.customer_id == Customer.id).where(
            (Customer.name.ilike(term))
            | (Repair.model.ilike(term))
            | (Repair.imei.ilike(term))
            | (Repair.issues.ilike(term))
        )
    total = (await db.execute(select(sqlfunc.count()).select_from(Repair).where(query.whereclause) if query.whereclause is not None else select(sqlfunc.count()).select_from(Repair))).scalar() or 0

    count_stmt = select(sqlfunc.count(Repair.id))
    if status_filter:
        count_stmt = count_stmt.where(Repair.status == status_filter)
    if assigned_to:
        count_stmt = count_stmt.where(Repair.assigned_to == assigned_to)
    if date_from:
        count_stmt = count_stmt.where(Repair.created_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(Repair.created_at <= date_to + " 23:59:59")
    if search:
        term = f"%{search}%"
        count_stmt = count_stmt.where(
            Repair.id.in_(
                select(Repair.id).join(Customer, Repair.customer_id == Customer.id).where(
                    (Customer.name.ilike(term)) | (Repair.model.ilike(term))
                    | (Repair.imei.ilike(term)) | (Repair.issues.ilike(term))
                )
            )
        )
    total = (await db.execute(count_stmt)).scalar() or 0

    list_query = select(Repair)
    if status_filter:
        list_query = list_query.where(Repair.status == status_filter)
    if assigned_to:
        list_query = list_query.where(Repair.assigned_to == assigned_to)
    if date_from:
        list_query = list_query.where(Repair.created_at >= date_from)
    if date_to:
        list_query = list_query.where(Repair.created_at <= date_to + " 23:59:59")
    if search:
        term = f"%{search}%"
        list_query = list_query.join(Customer, Repair.customer_id == Customer.id).where(
            (Customer.name.ilike(term)) | (Repair.model.ilike(term))
            | (Repair.imei.ilike(term)) | (Repair.issues.ilike(term))
        )
    rows = (
        (await db.execute(
            list_query.order_by(Repair.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        ))
        .scalars()
        .unique()
        .all()
    )
    items = [await build_repair_response(r, db) for r in rows]
    return {
        "items": items, "total": total, "page": page,
        "limit": limit, "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=RepairResponse, status_code=status.HTTP_201_CREATED)
async def create_repair(
    data: RepairCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    cust = await db.execute(select(Customer).where(Customer.id == data.customer_id))
    if not cust.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if data.assigned_to:
        u = await db.execute(select(User).where(User.id == data.assigned_to))
        if not u.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    repair = Repair(
        customer_id=data.customer_id, created_by=current_user.id,
        model=data.model, issues=data.issues, imei=data.imei,
        estimated_cost=data.estimated_cost, assigned_to=data.assigned_to,
        notes=data.notes, service_fee=data.service_fee,
    )
    db.add(repair)
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_created", {
        "repair_id": repair.id,
        "customer_id": repair.customer_id,
        "model": repair.model,
        "status": repair.status,
        "created_by": current_user.id,
    })
    return await build_repair_response(repair, db)


@router.get("/{repair_id}", response_model=RepairResponse)
async def get_repair(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    return await build_repair_response(repair, db)


@router.put("/{repair_id}", response_model=RepairResponse)
async def update_repair(
    repair_id: int,
    data: RepairUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(repair, key, value)
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_updated", {
        "repair_id": repair.id,
        "status": repair.status,
        "updated_by": current_user.id,
    })
    return await build_repair_response(repair, db)


@router.put("/{repair_id}/status", response_model=RepairResponse)
async def update_repair_status(
    repair_id: int,
    data: RepairStatusUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")

    allowed = VALID_TRANSITIONS.get(repair.status, set())
    if data.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition from '{repair.status}' to '{data.status}'",
        )
    old_status = repair.status
    repair.status = data.status
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_status_changed", {
        "repair_id": repair.id,
        "old_status": old_status,
        "new_status": repair.status,
        "changed_by": current_user.id,
    })
    return await build_repair_response(repair, db)


@router.get("/{repair_id}/parts", response_model=list[RepairPartResponse])
async def list_repair_parts(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    rows = (
        (await db.execute(select(RepairPart).where(RepairPart.repair_id == repair_id)))
        .scalars()
        .all()
    )
    from app.models.part import Part
    part_ids = list(set(rp.part_id for rp in rows if rp.part_id))
    part_map = {}
    if part_ids:
        pr = await db.execute(select(Part).where(Part.id.in_(part_ids)))
        part_map = {p.id: p.name for p in pr.scalars().all()}
    return [
        RepairPartResponse(
            id=rp.id, part_id=rp.part_id, qty=rp.qty,
            unit_price=rp.unit_price, selling_price=rp.selling_price,
            returned_qty=rp.returned_qty,
            part_name=part_map.get(rp.part_id) or "",
        )
        for rp in rows
    ]


@router.post("/{repair_id}/parts", response_model=RepairPartResponse, status_code=status.HTTP_201_CREATED)
async def add_repair_part(
    repair_id: int,
    part_id: int = Query(...),
    qty: int = Query(1, ge=1),
    selling_price: float = Query(0),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    repair = (await db.execute(select(Repair).where(Repair.id == repair_id))).scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    part = (await db.execute(select(Part).where(Part.id == part_id).with_for_update())).scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    if part.stock_qty < qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {part.stock_qty}",
        )
    part.stock_qty -= qty
    final_price = selling_price if selling_price > 0 else part.selling_price
    repair_part = RepairPart(
        repair_id=repair_id, part_id=part_id, qty=qty,
        unit_price=part.unit_price, selling_price=final_price,
    )
    db.add(repair_part)
    await db.commit()
    await db.refresh(repair_part)
    await ws_manager.broadcast("repair_part_added", {
        "repair_id": repair_id,
        "part_id": part_id,
        "part_name": part.name,
        "qty": qty,
        "added_by": current_user.id,
    })
    return RepairPartResponse(
        id=repair_part.id, part_id=repair_part.part_id, qty=repair_part.qty,
        unit_price=repair_part.unit_price, selling_price=repair_part.selling_price,
        returned_qty=repair_part.returned_qty, part_name=part.name,
    )


@router.delete("/{repair_id}/parts/{rp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repair_part(
    repair_id: int,
    rp_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    repair_part = (
        await db.execute(
            select(RepairPart).where(
                RepairPart.id == rp_id, RepairPart.repair_id == repair_id
            )
        )
    ).scalar_one_or_none()
    if not repair_part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair part not found")
    part = (await db.execute(select(Part).where(Part.id == repair_part.part_id))).scalar_one_or_none()
    if part:
        part.stock_qty += repair_part.qty
    await db.delete(repair_part)
    await db.commit()


@router.get("/{repair_id}/payments", response_model=list[RepairPaymentResponse])
async def list_repair_payments(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    rows = (
        (await db.execute(select(Payment).where(Payment.repair_id == repair_id)))
        .scalars()
        .all()
    )
    return [
        RepairPaymentResponse(
            id=p.id, amount=p.amount, currency=p.currency,
            method=p.method, notes=p.notes, paid_at=p.paid_at,
        )
        for p in rows
    ]


@router.post("/{repair_id}/parts/{rp_id}/return", response_model=RepairPartResponse)
async def return_repair_part(
    repair_id: int,
    rp_id: int,
    qty: int = Query(1, ge=1),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    repair_part = (
        await db.execute(
            select(RepairPart).where(
                RepairPart.id == rp_id, RepairPart.repair_id == repair_id
            )
        )
    ).scalar_one_or_none()
    if not repair_part:
        raise HTTPException(status_code=404, detail="Repair part not found")
    available = repair_part.qty - repair_part.returned_qty
    if qty > available:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot return {qty}. Only {available} available to return",
        )
    repair_part.returned_qty += qty
    part = (await db.execute(select(Part).where(Part.id == repair_part.part_id))).scalar_one_or_none()
    if part:
        part.stock_qty += qty
    await db.commit()
    await db.refresh(repair_part)
    await ws_manager.broadcast("repair_part_added", {
        "repair_id": repair_id,
        "part_id": part_id,
        "part_name": part.name,
        "qty": qty,
        "added_by": current_user.id,
    })
    return RepairPartResponse(
        id=repair_part.id, part_id=repair_part.part_id,
        qty=repair_part.qty, unit_price=repair_part.unit_price,
        selling_price=repair_part.selling_price,
        returned_qty=repair_part.returned_qty,
        part_name=(await db.execute(select(Part.name).where(Part.id == repair_part.part_id))).scalar() or "",
    )


@router.post("/{repair_id}/cancel", response_model=RepairResponse)
async def cancel_repair(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(require_reseller_or_admin),
):
    repair = (await db.execute(select(Repair).where(Repair.id == repair_id))).scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair not found")
    if repair.status not in CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Can only cancel repairs with status: {', '.join(CANCELLABLE_STATUSES)}",
        )
    rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == repair_id))).scalars().all()
    for rp in rps:
        remaining = rp.qty - rp.returned_qty
        if remaining > 0:
            rp.returned_qty = rp.qty
            part = (await db.execute(select(Part).where(Part.id == rp.part_id))).scalar_one_or_none()
            if part:
                part.stock_qty += remaining
    pay_rows = (await db.execute(select(Payment).where(Payment.repair_id == repair_id))).scalars().all()
    for p in pay_rows:
        if p.amount > 0:
            refund = Payment(
                repair_id=repair_id, amount=-p.amount, currency=p.currency,
                method="cash", notes=f"Refund for cancelled repair",
                created_by=current_user.id,
            )
            db.add(refund)
    repair.status = "cancelled"
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_cancelled", {
        "repair_id": repair.id,
        "customer_id": repair.customer_id,
        "cancelled_by": current_user.id,
    })
    return await build_repair_response(repair, db)
