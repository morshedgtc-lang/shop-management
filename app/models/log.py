from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.database import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default="info", index=True)
    source = Column(String, index=True, default="system")
    action = Column(String, index=True)
    user_id = Column(Integer, nullable=True)
    user_name = Column(String, default="")
    details = Column(Text, default="")
    ip_address = Column(String, default="")
    entity_type = Column(String, default="")
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
