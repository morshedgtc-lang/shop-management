from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqlfunc
from typing import Optional
from datetime import date, timedelta
import calendar

from app.database import get_db
from app.models.payment import Payment
from app.models.repair import Repair
from app.models.daily_sale import DailySale
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.models.customer import Customer
from app.schemas.report import DailySummary, MonthlySummary, ProfitLossItem, ProfitLossReport
from app.utils.auth import get_current_user
from app.utils.permissions import require_admin, require_warehouse, require_warehouse_or_admin, require_reception_or_admin

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily", response_model=DailySummary)
async def daily_summary(
    date_str: Optional[str] = Query(None, alias="date"),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    target_date = date_str or date.today().isoformat()
    end_bound = target_date + " 23:59:59"

    payments = (
        (await db.execute(
            select(Payment).where(
                Payment.paid_at >= target_date, Payment.paid_at <= end_bound
            )
        ))
        .scalars().all()
    )
    total_repair_revenue = sum(p.amount for p in payments)
    payment_methods = {}
    for p in payments:
        payment_methods[p.method] = payment_methods.get(p.method, 0) + p.amount

    manual_rows = (
        (await db.execute(select(DailySale).where(DailySale.date == target_date)))
        .scalars().all()
    )
    total_manual_sales = sum(s.amount for s in manual_rows)

    expense_rows = (
        (await db.execute(select(Expense).where(Expense.date == target_date)))
        .scalars().all()
    )
    expenses_dict = {}
    total_expenses = 0
    for e in expense_rows:
        cat = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == e.category_id))).scalar_one_or_none()
        cat_name = cat.name if cat else "Unknown"
        expenses_dict[cat_name] = expenses_dict.get(cat_name, 0) + e.amount
        total_expenses += e.amount

    completed = (
        await db.execute(
            select(sqlfunc.count(Repair.id)).where(
                Repair.status == "delivered",
                Repair.updated_at >= target_date, Repair.updated_at <= end_bound,
            )
        )
    ).scalar() or 0

    new_cust = (
        await db.execute(
            select(sqlfunc.count(Customer.id)).where(
                Customer.created_at >= target_date, Customer.created_at <= end_bound,
            )
        )
    ).scalar() or 0

    return DailySummary(
        date=target_date,
        sales={"repair_payments": total_repair_revenue, "manual_sales": total_manual_sales},
        expenses=expenses_dict,
        net_profit=total_repair_revenue + total_manual_sales - total_expenses,
        payment_methods=payment_methods,
        repairs_completed=completed,
        new_customers=new_cust,
        total_repair_revenue=total_repair_revenue,
        total_manual_sales=total_manual_sales,
        total_expenses=total_expenses,
    )


@router.get("/monthly", response_model=MonthlySummary)
async def monthly_summary(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month
    first_day = f"{target_year}-{target_month:02d}-01"
    last_day_num = calendar.monthrange(target_year, target_month)[1]
    last_day = f"{target_year}-{target_month:02d}-{last_day_num:02d}"
    end_bound = last_day + " 23:59:59"

    payments = (
        (await db.execute(
            select(Payment).where(Payment.paid_at >= first_day, Payment.paid_at <= end_bound)
        ))
        .scalars().all()
    )
    total_revenue = sum(p.amount for p in payments)
    payment_methods = {}
    for p in payments:
        payment_methods[p.method] = payment_methods.get(p.method, 0) + p.amount

    manual_rows = (
        (await db.execute(
            select(DailySale).where(DailySale.date >= first_day, DailySale.date <= last_day)
        ))
        .scalars().all()
    )
    total_revenue += sum(s.amount for s in manual_rows)

    expense_rows = (
        (await db.execute(
            select(Expense).where(Expense.date >= first_day, Expense.date <= last_day)
        ))
        .scalars().all()
    )
    total_expenses = sum(e.amount for e in expense_rows)
    expense_categories = {}
    for e in expense_rows:
        cat = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == e.category_id))).scalar_one_or_none()
        cat_name = cat.name if cat else "Unknown"
        expense_categories[cat_name] = expense_categories.get(cat_name, 0) + e.amount

    completed = (
        await db.execute(
            select(sqlfunc.count(Repair.id)).where(
                Repair.status == "delivered",
                Repair.updated_at >= first_day, Repair.updated_at <= end_bound,
            )
        )
    ).scalar() or 0

    received = (
        await db.execute(
            select(sqlfunc.count(Repair.id)).where(
                Repair.created_at >= first_day, Repair.created_at <= end_bound,
            )
        )
    ).scalar() or 0

    new_cust = (
        await db.execute(
            select(sqlfunc.count(Customer.id)).where(
                Customer.created_at >= first_day, Customer.created_at <= end_bound,
            )
        )
    ).scalar() or 0

    daily_breakdown = []
    for day in range(1, last_day_num + 1):
        day_str = f"{target_year}-{target_month:02d}-{day:02d}"
        day_end = day_str + " 23:59:59"
        day_pay = (await db.execute(select(Payment).where(Payment.paid_at >= day_str, Payment.paid_at <= day_end))).scalars().all()
        day_man = (await db.execute(select(DailySale).where(DailySale.date == day_str))).scalars().all()
        day_exp = (await db.execute(select(Expense).where(Expense.date == day_str))).scalars().all()
        day_rev = sum(p.amount for p in day_pay) + sum(s.amount for s in day_man)
        day_exp_sum = sum(e.amount for e in day_exp)
        day_methods = {}
        for p in day_pay:
            day_methods[p.method] = day_methods.get(p.method, 0) + p.amount
        daily_breakdown.append(
            DailySummary(
                date=day_str,
                sales={"repair_payments": sum(p.amount for p in day_pay), "manual_sales": sum(s.amount for s in day_man)},
                expenses={},
                net_profit=day_rev - day_exp_sum,
                payment_methods=day_methods,
                repairs_completed=0, new_customers=0,
                total_repair_revenue=sum(p.amount for p in day_pay),
                total_manual_sales=sum(s.amount for s in day_man),
                total_expenses=day_exp_sum,
            )
        )

    return MonthlySummary(
        year=target_year, month=target_month,
        total_revenue=total_revenue, total_expenses=total_expenses,
        net_profit=total_revenue - total_expenses,
        repairs_completed=completed, repairs_received=received,
        new_customers=new_cust, daily_breakdown=daily_breakdown,
        payment_methods=payment_methods, expense_categories=expense_categories,
    )


@router.get("/revenue")
async def revenue_by_service(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Payment)
    if date_from:
        query = query.where(Payment.paid_at >= date_from)
    if date_to:
        query = query.where(Payment.paid_at <= date_to + " 23:59:59")
    payments = (await db.execute(query)).scalars().all()

    repair_revenue = {}
    for p in payments:
        repair = (await db.execute(select(Repair).where(Repair.id == p.repair_id))).scalar_one_or_none()
        if repair:
            repair_revenue[repair.model] = repair_revenue.get(repair.model, 0) + p.amount

    return {"by_model": repair_revenue, "total": sum(p.amount for p in payments)}


@router.get("/profit-loss", response_model=ProfitLossReport)
async def profit_loss_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    start = date_from or (today - timedelta(days=30)).isoformat()
    end = date_to or today.isoformat()
    end_bound = end + " 23:59:59"

    payments = (await db.execute(select(Payment).where(Payment.paid_at >= start, Payment.paid_at <= end_bound))).scalars().all()
    manual_rows = (await db.execute(select(DailySale).where(DailySale.date >= start, DailySale.date <= end))).scalars().all()
    expense_rows = (await db.execute(select(Expense).where(Expense.date >= start, Expense.date <= end))).scalars().all()

    revenue_by_date = {}
    for p in payments:
        day = p.paid_at.strftime("%Y-%m-%d") if p.paid_at else start
        revenue_by_date[day] = revenue_by_date.get(day, 0) + p.amount
    for s in manual_rows:
        revenue_by_date[s.date] = revenue_by_date.get(s.date, 0) + s.amount

    expense_by_date = {}
    for e in expense_rows:
        expense_by_date[e.date] = expense_by_date.get(e.date, 0) + e.amount

    all_dates = sorted(set(list(revenue_by_date.keys()) + list(expense_by_date.keys())))
    items = []
    for d in all_dates:
        rev = revenue_by_date.get(d, 0)
        exp = expense_by_date.get(d, 0)
        items.append(ProfitLossItem(date=d, revenue=rev, expenses=exp, net=rev - exp))

    expense_breakdown = {}
    for e in expense_rows:
        cat = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == e.category_id))).scalar_one_or_none()
        cat_name = cat.name if cat else "Unknown"
        expense_breakdown[cat_name] = expense_breakdown.get(cat_name, 0) + e.amount

    revenue_breakdown = {}
    for p in payments:
        repair = (await db.execute(select(Repair).where(Repair.id == p.repair_id))).scalar_one_or_none()
        if repair:
            revenue_breakdown[repair.model] = revenue_breakdown.get(repair.model, 0) + p.amount
    for s in manual_rows:
        revenue_breakdown[s.category] = revenue_breakdown.get(s.category, 0) + s.amount

    total_revenue = sum(i.revenue for i in items)
    total_expenses = sum(i.expenses for i in items)

    return ProfitLossReport(
        start_date=start, end_date=end,
        total_revenue=total_revenue, total_expenses=total_expenses,
        net_profit=total_revenue - total_expenses, items=items,
        expense_breakdown=expense_breakdown, revenue_breakdown=revenue_breakdown,
    )
