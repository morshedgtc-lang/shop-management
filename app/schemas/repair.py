from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

REPAIR_STATUSES = [
    "PENDING_ESTIMATE", "ESTIMATE_GIVEN", "APPROVED",
    "WAITING_PARTS", "REPAIRED", "READY_FOR_PICKUP", "COMPLETED",
]
CANCELLABLE_STATUSES = {"PENDING_ESTIMATE", "ESTIMATE_GIVEN"}
VALID_TRANSITIONS = {
    "PENDING_ESTIMATE": {"ESTIMATE_GIVEN"},
    "ESTIMATE_GIVEN": {"APPROVED", "COMPLETED"},
    "APPROVED": {"WAITING_PARTS", "REPAIRED"},
    "WAITING_PARTS": {"REPAIRED"},
    "REPAIRED": {"READY_FOR_PICKUP"},
    "READY_FOR_PICKUP": {"COMPLETED"},
    "COMPLETED": set(),
}

ORDER_TYPES = ("OR", "IR")


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
    customer_name: str = ""
    customer_phone: str = ""
    order_type: str = "OR"
    intermediate_shop_id: Optional[int] = None
    model: str = Field(..., min_length=1, max_length=200)
    brand: str = ""
    passcode: str = ""
    issues: str = Field(..., min_length=1)
    imei: str = ""
    estimated_cost: float = Field(0, ge=0)
    estimated_time: str = ""
    service_fee: float = Field(0, ge=0)
    assigned_to: Optional[int] = None
    notes: str = ""
    handover_items: str = "[]"
    handover_memory_note: str = ""
    condition_data: str = "{}"

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

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ORDER_TYPES:
            raise ValueError("order_type must be OR or IR")
        return v


class RepairUpdate(BaseModel):
    model: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = None
    passcode: Optional[str] = None
    issues: Optional[str] = Field(None, min_length=1)
    imei: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    estimated_time: Optional[str] = None
    actual_cost: Optional[float] = Field(None, ge=0)
    service_fee: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    handover_items: Optional[str] = None
    handover_memory_note: Optional[str] = None
    condition_data: Optional[str] = None

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

    model_config = ConfigDict(from_attributes=True)


class RepairPaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    method: str
    notes: str
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PartRequestResponse(BaseModel):
    id: int
    repair_id: int
    part_id: int
    part_name: str = ""
    requested_by: int
    requester_name: str = ""
    fulfilled_by: Optional[int] = None
    fulfiller_name: str = ""
    quantity: int = 1
    status: str = "PENDING"
    notes: str = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PartRequestCreate(BaseModel):
    part_id: int
    quantity: int = Field(1, ge=1)
    notes: str = ""


class PartRequestFulfill(BaseModel):
    quantity: int = Field(1, ge=1)


class RepairResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    customer_name: str = ""
    assigned_to: Optional[int] = None
    assigned_user_name: str = ""
    created_by: int
    creator_name: str = ""
    status: str
    model: str
    brand: str = ""
    passcode: str = ""
    issues: str
    imei: str
    estimated_cost: float
    estimated_time: str = ""
    actual_cost: float
    service_fee: float = 0
    payment_status: str = "UNPAID"
    order_type: str = "OR"
    intermediate_shop_id: Optional[int] = None
    intermediate_shop_name: str = ""
    notes: str
    handover_items: str = "[]"
    handover_memory_note: str = ""
    condition_data: str = "{}"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parts: List[RepairPartResponse] = []
    payments: List[RepairPaymentResponse] = []
    part_requests: List[PartRequestResponse] = []
    total_parts_cost: float = 0
    total_payments: float = 0
    balance: float = 0

    model_config = ConfigDict(from_attributes=True)


class CheckoutResponse(BaseModel):
    repair_id: int
    total_amount: float
    parts_cost: float
    service_fee: float
    message: str


class CancelRepairResponse(BaseModel):
    repair_id: int
    status: str
    message: str
