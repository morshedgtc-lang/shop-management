import json
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingUpdate, SettingResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def get_setting_value(db, key: str, default: str = "") -> str:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else default


def set_setting_value(db, key: str, value: str):
    async def _inner():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))
    return _inner


async def _do_set(db, key: str, value: str):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))


def _parse_currencies(raw: str) -> list:
    try:
        return json.loads(raw) if raw else ["USD", "BDT", "INR", "NGN"]
    except (json.JSONDecodeError, TypeError):
        return ["USD", "BDT", "INR", "NGN"]


@router.get("", response_model=SettingResponse)
async def get_settings(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    currencies_str = await get_setting_value(db, "supported_currencies", '["USD", "BDT", "INR", "NGN"]')
    return SettingResponse(
        shop_name=await get_setting_value(db, "shop_name", "My Shop"),
        shop_address=await get_setting_value(db, "shop_address", ""),
        shop_phone=await get_setting_value(db, "shop_phone", ""),
        default_currency=await get_setting_value(db, "default_currency", "USD"),
        supported_currencies=_parse_currencies(currencies_str),
    )


@router.put("", response_model=SettingResponse)
async def update_settings(
    data: SettingUpdate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    if data.shop_name is not None:
        await _do_set(db, "shop_name", data.shop_name)
    if data.shop_address is not None:
        await _do_set(db, "shop_address", data.shop_address)
    if data.shop_phone is not None:
        await _do_set(db, "shop_phone", data.shop_phone)
    if data.default_currency is not None:
        await _do_set(db, "default_currency", data.default_currency)
    await db.commit()

    currencies_str = await get_setting_value(db, "supported_currencies", '["USD", "BDT", "INR", "NGN"]')
    return SettingResponse(
        shop_name=await get_setting_value(db, "shop_name", "My Shop"),
        shop_address=await get_setting_value(db, "shop_address", ""),
        shop_phone=await get_setting_value(db, "shop_phone", ""),
        default_currency=await get_setting_value(db, "default_currency", "USD"),
        supported_currencies=_parse_currencies(currencies_str),
    )
