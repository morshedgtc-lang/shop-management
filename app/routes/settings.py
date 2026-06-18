import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.setting import Setting
from app.models.user import User
from app.schemas.setting import SettingUpdate, SettingResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_setting_value(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def set_setting_value(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)


@router.get("/", response_model=SettingResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    currencies_str = get_setting_value(db, "supported_currencies", '["USD", "BDT", "INR", "NGN"]')
    try:
        currencies = json.loads(currencies_str)
    except (json.JSONDecodeError, TypeError):
        currencies = ["USD", "BDT", "INR", "NGN"]

    return SettingResponse(
        shop_name=get_setting_value(db, "shop_name", "My Shop"),
        shop_address=get_setting_value(db, "shop_address", ""),
        shop_phone=get_setting_value(db, "shop_phone", ""),
        default_currency=get_setting_value(db, "default_currency", "USD"),
        supported_currencies=currencies,
    )


@router.put("/", response_model=SettingResponse)
def update_settings(
    data: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if data.shop_name is not None:
        set_setting_value(db, "shop_name", data.shop_name)
    if data.shop_address is not None:
        set_setting_value(db, "shop_address", data.shop_address)
    if data.shop_phone is not None:
        set_setting_value(db, "shop_phone", data.shop_phone)
    if data.default_currency is not None:
        set_setting_value(db, "default_currency", data.default_currency)
    db.commit()

    currencies_str = get_setting_value(db, "supported_currencies", '["USD", "BDT", "INR", "NGN"]')
    try:
        currencies = json.loads(currencies_str)
    except (json.JSONDecodeError, TypeError):
        currencies = ["USD", "BDT", "INR", "NGN"]

    return SettingResponse(
        shop_name=get_setting_value(db, "shop_name", "My Shop"),
        shop_address=get_setting_value(db, "shop_address", ""),
        shop_phone=get_setting_value(db, "shop_phone", ""),
        default_currency=get_setting_value(db, "default_currency", "USD"),
        supported_currencies=currencies,
    )
