from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class IntermediateShopCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = ""
    photo_url: str = ""
    address: str = ""


class IntermediateShopUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    address: Optional[str] = None


class IntermediateShopResponse(BaseModel):
    id: int
    name: str
    phone: str
    photo_url: str = ""
    address: str = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
