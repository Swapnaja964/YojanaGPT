from __future__ import annotations

from typing import Optional


# --- State normalization ---

STATE_ALIASES = {
    "Maharashtra": ["mh", "maha", "maharastra", "maharashtra"],
    "Uttar Pradesh": ["up", "u.p.", "uttar pradesh"],
    "Madhya Pradesh": ["mp", "m.p.", "madhya pradesh"],
    "Gujarat": ["gj", "guj", "gujarat"],
    "Karnataka": ["ka", "kar", "karnataka"],
    "Tamil Nadu": ["tn", "tamilnadu", "tamil nadu"],
    "Telangana": ["ts", "telangana"],
    "Andhra Pradesh": ["ap", "andhra pradesh"],
    "Rajasthan": ["rj", "raj", "rajasthan"],
    "Bihar": ["br", "bih", "bihar"],
    "West Bengal": ["wb", "w.b.", "west bengal"],
    "Odisha": ["od", "odisha", "orissa"],
    "Delhi": ["dl", "delhi", "nct delhi", "nct of delhi"],
    "Haryana": ["hr", "haryana"],
    "Punjab": ["pb", "punjab"],
    "Kerala": ["kl", "kerala"],
    "Jharkhand": ["jh", "jharkhand"],
    "Chhattisgarh": ["ct", "chhattisgarh", "chattisgarh"],
    "Assam": ["as", "assam"],
    "Jammu and Kashmir": ["jk", "j&k", "jammu & kashmir", "jammu and kashmir"],
    "Ladakh": ["la", "ladakh"],
}

_STATE_LOOKUP = {
    alias.strip().lower(): canonical
    for canonical, aliases in STATE_ALIASES.items()
    for alias in aliases
}


def normalize_state(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    key = raw.lower()
    # Direct alias match
    if key in _STATE_LOOKUP:
        return _STATE_LOOKUP[key]

    # Basic title-casing fallback
    return " ".join(part.capitalize() for part in raw.split())


# --- Category normalization ---

CATEGORY_ALIASES = {
    "SC": ["sc", "scheduled caste", "schedule caste"],
    "ST": ["st", "scheduled tribe", "schedule tribe"],
    "OBC": ["obc", "other backward class", "other backward classes"],
    "EWS": ["ews", "economically weaker section"],
    "General": ["gen", "general", "open", "unreserved"],
}

_CATEGORY_LOOKUP = {
    alias.strip().lower(): canonical
    for canonical, aliases in CATEGORY_ALIASES.items()
    for alias in aliases
}


def normalize_category(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    key = raw.lower()
    if key in _CATEGORY_LOOKUP:
        return _CATEGORY_LOOKUP[key]

    # If already upper-case short code, keep as is
    if len(raw) <= 4 and raw.isalpha() and raw.upper() in CATEGORY_ALIASES:
        return raw.upper()

    # Fallback: title-case
    return raw.title()


# --- Gender normalization ---

_GENDER_MAP = {
    "m": "male",
    "male": "male",
    "man": "male",
    "boy": "male",
    "f": "female",
    "female": "female",
    "woman": "female",
    "girl": "female",
    "transgender": "other",
    "other": "other",
    "non-binary": "other",
    "nb": "other",
}


def normalize_gender(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    key = raw.lower()
    return _GENDER_MAP.get(key, "unspecified")


# --- Income normalization ---

def normalize_income(value: Optional[str | float | int]) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw:
        return None

    # Remove common noise
    cleaned = raw.replace(\",\").replace(\"₹\", \"\").replace(\"rs.\", \"\").replace(\"rs\", \"\")
    cleaned = cleaned.lower().replace(\"inr\", \"\").strip()

    # Handle common textual magnitudes
    multiplier = 1.0
    if \"lakh\" in cleaned:
        multiplier = 100_000.0
        cleaned = cleaned.replace(\"lakh\", \"\").strip()
    elif \"lac\" in cleaned:
        multiplier = 100_000.0
        cleaned = cleaned.replace(\"lac\", \"\").strip()
    elif \"crore\" in cleaned:
        multiplier = 10_000_000.0
        cleaned = cleaned.replace(\"crore\", \"\").strip()

    try:
        base = float(cleaned)
        return base * multiplier
    except ValueError:
        return None


# --- Education normalization ---

_EDU_MAP = {
    \"below 10th\": \"below_10th\",
    \"under 10th\": \"below_10th\",
    \"upto 9th\": \"below_10th\",
    \"10th\": \"10th\",
    \"ssc\": \"10th\",
    \"matric\": \"10th\",
    \"matriculation\": \"10th\",
    \"12th\": \"12th\",
    \"hsc\": \"12th\",
    \"higher secondary\": \"12th\",
    \"diploma\": \"diploma\",
    \"iti\": \"diploma\",
    \"polytechnic\": \"diploma\",
    \"graduate\": \"graduate\",
    \"bachelor\": \"graduate\",
    \"bachelors\": \"graduate\",
    \"ba\": \"graduate\",
    \"bsc\": \"graduate\",
    \"bcom\": \"graduate\",
    \"b.tech\": \"graduate\",
    \"btech\": \"graduate\",
    \"postgraduate\": \"postgraduate\",
    \"post graduate\": \"postgraduate\",
    \"pg\": \"postgraduate\",
    \"ma\": \"postgraduate\",
    \"msc\": \"postgraduate\",
    \"mcom\": \"postgraduate\",
    \"m.tech\": \"postgraduate\",
    \"mtech\": \"postgraduate\",
    \"doctorate\": \"doctorate\",
    \"phd\": \"doctorate\",
}


def normalize_education(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    key = raw.lower()
    if key in _EDU_MAP:
        return _EDU_MAP[key]

    # Simple heuristics
    if \"10\" in key and \"12\" not in key:
        return \"10th\"
    if \"12\" in key:
        return \"12th\"
    if \"diploma\" in key or \"iti\" in key or \"polytechnic\" in key:
        return \"diploma\"
    if \"b.\" in key or \"b \" in key:
        return \"graduate\"
    if \"m.\" in key or \"m \" in key:
        return \"postgraduate\"
    if \"phd\" in key or \"ph.d\" in key or \"doctor\" in key:
        return \"doctorate\"

    return None


# --- Boolean normalization (farmer etc.) ---

TRUE_VALUES = {\"yes\", \"y\", \"true\", \"1\", \"farmer\"}
FALSE_VALUES = {\"no\", \"n\", \"false\", \"0\", \"non_farmer\", \"non-farmer\", \"not farmer\"}


def normalize_bool(value: Optional[str | bool | int | float]) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    raw = str(value).strip()
    if not raw:
        return None

    key = raw.lower()
    if key in TRUE_VALUES:
        return True
    if key in FALSE_VALUES:
        return False

    return None


__all__ = [
    \"STATE_ALIASES\",
    \"CATEGORY_ALIASES\",
    \"TRUE_VALUES\",
    \"FALSE_VALUES\",
    \"normalize_state\",
    \"normalize_category\",
    \"normalize_gender\",
    \"normalize_income\",
    \"normalize_education\",
    \"normalize_bool\",
]

