from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional
from datetime import date, datetime, timedelta
import calendar

from app.database import get_db
from app.models.payment import Payment
from app.models.repair import Repair
from app.models.daily_sale import DailySale
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.models.customer import Customer
from app.models.user import User
from app.schemas.report import DailySummary, MonthlySummary, ProfitLossItem, ProfitLossReport
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily", response_model=DailySummary)
def daily_summary(
    date_str: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = date_str or date.today().isoformat()

    payments = (
        db.query(Payment)
        .filter(
            Payment.paid_at >= target_date,
            Payment.paid_at <= target_date + " 23:59:59",
        )
        .all()
    )
    total_repair_revenue = sum(p.amount for p in payments)

    payment_methods = {}
    for p in payments:
        if p.method not in payment_methods:
            payment_methods[p.method] = 0
        payment_methods[p.method] += p.amount

    manual_sales = (
        db.query(DailySale)
        .filter(DailySale.date == target_date)
        .all()
    )
    total_manual_sales = sum(s.amount for s in manual_sales)

    sales_dict = {"repair_payments": total_repair_revenue, "manual_sales": total_manual_sales}

    expenses = (
        db.query(Expense)
        .filter(Expense.date == target_date)
        .all()
    )
    expenses_dict = {}
    total_expenses = 0
    for e in expenses:
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first()
        cat_name = cat.name if cat else "Unknown"
        if cat_name not in expenses_dict:
            expenses_dict[cat_name] = 0
        expenses_dict[cat_name] += e.amount
        total_expenses += e.amount

    repairs_completed = (
        db.query(Repair)
        .filter(
            Repair.status == "delivered",
            Repair.updated_at >= target_date,
            Repair.updated_at <= target_date + " 23:59:59",
        )
        .count()
    )

    new_customers = (
        db.query(Customer)
        .filter(
            Customer.created_at >= target_date,
            Customer.created_at <= target_date + " 23:59:59",
        )
        .count()
    )

    net_profit = total_repair_revenue + total_manual_sales - total_expenses

    return DailySummary(
        date=target_date,
        sales=sales_dict,
        expenses=expenses_dict,
        net_profit=net_profit,
        payment_methods=payment_methods,
        repairs_completed=repairs_completed,
        new_customers=new_customers,
        total_repair_revenue=total_repair_revenue,
        total_manual_sales=total_manual_sales,
        total_expenses=total_expenses,
    )


@router.get("/monthly", response_model=MonthlySummary)
def monthly_summary(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month

    first_day = f"{target_year}-{target_month:02d}-01"
    last_day_num = calendar.monthrange(target_year, target_month)[1]
    last_day = f"{target_year}-{target_month:02d}-{last_day_num:02d}"

    payments = (
        db.query(Payment)
        .filter(Payment.paid_at >= first_day, Payment.paid_at <= last_day + " 23:59:59")
        .all()
    )
    total_revenue = sum(p.amount for p in payments)

    payment_methods = {}
    for p in payments:
        if p.method not in payment_methods:
            payment_methods[p.method] = 0
        payment_methods[p.method] += p.amount

    manual_sales = (
        db.query(DailySale)
        .filter(DailySale.date >= first_day, DailySale.date <= last_day)
        .all()
    )
    total_revenue += sum(s.amount for s in manual_sales)

    expenses = (
        db.query(Expense)
        .filter(Expense.date >= first_day, Expense.date <= last_day)
        .all()
    )
    total_expenses = sum(e.amount for e in expenses)

    expense_categories = {}
    for e in expenses:
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first()
        cat_name = cat.name if cat else "Unknown"
        if cat_name not in expense_categories:
            expense_categories[cat_name] = 0
        expense_categories[cat_name] += e.amount

    repairs_completed = (
        db.query(Repair)
        .filter(
            Repair.status == "delivered",
            Repair.updated_at >= first_day,
            Repair.updated_at <= last_day + " 23:59:59",
        )
        .count()
    )

    repairs_received = (
        db.query(Repair)
        .filter(Repair.created_at >= first_day, Repair.created_at <= last_day + " 23:59:59")
        .count()
    )

    new_customers = (
        db.query(Customer)
        .filter(Customer.created_at >= first_day, Customer.created_at <= last_day + " 23:59:59")
        .count()
    )

    daily_breakdown = []
    for day in range(1, last_day_num + 1):
        day_str = f"{target_year}-{target_month:02d}-{day:02d}"
        day_payments = (
            db.query(Payment)
            .filter(Payment.paid_at >= day_str, Payment.paid_at <= day_str + " 23:59:59")
            .all()
        )
        day_manual = (
            db.query(DailySale).filter(DailySale.date == day_str).all()
        )
        day_expenses = (
            db.query(Expense).filter(Expense.date == day_str).all()
        )
        day_revenue = sum(p.amount for p in day_payments) + sum(
            s.amount for s in day_manual
        )
        day_exp = sum(e.amount for e in day_expenses)
        day_methods = {}
        for p in day_payments:
            if p.method not in day_methods:
                day_methods[p.method] = 0
            day_methods[p.method] += p.amount

        daily_breakdown.append(
            DailySummary(
                date=day_str,
                sales={"repair_payments": sum(p.amount for p in day_payments), "manual_sales": sum(s.amount for s in day_manual)},
                expenses={},
                net_profit=day_revenue - day_exp,
                payment_methods=day_methods,
                repairs_completed=0,
                new_customers=0,
                total_repair_revenue=sum(p.amount for p in day_payments),
                total_manual_sales=sum(s.amount for s in day_manual),
                total_expenses=day_exp,
            )
        )

    return MonthlySummary(
        year=target_year,
        month=target_month,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=total_revenue - total_expenses,
        repairs_completed=repairs_completed,
        repairs_received=repairs_received,
        new_customers=new_customers,
        daily_breakdown=daily_breakdown,
        payment_methods=payment_methods,
        expense_categories=expense_categories,
    )


@router.get("/revenue")
def revenue_by_service(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Payment)
    if date_from:
        query = query.filter(Payment.paid_at >= date_from)
    if date_to:
        query = query.filter(Payment.paid_at <= date_to + " 23:59:59")
    payments = query.all()

    repair_revenue = {}
    for p in payments:
        repair = db.query(Repair).filter(Repair.id == p.repair_id).first()
        if repair:
            model = repair.model
            if model not in repair_revenue:
                repair_revenue[model] = 0
            repair_revenue[model] += p.amount

    return {"by_model": repair_revenue, "total": sum(p.amount for p in payments)}


@router.get("/profit-loss", response_model=ProfitLossReport)
def profit_loss_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    start = date_from or (today - timedelta(days=30)).isoformat()
    end = date_to or today.isoformat()

    payments = (
        db.query(Payment)
        .filter(Payment.paid_at >= start, Payment.paid_at <= end + " 23:59:59")
        .all()
    )
    manual_sales = (
        db.query(DailySale)
        .filter(DailySale.date >= start, DailySale.date <= end)
        .all()
    )
    expenses = (
        db.query(Expense)
        .filter(Expense.date >= start, Expense.date <= end)
        .all()
    )

    revenue_by_date = {}
    for p in payments:
        day = p.paid_at.strftime("%Y-%m-%d") if p.paid_at else start
        if day not in revenue_by_date:
            revenue_by_date[day] = 0
        revenue_by_date[day] += p.amount

    for s in manual_sales:
        if s.date not in revenue_by_date:
            revenue_by_date[s.date] = 0
        revenue_by_date[s.date] += s.amount

    expense_by_date = {}
    for e in expenses:
        if e.date not in expense_by_date:
            expense_by_date[e.date] = 0
        expense_by_date[e.date] += e.amount

    all_dates = sorted(set(list(revenue_by_date.keys()) + list(expense_by_date.keys())))
    items = []
    for d in all_dates:
        rev = revenue_by_date.get(d, 0)
        exp = expense_by_date.get(d, 0)
        items.append(ProfitLossItem(date=d, revenue=rev, expenses=exp, net=rev - exp))

    expense_breakdown = {}
    for e in expenses:
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first()
        cat_name = cat.name if cat else "Unknown"
        if cat_name not in expense_breakdown:
            expense_breakdown[cat_name] = 0
        expense_breakdown[cat_name] += e.amount

    revenue_breakdown = {}
    for p in payments:
        repair = db.query(Repair).filter(Repair.id == p.repair_id).first()
        if repair:
            model = repair.model
            if model not in revenue_breakdown:
                revenue_breakdown[model] = 0
            revenue_breakdown[model] += p.amount
    for s in manual_sales:
        if s.category not in revenue_breakdown:
            revenue_breakdown[s.category] = 0
        revenue_breakdown[s.category] += s.amount

    total_revenue = sum(i.revenue for i in items)
    total_expenses = sum(i.expenses for i in items)

    return ProfitLossReport(
        start_date=start,
        end_date=end,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=total_revenue - total_expenses,
        items=items,
        expense_breakdown=expense_breakdown,
        revenue_breakdown=revenue_breakdown,
    )
