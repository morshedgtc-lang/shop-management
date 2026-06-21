from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select

from app.database import get_db
from app.models.part import Part
from app.utils.permissions import require_warehouse_or_admin
from app.utils.ocr_engine import ocr_engine

router = APIRouter(prefix="/api/inventory/bulk", tags=["inventory-bulk"])


@router.post("/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    content = await file.read()
    try:
        draft_items = await ocr_engine.process_invoice(content)
    except Exception as e:
        raise HTTPException(400, detail=f"OCR processing failed: {str(e)}")
    return {"draft": draft_items, "count": len(draft_items)}


@router.post("/commit", response_model=dict)
async def commit_draft(
    data: dict,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    items = data.get("items", [])
    if not items:
        raise HTTPException(400, detail="No items to commit")
    created = []
    for item in items:
        existing = None
        if item.get("sku"):
            result = await db.execute(select(Part).where(Part.sku == item["sku"]))
            existing = result.scalar_one_or_none()
        if existing:
            existing.stock_qty += int(item.get("stock_qty", 1))
            created.append({"id": existing.id, "name": existing.name, "updated": True})
        else:
            part = Part(
                name=item.get("name", ""),
                model=item.get("model", ""),
                sku=item.get("sku", ""),
                supplier_barcode=item.get("supplier_barcode", ""),
                stock_qty=int(item.get("stock_qty", 1)),
                unit_price=float(item.get("unit_price", 0)),
                selling_price=float(item.get("selling_price", 0)),
                wholesale_price=float(item.get("wholesale_price", 0)),
                box_number=item.get("box_number", ""),
                shelf_number=item.get("shelf_number", ""),
            )
            db.add(part)
            await db.flush()
            created.append({"id": part.id, "name": part.name, "updated": False})
    await db.commit()
    return {"created": len(created), "items": created}
