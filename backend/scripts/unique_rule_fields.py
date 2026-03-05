import json
import pandas as pd


def main():
    # For now, use the locally processed subset with eligibility_structured:
    # this is what extract_eligibility_rules.py is writing.
    input_path = "output/processed_schemes.parquet"
    output_path = "unique_rule_fields.txt"

    df = pd.read_parquet(input_path)

    unique_fields = set()

    for _, row in df.iterrows():
        raw = row.get("eligibility_structured")
        if raw is None:
            continue

        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
        elif isinstance(raw, dict):
            data = raw
        else:
            continue

        for bucket in ("required", "optional"):
            rules = data.get(bucket) or []
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                field = rule.get("field")
                if field is None:
                    continue
                unique_fields.add(str(field))

    fields_sorted = sorted(unique_fields)

    with open(output_path, "w", encoding="utf-8") as f:
        for field in fields_sorted:
            f.write(field + "\n")

    print(f"Wrote {len(fields_sorted)} unique fields to {output_path}")


if __name__ == "__main__":
    main()


