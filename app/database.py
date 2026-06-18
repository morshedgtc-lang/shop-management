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
    from app.models import brand, device_model, part_category, part_type
    from app.models import supplier, purchase_order, supplier_payment

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

        _seed_catalog(db)
    finally:
        db.close()


def _seed_catalog(db):
    from app.models.brand import Brand
    from app.models.device_model import DeviceModel
    from app.models.part_category import PartCategory
    from app.models.part_type import PartType

    if db.query(Brand).count() == 0:
        brands = [
            "Realme", "Samsung", "iPhone", "Xiaomi", "Redmi", "Poco",
            "OnePlus", "Oppo", "Vivo", "Honor", "Huawei", "Motorola",
            "Nokia", "Tecno", "Infinix", "iTel", "Google Pixel",
            "Sony", "LG", "ASUS", "Nothing", "Meizu", "ZTE",
        ]
        for i, name in enumerate(brands):
            db.add(Brand(name=name, sort_order=i))
        db.commit()

    if db.query(PartCategory).count() == 0:
        categories = {
            "Screen & Display": [
                "LCD Display", "OLED Display", "AMOLED Display", "Display Frame",
                "Touch Screen (Digitizer)", "Display Flex Cable", "Display Glass",
            ],
            "Battery & Charging": [
                "Battery", "Charging Port Board", "Charging Flex Cable",
                "Wireless Charging Coil", "Battery Connector",
            ],
            "Board Components (IC/Chips)": [
                "Power IC (PMIC)", "CPU / SoC", "Memory (RAM/eMMC/UFS)",
                "Charging IC", "Audio IC", "WiFi/Bluetooth IC", "NFC IC",
                "Display Driver IC (DDIC)", "Baseband IC", "Touch IC",
                "SIM IC", "Sensor IC",
            ],
            "Audio": [
                "Main Speaker (Loudspeaker)", "Ear Speaker (Earpiece)",
                "Main Microphone", "Sub Microphone", "Audio Jack Board",
            ],
            "Camera": [
                "Rear Camera (Main)", "Rear Camera (Ultrawide)",
                "Rear Camera (Telephoto/Macro)", "Front Camera (Selfie)",
                "Camera Flex Cable", "Camera Glass",
            ],
            "Sensors & Buttons": [
                "Power Button Flex", "Volume Button Flex",
                "Fingerprint Sensor (Side)", "Fingerprint Sensor (Under Display)",
                "Proximity/Light Sensor", "Gyroscope/Accelerometer",
            ],
            "Flex Cables & Connectors": [
                "Main Flex Cable", "Display Flex Cable",
                "Battery Connector", "SIM Tray", "Antenna Cable",
            ],
            "Housing & Frame": [
                "Back Cover", "Middle Frame / Chassis",
                "SIM Tray", "Side Buttons", "Antenna Band",
            ],
            "Accessories - Protection": [
                "Phone Case", "Back Cover", "Tempered Glass",
                "Camera Lens Protector", "Waterproof Case",
            ],
            "Accessories - Charging": [
                "Charger (Adapter)", "USB Cable", "Wireless Charger",
                "Car Charger", "Power Bank",
            ],
            "Accessories - Audio": [
                "Wired Earphones", "Bluetooth Earbuds",
                "External Speaker", "Audio Splitter",
            ],
            "Accessories - Other": [
                "Phone Holder / Stand", "Ring Holder", "Car Mount",
                "Pop Socket", "Stylus / Pen", "Memory Card (SD)", "SIM Adapter",
            ],
        }
        for i, (cat_name, types) in enumerate(categories.items()):
            cat = PartCategory(name=cat_name, sort_order=i)
            db.add(cat)
            db.flush()
            for j, type_name in enumerate(types):
                db.add(PartType(category_id=cat.id, name=type_name, sort_order=j))
        db.commit()
