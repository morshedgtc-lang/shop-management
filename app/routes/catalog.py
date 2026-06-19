from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.brand import Brand
from app.models.device_model import DeviceModel
from app.models.part_category import PartCategory
from app.models.part_type import PartType
from app.schemas.catalog import (
    BrandCreate, BrandUpdate, BrandResponse,
    DeviceModelCreate, DeviceModelUpdate, DeviceModelResponse,
    PartCategoryCreate, PartCategoryUpdate, PartCategoryResponse,
    PartTypeCreate, PartTypeUpdate, PartTypeResponse,
)
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/brands", response_model=list[BrandResponse])
async def list_brands(db=Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(Brand).order_by(Brand.sort_order, Brand.name))).scalars().all()
    return rows


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(data: BrandCreate, db=Depends(get_db), current_user=Depends(require_admin)):
    existing = (await db.execute(select(Brand).where(Brand.name == data.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Brand already exists")
    brand = Brand(**data.model_dump())
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


@router.put("/brands/{brand_id}", response_model=BrandResponse)
async def update_brand(brand_id: int, data: BrandUpdate, db=Depends(get_db), current_user=Depends(require_admin)):
    brand = (await db.execute(select(Brand).where(Brand.id == brand_id))).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, key, value)
    await db.commit()
    await db.refresh(brand)
    return brand


@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(brand_id: int, db=Depends(get_db), current_user=Depends(require_admin)):
    brand = (await db.execute(select(Brand).where(Brand.id == brand_id))).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand.active = False
    await db.commit()


@router.get("/models", response_model=list[DeviceModelResponse])
async def list_models(brand_id: Optional[int] = Query(None), db=Depends(get_db), current_user=Depends(get_current_user)):
    query = select(DeviceModel).where(DeviceModel.active == True)
    if brand_id:
        query = query.where(DeviceModel.brand_id == brand_id)
    models = (await db.execute(query.order_by(DeviceModel.sort_order, DeviceModel.name))).scalars().all()
    result = []
    for m in models:
        resp = DeviceModelResponse.model_validate(m)
        resp.brand_name = m.brand.name if m.brand else ""
        result.append(resp)
    return result


@router.post("/models", response_model=DeviceModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(data: DeviceModelCreate, db=Depends(get_db), current_user=Depends(require_admin)):
    model = DeviceModel(**data.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    resp = DeviceModelResponse.model_validate(model)
    resp.brand_name = model.brand.name if model.brand else ""
    return resp


@router.put("/models/{model_id}", response_model=DeviceModelResponse)
async def update_model(model_id: int, data: DeviceModelUpdate, db=Depends(get_db), current_user=Depends(require_admin)):
    model = (await db.execute(select(DeviceModel).where(DeviceModel.id == model_id))).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    await db.commit()
    await db.refresh(model)
    resp = DeviceModelResponse.model_validate(model)
    resp.brand_name = model.brand.name if model.brand else ""
    return resp


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: int, db=Depends(get_db), current_user=Depends(require_admin)):
    model = (await db.execute(select(DeviceModel).where(DeviceModel.id == model_id))).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    model.active = False
    await db.commit()


@router.get("/categories", response_model=list[PartCategoryResponse])
async def list_categories(db=Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(PartCategory).order_by(PartCategory.sort_order))).scalars().all()
    return rows


@router.post("/categories", response_model=PartCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: PartCategoryCreate, db=Depends(get_db), current_user=Depends(require_admin)):
    existing = (await db.execute(select(PartCategory).where(PartCategory.name == data.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = PartCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/categories/{cat_id}", response_model=PartCategoryResponse)
async def update_category(cat_id: int, data: PartCategoryUpdate, db=Depends(get_db), current_user=Depends(require_admin)):
    cat = (await db.execute(select(PartCategory).where(PartCategory.id == cat_id))).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(cat_id: int, db=Depends(get_db), current_user=Depends(require_admin)):
    cat = (await db.execute(select(PartCategory).where(PartCategory.id == cat_id))).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()


@router.get("/types", response_model=list[PartTypeResponse])
async def list_part_types(category_id: Optional[int] = Query(None), db=Depends(get_db), current_user=Depends(get_current_user)):
    query = select(PartType).where(PartType.active == True)
    if category_id:
        query = query.where(PartType.category_id == category_id)
    types = (await db.execute(query.order_by(PartType.sort_order, PartType.name))).scalars().all()
    result = []
    for t in types:
        resp = PartTypeResponse.model_validate(t)
        resp.category_name = t.category.name if t.category else ""
        result.append(resp)
    return result


@router.post("/types", response_model=PartTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_part_type(data: PartTypeCreate, db=Depends(get_db), current_user=Depends(require_admin)):
    pt = PartType(**data.model_dump())
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    resp = PartTypeResponse.model_validate(pt)
    resp.category_name = pt.category.name if pt.category else ""
    return resp


@router.put("/types/{type_id}", response_model=PartTypeResponse)
async def update_part_type(type_id: int, data: PartTypeUpdate, db=Depends(get_db), current_user=Depends(require_admin)):
    pt = (await db.execute(select(PartType).where(PartType.id == type_id))).scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Part type not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pt, key, value)
    await db.commit()
    await db.refresh(pt)
    resp = PartTypeResponse.model_validate(pt)
    resp.category_name = pt.category.name if pt.category else ""
    return resp


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part_type(type_id: int, db=Depends(get_db), current_user=Depends(require_admin)):
    pt = (await db.execute(select(PartType).where(PartType.id == type_id))).scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Part type not found")
    pt.active = False
    await db.commit()
