"""
FairMed Normalizer Utility
Provides functions for normalizing medicine names, extracting strengths, 
and standardizing dosage forms and routes of administration.
"""

import re
from typing import Tuple, Optional, List


DOSAGE_FORM_MAP = {
    r"\b(tabs?|tablets?)\b": "Tablet",
    r"\b(caps?|capsules?)\b": "Capsule",
    r"\b(inj|injections?|vials?|ampoules?|amps?)\b": "Injection",
    r"\b(syr|syrups?|susp|suspensions?|oral liquid|soln?|solutions?)\b": "Oral Liquid / Syrup",
    r"\b(oint|ointments?|creams?|gels?)\b": "Ointment / Cream",
    r"\b(drops?|eye drops?|ear drops?)\b": "Drops",
    r"\b(inhalers?|respules?|rotacaps?)\b": "Inhaler / Respule",
    r"\b(infusions?|i\.?v\.?)\b": "Infusion",
}

STRENGTH_REGEX_EXPLICIT = re.compile(
    r"(\d+(?:\.\d+)?\s*(?:mg|g|gm|mcg|ml|iu|u|%|w/v|w/w)(?:\s*\+\s*\d+(?:\.\d+)?\s*(?:mg|g|gm|mcg|ml|iu|u|%|w/v|w/w))*)",
    re.IGNORECASE
)

# Extracts standalone numbers commonly representing dosages (e.g. 'Dolo 650', 'Pan 40', 'Augmentin 625')
NUMERIC_STRENGTH_REGEX = re.compile(
    r"\b(\d{1,4}(?:\.\d+)?)\s*(?:mg|g|gm)?\b",
    re.IGNORECASE
)


def clean_text(text: Optional[str]) -> str:
    """Normalize text by trimming, lowercasing, and removing redundant punctuation."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_medicine_name(name: str) -> str:
    """
    Standardize raw medicine name for searching and fuzzy matching.
    Removes packaging qualifiers, batch numbers, trailing dosage forms, and extra symbols.
    """
    if not name:
        return ""
    text = clean_text(name).lower()
    
    # Remove common bill suffixes like '10s', '1x10', 'strip of 10'
    text = re.sub(r"\b\d+\s*'?s\b", "", text)
    text = re.sub(r"\b\d+\s*x\s*\d+\b", "", text)
    text = re.sub(r"strip of \d+", "", text)
    
    # Remove symbols like #, *, @, /
    text = re.sub(r"[*#@$%&]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_strength(text: str) -> Optional[str]:
    """
    Extracts strength component (e.g. '500mg', '625mg', '500mg + 125mg', '1g') from text.
    If only a number like '650' or '500' or '40' is attached to a medicine name, infers 'mg'.
    """
    if not text:
        return None
        
    explicit = STRENGTH_REGEX_EXPLICIT.findall(text)
    if explicit:
        strength = explicit[0].strip().lower()
        strength = re.sub(r"\s+", "", strength)
        strength = re.sub(r"\+", " + ", strength)
        return strength
        
    # Check for standalone numeric token in names like 'Dolo 650' or 'Pan 40'
    clean = clean_text(text)
    tokens = clean.split()
    for tok in reversed(tokens):
        if tok.isdigit():
            val = int(tok)
            # Standard medicinal mg dosages range from 1 to 2000
            if 1 <= val <= 2000:
                return f"{val}mg"
                
    return None


def standardize_dosage_form(text: str) -> Optional[str]:
    """
    Standardizes dosage forms into primary regulatory categories:
    Tablet, Capsule, Injection, Oral Liquid / Syrup, Ointment / Cream, etc.
    Returns None if no dosage form is explicitly identifiable.
    """
    if not text:
        return None
    clean = text.lower()
    for pattern, standardized in DOSAGE_FORM_MAP.items():
        if re.search(pattern, clean):
            return standardized
    return None


def parse_medicine_components(raw_name: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Splits raw medicine name string into:
    (clean_base_name, extracted_strength, standardized_dosage_form)
    Example: 'PAN 40 TAB' -> ('pan', '40mg', 'Tablet')
    """
    clean = clean_text(raw_name)
    strength = extract_strength(clean)
    dosage = standardize_dosage_form(clean)
    
    base_name = clean
    if strength:
        # Remove matched strength from base name
        base_name = re.sub(r"\b" + re.escape(strength.replace("mg", "")) + r"(?:mg)?\b", "", base_name, flags=re.IGNORECASE)
    for pattern in DOSAGE_FORM_MAP.keys():
        base_name = re.sub(pattern, "", base_name, flags=re.IGNORECASE)
    
    base_name = normalize_medicine_name(base_name)
    return base_name, strength, dosage
