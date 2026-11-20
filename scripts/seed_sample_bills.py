"""
Seed Sample Medical Bill Script
Generates a realistic hospital pharmacy bill in PDF format for testing OCR,
matching, deterministic pricing audit, and grievance reporting.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings


def generate_sample_bill_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "HospitalTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )
    sub_style = ParagraphStyle(
        "HospitalSub",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    body_style = ParagraphStyle(
        "BillBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )
    bold_style = ParagraphStyle(
        "BillBold",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    elements = []

    # Hospital Header
    elements.append(Paragraph("APOLLO CARE MULTISPECIALITY HOSPITAL", title_style))
    elements.append(Paragraph("In-Patient Pharmacy & Medical Supplies Billing Department", sub_style))
    elements.append(Paragraph("GSTIN: 07AAAAA1234A1Z5 | DL No: DL-20B-12345", sub_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    # Patient & Invoice Meta
    meta_data = [
        [
            Paragraph("<b>Patient Name:</b> Ramesh Verma", body_style),
            Paragraph("<b>Invoice No:</b> IP-2024-8849", body_style)
        ],
        [
            Paragraph("<b>Admission ID:</b> IPD-9032", body_style),
            Paragraph("<b>Bill Date:</b> 15/05/2024", body_style)
        ],
        [
            Paragraph("<b>Consultant:</b> Dr. S. K. Gupta (MD, Medicine)", body_style),
            Paragraph("<b>Payment Mode:</b> Cash / TP A", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # Medicine Line Items Table
    bill_items = [
        ["S.No", "Description of Medicines & Consumables", "Batch", "Qty", "Rate (INR)", "Amount (INR)"],
        ["1", "TAB DOLO 650MG", "DL2401", "15", "5.50", "82.50"],
        ["2", "AUGMENTIN 625 DUO", "AG8902", "10", "35.00", "350.00"],
        ["3", "INJ MONOCEF 1GM", "MC1104", "2", "60.00", "120.00"],
        ["4", "TAB PAN 40", "PN5521", "15", "9.50", "142.50"],
        ["5", "CIPLOX 500", "CP4019", "10", "8.00", "80.00"],
    ]

    item_table = Table(bill_items, colWidths=[35, 245, 60, 45, 65, 70])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 10))

    # Totals
    total_data = [
        ["", "", "", "", "Sub Total:", "775.00"],
        ["", "", "", "", "CGST (6%):", "46.50"],
        ["", "", "", "", "SGST (6%):", "46.50"],
        ["", "", "", "", "Grand Total:", "868.00"]
    ]
    tot_table = Table(total_data, colWidths=[35, 245, 60, 45, 65, 70])
    tot_table.setStyle(TableStyle([
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (4, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(tot_table)

    doc.build(elements)
    print(f"[+] Sample medical bill PDF generated at: {output_path}")


def main():
    target = settings.DATASETS_DIR / "sample_hospital_bill.pdf"
    generate_sample_bill_pdf(target)


if __name__ == "__main__":
    main()
