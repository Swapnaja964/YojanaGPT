import pandas as pd
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--parquet", default="backend/data/processed/schemes_with_rules.parquet")
parser.add_argument("--id", default="a23c0261-7711-4213-aecf-6b7c4cc844ed")
args = parser.parse_args()

df = pd.read_parquet(args.parquet)
row = df[df.scheme_id == args.id].iloc[0]

print("Raw eligibility_structured JSON:\n")
print(row["eligibility_structured"])

obj = row["eligibility_structured"]
if isinstance(obj, str):
    try:
        obj = json.loads(obj)
    except Exception:
        obj = {}

print("\nKeys:", list(obj.keys()))
print("\nRequired clauses:", obj.get("required"))
print("\nOptional clauses:", obj.get("optional"))
