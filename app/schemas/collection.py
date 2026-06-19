from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CollectionItemCreate(BaseModel):
    repair_id: int
    amount_paid: float = Field(0, ge=0)
    discount_amount: float = Field(0, ge=0)


class CollectionItemResponse(BaseModel):
    id: int
    collection_run_id: int
    repair_id: int
    amount_paid: float
    discount_amount: float = 0
    repair_model: str = ""
    repair_status: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectionRunCreate(BaseModel):
    shop_id: int
    notes: str = ""
    items: List[CollectionItemCreate] = []


class CollectionRunResponse(BaseModel):
    id: int
    shop_id: int
    shop_name: str = ""
    collected_by: int
    collector_name: str = ""
    total_collected: float = 0
    notes: str = ""
    collected_at: Optional[datetime] = None
    items: List[CollectionItemResponse] = []

    class Config:
        from_attributes = True


class PendingCollectionResponse(BaseModel):
    repair_id: int
    customer_name: str = ""
    model: str
    total_amount: float
    parts_cost: float
    service_fee: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShopSummaryResponse(BaseModel):
    shop_id: int
    shop_name: str
    total_pending: float = 0
    total_collected: float = 0
    pending_count: int = 0
