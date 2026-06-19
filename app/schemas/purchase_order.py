from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

PO_STATUSES = ["draft", "sent", "partially_received", "received", "closed", "cancelled"]
PO_PAYMENT_TYPES = ["credit", "cash"]
PO_ITEM_STATUSES = ["pending", "partial", "received"]
PO_VALID_TRANSITIONS = {
    "draft": {"sent"},
    "sent": {"partially_received", "received", "cancelled"},
    "partially_received": {"received", "cancelled"},
    "received": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


class PurchaseOrderItemCreate(BaseModel):
    part_id: Optional[int] = None
    name: str = ""
    sku: str = ""
    qty_ordered: int = Field(1, ge=1)
    cost_price: float = Field(0, ge=0)
    selling_price: float = Field(0, ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    payment_type: str = "credit"
    notes: str = ""
    items: List[PurchaseOrderItemCreate] = []

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[PurchaseOrderItemCreate]) -> List[PurchaseOrderItemCreate]:
        if not v:
            raise ValueError("At least one item is required")
        return v

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        if v not in PO_PAYMENT_TYPES:
            raise ValueError(f"Invalid payment_type. Must be one of: {', '.join(PO_PAYMENT_TYPES)}")
        return v


class PurchaseOrderItemResponse(BaseModel):
    id: int
    part_id: Optional[int] = None
    part_name: str = ""
    sku: str = ""
    qty_ordered: int
    qty_received: int
    cost_price: float
    invoice_price: float
    selling_price: float
    status: str = "pending"

    class Config:
        from_attributes = True


class PurchaseOrderResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    supplier_name: str = ""
    status: str
    payment_type: str
    notes: str
    total_amount: float = 0
    created_by: int
    creator_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[PurchaseOrderItemResponse] = []

    class Config:
        from_attributes = True


class POReceiptItemUpdate(BaseModel):
    po_item_id: int
    qty_received: int = Field(..., ge=0)
    cost_price: float = Field(0, ge=0)


class POReceiptCreate(BaseModel):
    invoice_number: str = Field(..., min_length=1)
    invoice_date: str = ""
    notes: str = ""
    items: List[POReceiptItemUpdate] = []

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[POReceiptItemUpdate]) -> List[POReceiptItemUpdate]:
        if not v:
            raise ValueError("At least one receipt item is required")
        return v


class POReceiptResponse(BaseModel):
    id: int
    po_id: int
    invoice_number: str
    invoice_date: str
    notes: str
    received_by: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PODiscrepancyResponse(BaseModel):
    id: int
    po_id: int
    po_item_id: int
    field: str
    expected: float
    actual: float
    note: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
