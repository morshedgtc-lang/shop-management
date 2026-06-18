from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.database import init_db, get_db
from app.routes import auth, customers, repairs, services, parts, payments, expenses, daily_sales, reports, staff, settings

app = FastAPI(
    title="Shop Management",
    description="A comprehensive shop management system for repair shops",
    version="1.0.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(repairs.router)
app.include_router(services.router)
app.include_router(parts.router)
app.include_router(payments.router)
app.include_router(expenses.router)
app.include_router(daily_sales.router)
app.include_router(reports.router)
app.include_router(staff.router)
app.include_router(settings.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Shop Management API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Shop Management API"}


@app.get("/api/dashboard")
def dashboard(
    db=Depends(get_db),
):
    from datetime import date
    from sqlalchemy import func as sqlfunc
    from app.models.repair import Repair
    from app.models.payment import Payment
    from app.models.daily_sale import DailySale
    from app.models.expense import Expense
    from app.models.customer import Customer
    from app.models.part import Part

    today = date.today().isoformat()

    total_repairs = db.query(Repair).count()
    pending = db.query(Repair).filter(Repair.status.in_(["received", "diagnosed"])).count()
    in_progress = db.query(Repair).filter(Repair.status.in_(["waiting_parts", "repairing", "testing"])).count()
    completed_today = (
        db.query(Repair)
        .filter(Repair.status == "delivered", Repair.updated_at >= today, Repair.updated_at <= today + " 23:59:59")
        .count()
    )

    repair_payments = (
        db.query(Payment)
        .filter(Payment.paid_at >= today, Payment.paid_at <= today + " 23:59:59")
        .all()
    )
    total_revenue = sum(p.amount for p in repair_payments)

    manual_sales = (
        db.query(DailySale)
        .filter(DailySale.date == today)
        .all()
    )
    total_revenue += sum(s.amount for s in manual_sales)

    expenses = (
        db.query(Expense)
        .filter(Expense.date == today)
        .all()
    )
    total_expenses = sum(e.amount for e in expenses)

    low_stock = db.query(Part).filter(Part.stock_qty <= Part.min_stock_alert).count()

    recent_repairs = (
        db.query(Repair)
        .order_by(Repair.created_at.desc())
        .limit(5)
        .all()
    )

    from app.models.customer import Customer as Cust
    recent_list = []
    for r in recent_repairs:
        cust = db.query(Cust).filter(Cust.id == r.customer_id).first()
        recent_list.append({
            "id": r.id,
            "customer": cust.name if cust else "Unknown",
            "model": r.model,
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else "",
        })

    return {
        "total_repairs": total_repairs,
        "pending": pending,
        "in_progress": in_progress,
        "completed_today": completed_today,
        "revenue_today": total_revenue,
        "expenses_today": total_expenses,
        "net_profit_today": total_revenue - total_expenses,
        "low_stock_count": low_stock,
        "recent_repairs": recent_list,
    }
