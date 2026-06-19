from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.customer import Customer
from app.models.repair import Repair
from app.models.payment import Payment
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.repair import RepairResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=dict)
async def list_customers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Customer)
    if search:
        term = f"%{search}%"
        query = query.where(
            (Customer.name.ilike(term))
            | (Customer.phone.ilike(term))
            | (Customer.email.ilike(term))
        )
    total = (await db.execute(select(sqlfunc.count()).select_from(Customer).where(query.whereclause) if search else select(sqlfunc.count()).select_from(Customer))).scalar() or 0

    # Simplified: count first then paginate
    count_query = select(sqlfunc.count(Customer.id))
    if search:
        term = f"%{search}%"
        count_query = count_query.where(
            (Customer.name.ilike(term)) | (Customer.phone.ilike(term)) | (Customer.email.ilike(term))
        )
    total = (await db.execute(count_query)).scalar() or 0

    list_query = select(Customer)
    if search:
        term = f"%{search}%"
        list_query = list_query.where(
            (Customer.name.ilike(term)) | (Customer.phone.ilike(term)) | (Customer.email.ilike(term))
        )
    customers = (
        (await db.execute(list_query.offset((page - 1) * limit).limit(limit)))
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
    from app.models.part import Part
    items = []
    for r in repairs:
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
