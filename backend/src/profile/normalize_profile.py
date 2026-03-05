from __future__ import annotations

from typing import Tuple, Dict, Any, Optional

from backend.src.profile.user_profile_model import UserProfile
from backend.src.profile.profile_value_normalizers import (
    normalize_state,
    normalize_category,
    normalize_gender,
    normalize_income,
    normalize_education,
    normalize_bool,
)


# Flexible input key aliases → canonical UserProfile attribute
INPUT_KEY_ALIASES: Dict[str, str] = {
    # state
    "state": "state",
    "state_name": "state",
    "user_state": "state",
    "residing_state": "state",
    "state_of_residence": "state",
    # district
    "district": "district",
    "district_name": "district",
    # pincode
    "pincode": "pincode",
    "pin": "pincode",
    "zip": "pincode",
    "zipcode": "pincode",
    # age
    "age": "age",
    "user_age": "age",
    # gender
    "gender": "gender",
    "sex": "gender",
    # category / caste
    "category": "category",
    "caste": "category",
    "social_category": "category",
    # income
    "income": "income_annual",
    "annual_income": "income_annual",
    "income_annual": "income_annual",
    "yearly_income": "income_annual",
    "family_income": "income_annual",
    # occupation
    "occupation": "occupation",
    "job": "occupation",
    "work": "occupation",
    # education
    "education": "education_level",
    "education_level": "education_level",
    "qualification": "education_level",
    # farmer
    "farmer": "farmer",
    "is_farmer": "farmer",
    # land
    "land": "land_area",
    "land_area": "land_area",
    "landholding": "land_area",
    # disability
    "disability": "disability",
    "disability_type": "disability",
    # business
    "business": "business_type",
    "business_type": "business_type",
}


COMMONLY_REQUIRED_FIELDS = ["state", "age", "income_annual", "category", "occupation"]


def _extract_raw_value(raw_profile: Dict[str, Any], canonical_key: str) -> Optional[Any]:
    """
    Try multiple alias keys in raw_profile to get the value for canonical_key.
    """
    candidates = [k for k, v in INPUT_KEY_ALIASES.items() if v == canonical_key]
    # Also allow exact canonical key
    candidates.append(canonical_key)

    for key in candidates:
        for variant in {key, key.lower(), key.upper(), key.title()}:
            if variant in raw_profile:
                return raw_profile.get(variant)
    return None


def normalize_profile(raw_profile: Dict[str, Any]) -> Tuple[UserProfile, Dict[str, Any]]:
    """
    Normalize a raw user profile dict into a UserProfile and diagnostics.

    Args:
        raw_profile: dictionary with raw user input (from UI or API).

    Returns:
        (normalized_profile, diagnostics) where diagnostics is:
        {
            "missing_fields": [...],
            "invalid_fields": {...},
            "warnings": [...]
        }
    """
    diagnostics: Dict[str, Any] = {
        "missing_fields": [],
        "invalid_fields": {},
        "warnings": [],
    }

    # --- Extract and normalize fields ---

    # state
    raw_state = _extract_raw_value(raw_profile, "state")
    norm_state = normalize_state(raw_state) if raw_state is not None else None
    if raw_state and norm_state and str(raw_state).strip() != norm_state:
        diagnostics["warnings"].append(f"state '{raw_state}' normalized to '{norm_state}'.")

    # age
    raw_age = _extract_raw_value(raw_profile, "age")
    age: Optional[int] = None
    if raw_age is not None:
        try:
            age = int(str(raw_age).strip())
        except (TypeError, ValueError):
            diagnostics["invalid_fields"]["age"] = raw_age
            diagnostics["warnings"].append(f"age could not be parsed from '{raw_age}'.")

    # gender
    raw_gender = _extract_raw_value(raw_profile, "gender")
    gender = normalize_gender(raw_gender) if raw_gender is not None else None

    # category
    raw_category = _extract_raw_value(raw_profile, "category")
    category = normalize_category(raw_category) if raw_category is not None else None

    # income
    raw_income = _extract_raw_value(raw_profile, "income_annual")
    income_annual = normalize_income(raw_income) if raw_income is not None else None
    if raw_income is not None and income_annual is None:
        diagnostics["invalid_fields"]["income_annual"] = raw_income
        diagnostics["warnings"].append(
            f"income_annual could not be parsed from '{raw_income}'."
        )

    # occupation
    raw_occupation = _extract_raw_value(raw_profile, "occupation")
    occupation = str(raw_occupation).strip() if raw_occupation not in (None, "") else None

    # education
    raw_education = _extract_raw_value(raw_profile, "education_level")
    education_level = normalize_education(raw_education) if raw_education is not None else None
    if raw_education is not None and education_level is None:
        # Not critical, but we can warn
        diagnostics["warnings"].append(
            f"education_level could not be normalized from '{raw_education}'."
        )

    # farmer (boolean)
    raw_farmer = _extract_raw_value(raw_profile, "farmer")
    farmer = normalize_bool(raw_farmer) if raw_farmer is not None else None
    if raw_farmer is not None and farmer is None:
        diagnostics["warnings"].append(f"farmer could not be parsed from '{raw_farmer}'.")

    # land_area (float, in acres; assume numeric already in acres)
    raw_land_area = _extract_raw_value(raw_profile, "land_area")
    land_area: Optional[float] = None
    if raw_land_area is not None:
        try:
            land_area = float(str(raw_land_area).strip())
        except (TypeError, ValueError):
            diagnostics["invalid_fields"]["land_area"] = raw_land_area
            diagnostics["warnings"].append(
                f"land_area could not be parsed from '{raw_land_area}'."
            )

    # disability
    raw_disability = _extract_raw_value(raw_profile, "disability")
    disability = str(raw_disability).strip() if raw_disability not in (None, "") else None

    # business_type
    raw_business_type = _extract_raw_value(raw_profile, "business_type")
    business_type = (
        str(raw_business_type).strip() if raw_business_type not in (None, "") else None
    )

    # district, pincode, user_id, documents (simple pass-through)
    user_id = raw_profile.get("user_id") or raw_profile.get("userId")
    raw_district = _extract_raw_value(raw_profile, "district")
    district = str(raw_district).strip() if raw_district not in (None, "") else None

    raw_pincode = _extract_raw_value(raw_profile, "pincode")
    pincode = str(raw_pincode).strip() if raw_pincode not in (None, "") else None

    documents = raw_profile.get("documents") or {}
    if not isinstance(documents, dict):
        documents = {}
        diagnostics["warnings"].append("documents field was not a dict and has been ignored.")

    profile = UserProfile(
        user_id=user_id,
        state=norm_state,
        district=district,
        pincode=pincode,
        age=age,
        gender=gender,
        category=category,
        income_annual=income_annual,
        occupation=occupation,
        education_level=education_level,
        farmer=farmer,
        land_area=land_area,
        disability=disability,
        business_type=business_type,
        documents=documents,
    )

    # --- Missing field diagnostics ---
    for field in COMMONLY_REQUIRED_FIELDS:
        if getattr(profile, field) is None:
            diagnostics["missing_fields"].append(field)

    return profile, diagnostics


__all__ = ["normalize_profile", "INPUT_KEY_ALIASES", "COMMONLY_REQUIRED_FIELDS"]
