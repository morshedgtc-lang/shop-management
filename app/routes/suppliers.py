from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierResponse, SupplierDetailResponse,
    SupplierPaymentCreate, SupplierPaymentResponse,
)
from app.utils.auth import get_current_user, require_admin, require_reseller_or_admin

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=dict)
async def list_suppliers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    count_stmt = select(sqlfunc.count(Supplier.id))
    list_stmt = select(Supplier)
    if search:
        term = f"%{search}%"
        count_stmt = count_stmt.where((Supplier.name.ilike(term)) | (Supplier.phone.ilike(term)))
        list_stmt = list_stmt.where((Supplier.name.ilike(term)) | (Supplier.phone.ilike(term)))
    total = (await db.execute(count_stmt)).scalar() or 0
    suppliers = (await db.execute(list_stmt.offset((page - 1) * limit).limit(limit))).scalars().all()

    items = []
    for s in suppliers:
        # Aggregate credit purchase totals
        credit_pos = (
            await db.execute(
                select(PurchaseOrderItem.cost_price, PurchaseOrderItem.qty_ordered)
                .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
                .where(
                    PurchaseOrder.supplier_id == s.id,
                    PurchaseOrder.payment_type == "credit",
                )
            )
        ).all()
        total_purchases = sum(row.cost_price * row.qty_ordered for row in credit_pos)

        total_paid = (
            await db.execute(
                select(sqlfunc.coalesce(sqlfunc.sum(SupplierPayment.amount), 0))
                .where(SupplierPayment.supplier_id == s.id)
            )
        ).scalar() or 0

        items.append(SupplierDetailResponse(
            id=s.id, name=s.name, phone=s.phone, address=s.address,
            notes=s.notes, created_at=s.created_at,
            total_purchases=total_purchases,
            total_paid=float(total_paid),
            balance=total_purchases - float(total_paid),
        ))
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(data: SupplierCreate, db=Depends(get_db), current_user=Depends(require_reseller_or_admin)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierDetailResponse)
async def get_supplier(supplier_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")

    credit_pos = (
        await db.execute(
            select(PurchaseOrderItem.cost_price, PurchaseOrderItem.qty_ordered)
            .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
            .where(PurchaseOrder.supplier_id == s.id, PurchaseOrder.payment_type == "credit")
        )
    ).all()
    total_purchases = sum(row.cost_price * row.qty_ordered for row in credit_pos)

    total_paid = (
        await db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(SupplierPayment.amount), 0))
            .where(SupplierPayment.supplier_id == s.id)
        )
    ).scalar() or 0

    return SupplierDetailResponse(
        id=s.id, name=s.name, phone=s.phone, address=s.address,
        notes=s.notes, created_at=s.created_at,
        total_purchases=total_purchases, total_paid=float(total_paid),
        balance=total_purchases - float(total_paid),
    )


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(supplier_id: int, data: SupplierUpdate, db=Depends(get_db), current_user=Depends(require_reseller_or_admin)):
    supplier = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(supplier_id: int, db=Depends(get_db), current_user=Depends(require_admin)):
    supplier = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await db.delete(supplier)
    await db.commit()


@router.get("/{supplier_id}/payments", response_model=list[SupplierPaymentResponse])
async def list_supplier_payments(supplier_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        await db.execute(
            select(SupplierPayment)
            .where(SupplierPayment.supplier_id == supplier_id)
            .order_by(SupplierPayment.created_at.desc())
        )
    ).scalars().all()
    return rows


@router.post("/{supplier_id}/payments", response_model=SupplierPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_payment(supplier_id: int, data: SupplierPaymentCreate, db=Depends(get_db), current_user=Depends(require_reseller_or_admin)):
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    payment = SupplierPayment(
        supplier_id=supplier_id, amount=data.amount,
        method=data.method, date=data.date, notes=data.notes,
        created_by=current_user.id,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/{supplier_id}/purchases", response_model=list[dict])
async def list_supplier_purchases(supplier_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    pos = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.supplier_id == supplier_id)
            .order_by(PurchaseOrder.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": po.id, "po_number": po.po_number, "status": po.status,
            "payment_type": po.payment_type, "total_amount": po.total_amount,
            "date": str(po.created_at) if po.created_at else "",
        }
        for po in pos
    ]
