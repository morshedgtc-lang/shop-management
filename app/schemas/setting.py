from typing import Optional

from pydantic import BaseModel


class SettingUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_address: Optional[str] = None
    shop_phone: Optional[str] = None
    default_currency: Optional[str] = None


class SettingResponse(BaseModel):
    shop_name: str = ""
    shop_address: str = ""
    shop_phone: str = ""
    default_currency: str = "USD"
    supported_currencies: list = ["USD", "BDT", "INR", "NGN"]
