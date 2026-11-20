import uuid
from sqlalchemy import Column, String, Text, Date
from app.database import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_name = Column(String(255), nullable=False)
    issuing_authority = Column(String(255), default="NPPA, Ministry of Chemicals and Fertilizers")
    notification_number = Column(String(100), nullable=False, index=True)
    publication_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=False)
    document_url = Column(Text, nullable=True)
    file_hash = Column(String(128), nullable=True)
    verification_status = Column(String(50), default="VERIFIED")  # VERIFIED, PROVISIONAL, PENDING_REVIEW
