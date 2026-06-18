from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.customer import Customer
from app.models.repair import Repair
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.repair import RepairResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/", response_model=dict)
def list_customers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Customer)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(search_term))
            | (Customer.phone.ilike(search_term))
            | (Customer.email.ilike(search_term))
        )
    total = query.count()
    customers = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [CustomerResponse.model_validate(c) for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    db.delete(customer)
    db.commit()


@router.get("/{customer_id}/repairs", response_model=list[RepairResponse])
def get_customer_repairs(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    repairs = db.query(Repair).filter(Repair.customer_id == customer_id).all()
    result = []
    for r in repairs:
        customer_name = r.customer.name if r.customer else ""
        assigned_name = r.assigned_user.name if r.assigned_user else ""
        creator_name = r.creator.name if r.creator else ""
        total_parts_cost = sum(
            rp.qty * rp.unit_price for rp in r.repair_parts
        )
        total_payments = sum(p.amount for p in r.payments if hasattr(r, "payments"))
        from app.models.payment import Payment

        total_payments = (
            db.query(Payment).filter(Payment.repair_id == r.id).with_entities(Payment.amount).all()
        )
        total_payments = sum(p[0] for p in total_payments)

        result.append(
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
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
                total_parts_cost=total_parts_cost,
                total_payments=total_payments,
                balance=r.actual_cost - total_payments,
            )
        )
    return result
