from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select
from app.config import DATABASE_URL

_ASYNC_SCHEMES = {
    "sqlite://": "sqlite+aiosqlite://",
    "postgresql://": "postgresql+asyncpg://",
    "postgresql+psycopg2://": "postgresql+asyncpg://",
}
async_db_url = DATABASE_URL
for old, new in _ASYNC_SCHEMES.items():
    if DATABASE_URL.startswith(old):
        async_db_url = new + DATABASE_URL[len(old):]
        break

engine_kwargs = {}
if not async_db_url.startswith("sqlite"):
    engine_kwargs["pool_pre_ping"] = True
    if "sslmode" not in async_db_url:
        sep = "&" if "?" in async_db_url else "?"
        async_db_url = async_db_url + sep + "sslmode=require"

engine = create_async_engine(async_db_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

ROLE_ADMIN = "admin"
ROLE_TECHNICIAN = "technician"
ROLE_WAREHOUSE = "warehouse"
ROLE_RECEPTION = "reception"
VALID_ROLES = {ROLE_ADMIN, ROLE_TECHNICIAN, ROLE_WAREHOUSE, ROLE_RECEPTION}

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _migrate_repairs()
    await _seed_expense_categories()
    await _seed_admin_user()
    await _seed_settings()
    await _seed_catalog()


async def _migrate_repairs():
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            for col, col_type in [
                ("brand", "VARCHAR(200) DEFAULT ''"),
                ("passcode", "VARCHAR(200) DEFAULT ''"),
                ("handover_items", "TEXT DEFAULT '[]'"),
                ("handover_memory_note", "VARCHAR(200) DEFAULT ''"),
                ("condition_data", "TEXT DEFAULT '{}'"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE repairs ADD COLUMN {col} {col_type}"))
                except Exception:
                    pass
    except Exception:
        pass

async def _seed_expense_categories():
    from app.models.expense_category import ExpenseCategory
    from sqlalchemy.exc import IntegrityError
    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(ExpenseCategory).limit(1))
            if r.scalar():
                return
            for name in ["Rent", "Electricity / Utilities", "Internet",
                         "Parts Purchase", "Staff Salary", "Transport",
                         "Miscellaneous"]:
                db.add(ExpenseCategory(name=name))
            await db.commit()
        except IntegrityError:
            await db.rollback()

async def _seed_admin_user():
    from app.models.user import User
    from app.utils.auth import hash_password
    from sqlalchemy.exc import IntegrityError
    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(User).where(User.role == ROLE_ADMIN).limit(1))
            if r.scalar():
                return
            db.add(User(
                name="Admin",
                email="admin@shop.com",
                password_hash=hash_password("admin123"),
                phone="",
                role=ROLE_ADMIN,
                active=True,
            ))
            await db.commit()
        except IntegrityError:
            await db.rollback()

async def _seed_settings():
    from app.models.setting import Setting
    from sqlalchemy.exc import IntegrityError
    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(Setting).limit(1))
            if r.scalar():
                return
            for key, value in {
                "shop_name": "My Shop",
                "shop_address": "",
                "shop_phone": "",
                "default_currency": "USD",
                "supported_currencies": '["USD", "BDT", "INR", "NGN"]',
            }.items():
                db.add(Setting(key=key, value=value))
            await db.commit()
        except IntegrityError:
            await db.rollback()

async def _seed_catalog():
    from app.models.brand import Brand
    from app.models.part_category import PartCategory
    from app.models.part_type import PartType
    from sqlalchemy.exc import IntegrityError

    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(Brand).limit(1))
            if not r.scalar():
                for i, name in enumerate([
                    "Realme", "Samsung", "iPhone", "Xiaomi", "Redmi", "Poco",
                    "OnePlus", "Oppo", "Vivo", "Honor", "Huawei", "Motorola",
                    "Nokia", "Tecno", "Infinix", "iTel", "Google Pixel",
                    "Sony", "LG", "ASUS", "Nothing", "Meizu", "ZTE",
                ]):
                    db.add(Brand(name=name, sort_order=i))
                await db.commit()
        except IntegrityError:
            await db.rollback()

    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(PartCategory).limit(1))
            if r.scalar():
                return
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
            cats = []
            for i, cat_name in enumerate(categories.keys()):
                cats.append(PartCategory(name=cat_name, sort_order=i))
            db.add_all(cats)
            await db.flush()
            types = []
            for cat, (_, type_names) in zip(cats, categories.items()):
                for j, type_name in enumerate(type_names):
                    types.append(PartType(category_id=cat.id, name=type_name, sort_order=j))
            db.add_all(types)
            await db.commit()
        except IntegrityError:
            await db.rollback()


