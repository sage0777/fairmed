"""
FairMed Audit Repository
Database operations for audits and audit results.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.audit import Audit
from app.models.audit_result import AuditResult


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_audit(self, audit: Audit) -> Audit:
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def get_by_id(self, audit_id: str) -> Optional[Audit]:
        return self.db.query(Audit).options(
            joinedload(Audit.results).joinedload(AuditResult.extracted_item),
            joinedload(Audit.results).joinedload(AuditResult.pricing_record),
            joinedload(Audit.bill)
        ).filter(Audit.id == audit_id).first()

    def get_by_bill_id(self, bill_id: str) -> Optional[Audit]:
        return self.db.query(Audit).options(
            joinedload(Audit.results).joinedload(AuditResult.extracted_item),
            joinedload(Audit.results).joinedload(AuditResult.pricing_record),
            joinedload(Audit.bill)
        ).filter(Audit.bill_id == bill_id).order_by(Audit.audit_date.desc()).first()

    def add_audit_results(self, results: List[AuditResult]) -> List[AuditResult]:
        self.db.add_all(results)
        self.db.commit()
        return results

    def get_results(self, audit_id: str) -> List[AuditResult]:
        return self.db.query(AuditResult).options(
            joinedload(AuditResult.extracted_item),
            joinedload(AuditResult.pricing_record)
        ).filter(AuditResult.audit_id == audit_id).all()
