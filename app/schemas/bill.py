"""
FairMed Schemas - Bills
Pydantic schemas for hospital bill uploads, summary, and detail views.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.ocr import ExtractedItemSchema


class BillUploadResponse(BaseModel):
    bill_id: str
    file_name: str
    hospital_name: Optional[str] = None
    bill_date: Optional[date] = None
    status: str
    message: str


class BillSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    file_path: str
    upload_date: datetime
    bill_date: Optional[date] = None
    hospital_name: Optional[str] = None
    status: str
    item_count: int = 0


class BillDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    file_path: str
    upload_date: datetime
    bill_date: Optional[date] = None
    hospital_name: Optional[str] = None
    status: str
    extracted_items: List[ExtractedItemSchema] = []
