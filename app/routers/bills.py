"""
FairMed Bills Router
Endpoints for uploading, listing, viewing, and deleting hospital medical bills.
"""

from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.bill import BillUploadResponse, BillSummaryResponse, BillDetailResponse
from app.services.bill_service import BillService
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api/bills", tags=["Bills"])


@router.post("/upload", response_model=BillUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_medical_bill(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a hospital medical bill (PDF or image).
    Stores the file securely and initializes the bill record.
    """
    bill_svc = BillService(db)
    bill = bill_svc.upload_bill(file, current_user)
    return BillUploadResponse(
        bill_id=bill.id,
        file_name=Path(bill.file_path).name,
        hospital_name=bill.hospital_name,
        bill_date=bill.bill_date,
        status=bill.status,
        message="Medical bill uploaded successfully. Ready for OCR extraction."
    )


@router.get("/", response_model=List[BillSummaryResponse])
def list_user_bills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all medical bills uploaded by the authenticated user."""
    bill_svc = BillService(db)
    bills = bill_svc.bill_repo.get_by_user(current_user.id)
    summaries = []
    for b in bills:
        summaries.append(
            BillSummaryResponse(
                id=b.id,
                user_id=b.user_id,
                file_path=b.file_path,
                upload_date=b.upload_date,
                bill_date=b.bill_date,
                hospital_name=b.hospital_name,
                status=b.status,
                item_count=len(b.extracted_items)
            )
        )
    return summaries


@router.get("/{bill_id}", response_model=BillDetailResponse)
def get_bill_detail(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full details and extracted line items of a specific bill."""
    bill_svc = BillService(db)
    bill = bill_svc.bill_repo.get_by_id(bill_id, user_id=current_user.id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found."
        )
    return bill


@router.delete("/{bill_id}", status_code=status.HTTP_200_OK)
def delete_medical_bill(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a medical bill and its associated line items and audits."""
    bill_svc = BillService(db)
    bill = bill_svc.bill_repo.get_by_id(bill_id, user_id=current_user.id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found."
        )
    
    # Remove file from disk if exists
    try:
        p = Path(bill.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    bill_svc.bill_repo.delete(bill)
    return {"message": f"Bill {bill_id} deleted successfully."}
