import json
import pandas as pd
import pytest

DIGGY_ID = "a23c0261-7711-4213-aecf-6b7c4cc844ed"
PARQUET = "schemes_with_rules_llm.parquet"

def load_scheme_df(path=PARQUET):
    return pd.read_parquet(path)

def test_diggy_has_expected_required_clauses():
    df = load_scheme_df()
    row = df[df["scheme_id"] == DIGGY_ID]
    assert len(row) == 1, f"Diggy scheme (id={DIGGY_ID}) not found in {PARQUET}"
    rec = row.iloc[0]
    structured = rec["eligibility_structured"]
    if isinstance(structured, str):
        structured = json.loads(structured)
    assert "required" in structured, "eligibility_structured must contain 'required'"
    required = structured["required"]
    assert len(required) >= 2, f"expected >=2 required clauses, got {len(required)}"
    fields = {clause["field"]: clause for clause in required}
    assert "state" in fields, "state clause missing"
    assert fields["state"]["value"].lower() == "rajasthan", f"expected state=Rajasthan, got {fields['state']['value']}"
    assert "occupation" in fields, "occupation clause missing"
    assert fields["occupation"]["value"].lower() in ("farmer", "farmer "), f"expected occupation=Farmer, got {fields['occupation']['value']}"
