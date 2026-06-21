from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field("", pattern=r'^\+?[\d\s\-\(\)]{7,20}$')
    address: str = ""
    notes: str = ""


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{7,20}$')
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    phone: str
    address: str
    notes: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierPaymentCreate(BaseModel):
    amount: float = Field(..., ge=0)
    method: str = "cash"
    date: str = ""
    notes: str = ""


class SupplierPaymentResponse(BaseModel):
    id: int
    supplier_id: int
    amount: float
    method: str
    date: str
    notes: str
    created_by: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierDetailResponse(SupplierResponse):
    total_purchases: float = 0
    total_paid: float = 0
    balance: float = 0
