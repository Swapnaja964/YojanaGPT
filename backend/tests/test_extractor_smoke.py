import json
import pandas as pd
import pytest

from backend.src.extraction.extract_eligibility_rules import EligibilityExtractor

EXTRACTOR = EligibilityExtractor()

def load_scheme_by_id(parquet_path: str, scheme_id: str):
    df = pd.read_parquet(parquet_path)
    row = df[df["scheme_id"] == scheme_id]
    assert len(row) == 1, f"scheme_id={scheme_id} not found in {parquet_path}"
    return row.iloc[0]

def test_diggy_extraction_matches_expected():
    row = load_scheme_by_id("schemes_cleaned.parquet", "a23c0261-7711-4213-aecf-6b7c4cc844ed")
    structured = EXTRACTOR._extract_rules_for_scheme(row.to_dict())
    assert isinstance(structured, dict)
    req = structured.get("required", [])
    states = [c for c in req if c.get("field") == "state"]
    assert len(states) >= 1, "no state clause found for Diggy"
    assert str(states[0]["value"]).lower() == "rajasthan"
    occs = [c for c in req if c.get("field") == "occupation"]
    assert len(occs) >= 1, "no occupation clause found for Diggy"
    assert str(occs[0]["value"]).lower().strip() == "farmer"

def test_land_area_normalization():
    fake_row = {
        "scheme_id": "test-land-area",
        "eligibility_raw": "The farmer must have at least 0.5 hectares of irrigated land.",
        "description_raw": "",
    }
    structured = EXTRACTOR._extract_rules_for_scheme(fake_row)
    req = structured.get("required", [])
    land = [c for c in req if c.get("field") == "land_area"]
    assert len(land) >= 1, f"expected at least one land_area clause, got {len(land)}"
    clause = land[0]
    val = clause.get("value")
    assert isinstance(val, (int, float)), f"land_area value should be numeric, got {type(val)}"
    assert val >= 0.5, f"expected land_area >= 0.5, got {val}"
    assert clause.get("operator") in (">=", "between")
