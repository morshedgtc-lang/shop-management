from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (await db.execute(select(Service))).scalars().all()
    return rows


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    service = Service(**data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    await db.delete(service)
    await db.commit()
