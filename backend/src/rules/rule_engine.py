import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.src.profile.user_profile_model import UserProfile


RuleValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]


ALLOWED_OPERATORS = {
    "=", "in", "contains", ">=", "<=", ">", "<", "between", "exists", "not_exists"
}


@dataclass
class RuleEvaluation:
    rule: Dict[str, Any]
    passed: Optional[bool]  # True / False / None (unknown / not-applicable)
    reason: str


def _load_field_mapping(path: str = "rule_field_to_profile_field.json") -> Dict[str, str]:
    """
    Load rule_field_to_profile_field.json mapping.
    Falls back to identity mapping if the file is missing.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        # Ensure keys are treated case-insensitively at lookup time
        return mapping
    except FileNotFoundError:
        return {}


def _map_field_name(field: str, mapping: Dict[str, str]) -> str:
    """Map a rule field name to a UserProfile attribute using the provided mapping."""
    if not field:
        return "other"
    key = str(field).strip()
    # Try exact mapping first, then lowercase key
    if key in mapping:
        return mapping[key]
    if key.lower() in mapping:
        return mapping[key.lower()]
    # If no mapping, use the field name itself; caller can decide whether to use it
    return key


def _get_profile_value(profile: UserProfile, attr: str) -> Any:
    """Safely get an attribute from UserProfile."""
    return getattr(profile, attr, None)


def _coerce_numeric(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if not s:
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def _evaluate_single_rule(
    rule: Dict[str, Any],
    profile: UserProfile,
    field_mapping: Dict[str, str],
) -> RuleEvaluation:
    """
    Evaluate a single rule against a UserProfile.

    Returns RuleEvaluation with passed = True / False / None (unknown).
    """
    raw_field = rule.get("field")
    operator = rule.get("operator")
    value: RuleValue = rule.get("value")

    mapped_field = _map_field_name(str(raw_field or ""), field_mapping)

    # Ignore rules that map to "other" or unknown fields for now
    if mapped_field == "other":
        return RuleEvaluation(rule, None, "field_mapped_to_other")

    if not operator or operator not in ALLOWED_OPERATORS:
        return RuleEvaluation(rule, None, "unsupported_operator")

    # For most operators we require a non-null value
    if operator not in {"exists", "not_exists"} and value is None:
        return RuleEvaluation(rule, None, "missing_rule_value")

    profile_val = _get_profile_value(profile, mapped_field)

    # Handle exists / not_exists first
    if operator == "exists":
        passed = profile_val is not None
        return RuleEvaluation(rule, passed, "exists_check")
    if operator == "not_exists":
        passed = profile_val is None
        return RuleEvaluation(rule, passed, "not_exists_check")

    # If we don't have a value in the profile, we can't decide
    if profile_val is None:
        return RuleEvaluation(rule, None, "missing_profile_value")

    # Equality / contains / in for non-numeric fields
    if operator == "=":
        passed = str(profile_val) == str(value)
        return RuleEvaluation(rule, passed, "equality_check")

    if operator == "contains":
        passed = str(value) in str(profile_val)
        return RuleEvaluation(rule, passed, "contains_check")

    if operator == "in":
        if isinstance(value, list):
            passed = str(profile_val) in [str(v) for v in value]
        else:
            passed = str(profile_val) == str(value)
        return RuleEvaluation(rule, passed, "in_check")

    # Numeric comparisons
    left = _coerce_numeric(profile_val)
    if left is None:
        return RuleEvaluation(rule, None, "profile_value_not_numeric")

    if operator in {">", "<", ">=", "<="}:
        right = _coerce_numeric(value)
        if right is None:
            return RuleEvaluation(rule, None, "rule_value_not_numeric")
        if operator == ">":
            passed = left > right
        elif operator == "<":
            passed = left < right
        elif operator == ">=":
            passed = left >= right
        else:  # "<="
            passed = left <= right
        return RuleEvaluation(rule, passed, "numeric_compare")

    if operator == "between":
        # value can be [min, max] or {"min": x, "max": y}
        lo = hi = None
        if isinstance(value, list) and len(value) == 2:
            lo = _coerce_numeric(value[0])
            hi = _coerce_numeric(value[1])
        elif isinstance(value, dict):
            lo = _coerce_numeric(value.get("min"))
            hi = _coerce_numeric(value.get("max"))
        if lo is None or hi is None:
            return RuleEvaluation(rule, None, "between_value_not_numeric")
        passed = lo <= left <= hi
        return RuleEvaluation(rule, passed, "between_check")

    # Fallback: unknown combination
    return RuleEvaluation(rule, None, "unsupported_rule_type")


def evaluate_scheme_eligibility(
    scheme_row: Dict[str, Any],
    profile: UserProfile,
    mapping_path: str = "rule_field_to_profile_field.json",
) -> Dict[str, Any]:
    """
    Evaluate whether a UserProfile satisfies the required rules for a given scheme.

    Args:
        scheme_row: dict-like row from processed_schemes with 'eligibility_structured' as JSON or dict.
        profile: normalized UserProfile.
        mapping_path: path to rule_field_to_profile_field.json.

    Returns:
        {
          "is_eligible": True | False | None,
          "required": [RuleEvaluation...],
          "optional": [RuleEvaluation...],
          "summary": {
             "required_passed": int,
             "required_failed": int,
             "required_unknown": int,
             "optional_passed": int,
             "optional_failed": int,
             "optional_unknown": int,
          }
        }
    """
    field_mapping = _load_field_mapping(mapping_path)

    raw_structured = scheme_row.get("eligibility_structured") or {}
    if isinstance(raw_structured, str):
        try:
            structured = json.loads(raw_structured)
        except json.JSONDecodeError:
            structured = {"required": [], "optional": [], "notes": "invalid_json"}
    elif isinstance(raw_structured, dict):
        structured = raw_structured
    else:
        structured = {"required": [], "optional": [], "notes": "unknown_type"}

    required_rules = structured.get("required") or []
    optional_rules = structured.get("optional") or []

    required_evals: List[RuleEvaluation] = []
    optional_evals: List[RuleEvaluation] = []

    for rule in required_rules:
        if not isinstance(rule, dict):
            continue
        required_evals.append(_evaluate_single_rule(rule, profile, field_mapping))

    for rule in optional_rules:
        if not isinstance(rule, dict):
            continue
        optional_evals.append(_evaluate_single_rule(rule, profile, field_mapping))

    def _summarize(evals: List[RuleEvaluation]) -> Tuple[int, int, int]:
        passed = sum(1 for ev in evals if ev.passed is True)
        failed = sum(1 for ev in evals if ev.passed is False)
        unknown = sum(1 for ev in evals if ev.passed is None)
        return passed, failed, unknown

    req_passed, req_failed, req_unknown = _summarize(required_evals)
    opt_passed, opt_failed, opt_unknown = _summarize(optional_evals)

    # Determine overall eligibility:
    # - any failed required rule => False
    # - no failed required rules, at least one required unknown => None (unknown)
    # - otherwise (no required failed, all known passed or no required rules) => True
    if req_failed > 0:
        overall = False
    elif req_unknown > 0 and req_passed == 0:
        overall = None
    else:
        overall = True

    return {
        "is_eligible": overall,
        "required": [ev.__dict__ for ev in required_evals],
        "optional": [ev.__dict__ for ev in optional_evals],
        "summary": {
            "required_passed": req_passed,
            "required_failed": req_failed,
            "required_unknown": req_unknown,
            "optional_passed": opt_passed,
            "optional_failed": opt_failed,
            "optional_unknown": opt_unknown,
        },
    }


__all__ = [
    "RuleEvaluation",
    "evaluate_scheme_eligibility",
]
