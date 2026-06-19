from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PAYMENT_METHODS = Literal[
    "cash", "bkash", "nagad", "rocket", "card",
    "bank_transfer", "other",
]


class PaymentCreate(BaseModel):
    repair_id: int
    amount: float = Field(..., ge=0)
    currency: str = "USD"
    method: str = "cash"
    notes: str = ""


class PaymentResponse(BaseModel):
    id: int
    repair_id: int
    amount: float
    currency: str
    method: str
    notes: str
    created_by: int
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True
