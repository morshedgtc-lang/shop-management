from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    model = Column(String, default="")
    sku = Column(String, unique=True, nullable=True)
    supplier_barcode = Column(String, default="")
    stock_qty = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    currency = Column(String, default="USD")
    min_stock_alert = Column(Integer, default=5)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("device_models.id"), nullable=True)
    part_type_id = Column(Integer, ForeignKey("part_types.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    brand = relationship("Brand")
    device_model = relationship("DeviceModel")
    part_type = relationship("PartType")
