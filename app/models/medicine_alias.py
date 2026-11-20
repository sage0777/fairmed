import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class MedicineAlias(Base):
    __tablename__ = "medicine_aliases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medicine_id = Column(String(36), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_name = Column(String(255), nullable=False, index=True)
    alias_type = Column(String(50), default="BRAND", nullable=False)  # BRAND, GENERIC, SPELLING_VARIANT

    medicine = relationship("Medicine", back_populates="aliases")
