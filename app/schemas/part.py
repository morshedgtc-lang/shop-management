from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PartCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    model: str = ""
    sku: str = ""
    supplier_barcode: str = ""
    stock_qty: int = Field(0, ge=0)
    unit_price: float = Field(0, ge=0)
    selling_price: float = Field(0, ge=0)
    wholesale_price: float = Field(0, ge=0)
    box_number: str = ""
    shelf_number: str = ""
    currency: str = "USD"
    min_stock_alert: int = Field(5, ge=0)
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None


class PartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    model: Optional[str] = None
    sku: Optional[str] = None
    supplier_barcode: Optional[str] = None
    stock_qty: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    wholesale_price: Optional[float] = Field(None, ge=0)
    box_number: Optional[str] = None
    shelf_number: Optional[str] = None
    currency: Optional[str] = None
    min_stock_alert: Optional[int] = Field(None, ge=0)
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None


class PartResponse(BaseModel):
    id: int
    name: str
    model: str
    sku: Optional[str] = None
    supplier_barcode: str
    stock_qty: int
    unit_price: float
    selling_price: float
    wholesale_price: float = 0
    box_number: str = ""
    shelf_number: str = ""
    currency: str
    min_stock_alert: int
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    part_type_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
