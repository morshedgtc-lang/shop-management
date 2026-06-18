from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PartCreate(BaseModel):
    name: str
    model: str = ""
    sku: Optional[str] = None
    supplier_barcode: str = ""
    stock_qty: int = 0
    unit_price: float = 0
    selling_price: float = 0
    currency: str = "USD"
    min_stock_alert: int = 5
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None

class PartUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    supplier_barcode: Optional[str] = None
    stock_qty: Optional[int] = None
    unit_price: Optional[float] = None
    selling_price: Optional[float] = None
    currency: Optional[str] = None
    min_stock_alert: Optional[int] = None
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None

class PartResponse(BaseModel):
    id: int
    name: str
    model: str
    sku: Optional[str] = None
    supplier_barcode: str = ""
    stock_qty: int
    unit_price: float
    selling_price: float
    currency: str
    min_stock_alert: int
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
