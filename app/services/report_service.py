"""
FairMed Grievance Report Service
Generates formal audit summary and legal grievance petition PDFs using ReportLab.
"""

from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.config import settings
from app.models.audit import Audit
from app.models.audit_result import AuditResult
from app.models.bill import Bill


class ReportService:
    @classmethod
    def generate_pdf_report(cls, audit: Audit) -> Path:
        """
        Builds a comprehensive audit and formal grievance report PDF.
        """
        report_filename = f"FairMed_Audit_Report_{audit.id[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        output_path = settings.REPORTS_DIR / report_filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e3a8a"),
            alignment=1
        )
        subtitle_style = ParagraphStyle(
            "SubtitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            alignment=1
        )
        section_style = ParagraphStyle(
            "SectionStyle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1f2937")
        )
        bold_body = ParagraphStyle(
            "BoldBody",
            parent=body_style,
            fontName="Helvetica-Bold"
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b7280")
        )

        elements = []

        # Header Title
        elements.append(Paragraph("FAIRMED - MEDICAL BILL AUDIT REPORT", title_style))
        elements.append(Paragraph("Independent Regulatory Compliance & Price Discrepancy Verification", subtitle_style))
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=12))

        # Bill & Audit Information Table
        bill = audit.bill
        hospital_name = bill.hospital_name or "Hospital / Healthcare Facility"
        bill_date_str = bill.bill_date.strftime("%d-%b-%Y") if bill.bill_date else "N/A"
        audit_date_str = audit.audit_date.strftime("%d-%b-%Y %H:%M UTC")

        info_data = [
            [
                Paragraph("<b>Audit ID:</b> " + audit.id, body_style),
                Paragraph("<b>Bill Date:</b> " + bill_date_str, body_style)
            ],
            [
                Paragraph("<b>Hospital / Provider:</b> " + hospital_name, body_style),
                Paragraph("<b>Audit Date:</b> " + audit_date_str, body_style)
            ],
            [
                Paragraph("<b>Status:</b> " + audit.audit_status, body_style),
                Paragraph(f"<b>Total Items Analyzed:</b> {audit.total_items}", body_style)
            ]
        ]
        info_table = Table(info_data, colWidths=[270, 270])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 14))

        # Executive Metrics Box
        flagged_count = audit.flagged_items or 0
        total_diff = Decimal(str(audit.total_potential_difference or 0.00))
        flag_bg = colors.HexColor("#fee2e2") if flagged_count > 0 else colors.HexColor("#dcfce7")
        flag_border = colors.HexColor("#ef4444") if flagged_count > 0 else colors.HexColor("#22c55e")

        summary_data = [
            [
                Paragraph(f"<b>Flagged Discrepancies:</b> {flagged_count} item(s)", bold_body),
                Paragraph(f"<b>Verified Regulated Items:</b> {audit.verified_items or 0}", bold_body),
                Paragraph(f"<b>Total Estimated Discrepancy:</b> ₹{total_diff:.2f}", bold_body)
            ]
        ]
        summary_table = Table(summary_data, colWidths=[180, 180, 180])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), flag_bg),
            ("BOX", (0, 0), (-1, -1), 1, flag_border),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 14))

        # Detailed Audit Item Table
        elements.append(Paragraph("Detailed Medicine Price Verification", section_style))

        table_data = [
            ["Medicine Name", "Billed Rate", "NPPA Ceiling", "Diff / Unit", "Qty", "Total Discrepancy", "Status"]
        ]

        for res in audit.results:
            ext_item = res.extracted_item
            med_name = ext_item.extracted_medicine_name if ext_item else "Unknown"
            billed_p = f"₹{res.billed_price:.2f}"
            ref_p = f"₹{res.reference_price:.2f}" if res.reference_price else "N/A"
            diff_u = f"₹{res.price_difference:.2f}"
            qty_s = f"{res.quantity}"
            tot_d = f"₹{res.total_difference:.2f}"
            status_s = res.result_status

            table_data.append([
                Paragraph(med_name, body_style),
                billed_p,
                ref_p,
                diff_u,
                qty_s,
                tot_d,
                status_s
            ])

        col_widths = [160, 60, 65, 60, 40, 85, 70]
        results_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        results_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]))
        elements.append(results_table)
        elements.append(Spacer(1, 16))

        # Formal Grievance Petition Section
        if flagged_count > 0:
            elements.append(Paragraph("Formal Grievance Petition Draft", section_style))
            grievance_text = (
                f"<b>To:</b> National Pharmaceutical Pricing Authority (NPPA) / State Drug Controller / National Consumer Helpline<br/>"
                f"<b>Subject:</b> Grievance against apparent non-compliance with DPCO Ceiling Prices at {hospital_name}<br/><br/>"
                f"Respected Authorities,<br/>"
                f"During an automated audit of medical bill dated {bill_date_str} issued by {hospital_name}, "
                f"a total potential pricing discrepancy of <b>₹{total_diff:.2f}</b> was identified across {flagged_count} regulated item(s). "
                f"The billed rates appear to exceed the ceiling prices notified by the Central Government under Drugs (Prices Control) Order, 2013 "
                f"(DPCO 2013) read with Section 3 of the Essential Commodities Act, 1955.<br/><br/>"
                f"The patient requests an official review of the itemized prices and appropriate corrective action or refund."
            )
            elements.append(Paragraph(grievance_text, body_style))
            elements.append(Spacer(1, 16))

        # Legal Disclaimer
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9ca3af"), spaceAfter=8))
        disclaimer_text = (
            "<b>Disclaimer:</b> FairMed identifies potential pricing discrepancies based on official NPPA notifications. "
            "This report is generated for evidentiary and informational review and does not constitute a judicial ruling. "
            "Hospital billing adjustments or refunds remain subject to verification with the billing authority and competent Drug Control administrations."
        )
        elements.append(Paragraph(disclaimer_text, disclaimer_style))

        doc.build(elements)
        return output_path
