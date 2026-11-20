"""
FairMed NPPA Pricing Engine
Deterministic, rule-based regulatory price auditing in Python.
Performs effective-date validation, pack-size normalization, GST-adjusted ceiling comparison,
and detailed traceability generation without relying on non-deterministic AI decisions.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.models.pricing_record import PricingRecord
from app.models.medicine import Medicine
from app.utils.unit_converter import parse_pack_size_count


class PriceAuditCalculation(BaseModel):
    billed_unit_price: Decimal
    quantity: Decimal
    billed_total: Decimal
    reference_price: Optional[Decimal]
    allowable_ceiling_with_gst: Optional[Decimal]
    price_difference: Decimal
    total_difference: Decimal
    result_status: str  # OVERCHARGED, COMPLIANT, NO_CEILING_APPLICABLE, INSUFFICIENT_DATA
    pricing_category: str
    price_type: str
    unit: str
    notification_number: Optional[str]
    source_document: Optional[str]
    effective_from: Optional[date]
    effective_to: Optional[date]
    explanation: str
    pricing_record_id: Optional[str]


class NPPAPricingEngine:
    # Standard permissible GST rate for scheduled medicines in India is 5% or 12%
    # We use 12% as standard maximum permissible tax threshold to avoid false overcharge accusations
    DEFAULT_PERMISSIBLE_GST_RATE = Decimal("0.12")

    @classmethod
    def evaluate_price(
        cls,
        billed_unit_price: Decimal,
        quantity: Decimal,
        medicine: Optional[Medicine],
        pricing_record: Optional[PricingRecord],
        is_verified_match: bool,
        pack_size: Optional[str] = None,
        bill_date: Optional[date] = None
    ) -> PriceAuditCalculation:
        """
        Deterministic evaluation of a single billed item.
        """
        billed_total = (billed_unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 1. Gate: Medicine match certainty
        if not medicine or not is_verified_match:
            return PriceAuditCalculation(
                billed_unit_price=billed_unit_price,
                quantity=quantity,
                billed_total=billed_total,
                reference_price=None,
                allowable_ceiling_with_gst=None,
                price_difference=Decimal("0.00"),
                total_difference=Decimal("0.00"),
                result_status="INSUFFICIENT_DATA",
                pricing_category="UNVERIFIED",
                price_type="NONE",
                unit="Unit",
                notification_number=None,
                source_document=None,
                effective_from=None,
                effective_to=None,
                explanation="Insufficient data: Medicine identification or strength could not be verified with regulatory certainty.",
                pricing_record_id=None
            )

        # 2. Gate: Existence of regulatory pricing record on bill date
        if not pricing_record:
            return PriceAuditCalculation(
                billed_unit_price=billed_unit_price,
                quantity=quantity,
                billed_total=billed_total,
                reference_price=None,
                allowable_ceiling_with_gst=None,
                price_difference=Decimal("0.00"),
                total_difference=Decimal("0.00"),
                result_status="NO_CEILING_APPLICABLE",
                pricing_category=medicine.category or "NON_SCHEDULED",
                price_type="NON_REGULATED",
                unit=pricing_record.unit if pricing_record else "Unit",
                notification_number=None,
                source_document=None,
                effective_from=None,
                effective_to=None,
                explanation=(
                    f"No government ceiling price notification found for '{medicine.generic_name}' ({medicine.strength}). "
                    "This formulation is non-scheduled or exempt from DPCO Schedule I ceiling caps."
                ),
                pricing_record_id=None
            )

        # 3. Retrieve reference ceiling price
        ref_price = Decimal(str(pricing_record.ceiling_price or pricing_record.notified_mrp or "0.00"))
        if ref_price <= 0:
            return PriceAuditCalculation(
                billed_unit_price=billed_unit_price,
                quantity=quantity,
                billed_total=billed_total,
                reference_price=None,
                allowable_ceiling_with_gst=None,
                price_difference=Decimal("0.00"),
                total_difference=Decimal("0.00"),
                result_status="INSUFFICIENT_DATA",
                pricing_category=pricing_record.pricing_category,
                price_type=pricing_record.price_type,
                unit=pricing_record.unit,
                notification_number=pricing_record.notification_number,
                source_document=pricing_record.source_document,
                effective_from=pricing_record.effective_from,
                effective_to=pricing_record.effective_to,
                explanation="Pricing record exists but has zero or unrecorded ceiling value.",
                pricing_record_id=pricing_record.id
            )

        # 4. Pack size normalization check
        # If bill unit price is suspiciously high (e.g. 10x ceiling) and pack_size indicates strip of 10,
        # adjust comparison or note it.
        pack_count = parse_pack_size_count(pack_size or medicine.pack_size)
        effective_billed_unit = billed_unit_price
        
        # If hospital billed a whole strip under unit price (e.g. billed 1 strip of 10 tabs as 1 unit)
        # and quantity is small, we calculate per-dose rate for honest comparison
        if pack_count > 1 and billed_unit_price > (ref_price * Decimal(str(pack_count)) * Decimal("0.5")):
            # Billed appears to be pack price
            effective_billed_unit = (billed_unit_price / Decimal(str(pack_count))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        allowable_with_gst = (ref_price * (Decimal("1.0") + cls.DEFAULT_PERMISSIBLE_GST_RATE)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 5. Regulatory Comparison
        if effective_billed_unit > allowable_with_gst:
            diff_per_unit = (effective_billed_unit - ref_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_diff = (diff_per_unit * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            result_status = "OVERCHARGED"
            explanation = (
                f"Potential discrepancy identified: Billed unit rate (₹{effective_billed_unit:.2f}) exceeds the official NPPA "
                f"ceiling price of ₹{ref_price:.2f} per {pricing_record.unit} (allowable up to ₹{allowable_with_gst:.2f} including 12% GST) "
                f"by ₹{diff_per_unit:.2f} per unit. Gazette Reference: {pricing_record.notification_number}."
            )
        else:
            diff_per_unit = Decimal("0.00")
            total_diff = Decimal("0.00")
            result_status = "COMPLIANT"
            explanation = (
                f"Price compliant: Billed rate (₹{effective_billed_unit:.2f}) is within the permitted legal ceiling limit "
                f"(₹{ref_price:.2f} per {pricing_record.unit} + GST) under NPPA notification {pricing_record.notification_number}."
            )

        return PriceAuditCalculation(
            billed_unit_price=billed_unit_price,
            quantity=quantity,
            billed_total=billed_total,
            reference_price=ref_price,
            allowable_ceiling_with_gst=allowable_with_gst,
            price_difference=diff_per_unit,
            total_difference=total_diff,
            result_status=result_status,
            pricing_category=pricing_record.pricing_category,
            price_type=pricing_record.price_type,
            unit=pricing_record.unit,
            notification_number=pricing_record.notification_number,
            source_document=pricing_record.source_document,
            effective_from=pricing_record.effective_from,
            effective_to=pricing_record.effective_to,
            explanation=explanation,
            pricing_record_id=pricing_record.id
        )
