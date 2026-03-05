import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, Any, Set

import pandas as pd


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


DEFAULT_INPUT = "backend/data/processed/schemes_with_rules.parquet"
DEFAULT_OUTPUT_JSON = "backend/data/mappings/rule_field_to_profile_field.json"
DEFAULT_UNMAPPED_LOG = "unmapped_fields.log"


# Canonical mapping from rule field names to UserProfile attributes
BASE_FIELD_MAPPING: Dict[str, str] = {
    # direct
    "age": "age",
    "state": "state",
    "district": "district",
    "pincode": "pincode",
    "gender": "gender",
    "occupation": "occupation",
    "education": "education_level",
    "education_level": "education_level",
    "farmer": "farmer",
    "land": "land_area",
    "land_area": "land_area",
    "disability": "disability",
    "business": "business_type",
    "business_type": "business_type",
    "income_annual": "income_annual",
    "category": "category",
    "documents": "documents",
    # income synonyms
    "income": "income_annual",
    "annual_income": "income_annual",
    "family_income": "income_annual",
    "household_income": "income_annual",
    # state synonyms
    "state_of_residence": "state",
    "residing_state": "state",
    "residence_state": "state",
    "location_state": "state",
    # category synonyms
    "caste": "category",
    "social_category": "category",
    # gender synonyms when used as field name
    "woman": "gender",
    "women": "gender",
    "female": "gender",
    # other catch-all
    "other": "other",
}


def _load_rules(df: pd.DataFrame) -> Dict[str, Any]:
    """Return a dict-like view of eligibility_structured per row."""
    if "eligibility_structured" not in df.columns:
        raise KeyError("Column 'eligibility_structured' not found in input data.")

    parsed_rules = {}
    for idx, raw in df["eligibility_structured"].items():
        if isinstance(raw, dict):
            parsed_rules[idx] = raw
            continue
        if isinstance(raw, str):
            try:
                parsed_rules[idx] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Row %s has invalid JSON in eligibility_structured; skipping.", idx)
        else:
            logger.warning("Row %s has unsupported type for eligibility_structured; skipping.", idx)
    return parsed_rules


def _collect_unique_fields(rules_by_row: Dict[int, Any]) -> Counter:
    fields_counter: Counter = Counter()
    for rules in rules_by_row.values():
        for bucket in ("required", "optional"):
            raw_list = rules.get(bucket, [])

            # Guard against unexpected types (e.g., numpy arrays, None, scalars)
            if raw_list is None:
                continue
            if not isinstance(raw_list, list):
                try:
                    # Try to coerce to list (for numpy arrays etc.)
                    raw_list = list(raw_list)
                except TypeError:
                    continue

            for rule in raw_list:
                if not isinstance(rule, dict):
                    continue
                field_name = str(rule.get("field", "")).strip()
                if not field_name:
                    continue
                fields_counter[field_name] += 1
    return fields_counter


def _map_field_name(field_name: str) -> str:
    key = field_name.strip().lower()
    return BASE_FIELD_MAPPING.get(key, "other")


def build_mapping(
    input_path: str = DEFAULT_INPUT,
    output_json: str = DEFAULT_OUTPUT_JSON,
    unmapped_log: str = DEFAULT_UNMAPPED_LOG,
) -> None:
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    logger.info("Loading %s ...", input_file)
    df = pd.read_parquet(input_file)

    rules_by_row = _load_rules(df)
    fields_counter = _collect_unique_fields(rules_by_row)

    logger.info("Found %d unique field names in eligibility_structured.", len(fields_counter))

    mapping: Dict[str, str] = {}
    unmapped_fields: Set[str] = set()

    for field, count in fields_counter.items():
        mapped_to = _map_field_name(field)
        mapping[field] = mapped_to
        if mapped_to == "other":
            unmapped_fields.add(field)

    # Write mapping JSON
    output_file = Path(output_json)
    output_file.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote field mapping to %s", output_file)

    # Log unmapped fields for manual review
    if unmapped_fields:
        log_file = Path(unmapped_log)
        with log_file.open("w", encoding="utf-8") as f:
            f.write("Fields mapped to 'other' (review needed):\n")
            for field in sorted(unmapped_fields):
                f.write(f"{field}\n")
        logger.info("Wrote %d unmapped fields to %s", len(unmapped_fields), log_file)
    else:
        logger.info("All fields mapped to concrete UserProfile attributes.")


if __name__ == "__main__":
    build_mapping()

