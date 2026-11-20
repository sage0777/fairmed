"""
FairMed Dataset Service
Handles ingestion, cleaning, standardization, deduplication, and historical versioning
of official NPPA DPCO regulatory pricing datasets.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.medicine import Medicine
from app.models.medicine_alias import MedicineAlias
from app.models.pricing_record import PricingRecord
from app.models.source_document import SourceDocument
from app.utils.normalizer import clean_text, extract_strength, standardize_dosage_form
from app.utils.unit_converter import standardize_unit_label


class DatasetIngestionReport:
    def __init__(self):
        self.total_processed: int = 0
        self.medicines_created: int = 0
        self.aliases_created: int = 0
        self.pricing_records_created: int = 0
        self.superseded_records_updated: int = 0
        self.skipped_duplicates: int = 0
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "medicines_created": self.medicines_created,
            "aliases_created": self.aliases_created,
            "pricing_records_created": self.pricing_records_created,
            "superseded_records_updated": self.superseded_records_updated,
            "skipped_duplicates": self.skipped_duplicates,
            "errors": self.errors
        }


class DatasetService:
    @staticmethod
    def parse_date(date_val: Optional[str]) -> Optional[date]:
        if not date_val:
            return None
        if isinstance(date_val, date):
            return date_val
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_val, fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def ingest_nppa_dataset(cls, file_path: Path, db: Session) -> DatasetIngestionReport:
        report = DatasetIngestionReport()

        if not file_path.exists():
            report.errors.append(f"File not found: {file_path}")
            return report

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                records = json.load(f)
            except Exception as e:
                report.errors.append(f"JSON parsing error: {str(e)}")
                return report

        for entry in records:
            report.total_processed += 1
            try:
                cls._process_single_entry(entry, db, report)
            except Exception as e:
                report.errors.append(f"Error processing entry {entry.get('generic_name', 'unknown')}: {str(e)}")

        db.commit()
        return report

    @classmethod
    def _process_single_entry(cls, item: Dict[str, Any], db: Session, report: DatasetIngestionReport):
        raw_generic = item.get("generic_name", "").strip()
        raw_strength = item.get("strength") or extract_strength(raw_generic) or "Standard"
        dosage_form = standardize_dosage_form(item.get("dosage_form") or raw_generic)
        unit = standardize_unit_label(item.get("unit"), dosage_form)
        ceiling_price = Decimal(str(item.get("ceiling_price", 0)))
        notif_num = item.get("notification_number", "").strip()
        source_doc_name = item.get("source_document", "NPPA Price Notification")
        pub_date = cls.parse_date(item.get("publication_date"))
        effective_from = cls.parse_date(item.get("effective_from")) or date.today()
        effective_to = cls.parse_date(item.get("effective_to"))

        if not notif_num or ceiling_price <= 0:
            report.errors.append(f"Invalid record skipped (missing notification or zero price): {raw_generic}")
            return

        # 1. Source Document
        source_doc = db.query(SourceDocument).filter_by(notification_number=notif_num).first()
        if not source_doc:
            source_doc = SourceDocument(
                source_name=source_doc_name,
                issuing_authority="NPPA, Ministry of Chemicals and Fertilizers",
                notification_number=notif_num,
                publication_date=pub_date,
                effective_date=effective_from,
                document_url=item.get("document_url"),
                verification_status="VERIFIED"
            )
            db.add(source_doc)
            db.flush()

        # 2. Medicine lookup or creation
        medicine = db.query(Medicine).filter(
            Medicine.generic_name == raw_generic,
            Medicine.strength == raw_strength
        ).first()

        if not medicine:
            medicine = Medicine(
                generic_name=raw_generic,
                brand_name=item.get("brand_name"),
                active_ingredients=item.get("active_ingredients", raw_generic),
                strength=raw_strength,
                dosage_form=dosage_form,
                route=item.get("route", "Oral"),
                pack_size=item.get("pack_size"),
                manufacturer=item.get("manufacturer"),
                category=item.get("pricing_category", "DPCO_SCHEDULED_CEILING")
            )
            db.add(medicine)
            db.flush()
            report.medicines_created += 1

        # 3. Add brand aliases
        aliases = item.get("brand_aliases", [])
        for alias_name in aliases:
            clean_alias = clean_text(alias_name)
            existing_alias = db.query(MedicineAlias).filter_by(
                medicine_id=medicine.id,
                alias_name=clean_alias
            ).first()
            if not existing_alias:
                alias = MedicineAlias(
                    medicine_id=medicine.id,
                    alias_name=clean_alias,
                    alias_type="BRAND"
                )
                db.add(alias)
                report.aliases_created += 1

        # 4. Check existing pricing record
        existing_price = db.query(PricingRecord).filter_by(
            medicine_id=medicine.id,
            notification_number=notif_num
        ).first()

        if existing_price:
            report.skipped_duplicates += 1
            return

        # 5. Handle historical supersession (if an older active record exists, set effective_to)
        older_active_records = db.query(PricingRecord).filter(
            PricingRecord.medicine_id == medicine.id,
            PricingRecord.effective_from < effective_from,
            PricingRecord.effective_to.is_(None)
        ).all()

        for old_rec in older_active_records:
            old_rec.effective_to = effective_from - timedelta(days=1)
            report.superseded_records_updated += 1

        # 6. Insert new pricing record
        new_pricing = PricingRecord(
            medicine_id=medicine.id,
            pricing_category=item.get("pricing_category", "DPCO_SCHEDULED_CEILING"),
            price_type="CEILING_PRICE",
            ceiling_price=ceiling_price,
            notified_mrp=item.get("notified_mrp"),
            unit=unit,
            pack_size=item.get("pack_size"),
            effective_from=effective_from,
            effective_to=effective_to,
            notification_number=notif_num,
            source_document=source_doc_name,
            source_page=item.get("source_page", 1),
            verification_status="OFFICIAL_VERIFIED"
        )
        db.add(new_pricing)
        report.pricing_records_created += 1
