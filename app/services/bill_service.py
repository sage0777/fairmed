"""
FairMed Bill Service
Manages bill file upload, storage, OCR dispatch, item extraction, and persistence.
"""

import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bill import Bill
from app.models.extracted_item import ExtractedItem
from app.models.user import User
from app.repositories.bill_repo import BillRepository
from app.repositories.medicine_repo import MedicineRepository
from app.integrations.ocr_pipeline import OCRPipeline
from app.engines.matching_engine import MedicineMatchingEngine


class BillService:
    def __init__(self, db: Session):
        self.db = db
        self.bill_repo = BillRepository(db)
        self.med_repo = MedicineRepository(db)

    def upload_bill(self, file: UploadFile, user: User) -> Bill:
        """Validates file, writes to secure storage, and records bill entry."""
        # Validate extension
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{file_ext}'. Allowed formats: PDF, PNG, JPG, JPEG."
            )

        # Generate unique storage filename
        stored_filename = f"bill_{uuid.uuid4().hex}{file_ext}"
        target_path = settings.UPLOAD_DIR / stored_filename

        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        bill = Bill(
            user_id=user.id,
            file_path=str(target_path),
            hospital_name="Pending Extraction",
            status="UPLOADED"
        )
        return self.bill_repo.create(bill)

    def extract_and_match_bill(self, bill_id: str, user: User) -> Bill:
        """Executes OCR extraction and initial medicine matching on a bill."""
        bill = self.bill_repo.get_by_id(bill_id, user_id=user.id)
        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bill not found or you do not have permission to access it."
            )

        file_path = Path(bill.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uploaded file not found on disk."
            )

        # 1. OCR Extraction
        text = OCRPipeline.extract_text_from_file(file_path)
        metadata = OCRPipeline.parse_bill_metadata(text)
        raw_items = OCRPipeline.parse_medicine_line_items(text)

        # Update bill metadata
        bill.hospital_name = metadata.get("hospital_name") or bill.hospital_name
        bill.bill_date = metadata.get("bill_date") or bill.bill_date
        bill.status = "OCR_EXTRACTED"

        # 2. Match extracted items against medicine database
        registry = self.med_repo.get_all_for_matching()
        matching_engine = MedicineMatchingEngine(registry)

        extracted_entities = []
        for item in raw_items:
            match_res = matching_engine.match(item.medicine_name)
            matched_id = match_res.matched_candidate.medicine_id if match_res.matched_candidate else None
            
            ent = ExtractedItem(
                bill_id=bill.id,
                extracted_medicine_name=item.medicine_name,
                extracted_strength=item.strength,
                dosage_form=item.dosage_form,
                quantity=item.quantity,
                billed_unit_price=item.unit_price,
                billed_total=item.total_amount,
                matched_medicine_id=matched_id,
                confidence_score=match_res.overall_confidence,
                verification_status=match_res.verification_status
            )
            extracted_entities.append(ent)

        if extracted_entities:
            self.bill_repo.add_extracted_items(extracted_entities)

        self.db.commit()
        self.db.refresh(bill)
        return bill
