from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.collection_run import CollectionRun
from app.models.collection_item import CollectionItem
from app.models.repair import Repair
from app.models.customer import Customer
from app.models.intermediate_shop import IntermediateShop
from app.models.user import User
from app.models.payment import Payment
from app.models.repair_part import RepairPart
from app.schemas.collection import (
    CollectionRunCreate, CollectionRunResponse, CollectionItemResponse,
    CollectionItemCreate, PendingCollectionResponse, ShopSummaryResponse,
)
from app.utils.auth import get_current_user
from app.utils.permissions import require_warehouse_or_admin

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("/pending", response_model=list[PendingCollectionResponse])
async def list_pending_collections(
    shop_id: Optional[int] = Query(None),
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    query = select(Repair).where(
        Repair.status == "COMPLETED",
        Repair.order_type == "IR",
        Repair.payment_status == "UNPAID",
    )
    if shop_id:
        query = query.where(Repair.intermediate_shop_id == shop_id)
    rows = (await db.execute(query.order_by(Repair.created_at.desc()))).scalars().all()

    result = []
    for r in rows:
        rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == r.id))).scalars().all()
        parts_cost = sum(rp.qty * rp.unit_price for rp in rps)
        result.append(PendingCollectionResponse(
            repair_id=r.id,
            customer_name="",
            model=r.model,
            total_amount=parts_cost + (r.service_fee or 0),
            parts_cost=parts_cost,
            service_fee=r.service_fee or 0,
            created_at=r.created_at,
        ))
    return result


@router.post("/runs", response_model=CollectionRunResponse, status_code=201)
async def create_collection_run(
    data: CollectionRunCreate,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = await db.get(IntermediateShop, data.shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")

    run = CollectionRun(
        shop_id=data.shop_id,
        collected_by=current_user.id,
        notes=data.notes,
    )
    db.add(run)
    await db.flush()

    total = 0
    items = []
    for item_data in data.items:
        repair = await db.get(Repair, item_data.repair_id)
        if not repair or repair.intermediate_shop_id != data.shop_id:
            continue
        if repair.payment_status == "PAID":
            continue

        # Create collection item
        ci = CollectionItem(
            collection_run_id=run.id,
            repair_id=item_data.repair_id,
            amount_paid=item_data.amount_paid,
            discount_amount=item_data.discount_amount,
        )
        db.add(ci)

        # Create a payment record for the repair
        rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == repair.id))).scalars().all()
        parts_cost = sum(rp.qty * rp.unit_price for rp in rps)
        expected = parts_cost + (repair.service_fee or 0)
        collected = item_data.amount_paid

        payment = Payment(
            repair_id=item_data.repair_id,
            amount=collected,
            currency="USD",
            method="Cash",
            notes=f"Collection run #{run.id} (discount: {item_data.discount_amount:.2f})",
            created_by=current_user.id,
        )
        db.add(payment)

        # Check if fully paid
        total_paid_result = await db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0)).where(
                Payment.repair_id == item_data.repair_id
            )
        )
        total_paid = float(total_paid_result.scalar() or 0)
        if total_paid >= expected:
            repair.payment_status = "PAID"

        total += collected
        items.append(ci)

    run.total_collected = total
    await db.commit()
    await db.refresh(run)

    item_responses = []
    for ci in items:
        rep = await db.get(Repair, ci.repair_id)
        item_responses.append(CollectionItemResponse(
            id=ci.id, collection_run_id=ci.collection_run_id,
            repair_id=ci.repair_id, amount_paid=ci.amount_paid,
            discount_amount=ci.discount_amount,
            repair_model=rep.model if rep else "",
            repair_status=rep.status if rep else "",
            created_at=ci.created_at,
        ))

    collector = await db.get(User, current_user.id)
    return CollectionRunResponse(
        id=run.id, shop_id=run.shop_id, shop_name=shop.name,
        collected_by=run.collected_by,
        collector_name=collector.name if collector else "",
        total_collected=run.total_collected,
        notes=run.notes, collected_at=run.collected_at,
        items=item_responses,
    )


@router.get("/runs", response_model=list[CollectionRunResponse])
async def list_collection_runs(
    shop_id: Optional[int] = Query(None),
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    query = select(CollectionRun)
    if shop_id:
        query = query.where(CollectionRun.shop_id == shop_id)
    rows = (await db.execute(query.order_by(CollectionRun.collected_at.desc()))).scalars().all()

    result = []
    for run in rows:
        shop = await db.get(IntermediateShop, run.shop_id)
        collector = await db.get(User, run.collected_by)
        items = (await db.execute(
            select(CollectionItem).where(CollectionItem.collection_run_id == run.id)
        )).scalars().all()
        item_responses = []
        for ci in items:
            rep = await db.get(Repair, ci.repair_id)
            item_responses.append(CollectionItemResponse(
                id=ci.id, collection_run_id=ci.collection_run_id,
                repair_id=ci.repair_id, amount_paid=ci.amount_paid,
                discount_amount=ci.discount_amount,
                repair_model=rep.model if rep else "",
                repair_status=rep.status if rep else "",
                created_at=ci.created_at,
            ))
        result.append(CollectionRunResponse(
            id=run.id, shop_id=run.shop_id, shop_name=shop.name if shop else "",
            collected_by=run.collected_by,
            collector_name=collector.name if collector else "",
            total_collected=run.total_collected,
            notes=run.notes, collected_at=run.collected_at,
            items=item_responses,
        ))
    return result


@router.get("/summary", response_model=ShopSummaryResponse)
async def collection_summary(
    shop_id: int = Query(...),
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    shop = await db.get(IntermediateShop, shop_id)
    if not shop:
        raise HTTPException(404, detail="Shop not found")

    pending_repairs = (await db.execute(
        select(Repair).where(
            Repair.status == "COMPLETED",
            Repair.order_type == "IR",
            Repair.intermediate_shop_id == shop_id,
            Repair.payment_status == "UNPAID",
        )
    )).scalars().all()

    total_pending = 0
    for r in pending_repairs:
        rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id == r.id))).scalars().all()
        parts_cost = sum(rp.qty * rp.unit_price for rp in rps)
        total_pending += parts_cost + (r.service_fee or 0)

    total_collected_result = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(CollectionRun.total_collected), 0)).where(
            CollectionRun.shop_id == shop_id
        )
    )
    total_collected = float(total_collected_result.scalar() or 0)

    return ShopSummaryResponse(
        shop_id=shop_id, shop_name=shop.name,
        total_pending=total_pending,
        total_collected=total_collected,
        pending_count=len(pending_repairs),
    )
