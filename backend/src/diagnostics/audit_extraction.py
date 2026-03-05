import json
import pandas as pd
from pathlib import Path
import statistics

P = Path("backend/data/processed/schemes_with_rules.parquet")
if not P.exists():
    print("ERROR: backend/data/processed/schemes_with_rules.parquet not found. Run extract_eligibility_rules.py first.")
    raise SystemExit(1)

df = pd.read_parquet(P)
n = len(df)
print(f"Loaded {n} schemes from {P}")

col = "eligibility_structured"
if col not in df.columns:
    print(f"Column '{col}' not present in dataframe. Extraction not run or saved to different file.")
    raise SystemExit(1)

has_structured = df[col].notna().sum()
print(f"Schemes with non-null '{col}': {has_structured} ({has_structured/n:.2%})")

total_required = 0
total_optional = 0
schemes_with_any_rule = 0
confidence_values = []

def safe_load(x):
    if x is None:
        return {}
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {}
    if isinstance(x, dict):
        return x
    return {}

for _, row in df.iterrows():
    obj = safe_load(row[col])
    req = obj.get("required", []) if isinstance(obj, dict) else []
    opt = obj.get("optional", []) if isinstance(obj, dict) else []
    if req or opt:
        schemes_with_any_rule += 1
    total_required += len(req)
    total_optional += len(opt)
    for r in req + opt:
        conf = r.get("confidence")
        if conf is not None:
            try:
                confidence_values.append(float(conf))
            except Exception:
                pass

print(f"Schemes with >=1 extracted clause: {schemes_with_any_rule} ({schemes_with_any_rule/n:.2%})")
print(f"Total required clauses extracted: {total_required}")
print(f"Total optional clauses extracted: {total_optional}")

if confidence_values:
    print(
        f"Confidence values: count={len(confidence_values)}, "
        f"mean={statistics.mean(confidence_values):.3f}, "
        f"median={statistics.median(confidence_values):.3f}, "
        f"min={min(confidence_values):.3f}, "
        f"max={max(confidence_values):.3f}"
    )
else:
    print("No confidence values found in clauses (extractor didn't set confidence)")

df["num_clauses"] = df[col].apply(lambda x: (
    len((safe_load(x) or {}).get("required", [])) + len((safe_load(x) or {}).get("optional", []))
))
top = df.sort_values("num_clauses", ascending=False).head(10)[["scheme_id", "scheme_name", "num_clauses"]]
print("\nTop 10 schemes by clause count:")
print(top.to_string(index=False))

no_clause_df = df[df["num_clauses"] == 0]
if len(no_clause_df) > 0:
    sample_n = min(10, len(no_clause_df))
    no_clause_sample = no_clause_df.sample(sample_n, random_state=42)[["scheme_id", "scheme_name", "eligibility_raw"]]
    print("\nSample schemes with ZERO extracted clauses (for manual review):")
    for _, r in no_clause_sample.iterrows():
        print("----")
        print("id:", r["scheme_id"])
        print("name:", r["scheme_name"])
        print("eligibility_raw (truncated):", (r["eligibility_raw"] or "")[:400].replace("\n", " "))
else:
    print("\nNo schemes with zero clauses detected.")
