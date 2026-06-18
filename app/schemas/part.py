from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PartCreate(BaseModel):
    name: str
    model: str = ""
    stock_qty: int = 0
    unit_price: float = 0
    currency: str = "USD"
    min_stock_alert: int = 5


class PartUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    stock_qty: Optional[int] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    min_stock_alert: Optional[int] = None


class PartResponse(BaseModel):
    id: int
    name: str
    model: str
    stock_qty: int
    unit_price: float
    currency: str
    min_stock_alert: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
