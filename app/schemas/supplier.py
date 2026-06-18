from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class SupplierCreate(BaseModel):
    name: str
    phone: str = ""
    address: str = ""
    notes: str = ""

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class SupplierResponse(BaseModel):
    id: int
    name: str
    phone: str
    address: str
    notes: str
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class SupplierPaymentCreate(BaseModel):
    amount: float
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
    class Config:
        from_attributes = True

class SupplierDetailResponse(SupplierResponse):
    total_purchases: float = 0
    total_paid: float = 0
    balance: float = 0
