"""
FairMed End-to-End Pipeline CLI Validator
Simulates complete workflow:
1. User Registration / Auth
2. Bill Upload
3. OCR Extraction
4. RapidFuzz Medicine Matching
5. Deterministic NPPA Pricing Audit
6. Grievance Report PDF Generation
"""

import sys
from pathlib import Path
from decimal import Decimal

# Ensure utf-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal, init_db
from app.models.user import User
from app.security.password import hash_password
from app.services.bill_service import BillService
from app.services.audit_service import AuditService
from app.services.report_service import ReportService
from app.config import settings


def main():
    print("=" * 65)
    print("FairMed End-to-End Pipeline Validation")
    print("=" * 65)

    init_db()
    db = SessionLocal()

    # 1. Setup Test User
    test_email = "test.patient@fairmed.org"
    user = db.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(
            full_name="Ramesh Verma (Test Patient)",
            email=test_email,
            password_hash=hash_password("Password123!")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[1] Test user prepared: {user.email} (ID: {user.id})")
    else:
        print(f"[1] Existing test user loaded: {user.email}")

    # 2. Bill Upload
    sample_bill_path = settings.DATASETS_DIR / "sample_hospital_bill.pdf"
    if not sample_bill_path.exists():
        print(f"[!] Sample bill not found at {sample_bill_path}. Generating it...")
        from scripts.seed_sample_bills import generate_sample_bill_pdf
        generate_sample_bill_pdf(sample_bill_path)

    import uuid, shutil
    stored_name = f"bill_{uuid.uuid4().hex}.pdf"
    dest_path = settings.UPLOAD_DIR / stored_name
    shutil.copyfile(sample_bill_path, dest_path)

    from app.models.bill import Bill
    bill = Bill(
        user_id=user.id,
        file_path=str(dest_path),
        hospital_name="Apollo Care Multispeciality Hospital",
        status="UPLOADED"
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    print(f"[2] Bill created: ID={bill.id}")

    # 3. OCR Extraction & Matching
    bill_svc = BillService(db)
    bill = bill_svc.extract_and_match_bill(bill.id, user)
    extracted_items = bill_svc.bill_repo.get_extracted_items(bill.id)
    print(f"[3] OCR extraction extracted {len(extracted_items)} items from bill:")
    for idx, item in enumerate(extracted_items, 1):
        print(f"    {idx}. '{item.extracted_medicine_name}' -> Strength: {item.extracted_strength}, "
              f"Rate: Rs.{item.billed_unit_price}, Qty: {item.quantity}, Status: {item.verification_status}")

    # 4. Regulatory Audit
    print(f"[4] Running deterministic NPPA pricing audit...")
    audit_svc = AuditService(db)
    audit = audit_svc.run_bill_audit(bill.id, user)
    print(f"    Audit ID: {audit.id}")
    print(f"    Total items: {audit.total_items}")
    print(f"    Verified items: {audit.verified_items}")
    print(f"    Flagged overcharging items: {audit.flagged_items}")
    print(f"    Total potential difference: Rs.{audit.total_potential_difference:.2f}")

    print("\n--- Detailed Audit Results ---")
    for r in audit.results:
        ext = r.extracted_item
        print(f"  * {ext.extracted_medicine_name}: Billed=Rs.{r.billed_price:.2f}, "
              f"NPPA Ceiling=Rs.{r.reference_price or 0:.2f}, Status={r.result_status}, "
              f"Diff/Unit=Rs.{r.price_difference:.2f}, TotalDiff=Rs.{r.total_difference:.2f}")

    # 5. PDF Grievance Report Generation
    print(f"\n[5] Generating formal ReportLab PDF Grievance Report...")
    pdf_path = ReportService.generate_pdf_report(audit)
    print(f"    Report generated: {pdf_path} (Size: {pdf_path.stat().st_size} bytes)")

    db.close()
    print("\n" + "=" * 65)
    print("[SUCCESS] End-to-end FairMed pipeline validated successfully!")
    print("=" * 65)


if __name__ == "__main__":
    main()
