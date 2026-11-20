"""
FairMed Medicine Matching Engine
Combines RapidFuzz token matching, alias indexing, strength verification,
and dosage form validation to safely identify medicines from noisy OCR strings.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from rapidfuzz import fuzz

from app.models.medicine import Medicine
from app.utils.normalizer import (
    normalize_medicine_name,
    extract_strength,
    standardize_dosage_form,
    parse_medicine_components
)


class MatchCandidate(BaseModel):
    medicine_id: str
    generic_name: str
    active_ingredients: str
    strength: str
    dosage_form: str
    matched_term: str
    match_method: str
    similarity_score: float
    strength_match: bool
    dosage_form_match: bool
    confidence_score: float
    verification_status: str  # MATCHED, UNCERTAIN, UNMATCHED


class MedicineMatchResult(BaseModel):
    matched_candidate: Optional[MatchCandidate]
    alternatives: List[MatchCandidate]
    overall_confidence: float
    verification_status: str  # MATCHED, UNCERTAIN, UNMATCHED
    explanation: str


class MedicineMatchingEngine:
    def __init__(self, medicine_registry: List[Tuple[Medicine, List[str]]]):
        """
        Initializes matching engine with pre-fetched medicines and aliases.
        """
        self.registry = medicine_registry

    @staticmethod
    def _is_strength_compatible(extracted_strength: Optional[str], target_strength: str) -> bool:
        if not extracted_strength or not target_strength:
            return True  # If unknown on bill, do not reject outright, will be marked UNCERTAIN
        
        ext = extracted_strength.lower().replace(" ", "")
        tgt = target_strength.lower().replace(" ", "")
        
        if ext == tgt:
            return True
        
        # Handle 625mg vs 500mg + 125mg
        if ext == "625mg" and ("500mg+125mg" in tgt or "625mg" in tgt):
            return True
        if "500mg+125mg" in ext and ("625mg" in tgt or "500mg+125mg" in tgt):
            return True
        
        # Standardize units: e.g. 1g == 1000mg
        if ext in ("1g", "1000mg") and tgt in ("1g", "1000mg"):
            return True
            
        return False

    @staticmethod
    def _is_dosage_compatible(extracted_dosage: Optional[str], target_dosage: str) -> bool:
        if not extracted_dosage or not target_dosage:
            return True  # Neutral if not specified on bill
        
        ext = extracted_dosage.lower()
        tgt = target_dosage.lower()
        
        if ext in tgt or tgt in ext:
            return True
        
        # Tablet vs Capsule: different forms
        if ("tablet" in ext and "capsule" in tgt) or ("capsule" in ext and "tablet" in tgt):
            return False
            
        # Injection vs Tablet: strictly incompatible
        if ("injection" in ext and "tablet" in tgt) or ("tablet" in ext and "injection" in tgt):
            return False

        return True

    def match(self, raw_medicine_name: str) -> MedicineMatchResult:
        """
        Main matching entry point for an extracted item string.
        """
        if not raw_medicine_name or not raw_medicine_name.strip():
            return MedicineMatchResult(
                matched_candidate=None,
                alternatives=[],
                overall_confidence=0.0,
                verification_status="UNMATCHED",
                explanation="No medicine name provided."
            )

        clean_base, extracted_str, extracted_dosage = parse_medicine_components(raw_medicine_name)
        norm_query = normalize_medicine_name(raw_medicine_name)
        
        candidates: List[MatchCandidate] = []

        for med, aliases in self.registry:
            best_term = ""
            best_ratio = 0.0
            match_method = "FUZZY_NAME"

            # 1. Check all brand aliases
            for alias in aliases:
                alias_clean = normalize_medicine_name(alias)
                # Exact or containment check
                if alias_clean.lower() == norm_query.lower():
                    exact_score = 100.0
                    if exact_score > best_ratio:
                        best_ratio = exact_score
                        best_term = alias
                        match_method = "EXACT_ALIAS"
                elif alias_clean.lower() in norm_query.lower() or norm_query.lower() in alias_clean.lower():
                    contain_score = 94.0
                    if contain_score > best_ratio:
                        best_ratio = contain_score
                        best_term = alias
                        match_method = "ALIAS_CONTAINMENT"
                else:
                    a_sort = fuzz.token_sort_ratio(norm_query, alias_clean)
                    a_set = fuzz.token_set_ratio(norm_query, alias_clean)
                    a_score = max(a_sort, a_set)
                    if a_score > best_ratio:
                        best_ratio = a_score
                        best_term = alias
                        match_method = "FUZZY_ALIAS"

            # 2. Check generic name
            gen_clean = normalize_medicine_name(med.generic_name)
            if gen_clean.lower() == norm_query.lower():
                best_ratio = 100.0
                best_term = med.generic_name
                match_method = "EXACT_GENERIC"
            else:
                sort_ratio = fuzz.token_sort_ratio(norm_query, gen_clean)
                set_ratio = fuzz.token_set_ratio(norm_query, gen_clean)
                med_score = max(sort_ratio, set_ratio)
                if med_score > best_ratio:
                    best_ratio = med_score
                    best_term = med.generic_name
                    match_method = "GENERIC_NAME"

            # 3. Check active ingredients
            ingr_clean = normalize_medicine_name(med.active_ingredients)
            ingr_score = fuzz.token_set_ratio(norm_query, ingr_clean)
            if ingr_score > best_ratio:
                best_ratio = ingr_score
                best_term = med.active_ingredients
                match_method = "INGREDIENTS"

            # Verify strength and dosage compatibility
            strength_ok = self._is_strength_compatible(extracted_str, med.strength)
            dosage_ok = self._is_dosage_compatible(extracted_dosage, med.dosage_form)

            # Strict penalty if strength conflict exists
            # E.g. Paracetamol 650mg queried, but this record is 500mg
            is_strength_conflict = (extracted_str is not None and not strength_ok)
            is_dosage_conflict = (extracted_dosage is not None and not dosage_ok)

            if is_strength_conflict:
                composite_score = best_ratio * 0.40  # severe discount
            elif is_dosage_conflict:
                composite_score = best_ratio * 0.50
            else:
                # Good match bonus
                if best_ratio >= 90:
                    composite_score = best_ratio
                else:
                    composite_score = best_ratio * 0.85
                    if extracted_str and strength_ok:
                        composite_score += 10.0
                    if extracted_dosage and dosage_ok:
                        composite_score += 5.0

            composite_score = max(0.0, min(100.0, composite_score))

            # Candidate status determination
            if best_ratio >= 85.0 and not is_strength_conflict and not is_dosage_conflict:
                status = "MATCHED"
            elif best_ratio >= 55.0 and not is_strength_conflict:
                status = "UNCERTAIN"
            else:
                status = "UNMATCHED"

            if best_ratio >= 45.0:
                candidates.append(
                    MatchCandidate(
                        medicine_id=med.id,
                        generic_name=med.generic_name,
                        active_ingredients=med.active_ingredients,
                        strength=med.strength,
                        dosage_form=med.dosage_form,
                        matched_term=best_term,
                        match_method=match_method,
                        similarity_score=round(best_ratio, 2),
                        strength_match=strength_ok and not is_strength_conflict,
                        dosage_form_match=dosage_ok and not is_dosage_conflict,
                        confidence_score=round(composite_score, 2),
                        verification_status=status
                    )
                )

        # Sort candidates descending by confidence
        candidates.sort(key=lambda c: (c.confidence_score, c.similarity_score), reverse=True)

        if not candidates or candidates[0].confidence_score < 50.0:
            return MedicineMatchResult(
                matched_candidate=None,
                alternatives=candidates[:3],
                overall_confidence=0.0,
                verification_status="UNMATCHED",
                explanation=f"No matching medicine found for '{raw_medicine_name}' with sufficient confidence."
            )

        best_cand = candidates[0]
        alternatives = candidates[1:4]

        # Safety gate: If strength was extracted and does not match, status is UNCERTAIN
        if extracted_str and not best_cand.strength_match:
            best_cand.verification_status = "UNCERTAIN"
            return MedicineMatchResult(
                matched_candidate=best_cand,
                alternatives=alternatives,
                overall_confidence=best_cand.confidence_score,
                verification_status="UNCERTAIN",
                explanation=(
                    f"Name similarity was high for '{best_cand.generic_name}', but extracted strength '{extracted_str}' "
                    f"does not match registered formulation strength '{best_cand.strength}'. Manual verification required."
                )
            )

        if best_cand.verification_status == "MATCHED":
            explanation = (
                f"Successfully matched to '{best_cand.generic_name}' via {best_cand.match_method} ('{best_cand.matched_term}') "
                f"with verified strength ({best_cand.strength}) and dosage form ({best_cand.dosage_form})."
            )
        else:
            explanation = (
                f"Uncertain match for '{raw_medicine_name}'. Potential candidate '{best_cand.generic_name}' "
                f"(confidence: {best_cand.confidence_score}%). Manual verification recommended."
            )

        return MedicineMatchResult(
            matched_candidate=best_cand,
            alternatives=alternatives,
            overall_confidence=best_cand.confidence_score,
            verification_status=best_cand.verification_status,
            explanation=explanation
        )
