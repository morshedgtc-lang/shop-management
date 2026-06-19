from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

REPAIR_STATUSES = [
    "received", "diagnosed", "waiting_parts",
    "repairing", "testing", "delivered", "cancelled",
]
CANCELLABLE_STATUSES = {"received", "diagnosed", "waiting_parts", "repairing"}
VALID_TRANSITIONS = {
    "received": {"diagnosed"},
    "diagnosed": {"waiting_parts", "repairing"},
    "waiting_parts": {"repairing"},
    "repairing": {"testing"},
    "testing": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def luhn_checksum(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class RepairCreate(BaseModel):
    customer_id: int
    model: str = Field(..., min_length=1, max_length=200)
    issues: str = Field(..., min_length=1)
    imei: str = ""
    estimated_cost: float = Field(0, ge=0)
    service_fee: float = Field(0, ge=0)
    assigned_to: Optional[int] = None
    notes: str = ""

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            return ""
        if not cleaned.isdigit() or len(cleaned) != 15:
            raise ValueError("IMEI must be exactly 15 digits")
        if not luhn_checksum(cleaned):
            raise ValueError("IMEI failed Luhn checksum validation")
        return cleaned


class RepairUpdate(BaseModel):
    model: Optional[str] = Field(None, min_length=1, max_length=200)
    issues: Optional[str] = Field(None, min_length=1)
    imei: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    service_fee: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return v
        cleaned = v.strip()
        if not cleaned.isdigit() or len(cleaned) != 15:
            raise ValueError("IMEI must be exactly 15 digits")
        if not luhn_checksum(cleaned):
            raise ValueError("IMEI failed Luhn checksum validation")
        return cleaned


class RepairStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in REPAIR_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(REPAIR_STATUSES)}"
            )
        return v


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
