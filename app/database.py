from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs["pool_pre_ping"] = True
    if "sslmode" not in DATABASE_URL:
        sep = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = DATABASE_URL + sep + "sslmode=require"

print(f"[DB] Connecting to: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import user, customer, repair, service, part, repair_part
    from app.models import payment, daily_sale, expense, expense_category, setting

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.models.expense_category import ExpenseCategory
        from app.models.setting import Setting

        existing_categories = db.query(ExpenseCategory).count()
        if existing_categories == 0:
            default_categories = [
                "Rent",
                "Electricity / Utilities",
                "Internet",
                "Parts Purchase",
                "Staff Salary",
                "Transport",
                "Miscellaneous",
            ]
            for cat_name in default_categories:
                db.add(ExpenseCategory(name=cat_name))
            db.commit()

        from app.models.user import User
        from app.utils.auth import hash_password

        existing_admin = db.query(User).filter(User.role == "admin").first()
        if not existing_admin:
            admin = User(
                name="Admin",
                email="admin@shop.com",
                password_hash=hash_password("admin123"),
                phone="",
                role="admin",
                active=True,
            )
            db.add(admin)
            db.commit()

        existing_settings = db.query(Setting).count()
        if existing_settings == 0:
            defaults = {
                "shop_name": "My Shop",
                "shop_address": "",
                "shop_phone": "",
                "default_currency": "USD",
                "supported_currencies": '["USD", "BDT", "INR", "NGN"]',
            }
            for key, value in defaults.items():
                db.add(Setting(key=key, value=value))
            db.commit()
    finally:
        db.close()
