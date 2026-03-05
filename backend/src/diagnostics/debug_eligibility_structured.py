import pandas as pd
import json

SCHEME_IDS_TO_CHECK = [
    "a23c0261-7711-4213-aecf-6b7c4cc844ed",  # Diggy
    "b4a7f934-4fb6-4809-ab3a-ff39bdde2d08",  # Jal Hauj
    "94189f08-1583-4be3-b0e4-0c2043bdf6c4",  # Shednet House
]

df = pd.read_parquet("backend/data/processed/schemes_with_rules.parquet")

for sid in SCHEME_IDS_TO_CHECK:
    row = df[df["scheme_id"] == sid]
    print("=" * 80)
    print("Scheme ID:", sid)
    if row.empty:
        print("⚠️ No row found for this scheme_id")
        continue

    name = row["scheme_name"].iloc[0] if hasattr(row["scheme_name"], 'iloc') else row["scheme_name"].values[0]
    print("Name:", name)

    es = row["eligibility_structured"].values[0]
    print("Raw eligibility_structured type:", type(es))

    # If it's a string, try to parse
    if isinstance(es, str):
        try:
            es_json = json.loads(es)
            print("Parsed JSON keys:", es_json.keys())
            print("Required rules count:", len(es_json.get("required", [])))
            print("Optional rules count:", len(es_json.get("optional", [])))
            
            # Print first few rules if available
            if "required" in es_json and es_json["required"]:
                print("\nSample required rules:")
                for i, rule in enumerate(es_json["required"][:3], 1):
                    print(f"  {i}. {rule}")
            
            if "optional" in es_json and es_json["optional"]:
                print("\nSample optional rules:")
                for i, rule in enumerate(es_json["optional"][:3], 1):
                    print(f"  {i}. {rule}")
                    
        except Exception as e:
            print("⚠️ Failed to parse eligibility_structured as JSON:", e)
            print("Value snippet:", es[:500])
    elif isinstance(es, dict):
        print("Dict keys:", es.keys())
        print("Required rules count:", len(es.get("required", [])))
        print("Optional rules count:", len(es.get("optional", [])))
        
        # Print first few rules if available
        if "required" in es and es["required"]:
            print("\nSample required rules:")
            for i, rule in enumerate(es["required"][:3], 1):
                print(f"  {i}. {rule}")
        
        if "optional" in es and es["optional"]:
            print("\nSample optional rules:")
            for i, rule in enumerate(es["optional"][:3], 1):
                print(f"  {i}. {rule}")
    else:
        print("⚠️ eligibility_structured is neither str nor dict:", es)
