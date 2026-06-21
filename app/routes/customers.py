from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.customer import Customer
from app.models.repair import Repair
from app.models.user import User
from app.models.payment import Payment
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.repair import RepairResponse
from app.utils.auth import get_current_user
from app.utils.permissions import require_admin

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=dict)
async def list_customers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = []
    if search:
        term = f"%{search}%"
        filters.append(
            (Customer.name.ilike(term)) | (Customer.phone.ilike(term)) | (Customer.email.ilike(term))
        )
    total = (await db.execute(select(sqlfunc.count(Customer.id)).where(*filters))).scalar() or 0
    customers = (
        (await db.execute(select(Customer).where(*filters).offset((page - 1) * limit).limit(limit)))
        .scalars()
        .all()
    )
    return {
        "items": [CustomerResponse.model_validate(c) for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    customer = Customer(**data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    await db.delete(customer)
    await db.commit()


@router.get("/{customer_id}/repairs", response_model=list[RepairResponse])
async def get_customer_repairs(
    customer_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    repairs_result = await db.execute(
        select(Repair).where(Repair.customer_id == customer_id)
    )
    repairs = repairs_result.scalars().all()

    from app.models.repair_part import RepairPart

    user_ids = set()
    for r in repairs:
        if r.assigned_to:
            user_ids.add(r.assigned_to)
        if r.created_by:
            user_ids.add(r.created_by)
    user_map = {}
    if user_ids:
        users = (await db.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
        user_map = {u.id: u.name for u in users}

    repair_ids = [r.id for r in repairs]
    rps_list = (await db.execute(select(RepairPart).where(RepairPart.repair_id.in_(repair_ids)))).scalars().all()
    parts_by_repair = {}
    for rp in rps_list:
        parts_by_repair.setdefault(rp.repair_id, []).append(rp)

    pay_rows = (await db.execute(select(Payment).where(Payment.repair_id.in_(repair_ids)))).scalars().all()
    pay_by_repair = {}
    for p in pay_rows:
        pay_by_repair.setdefault(p.repair_id, []).append(p)

    items = []
    for r in repairs:
        customer_name = (await db.get(Customer, r.customer_id)).name if r.customer_id else ""
        assigned_name = user_map.get(r.assigned_to, "")
        creator_name = user_map.get(r.created_by, "")

        rps = parts_by_repair.get(r.id, [])
        total_parts_cost = sum(rp.qty * rp.selling_price for rp in rps)

        pays = pay_by_repair.get(r.id, [])
        total_payments = sum(p.amount for p in pays)

        items.append(
            RepairResponse(
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
                service_fee=r.service_fee or 0,
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
                total_parts_cost=total_parts_cost,
                total_payments=total_payments,
                balance=(total_parts_cost + (r.service_fee or 0)) - total_payments,
            )
        )
    return items
