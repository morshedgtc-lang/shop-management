from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.repair import Repair
from app.models.customer import Customer
from app.models.user import User
from app.models.part import Part
from app.models.repair_part import RepairPart
from app.models.payment import Payment
from app.models.part_request import PartRequest
from app.models.intermediate_shop import IntermediateShop
from app.schemas.repair import (
    RepairCreate, RepairUpdate, RepairStatusUpdate, RepairResponse,
    RepairPartResponse, RepairPaymentResponse, PartRequestResponse,
    PartRequestCreate, PartRequestFulfill, CancelRepairResponse,
    VALID_TRANSITIONS,
)
from app.utils.auth import get_current_user
from app.utils.invoice_generator import invoice_generator
from app.utils.permissions import (
    require_technician, require_warehouse,
    require_reception_or_technician, can_cancel_repair,
)
from app.utils.ws_manager import ws_manager


async def _build_invoice_data(repair, response, db, estimate=False):
    """Build repair_data dict for the invoice generator."""
    shop_name = ""
    shop_address = ""
    shop_phone = ""
    if repair.intermediate_shop_id:
        shop = await db.get(IntermediateShop, repair.intermediate_shop_id)
        if shop:
            shop_name = shop.name or ""
            shop_address = shop.address or ""
            shop_phone = shop.phone or ""

    return {
        "id": response.id,
        "customer_name": response.customer_name,
        "model": response.model,
        "imei": response.imei,
        "issues": response.issues,
        "parts": [
            {
                "part_name": p.part_name,
                "qty": p.qty,
                "unit_price": p.unit_price,
                "selling_price": p.selling_price,
            }
            for p in response.parts
        ],
        "service_fee": response.service_fee,
        "payment_status": response.payment_status,
        "created_at": response.created_at,
        "shop_name": shop_name,
        "shop_address": shop_address,
        "shop_phone": shop_phone,
    }

router = APIRouter(prefix="/api/repairs", tags=["repairs"])


async def build_repair_response(r: Repair, db) -> RepairResponse:
    from app.models.repair_part import RepairPart
    from app.models.part_request import PartRequest
    from app.models.payment import Payment
    from app.models.intermediate_shop import IntermediateShop
    from app.models.part import Part
    cust = await db.get(Customer, r.customer_id) if r.customer_id else None
    customer_name = cust.name if cust else ""
    assigned_user = await db.get(User, r.assigned_to) if r.assigned_to else None
    assigned_name = assigned_user.name if assigned_user else ""
    creator = await db.get(User, r.created_by)
    creator_name = creator.name if creator else ""
    shop = await db.get(IntermediateShop, r.intermediate_shop_id) if r.intermediate_shop_id else None

    rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == r.id))).scalars().all()
    total_parts_cost = sum(rp.qty * rp.unit_price for rp in rps)

    pay_result = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0)).where(
            Payment.repair_id == r.id
        )
    )
    total_payments = float(pay_result.scalar() or 0)

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

    prs = (await db.execute(select(PartRequest).where(PartRequest.repair_id == r.id))).scalars().all()
    p_req_ids = list(set(p.part_id for p in prs if p.part_id))
    p_req_map = {}
    if p_req_ids:
        pr2 = await db.execute(select(Part).where(Part.id.in_(p_req_ids)))
        p_req_map = {p.id: p.name for p in pr2.scalars().all()}
    user_ids = set()
    for p in prs:
        if p.requested_by:
            user_ids.add(p.requested_by)
        if p.fulfilled_by:
            user_ids.add(p.fulfilled_by)
    user_map = {}
    if user_ids:
        ur = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        user_map = {u.id: u.name for u in ur.scalars().all()}
    part_requests = [
        PartRequestResponse(
            id=p.id, repair_id=p.repair_id, part_id=p.part_id,
            part_name=p_req_map.get(p.part_id) or "",
            requested_by=p.requested_by,
            requester_name=user_map.get(p.requested_by) or "",
            fulfilled_by=p.fulfilled_by,
            fulfiller_name=user_map.get(p.fulfilled_by) or "",
            quantity=p.quantity, status=p.status, notes=p.notes,
            created_at=p.created_at,
        )
        for p in prs
    ]

    return RepairResponse(
        id=r.id, customer_id=r.customer_id, customer_name=customer_name,
        assigned_to=r.assigned_to, assigned_user_name=assigned_name,
        created_by=r.created_by, creator_name=creator_name,
        status=r.status, model=r.model, issues=r.issues,
        imei=r.imei, estimated_cost=r.estimated_cost,
        estimated_time=r.estimated_time or "",
        actual_cost=r.actual_cost, service_fee=r.service_fee or 0,
        payment_status=r.payment_status or "UNPAID",
        order_type=r.order_type or "OR",
        intermediate_shop_id=r.intermediate_shop_id,
        intermediate_shop_name=shop.name if shop else "",
        notes=r.notes or "", created_at=r.created_at, updated_at=r.updated_at,
        parts=parts, payments=payments, part_requests=part_requests,
        total_parts_cost=total_parts_cost,
        total_payments=total_payments,
        balance=((total_parts_cost + (r.service_fee or 0)) - total_payments) if r.order_type == "OR" else total_parts_cost + (r.service_fee or 0),
    )


@router.get("", response_model=dict)
async def list_repairs(
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_to: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    order_type: Optional[str] = Query(None),
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
    if order_type:
        query = query.where(Repair.order_type == order_type)
    if search:
        term = f"%{search}%"
        query = query.outerjoin(Customer, Repair.customer_id == Customer.id).where(
            (Customer.name.ilike(term))
            | (Repair.model.ilike(term))
            | (Repair.imei.ilike(term))
            | (Repair.issues.ilike(term))
        )

    count_stmt = select(sqlfunc.count(Repair.id))
    if status_filter:
        count_stmt = count_stmt.where(Repair.status == status_filter)
    if assigned_to:
        count_stmt = count_stmt.where(Repair.assigned_to == assigned_to)
    if date_from:
        count_stmt = count_stmt.where(Repair.created_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(Repair.created_at <= date_to + " 23:59:59")
    if order_type:
        count_stmt = count_stmt.where(Repair.order_type == order_type)
    if search:
        term = f"%{search}%"
        count_stmt = count_stmt.where(
            Repair.id.in_(
                select(Repair.id).outerjoin(Customer, Repair.customer_id == Customer.id).where(
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
    if order_type:
        list_query = list_query.where(Repair.order_type == order_type)
    if search:
        term = f"%{search}%"
        list_query = list_query.outerjoin(Customer, Repair.customer_id == Customer.id).where(
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
    current_user=Depends(require_reception_or_technician),
):
    customer_id = None
    if data.order_type == "OR":
        if data.customer_name or data.customer_phone:
            existing = None
            if data.customer_phone:
                result = await db.execute(
                    select(Customer).where(Customer.phone == data.customer_phone)
                )
                existing = result.scalar_one_or_none()
            if existing:
                customer_id = existing.id
            else:
                cust = Customer(
                    name=data.customer_name or "Walk-in",
                    phone=data.customer_phone or "",
                )
                db.add(cust)
                await db.flush()
                customer_id = cust.id
    elif data.order_type == "IR":
        if not data.intermediate_shop_id:
            raise HTTPException(status_code=400, detail="IR orders require intermediate_shop_id")
        shop = await db.get(IntermediateShop, data.intermediate_shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail="Intermediate shop not found")

    repair = Repair(
        customer_id=customer_id,
        order_type=data.order_type,
        intermediate_shop_id=data.intermediate_shop_id,
        created_by=current_user.id,
        model=data.model, issues=data.issues, imei=data.imei,
        estimated_cost=data.estimated_cost,
        estimated_time=data.estimated_time,
        service_fee=data.service_fee,
        assigned_to=data.assigned_to,
        notes=data.notes,
    )
    db.add(repair)
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_created", {
        "repair_id": repair.id,
        "order_type": repair.order_type,
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

    if data.status == "COMPLETED" and repair.order_type == "OR":
        repair.payment_status = "PAID"

    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_status_changed", {
        "repair_id": repair.id,
        "old_status": old_status,
        "new_status": repair.status,
        "changed_by": current_user.id,
    })
    return await build_repair_response(repair, db)


@router.post("/{repair_id}/cancel", response_model=CancelRepairResponse)
async def cancel_repair(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    repair = (await db.execute(select(Repair).where(Repair.id == repair_id))).scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair not found")
    if not can_cancel_repair(repair.status, current_user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to cancel this repair at its current stage",
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
                method="cash", notes="Refund for cancelled repair",
                created_by=current_user.id,
            )
            db.add(refund)
    repair.status = "COMPLETED"
    await db.commit()
    await db.refresh(repair)
    await ws_manager.broadcast("repair_cancelled", {
        "repair_id": repair.id,
        "order_type": repair.order_type,
        "cancelled_by": current_user.id,
    })
    return CancelRepairResponse(repair_id=repair.id, status=repair.status, message="Repair cancelled")


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
    current_user=Depends(require_technician),
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
    final_price = selling_price if selling_price > 0 else (part.wholesale_price if repair.order_type == "IR" else part.selling_price)
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
        "order_type": repair.order_type,
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
    return RepairPartResponse(
        id=repair_part.id, part_id=repair_part.part_id,
        qty=repair_part.qty, unit_price=repair_part.unit_price,
        selling_price=repair_part.selling_price,
        returned_qty=repair_part.returned_qty,
        part_name=(await db.execute(select(Part.name).where(Part.id == repair_part.part_id))).scalar() or "",
    )


# ---- Part Request / Fulfill workflow ----

@router.get("/{repair_id}/part-requests", response_model=list[PartRequestResponse])
async def list_part_requests(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(PartRequest).where(PartRequest.repair_id == repair_id)
        )
    ).scalars().all()
    part_ids = list(set(p.part_id for p in rows if p.part_id))
    part_map = {}
    if part_ids:
        pr = await db.execute(select(Part).where(Part.id.in_(part_ids)))
        part_map = {p.id: p.name for p in pr.scalars().all()}
    user_ids = set()
    for p in rows:
        if p.requested_by:
            user_ids.add(p.requested_by)
        if p.fulfilled_by:
            user_ids.add(p.fulfilled_by)
    user_map = {}
    if user_ids:
        ur = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        user_map = {u.id: u.name for u in ur.scalars().all()}
    return [
        PartRequestResponse(
            id=p.id, repair_id=p.repair_id, part_id=p.part_id,
            part_name=part_map.get(p.part_id) or "",
            requested_by=p.requested_by,
            requester_name=user_map.get(p.requested_by) or "",
            fulfilled_by=p.fulfilled_by,
            fulfiller_name=user_map.get(p.fulfilled_by) or "",
            quantity=p.quantity, status=p.status, notes=p.notes,
            created_at=p.created_at,
        )
        for p in rows
    ]


@router.post("/{repair_id}/part-requests", response_model=PartRequestResponse, status_code=201)
async def request_part(
    repair_id: int,
    data: PartRequestCreate,
    db=Depends(get_db),
    current_user=Depends(require_technician),
):
    repair = await db.get(Repair, repair_id)
    if not repair:
        raise HTTPException(404, detail="Repair not found")
    part = await db.get(Part, data.part_id)
    if not part:
        raise HTTPException(404, detail="Part not found")
    req = PartRequest(
        repair_id=repair_id, part_id=data.part_id,
        requested_by=current_user.id, quantity=data.quantity,
        notes=data.notes,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    await ws_manager.broadcast("part_requested", {
        "request_id": req.id,
        "repair_id": repair_id,
        "part_id": data.part_id,
        "part_name": part.name,
        "quantity": data.quantity,
        "requested_by": current_user.id,
    })
    return PartRequestResponse(
        id=req.id, repair_id=req.repair_id, part_id=req.part_id,
        part_name=part.name,
        requested_by=req.requested_by,
        requester_name=current_user.name,
        quantity=req.quantity, status=req.status, notes=req.notes,
        created_at=req.created_at,
    )


@router.post("/{repair_id}/part-requests/{request_id}/fulfill", response_model=PartRequestResponse)
async def fulfill_part_request(
    repair_id: int,
    request_id: int,
    data: PartRequestFulfill,
    db=Depends(get_db),
    current_user=Depends(require_warehouse),
):
    req = await db.get(PartRequest, request_id)
    if not req or req.repair_id != repair_id:
        raise HTTPException(404, detail="Part request not found")
    if req.status != "PENDING":
        raise HTTPException(400, detail="Part request is not pending")
    part = (await db.execute(select(Part).where(Part.id == req.part_id).with_for_update())).scalar_one_or_none()
    if not part:
        raise HTTPException(404, detail="Part not found")
    qty = data.quantity
    if part.stock_qty < qty:
        raise HTTPException(400, detail=f"Insufficient stock. Available: {part.stock_qty}")
    part.stock_qty -= qty
    req.fulfilled_by = current_user.id
    req.status = "FULFILLED"
    # Also add to repair_parts
    rp = RepairPart(
        repair_id=repair_id, part_id=req.part_id, qty=qty,
        unit_price=part.unit_price,
        selling_price=part.wholesale_price if part.wholesale_price > 0 else part.selling_price,
    )
    db.add(rp)
    await db.commit()
    await db.refresh(req)
    await ws_manager.broadcast("part_fulfilled", {
        "request_id": request_id,
        "repair_id": repair_id,
        "part_id": req.part_id,
        "part_name": part.name,
        "quantity": qty,
        "fulfilled_by": current_user.id,
    })
    return PartRequestResponse(
        id=req.id, repair_id=req.repair_id, part_id=req.part_id,
        part_name=part.name,
        requested_by=req.requested_by,
        requester_name=(await db.get(User, req.requested_by)).name if req.requested_by else "",
        fulfilled_by=req.fulfilled_by,
        fulfiller_name=current_user.name,
        quantity=req.quantity, status=req.status, notes=req.notes,
        created_at=req.created_at,
    )


@router.post("/{repair_id}/part-requests/{request_id}/deny", response_model=PartRequestResponse)
async def deny_part_request(
    repair_id: int,
    request_id: int,
    db=Depends(get_db),
    current_user=Depends(require_warehouse),
):
    req = await db.get(PartRequest, request_id)
    if not req or req.repair_id != repair_id:
        raise HTTPException(404, detail="Part request not found")
    if req.status != "PENDING":
        raise HTTPException(400, detail="Part request is not pending")
    req.status = "DENIED"
    await db.commit()
    return PartRequestResponse(
        id=req.id, repair_id=req.repair_id, part_id=req.part_id,
        part_name=(await db.get(Part, req.part_id)).name if req.part_id else "",
        requested_by=req.requested_by,
        requester_name=(await db.get(User, req.requested_by)).name if req.requested_by else "",
        quantity=req.quantity, status=req.status, notes=req.notes,
        created_at=req.created_at,
    )


@router.get("/{repair_id}/estimate")
async def generate_estimate(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")

    response = await build_repair_response(repair, db)
    data = await _build_invoice_data(repair, response, db, estimate=True)
    pdf_path = invoice_generator.generate_invoice(data, estimate=True)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"estimate_{repair_id}.pdf")


@router.get("/{repair_id}/invoice")
async def generate_invoice(
    repair_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repair not found")
    if repair.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice can only be generated for completed repairs",
        )

    response = await build_repair_response(repair, db)
    data = await _build_invoice_data(repair, response, db)
    pdf_path = invoice_generator.generate_invoice(data)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"invoice_{repair_id}.pdf")
