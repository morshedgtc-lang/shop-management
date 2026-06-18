from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.database import init_db
from app.routes import auth, customers, repairs, services, parts, payments, expenses, daily_sales, reports, staff, settings

app = FastAPI(
    title="Shop Management",
    description="A comprehensive shop management system for repair shops",
    version="1.0.0",
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
