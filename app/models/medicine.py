import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    generic_name = Column(String(255), nullable=False, index=True)
    brand_name = Column(String(255), nullable=True, index=True)
    active_ingredients = Column(Text, nullable=False)
    strength = Column(String(100), nullable=False, index=True)
    dosage_form = Column(String(100), nullable=False)
    route = Column(String(100), nullable=True)
    pack_size = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    category = Column(String(100), default="SCHEDULED")  # SCHEDULED, NON_SCHEDULED, ONCOLOGY
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    aliases = relationship("MedicineAlias", back_populates="medicine", cascade="all, delete-orphan")
    pricing_records = relationship("PricingRecord", back_populates="medicine", cascade="all, delete-orphan")
    extracted_items = relationship("ExtractedItem", back_populates="matched_medicine")
