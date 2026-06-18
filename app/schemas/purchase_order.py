from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PurchaseOrderItemCreate(BaseModel):
    part_id: Optional[int] = None
    name: str = ""
    sku: str = ""
    qty_ordered: int = 1
    cost_price: float = 0
    selling_price: float = 0

class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    payment_type: str = "credit"
    notes: str = ""
    items: List[PurchaseOrderItemCreate] = []

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

class POReceiptCreate(BaseModel):
    invoice_number: str
    invoice_date: str = ""
    notes: str = ""
    items: List[dict] = []

class POReceiptItemUpdate(BaseModel):
    po_item_id: int
    qty_received: int
    cost_price: float

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
