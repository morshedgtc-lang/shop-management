from pydantic import BaseModel
from typing import Optional

class BrandCreate(BaseModel):
    name: str
    sort_order: int = 0

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None

class BrandResponse(BaseModel):
    id: int
    name: str
    active: bool
    sort_order: int
    class Config:
        from_attributes = True

class DeviceModelCreate(BaseModel):
    brand_id: int
    name: str
    sort_order: int = 0

class DeviceModelUpdate(BaseModel):
    brand_id: Optional[int] = None
    name: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None

class DeviceModelResponse(BaseModel):
    id: int
    brand_id: int
    name: str
    active: bool
    sort_order: int
    brand_name: str = ""
    class Config:
        from_attributes = True

class PartCategoryCreate(BaseModel):
    name: str
    sort_order: int = 0

class PartCategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None

class PartCategoryResponse(BaseModel):
    id: int
    name: str
    sort_order: int
    class Config:
        from_attributes = True

class PartTypeCreate(BaseModel):
    category_id: int
    name: str
    sort_order: int = 0

class PartTypeUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None

class PartTypeResponse(BaseModel):
    id: int
    category_id: int
    name: str
    active: bool
    sort_order: int
    category_name: str = ""
    class Config:
        from_attributes = True
