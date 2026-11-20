import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    upload_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    bill_date = Column(Date, nullable=True, index=True)
    hospital_name = Column(String(255), nullable=True)
    status = Column(String(50), default="UPLOADED")  # UPLOADED, OCR_EXTRACTED, AUDITED, FAILED

    user = relationship("User", back_populates="bills")
    extracted_items = relationship("ExtractedItem", back_populates="bill", cascade="all, delete-orphan")
    audits = relationship("Audit", back_populates="bill", cascade="all, delete-orphan")
