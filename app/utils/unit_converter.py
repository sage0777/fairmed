"""
FairMed Unit Converter Utility
Standardizes packaging units, extracts pack sizes, and normalizes prices
between package level (e.g. Strip of 10) and unit dose level (e.g. 1 Tablet).
"""

import re
from typing import Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP


PACK_SIZE_REGEX = re.compile(r"(\d+)\s*(?:tabs?|caps?|tablets?|capsules?|ampoules?|vials?|pills?|strip|s\b)", re.IGNORECASE)
ML_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*ml\b", re.IGNORECASE)


def parse_pack_size_count(pack_str: Optional[str]) -> int:
    """
    Extracts the integer count of unit doses from a pack size description.
    Examples:
    - '10 Tablets' -> 10
    - 'Strip of 15' -> 15
    - '1 x 10' -> 10
    - '1 Vial' -> 1
    - '1' -> 1
    """
    if not pack_str:
        return 1
    
    clean = pack_str.strip().lower()
    
    # Handle '1x10' or '10 x 1'
    mult_match = re.search(r"(\d+)\s*x\s*(\d+)", clean)
    if mult_match:
        try:
            return int(mult_match.group(1)) * int(mult_match.group(2))
        except ValueError:
            pass

    match = PACK_SIZE_REGEX.search(clean)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    digits = re.findall(r"\b\d+\b", clean)
    if digits:
        try:
            val = int(digits[0])
            if 1 <= val <= 1000:
                return val
        except ValueError:
            pass

    return 1


def standardize_unit_label(raw_unit: Optional[str], dosage_form: Optional[str] = None) -> str:
    """
    Standardizes NPPA regulatory unit strings (e.g., '1 Tablet', '1 Capsule', '1 ml', '1 Vial').
    """
    if not raw_unit:
        if dosage_form and "tablet" in dosage_form.lower():
            return "1 Tablet"
        elif dosage_form and "capsule" in dosage_form.lower():
            return "1 Capsule"
        elif dosage_form and "injection" in dosage_form.lower():
            return "1 Injection"
        return "1 Unit"
    
    clean = raw_unit.strip().lower()
    if "tab" in clean:
        return "1 Tablet"
    elif "cap" in clean:
        return "1 Capsule"
    elif "inj" in clean or "vial" in clean or "amp" in clean:
        return "1 Injection"
    elif "ml" in clean:
        ml_match = ML_REGEX.search(clean)
        if ml_match:
            return f"{ml_match.group(1)} ml"
        return "1 ml"
    
    return raw_unit.title().strip()


def normalize_to_unit_price(
    billed_price: Decimal,
    quantity: Decimal,
    pack_size: Optional[str] = None,
    is_pack_price: bool = False
) -> Decimal:
    """
    Calculates per-unit dose price from billed amount.
    If billed as pack (e.g., strip of 10), divides by pack size.
    """
    if not is_pack_price:
        return billed_price
    
    count = parse_pack_size_count(pack_size)
    if count > 1:
        return (billed_price / Decimal(count)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return billed_price
