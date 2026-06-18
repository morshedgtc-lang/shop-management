from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.purchase_order import (
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderReceipt,
    PurchaseOrderReceiptItem, PurchaseOrderDiscrepancy,
)
from app.models.part import Part
from app.models.user import User
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.schemas.purchase_order import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderItemResponse,
    POReceiptCreate, POReceiptResponse,
)
from app.utils.auth import get_current_user, require_manager_or_admin

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


def generate_po_number(db: Session) -> str:
    last = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"PO-{num:04d}"


def build_po_response(po: PurchaseOrder, db: Session) -> PurchaseOrderResponse:
    items = []
    total = 0
    for item in po.items:
        pname = item.part.name if item.part else ""
        items.append(PurchaseOrderItemResponse(
            id=item.id, part_id=item.part_id, part_name=pname, sku=item.sku,
            qty_ordered=item.qty_ordered, qty_received=item.qty_received,
            cost_price=item.cost_price, invoice_price=item.invoice_price,
            selling_price=item.selling_price, status=item.part_status,
        ))
        total += item.cost_price * item.qty_ordered
    return PurchaseOrderResponse(
        id=po.id, po_number=po.po_number, supplier_id=po.supplier_id,
        supplier_name=po.supplier.name if po.supplier else "",
        status=po.status, payment_type=po.payment_type, notes=po.notes,
        total_amount=total, created_by=po.created_by,
        creator_name=po.creator.name if po.creator else "",
        created_at=po.created_at, updated_at=po.updated_at, items=items,
    )


@router.get("", response_model=dict)
def list_pos(
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PurchaseOrder)
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    total = query.count()
    pos = query.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [build_po_response(po, db) for po in pos],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_po(data: PurchaseOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    po = PurchaseOrder(
        po_number=generate_po_number(db),
        supplier_id=data.supplier_id,
        payment_type=data.payment_type,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(po)
    db.flush()
    for item_data in data.items:
        sku = item_data.sku
        if item_data.part_id:
            part = db.query(Part).filter(Part.id == item_data.part_id).first()
            if part:
                sku = sku or part.sku or ""
        poi = PurchaseOrderItem(
            po_id=po.id,
            part_id=item_data.part_id,
            sku=sku,
            qty_ordered=item_data.qty_ordered,
            cost_price=item_data.cost_price,
            selling_price=item_data.selling_price,
        )
        db.add(poi)
    db.commit()
    db.refresh(po)
    return build_po_response(po, db)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_po(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return build_po_response(po, db)


@router.put("/{po_id}/status", response_model=PurchaseOrderResponse)
def update_po_status(po_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    new_status = data.get("status", "")
    valid = ["draft", "sent", "partially_received", "received", "closed", "cancelled"]
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")
    if po.status == "closed" or po.status == "cancelled":
        raise HTTPException(status_code=400, detail=f"Cannot change status of {po.status} PO")
    po.status = new_status
    db.commit()
    db.refresh(po)
    return build_po_response(po, db)


@router.post("/{po_id}/receive", response_model=dict, status_code=status.HTTP_201_CREATED)
def receive_shipment(po_id: int, data: POReceiptCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status in ["cancelled", "closed"]:
        raise HTTPException(status_code=400, detail="Cannot receive items for cancelled/closed PO")

    receipt = PurchaseOrderReceipt(
        po_id=po_id,
        invoice_number=data.invoice_number,
        invoice_date=data.invoice_date,
        notes=data.notes,
        received_by=current_user.id,
    )
    db.add(receipt)
    db.flush()

    all_received = True
    for item_data in data.items:
        po_item = db.query(PurchaseOrderItem).filter(
            PurchaseOrderItem.id == item_data.get("po_item_id"),
            PurchaseOrderItem.po_id == po_id,
        ).first()
        if not po_item:
            continue

        qty_recv = item_data.get("qty_received", 0)
        invoice_cost = item_data.get("cost_price", po_item.cost_price)

        receipt_item = PurchaseOrderReceiptItem(
            receipt_id=receipt.id,
            po_item_id=po_item.id,
            qty_received=qty_recv,
            cost_price=invoice_cost,
        )
        db.add(receipt_item)

        qty_diff = qty_recv - po_item.qty_ordered
        cost_diff = invoice_cost - po_item.cost_price

        if qty_diff != 0:
            disc = PurchaseOrderDiscrepancy(
                po_id=po_id, po_item_id=po_item.id,
                field="qty", expected=po_item.qty_ordered, actual=qty_recv,
                note=f"Expected {po_item.qty_ordered}, received {qty_recv}",
            )
            db.add(disc)

        if cost_diff != 0:
            disc = PurchaseOrderDiscrepancy(
                po_id=po_id, po_item_id=po_item.id,
                field="cost", expected=po_item.cost_price, actual=invoice_cost,
                note=f"Expected cost {po_item.cost_price}, invoice cost {invoice_cost}",
            )
            db.add(disc)

        po_item.qty_received += qty_recv
        po_item.invoice_price = invoice_cost

        if po_item.qty_received >= po_item.qty_ordered:
            po_item.part_status = "received"
        elif po_item.qty_received > 0:
            po_item.part_status = "partial"
        else:
            all_received = False

        if qty_recv > 0 and po_item.part_id:
            part = db.query(Part).filter(Part.id == po_item.part_id).first()
            if part:
                part.stock_qty += qty_recv
                if invoice_cost > 0:
                    part.unit_price = invoice_cost
                if po_item.selling_price > 0:
                    part.selling_price = po_item.selling_price

    if all_received:
        po.status = "received"
    else:
        po.status = "partially_received"

    db.commit()
    db.refresh(receipt)

    return {
        "receipt_id": receipt.id,
        "invoice_number": receipt.invoice_number,
        "message": "Shipment received successfully. Stock updated.",
    }


@router.get("/{po_id}/receipts", response_model=list[dict])
def list_receipts(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    receipts = db.query(PurchaseOrderReceipt).filter(PurchaseOrderReceipt.po_id == po_id).order_by(PurchaseOrderReceipt.created_at.desc()).all()
    return [
        {"id": r.id, "invoice_number": r.invoice_number, "invoice_date": r.invoice_date,
         "notes": r.notes, "received_by": r.received_by,
         "receiver_name": r.receiver.name if r.receiver else "",
         "created_at": str(r.created_at) if r.created_at else ""}
        for r in receipts
    ]


@router.get("/{po_id}/discrepancies", response_model=list[dict])
def list_discrepancies(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    discs = db.query(PurchaseOrderDiscrepancy).filter(PurchaseOrderDiscrepancy.po_id == po_id).all()
    return [
        {"id": d.id, "po_item_id": d.po_item_id, "field": d.field,
         "expected": d.expected, "actual": d.actual, "note": d.note,
         "created_at": str(d.created_at) if d.created_at else ""}
        for d in discs
    ]
