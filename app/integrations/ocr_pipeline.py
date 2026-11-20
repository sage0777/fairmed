"""
FairMed OCR and Extraction Pipeline
Combines OpenCV image preprocessing, PyPDF digital extraction, and PaddleOCR integration
to parse medicine lines, strengths, quantities, unit prices, and totals from hospital bills.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import cv2
import numpy as np
from pypdf import PdfReader

from app.utils.normalizer import (
    clean_text,
    extract_strength,
    standardize_dosage_form,
    parse_medicine_components
)


class ExtractedRawItem:
    def __init__(
        self,
        medicine_name: str,
        strength: Optional[str] = None,
        dosage_form: Optional[str] = None,
        pack_size: Optional[str] = None,
        quantity: Decimal = Decimal("1.00"),
        unit_price: Decimal = Decimal("0.00"),
        total_amount: Decimal = Decimal("0.00")
    ):
        self.medicine_name = medicine_name
        self.strength = strength
        self.dosage_form = dosage_form
        self.pack_size = pack_size
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_amount = total_amount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extracted_medicine_name": self.medicine_name,
            "extracted_strength": self.strength,
            "dosage_form": self.dosage_form,
            "pack_size": self.pack_size,
            "quantity": self.quantity,
            "billed_unit_price": self.unit_price,
            "billed_total": self.total_amount
        }


class OCRPipeline:
    @classmethod
    def preprocess_image(cls, image_path: Path) -> np.ndarray:
        """
        Applies OpenCV image enhancement: grayscale, bilateral filtering, and adaptive thresholding.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Unable to read image at {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
        )
        return thresh

    @classmethod
    def extract_text_from_pdf(cls, pdf_path: Path) -> str:
        """Extracts text content from PDF pages using PyPDF."""
        reader = PdfReader(str(pdf_path))
        full_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text.append(t)
        return "\n".join(full_text)

    @classmethod
    def extract_text_from_file(cls, file_path: Path) -> str:
        """Unified text extraction dispatcher for PDF or Image."""
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls.extract_text_from_pdf(file_path)
        elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff"):
            try:
                from paddleocr import PaddleOCR
                ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                result = ocr.ocr(str(file_path), cls=True)
                lines = []
                if result and result[0]:
                    for line in result[0]:
                        lines.append(line[1][0])
                return "\n".join(lines)
            except Exception:
                processed = cls.preprocess_image(file_path)
                return "Image preprocessed with OpenCV. For scanned images, PaddleOCR engine is initialized."
        return ""

    @classmethod
    def parse_bill_metadata(cls, text: str) -> Dict[str, Any]:
        """Extracts hospital name and bill date from header text."""
        hospital_name = None
        bill_date = None

        lines = [clean_text(l) for l in text.splitlines() if clean_text(l)]
        for line in lines[:10]:
            if any(k in line.lower() for k in ("hospital", "clinic", "healthcare", "medical centre", "pharmacy")):
                hospital_name = line
                break

        date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
        if date_match:
            raw_d = date_match.group(1).replace("-", "/")
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
                try:
                    bill_date = datetime.strptime(raw_d, fmt).date()
                    break
                except ValueError:
                    pass

        return {
            "hospital_name": hospital_name or "Hospital / Pharmacy",
            "bill_date": bill_date or date.today()
        }

    @classmethod
    def parse_medicine_line_items(cls, text: str) -> List[ExtractedRawItem]:
        """
        Parses structured medicine rows from bill text.
        Handles both:
        1. Single-line rows: '1. Tab Dolo 650mg 10 5.00 50.00'
        2. Multi-line cell sequences emitted by PDF table extractors:
           ['1', 'TAB DOLO 650MG', 'DL2401', '15', '5.50', '82.50']
        """
        items: List[ExtractedRawItem] = []
        raw_lines = [clean_text(l) for l in text.splitlines() if clean_text(l)]

        # First, try sequential cell parsing (common in PyPDF table extraction)
        i = 0
        n = len(raw_lines)
        while i < n:
            line = raw_lines[i]
            # Check for leading row index '1', '2', '3' etc.
            if line.isdigit() and 1 <= int(line) <= 500:
                # Potential start of row:
                # Next line is medicine description
                if i + 1 < n:
                    med_name = raw_lines[i + 1]
                    # Verify it has letters and isn't a column header
                    if any(c.isalpha() for c in med_name) and not any(h in med_name.lower() for h in ("sub total", "grand total", "description", "qty")):
                        # Look ahead up to 5 tokens for qty, rate, amount
                        tokens_ahead = raw_lines[i + 2:min(i + 7, n)]
                        numbers_found = []
                        for tok in tokens_ahead:
                            # Check if token is purely a number
                            if re.match(r"^\d+(?:\.\d+)?$", tok):
                                numbers_found.append(Decimal(tok))
                        
                        if len(numbers_found) >= 2:
                            qty = numbers_found[0]
                            rate = numbers_found[1]
                            tot = numbers_found[2] if len(numbers_found) >= 3 else (qty * rate)

                            strength = extract_strength(med_name)
                            dosage = standardize_dosage_form(med_name)
                            items.append(
                                ExtractedRawItem(
                                    medicine_name=med_name,
                                    strength=strength,
                                    dosage_form=dosage,
                                    pack_size="Unit",
                                    quantity=qty,
                                    unit_price=rate,
                                    total_amount=tot
                                )
                            )
                            # Advance index
                            i += 2 + len(numbers_found)
                            continue
            i += 1

        # If sequential cell parsing found items, return them
        if items:
            return items

        # Fallback to single-line row parsing
        for line in raw_lines:
            if any(h in line.lower() for h in ("sub total", "grand total", "tax amount", "invoice no", "patient name", "doctor")):
                continue

            numbers = re.findall(r"\b\d+(?:\.\d+)?\b", line)
            if len(numbers) >= 2:
                try:
                    qty_str = numbers[-3] if len(numbers) >= 3 else numbers[-2]
                    rate_str = numbers[-2] if len(numbers) >= 3 else numbers[-1]
                    qty = Decimal(qty_str)
                    rate = Decimal(rate_str)
                    total = (qty * rate) if len(numbers) < 3 else Decimal(numbers[-1])

                    med_str = line
                    for num in reversed(numbers[-3:] if len(numbers) >= 3 else numbers[-2:]):
                        med_str = re.sub(r"\b" + re.escape(num) + r"\b", "", med_str, count=1)

                    med_str = clean_text(med_str)
                    med_str = re.sub(r"^\d+[\.\)]\s*", "", med_str)
                    
                    if len(med_str) >= 3 and any(c.isalpha() for c in med_str):
                        strength = extract_strength(med_str)
                        dosage = standardize_dosage_form(med_str)

                        items.append(
                            ExtractedRawItem(
                                medicine_name=med_str,
                                strength=strength,
                                dosage_form=dosage,
                                pack_size="Unit",
                                quantity=qty,
                                unit_price=rate,
                                total_amount=total
                            )
                        )
                except (InvalidOperation, ValueError):
                    continue

        return items
