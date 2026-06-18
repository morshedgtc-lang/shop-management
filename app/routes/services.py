from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse
from app.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services = db.query(Service).all()
    return services


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    db.delete(service)
    db.commit()
