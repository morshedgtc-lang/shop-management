from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierResponse, SupplierDetailResponse,
    SupplierPaymentCreate, SupplierPaymentResponse,
)
from app.utils.auth import get_current_user, require_admin, require_manager_or_admin

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=dict)
def list_suppliers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Supplier)
    if search:
        term = f"%{search}%"
        query = query.filter((Supplier.name.ilike(term)) | (Supplier.phone.ilike(term)))
    total = query.count()
    suppliers = query.offset((page - 1) * limit).limit(limit).all()
    items = []
    for s in suppliers:
        credit_pos = db.query(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == s.id, PurchaseOrder.payment_type == "credit"
        ).all()
        total_purchases = 0
        for po in credit_pos:
            for item in db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po.id).all():
                total_purchases += item.cost_price * item.qty_ordered
        total_paid = db.query(sqlfunc.coalesce(sqlfunc.sum(SupplierPayment.amount), 0)).filter(
            SupplierPayment.supplier_id == s.id
        ).scalar()
        resp = SupplierDetailResponse(
            id=s.id, name=s.name, phone=s.phone, address=s.address, notes=s.notes,
            created_at=s.created_at,
            total_purchases=total_purchases,
            total_paid=float(total_paid or 0),
            balance=total_purchases - float(total_paid or 0),
        )
        items.append(resp)
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierDetailResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    credit_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.supplier_id == s.id, PurchaseOrder.payment_type == "credit"
    ).all()
    total_purchases = 0
    for po in credit_pos:
        for item in db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po.id).all():
            total_purchases += item.cost_price * item.qty_ordered
    total_paid = db.query(sqlfunc.coalesce(sqlfunc.sum(SupplierPayment.amount), 0)).filter(
        SupplierPayment.supplier_id == s.id
    ).scalar()
    return SupplierDetailResponse(
        id=s.id, name=s.name, phone=s.phone, address=s.address, notes=s.notes,
        created_at=s.created_at,
        total_purchases=total_purchases,
        total_paid=float(total_paid or 0),
        balance=total_purchases - float(total_paid or 0),
    )


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(supplier)
    db.commit()


# === SUPPLIER PAYMENTS ===

@router.get("/{supplier_id}/payments", response_model=list[SupplierPaymentResponse])
def list_supplier_payments(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(SupplierPayment).filter(SupplierPayment.supplier_id == supplier_id).order_by(SupplierPayment.created_at.desc()).all()


@router.post("/{supplier_id}/payments", response_model=SupplierPaymentResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_payment(supplier_id: int, data: SupplierPaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    payment = SupplierPayment(
        supplier_id=supplier_id,
        amount=data.amount,
        method=data.method,
        date=data.date,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{supplier_id}/purchases", response_model=list[dict])
def list_supplier_purchases(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.supplier_id == supplier_id).order_by(PurchaseOrder.created_at.desc()).all()
    return [
        {"id": po.id, "po_number": po.po_number, "status": po.status, "payment_type": po.payment_type,
         "total_amount": po.total_amount, "date": str(po.created_at) if po.created_at else ""}
        for po in pos
    ]
