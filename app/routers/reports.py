"""
FairMed Reports Router
Endpoints for generating and downloading PDF audit & grievance reports.
"""

from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.report import ReportGenerateResponse
from app.repositories.audit_repo import AuditRepository
from app.services.report_service import ReportService
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post("/generate/{audit_id}", response_model=ReportGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_grievance_report(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a formal ReportLab PDF audit and legal grievance petition report
    ready for submission to the hospital billing desk, National Consumer Helpline, or NPPA IPDMS.
    """
    audit_repo = AuditRepository(db)
    audit = audit_repo.get_by_id(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found."
        )

    if audit.bill.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to generate reports for this audit."
        )

    pdf_path = ReportService.generate_pdf_report(audit)
    file_size = pdf_path.stat().st_size
    report_id = pdf_path.stem

    return ReportGenerateResponse(
        report_id=report_id,
        audit_id=audit.id,
        file_name=pdf_path.name,
        file_size_bytes=file_size,
        download_url=f"/api/reports/{report_id}",
        created_at=datetime.now(timezone.utc),
        message="Grievance PDF report generated successfully."
    )


@router.get("/{report_id}")
def download_grievance_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Downloads the generated PDF report."""
    from app.config import settings
    pdf_file = settings.REPORTS_DIR / f"{report_id}.pdf"
    if not pdf_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested report PDF file not found."
        )

    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"{report_id}.pdf"
    )
