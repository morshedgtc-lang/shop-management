from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class RepairCreate(BaseModel):
    customer_id: int
    model: str
    issues: str
    imei: str = ""
    estimated_cost: float = 0
    service_fee: float = 0
    assigned_to: Optional[int] = None
    notes: str = ""

class RepairUpdate(BaseModel):
    model: Optional[str] = None
    issues: Optional[str] = None
    imei: Optional[str] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    service_fee: Optional[float] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None

class RepairStatusUpdate(BaseModel):
    status: str

class RepairPartResponse(BaseModel):
    id: int
    part_id: int
    qty: int
    unit_price: float
    selling_price: float
    returned_qty: int = 0
    part_name: str = ""
    class Config:
        from_attributes = True

class RepairPaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    method: str
    notes: str
    paid_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class RepairResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str = ""
    assigned_to: Optional[int] = None
    assigned_user_name: str = ""
    created_by: int
    creator_name: str = ""
    status: str
    model: str
    issues: str
    imei: str
    estimated_cost: float
    actual_cost: float
    service_fee: float = 0
    notes: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parts: List[RepairPartResponse] = []
    payments: List[RepairPaymentResponse] = []
    total_parts_cost: float = 0
    total_payments: float = 0
    balance: float = 0
    class Config:
        from_attributes = True
