from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sqlfunc
from typing import Optional

from app.database import get_db
from app.models.collection_run import CollectionRun
from app.models.collection_item import CollectionItem
from app.models.repair import Repair
from app.models.intermediate_shop import IntermediateShop
from app.models.user import User
from app.models.payment import Payment
from app.models.repair_part import RepairPart
from app.schemas.collection import (
    CollectionRunCreate, CollectionRunResponse, CollectionItemResponse,
    PendingCollectionResponse, ShopSummaryResponse,
)
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
    rep_ids = [r.id for r in rows]
    if rep_ids:
        all_rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id.in_(rep_ids)))).scalars().all()
        rps_by_repair = {}
        for rp in all_rps:
            rps_by_repair.setdefault(rp.repair_id, []).append(rp)
        for r in rows:
            rps = rps_by_repair.get(r.id, [])
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

    item_repair_ids = [item_data.repair_id for item_data in data.items]
    all_repairs = {}
    if item_repair_ids:
        reps = (await db.execute(select(Repair).where(Repair.id.in_(item_repair_ids)))).scalars().all()
        all_repairs = {r.id: r for r in reps}

    rep_part_ids = [r.id for r in all_repairs.values()]
    rps_by_repair = {}
    if rep_part_ids:
        all_rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id.in_(rep_part_ids)))).scalars().all()
        for rp in all_rps:
            rps_by_repair.setdefault(rp.repair_id, []).append(rp)

    existing_paid = {}
    if rep_part_ids:
        pay_rows = (await db.execute(
            select(Payment.repair_id, sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0))
            .where(Payment.repair_id.in_(rep_part_ids))
            .group_by(Payment.repair_id)
        )).all()
        for row in pay_rows:
            existing_paid[row.repair_id] = float(row[1])

    for item_data in data.items:
        repair = all_repairs.get(item_data.repair_id)
        if not repair or repair.intermediate_shop_id != data.shop_id:
            continue
        if repair.payment_status == "PAID":
            continue

        ci = CollectionItem(
            collection_run_id=run.id,
            repair_id=item_data.repair_id,
            amount_paid=item_data.amount_paid,
            discount_amount=item_data.discount_amount,
        )
        db.add(ci)

        rps = rps_by_repair.get(repair.id, [])
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

        total_paid = existing_paid.get(repair.id, 0) + collected
        existing_paid[repair.id] = total_paid
        if total_paid >= expected:
            repair.payment_status = "PAID"

        total += collected
        items.append(ci)

    run.total_collected = total
    await db.commit()
    await db.refresh(run)

    item_responses = []
    repair_ids = [ci.repair_id for ci in items]
    repairs_map = {}
    if repair_ids:
        reps = (await db.execute(select(Repair).where(Repair.id.in_(repair_ids)))).scalars().all()
        repairs_map = {r.id: r for r in reps}
    for ci in items:
        rep = repairs_map.get(ci.repair_id)
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
    run_ids = [run.id for run in rows]
    shop_ids = list(set(run.shop_id for run in rows))
    user_ids = list(set(run.collected_by for run in rows))

    shops = {}
    if shop_ids:
        s = (await db.execute(select(IntermediateShop).where(IntermediateShop.id.in_(shop_ids)))).scalars().all()
        shops = {x.id: x for x in s}
    users = {}
    if user_ids:
        u = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users = {x.id: x for x in u}

    all_items = (await db.execute(select(CollectionItem).where(CollectionItem.collection_run_id.in_(run_ids)))).scalars().all()
    items_by_run = {}
    for ci in all_items:
        items_by_run.setdefault(ci.collection_run_id, []).append(ci)

    rep_ids = list(set(ci.repair_id for ci in all_items))
    repairs = {}
    if rep_ids:
        r = (await db.execute(select(Repair).where(Repair.id.in_(rep_ids)))).scalars().all()
        repairs = {x.id: x for x in r}

    for run in rows:
        items = items_by_run.get(run.id, [])
        shop = shops.get(run.shop_id)
        collector = users.get(run.collected_by)
        item_responses = []
        for ci in items:
            rep = repairs.get(ci.repair_id)
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
    rep_ids = [r.id for r in pending_repairs]
    if rep_ids:
        all_rps = (await db.execute(select(RepairPart).where(RepairPart.repair_id.in_(rep_ids)))).scalars().all()
        rps_by_repair = {}
        for rp in all_rps:
            rps_by_repair.setdefault(rp.repair_id, []).append(rp)
        for r in pending_repairs:
            rps = rps_by_repair.get(r.id, [])
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
