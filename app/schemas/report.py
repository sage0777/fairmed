"""
FairMed Schemas - Grievance Reports
Pydantic schemas for generating and retrieving PDF grievance reports.
"""

from datetime import datetime
from pydantic import BaseModel


class ReportGenerateResponse(BaseModel):
    report_id: str
    audit_id: str
    file_name: str
    file_size_bytes: int
    download_url: str
    created_at: datetime
    message: str


class ReportDetailResponse(BaseModel):
    report_id: str
    audit_id: str
    file_path: str
    file_name: str
    created_at: datetime
