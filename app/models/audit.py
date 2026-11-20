import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Audit(Base):
    __tablename__ = "audits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_id = Column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    total_items = Column(Integer, default=0)
    verified_items = Column(Integer, default=0)
    flagged_items = Column(Integer, default=0)
    total_potential_difference = Column(Numeric(12, 4), default=0.00)
    audit_status = Column(String(50), default="COMPLETED")  # IN_PROGRESS, COMPLETED, FAILED

    bill = relationship("Bill", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit", cascade="all, delete-orphan")
