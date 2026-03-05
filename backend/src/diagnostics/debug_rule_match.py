import json
import pandas as pd
from pathlib import Path
import importlib
import sys

# Adjust these two scheme IDs (taken from your earlier test output)
SCHEME_IDS = [
    "a23c0261-7711-4213-aecf-6b7c4cc844ed",  # Diggy (Rajasthan)
    "b4a7f934-4fb6-4809-ab3a-ff39bdde2d08",  # Jal Hauj (Rajasthan)
]

# Two profiles used in tests (Karnataka farmer and Rajasthan farmer)
PROFILES = {
    "karnataka_farmer": {
        "user_id": None, "state":"Karnataka", "district":"Tumkur", "pincode":None,
        "age":45, "gender":"male", "category":"SC", "income_annual":120000.0,
        "occupation":"Farmer", "education_level":None, "farmer":True,
        "land_area":2.5, "land_type":"agricultural", "documents":{}, "extra_flags":{}
    },
    "rajasthan_farmer": {
        "user_id": None, "state":"Rajasthan", "district":"Jaipur", "pincode":None,
        "age":40, "gender":"male", "category":"General", "income_annual":150000.0,
        "occupation":"Farmer", "education_level":None, "farmer":True,
        "land_area":1.0, "land_type":"agricultural", "documents":{}, "extra_flags":{}
    }
}

DATA_FILE = Path("backend/data/processed/schemes_with_rules.parquet")
if not DATA_FILE.exists():
    print("ERROR: schemes_with_rules.parquet not found. Run extractor first.")
    raise SystemExit(1)

df = pd.read_parquet(DATA_FILE).set_index("scheme_id")
print(f"Loaded {len(df)} schemes from {DATA_FILE}\n")

# Try to import your rule evaluator (adapt if module name differs).
EVAL_MODULE_NAME = "backend.src.rules.rule_evaluator"
try:
    rule_eval = importlib.import_module(EVAL_MODULE_NAME)
    # prefer evaluate_scheme_rules or evaluate_rules function
    if hasattr(rule_eval, "evaluate_scheme_rules"):
        eval_fn = rule_eval.evaluate_scheme_rules
    elif hasattr(rule_eval, "evaluate_rules"):
        eval_fn = rule_eval.evaluate_rules
    else:
        print(f"ERROR: module '{EVAL_MODULE_NAME}' found but no evaluate_scheme_rules/evaluate_rules function.")
        eval_fn = None
except Exception as e:
    print(f"Could not import {EVAL_MODULE_NAME}: {e}")
    eval_fn = None

# Try to load field mapping that maps rule fields -> profile fields if it exists
mapping_path = Path("backend/data/mappings/rule_field_to_profile_field.json")
field_mapping = {}
if mapping_path.exists():
    try:
        field_mapping = json.load(open(mapping_path, "r", encoding="utf-8"))
        print(f"Loaded field mapping from {mapping_path} (len={len(field_mapping)})")
    except Exception as e:
        print(f"Failed to load mapping {mapping_path}: {e}")
else:
    print("No rule_field_to_profile_field.json found — continuing without mapping.\n")

def pretty_print_rule(rule, idx=None):
    idxs = f"[{idx}] " if idx is not None else ""
    return f"{idxs}field={rule.get('field')} op={rule.get('operator')} val={rule.get('value')} conf={rule.get('confidence')} src={rule.get('source')} span={repr(rule.get('text_span') or '')}"

for scheme_id in SCHEME_IDS:
    print("="*80)
    print("SCHEME:", scheme_id)
    if scheme_id not in df.index:
        print("Scheme id not found in parquet. Skipping.")
        continue
    row = df.loc[scheme_id]
    print("scheme_name:", row.get("scheme_name"))
    structured = row.get("eligibility_structured")
    # structured may be string; try parse
    if isinstance(structured, str):
        try:
            structured_obj = json.loads(structured)
        except Exception:
            structured_obj = None
    else:
        structured_obj = structured

    print("\nRaw eligibility snippet (first 600 chars):")
    text = (row.get("eligibility_raw") or row.get("description_raw") or "")
    print(text[:600].replace("\n", " "))

    print("\nParsed eligibility_structured type:", type(structured_obj))
    if not structured_obj:
        print("No structured object found — extractor failure for this scheme.")
        continue

    # Show required & optional counts and first 20 rules
    required = structured_obj.get("required", [])
    optional = structured_obj.get("optional", [])
    print(f"\nRequired clauses: {len(required)}; Optional clauses: {len(optional)}\n")
    print("First 30 required clauses (if present):")
    for i, r in enumerate(required[:30]):
        print(pretty_print_rule(r, i))

    print("\nFirst 10 optional clauses (if present):")
    for i, r in enumerate(optional[:10]):
        print(pretty_print_rule(r, i))

    # Print field names used in rules and how they map to profile fields (if mapping exists)
    rule_fields = sorted({r.get("field") for r in required+optional if r.get("field")})
    print("\nUnique rule fields detected:", rule_fields)
    if field_mapping:
        print("Mapping example (rule_field -> profile_field):")
        for rf in rule_fields[:40]:
            mapped = field_mapping.get(rf, "<no mapping>")
            print(f"  {rf}  ->  {mapped}")
    else:
        print("No field mapping available; evaluator will need exact field names or its own mapping.\n")

    # Show profile values that would be used for matching
    # Use both profiles (Karnataka and Rajasthan)
    for pname, profile in PROFILES.items():
        print("\n" + "-"*40)
        print("Evaluating against profile:", pname)
        # print relevant profile keys for detected rule fields
        print("Profile slice (fields relevant to rules):")
        for rf in rule_fields:
            pf = field_mapping.get(rf, rf) if field_mapping else rf
            print(f" {rf:20} -> profile field '{pf}':", profile.get(pf, "<missing>"))
        # If evaluator exists, call it and print result
        if eval_fn:
            try:
                # Call with correct signature: (eligibility_structured, user_profile)
                res = eval_fn(structured_obj, profile)
                print("\nEvaluator result (raw):")
                print(json.dumps(res, indent=2, default=str)[:4000])
            except Exception as e:
                print("Evaluator call failed:", e)
        else:
            print("No evaluator function available to compute rule-score.")

print("\nDiagnostic complete. Paste the whole output here.")
