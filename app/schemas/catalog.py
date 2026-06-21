from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class BrandResponse(BaseModel):
    id: int
    name: str
    active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class DeviceModelCreate(BaseModel):
    brand_id: int
    name: str = Field(..., min_length=1, max_length=200)
    sort_order: int = 0


class DeviceModelUpdate(BaseModel):
    brand_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class DeviceModelResponse(BaseModel):
    id: int
    brand_id: int
    name: str
    active: bool
    sort_order: int
    brand_name: str = ""

    model_config = ConfigDict(from_attributes=True)


class PartCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0


class PartCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None


class PartCategoryResponse(BaseModel):
    id: int
    name: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class PartTypeCreate(BaseModel):
    category_id: int
    name: str = Field(..., min_length=1, max_length=200)
    sort_order: int = 0


class PartTypeUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class PartTypeResponse(BaseModel):
    id: int
    category_id: int
    name: str
    active: bool
    sort_order: int
    category_name: str = ""

    model_config = ConfigDict(from_attributes=True)
