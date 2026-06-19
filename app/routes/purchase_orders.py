from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.purchase_order import (
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderReceipt,
    PurchaseOrderReceiptItem, PurchaseOrderDiscrepancy,
)
from app.models.part import Part
from app.schemas.purchase_order import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderItemResponse,
    POReceiptCreate, POReceiptItemUpdate, POReceiptResponse, PODiscrepancyResponse,
    PO_STATUSES, PO_VALID_TRANSITIONS,
)
from app.utils.auth import get_current_user
from app.utils.permissions import require_admin, require_warehouse, require_warehouse_or_admin, require_reception_or_admin
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


async def generate_po_number(db) -> str:
    result = await db.execute(select(sqlfunc.max(PurchaseOrder.id)))
    max_id = result.scalar() or 0
    return f"PO-{max_id + 1:04d}"


async def build_po_response(po: PurchaseOrder, db) -> PurchaseOrderResponse:
    from app.models.purchase_order import PurchaseOrderItem
    from app.models.supplier import Supplier
    from app.models.part import Part
    from app.models.user import User
    items = []
    total = 0
    po_items = (await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id))).scalars().all()
    part_ids = list(set(i.part_id for i in po_items if i.part_id))
    part_map = {}
    if part_ids:
        pr = await db.execute(select(Part).where(Part.id.in_(part_ids)))
        part_map = {p.id: p.name for p in pr.scalars().all()}
    for item in po_items:
        pname = part_map.get(item.part_id) or ""
        items.append(PurchaseOrderItemResponse(
            id=item.id, part_id=item.part_id, part_name=pname, sku=item.sku,
            qty_ordered=item.qty_ordered, qty_received=item.qty_received,
            cost_price=item.cost_price, invoice_price=item.invoice_price,
            selling_price=item.selling_price, status=item.part_status,
        ))
        total += item.cost_price * item.qty_ordered
    sup = await db.get(Supplier, po.supplier_id)
    creator = await db.get(User, po.created_by)
    return PurchaseOrderResponse(
        id=po.id, po_number=po.po_number, supplier_id=po.supplier_id,
        supplier_name=sup.name if sup else "",
        status=po.status, payment_type=po.payment_type, notes=po.notes,
        total_amount=total, created_by=po.created_by,
        creator_name=creator.name if creator else "",
        created_at=po.created_at, updated_at=po.updated_at, items=items,
    )


@router.get("", response_model=dict)
async def list_pos(
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    count_stmt = select(sqlfunc.count(PurchaseOrder.id))
    list_stmt = select(PurchaseOrder)
    if status_filter:
        count_stmt = count_stmt.where(PurchaseOrder.status == status_filter)
        list_stmt = list_stmt.where(PurchaseOrder.status == status_filter)
    if supplier_id:
        count_stmt = count_stmt.where(PurchaseOrder.supplier_id == supplier_id)
        list_stmt = list_stmt.where(PurchaseOrder.supplier_id == supplier_id)
    total = (await db.execute(count_stmt)).scalar() or 0
    pos = (
        (await db.execute(
            list_stmt.order_by(PurchaseOrder.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        ))
        .scalars()
        .all()
    )
    return {
        "items": [await build_po_response(po, db) for po in pos],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_po(data: PurchaseOrderCreate, db=Depends(get_db), current_user=Depends(require_warehouse_or_admin)):
    po = PurchaseOrder(
        po_number=await generate_po_number(db),
        supplier_id=data.supplier_id, payment_type=data.payment_type,
        notes=data.notes, created_by=current_user.id,
    )
    db.add(po)
    await db.flush()
    for item_data in data.items:
        sku = item_data.sku
        if item_data.part_id:
            part = (await db.execute(select(Part).where(Part.id == item_data.part_id))).scalar_one_or_none()
            if part:
                sku = sku or part.sku or ""
        db.add(PurchaseOrderItem(
            po_id=po.id, part_id=item_data.part_id, sku=sku,
            qty_ordered=item_data.qty_ordered, cost_price=item_data.cost_price,
            selling_price=item_data.selling_price,
        ))
    await db.commit()
    await db.refresh(po)
    await ws_manager.broadcast("po_created", {
        "po_id": po.id,
        "po_number": po.po_number,
        "supplier_id": po.supplier_id,
        "status": po.status,
        "created_by": current_user.id,
    })
    return await build_po_response(po, db)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_po(po_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return await build_po_response(po, db)


@router.put("/{po_id}/status", response_model=PurchaseOrderResponse)
async def update_po_status(
    po_id: int,
    data: dict,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    new_status = data.get("status", "")
    if new_status not in PO_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(PO_STATUSES)}")
    allowed = PO_VALID_TRANSITIONS.get(po.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from '{po.status}' to '{new_status}'",
        )
    old_status = po.status
    po.status = new_status
    await db.commit()
    await db.refresh(po)
    await ws_manager.broadcast("po_status_changed", {
        "po_id": po.id,
        "po_number": po.po_number,
        "old_status": old_status,
        "new_status": po.status,
        "changed_by": current_user.id,
    })
    return await build_po_response(po, db)


@router.post("/{po_id}/receive", response_model=dict, status_code=status.HTTP_201_CREATED)
async def receive_shipment(po_id: int, data: POReceiptCreate, db=Depends(get_db), current_user=Depends(require_warehouse_or_admin)):
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status in ("cancelled", "closed"):
        raise HTTPException(status_code=400, detail="Cannot receive items for cancelled/closed PO")

    receipt = PurchaseOrderReceipt(
        po_id=po_id, invoice_number=data.invoice_number,
        invoice_date=data.invoice_date, notes=data.notes,
        received_by=current_user.id,
    )
    db.add(receipt)
    await db.flush()

    all_received = True
    for item_data in data.items:
        po_item = (await db.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.id == item_data.po_item_id,
                PurchaseOrderItem.po_id == po_id,
            )
        )).scalar_one_or_none()
        if not po_item:
            continue

        qty_recv = item_data.qty_received
        invoice_cost = item_data.cost_price

        db.add(PurchaseOrderReceiptItem(
            receipt_id=receipt.id, po_item_id=po_item.id,
            qty_received=qty_recv, cost_price=invoice_cost,
        ))

        qty_diff = qty_recv - po_item.qty_ordered
        cost_diff = invoice_cost - po_item.cost_price

        if qty_diff != 0:
            db.add(PurchaseOrderDiscrepancy(
                po_id=po_id, po_item_id=po_item.id,
                field="qty", expected=float(po_item.qty_ordered), actual=float(qty_recv),
                note=f"Expected {po_item.qty_ordered}, received {qty_recv}",
            ))
        if cost_diff != 0:
            db.add(PurchaseOrderDiscrepancy(
                po_id=po_id, po_item_id=po_item.id,
                field="cost", expected=po_item.cost_price, actual=invoice_cost,
                note=f"Expected cost {po_item.cost_price}, invoice cost {invoice_cost}",
            ))

        po_item.qty_received += qty_recv
        po_item.invoice_price = invoice_cost

        if po_item.qty_received >= po_item.qty_ordered:
            po_item.part_status = "received"
        elif po_item.qty_received > 0:
            po_item.part_status = "partial"
        else:
            all_received = False

        if qty_recv > 0 and po_item.part_id:
            part = (await db.execute(select(Part).where(Part.id == po_item.part_id).with_for_update())).scalar_one_or_none()
            if part:
                part.stock_qty += qty_recv
                if invoice_cost > 0:
                    part.unit_price = invoice_cost
                if po_item.selling_price > 0:
                    part.selling_price = po_item.selling_price

    po.status = "received" if all_received else "partially_received"
    await db.commit()
    await db.refresh(receipt)
    await ws_manager.broadcast("po_received", {
        "po_id": po.id,
        "po_number": po.po_number,
        "receipt_id": receipt.id,
        "invoice_number": receipt.invoice_number,
        "status": po.status,
        "received_by": current_user.id,
    })
    return {
        "receipt_id": receipt.id,
        "invoice_number": receipt.invoice_number,
        "message": "Shipment received successfully. Stock updated.",
    }


@router.get("/{po_id}/receipts", response_model=list[dict])
async def list_receipts(po_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        await db.execute(
            select(PurchaseOrderReceipt)
            .where(PurchaseOrderReceipt.po_id == po_id)
            .order_by(PurchaseOrderReceipt.created_at.desc())
        )
    ).scalars().all()
    from app.models.user import User
    user_ids = list(set(r.received_by for r in rows if r.received_by))
    user_map = {}
    if user_ids:
        ur = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u.name for u in ur.scalars().all()}
    return [
        {
            "id": r.id, "invoice_number": r.invoice_number,
            "invoice_date": r.invoice_date, "notes": r.notes,
            "received_by": r.received_by,
            "receiver_name": user_map.get(r.received_by) or "",
            "created_at": str(r.created_at) if r.created_at else "",
        }
        for r in rows
    ]


@router.get("/{po_id}/discrepancies", response_model=list[dict])
async def list_discrepancies(po_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        await db.execute(
            select(PurchaseOrderDiscrepancy)
            .where(PurchaseOrderDiscrepancy.po_id == po_id)
        )
    ).scalars().all()
    return [
        {
            "id": d.id, "po_item_id": d.po_item_id, "field": d.field,
            "expected": d.expected, "actual": d.actual, "note": d.note,
            "created_at": str(d.created_at) if d.created_at else "",
        }
        for d in rows
    ]
