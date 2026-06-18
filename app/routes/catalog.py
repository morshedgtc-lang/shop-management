from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.brand import Brand
from app.models.device_model import DeviceModel
from app.models.part_category import PartCategory
from app.models.part_type import PartType
from app.models.user import User
from app.schemas.catalog import (
    BrandCreate, BrandUpdate, BrandResponse,
    DeviceModelCreate, DeviceModelUpdate, DeviceModelResponse,
    PartCategoryCreate, PartCategoryUpdate, PartCategoryResponse,
    PartTypeCreate, PartTypeUpdate, PartTypeResponse,
)
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

# === BRANDS ===

@router.get("/brands", response_model=list[BrandResponse])
def list_brands(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Brand).order_by(Brand.sort_order, Brand.name).all()

@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(data: BrandCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    existing = db.query(Brand).filter(Brand.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Brand already exists")
    brand = Brand(**data.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand

@router.put("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(brand_id: int, data: BrandUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return brand

@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(brand_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand.active = False
    db.commit()

# === DEVICE MODELS ===

@router.get("/models", response_model=list[DeviceModelResponse])
def list_models(brand_id: Optional[int] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(DeviceModel).filter(DeviceModel.active == True)
    if brand_id:
        query = query.filter(DeviceModel.brand_id == brand_id)
    models = query.order_by(DeviceModel.sort_order, DeviceModel.name).all()
    result = []
    for m in models:
        resp = DeviceModelResponse.model_validate(m)
        resp.brand_name = m.brand.name if m.brand else ""
        result.append(resp)
    return result

@router.post("/models", response_model=DeviceModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(data: DeviceModelCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    model = DeviceModel(**data.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    resp = DeviceModelResponse.model_validate(model)
    resp.brand_name = model.brand.name if model.brand else ""
    return resp

@router.put("/models/{model_id}", response_model=DeviceModelResponse)
def update_model(model_id: int, data: DeviceModelUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    model = db.query(DeviceModel).filter(DeviceModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    db.commit()
    db.refresh(model)
    resp = DeviceModelResponse.model_validate(model)
    resp.brand_name = model.brand.name if model.brand else ""
    return resp

@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    model = db.query(DeviceModel).filter(DeviceModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    model.active = False
    db.commit()

# === PART CATEGORIES ===

@router.get("/categories", response_model=list[PartCategoryResponse])
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(PartCategory).order_by(PartCategory.sort_order).all()

@router.post("/categories", response_model=PartCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: PartCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    existing = db.query(PartCategory).filter(PartCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = PartCategory(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.put("/categories/{cat_id}", response_model=PartCategoryResponse)
def update_category(cat_id: int, data: PartCategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = db.query(PartCategory).filter(PartCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(cat_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = db.query(PartCategory).filter(PartCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()

# === PART TYPES ===

@router.get("/types", response_model=list[PartTypeResponse])
def list_part_types(category_id: Optional[int] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(PartType).filter(PartType.active == True)
    if category_id:
        query = query.filter(PartType.category_id == category_id)
    types = query.order_by(PartType.sort_order, PartType.name).all()
    result = []
    for t in types:
        resp = PartTypeResponse.model_validate(t)
        resp.category_name = t.category.name if t.category else ""
        result.append(resp)
    return result

@router.post("/types", response_model=PartTypeResponse, status_code=status.HTTP_201_CREATED)
def create_part_type(data: PartTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    pt = PartType(**data.model_dump())
    db.add(pt)
    db.commit()
    db.refresh(pt)
    resp = PartTypeResponse.model_validate(pt)
    resp.category_name = pt.category.name if pt.category else ""
    return resp

@router.put("/types/{type_id}", response_model=PartTypeResponse)
def update_part_type(type_id: int, data: PartTypeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    pt = db.query(PartType).filter(PartType.id == type_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Part type not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pt, key, value)
    db.commit()
    db.refresh(pt)
    resp = PartTypeResponse.model_validate(pt)
    resp.category_name = pt.category.name if pt.category else ""
    return resp

@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part_type(type_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    pt = db.query(PartType).filter(PartType.id == type_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Part type not found")
    pt.active = False
    db.commit()
