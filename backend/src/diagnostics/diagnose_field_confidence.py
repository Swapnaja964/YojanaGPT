import json
import statistics
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter

P = Path("backend/data/processed/schemes_with_rules.parquet")
if not P.exists():
    print("ERROR: backend/data/processed/schemes_with_rules.parquet not found. Run extraction first.")
    raise SystemExit(1)

df = pd.read_parquet(P)
col = "eligibility_structured"
if col not in df.columns:
    print(f"Column '{col}' missing.")
    raise SystemExit(1)

def safe_load(x):
    if x is None:
        return {}
    if isinstance(x, str):
        try:
            obj = json.loads(x)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    if isinstance(x, dict):
        return x
    return {}

field_stats = defaultdict(lambda: {"count": 0, "confidences": [], "sources": Counter(), "examples": []})

for _, row in df.iterrows():
    raw = row.get("eligibility_raw", "") or ""
    obj = safe_load(row[col])
    if not isinstance(obj, dict):
        obj = {}
    for bucket in ("required", "optional"):
        items = obj.get(bucket) or []
        if not isinstance(items, list):
            continue
        for clause in items:
            if not isinstance(clause, dict):
                continue
            field = clause.get("field") or "OTHER"
            conf = clause.get("confidence")
            src = clause.get("source") or "unknown"
            text_span = clause.get("text_span") or clause.get("text", "") or ""
            field_stats[field]["count"] += 1
            if conf is not None:
                try:
                    field_stats[field]["confidences"].append(float(conf))
                except Exception:
                    pass
            field_stats[field]["sources"][src] += 1
            try:
                confv = float(conf) if conf is not None else None
            except Exception:
                confv = None
            if confv is None or confv <= 0.6:
                if len(field_stats[field]["examples"]) < 10:
                    field_stats[field]["examples"].append({
                        "conf": confv,
                        "text_span": text_span.strip(),
                        "eligibility_raw_snippet": (raw[:600].replace("\n", " ") if raw else "")
                    })

total_fields = sum(v["count"] for v in field_stats.values())
print(f"Total clauses across all fields: {total_fields}")
print(f"Unique fields extracted: {len(field_stats)}\n")

summary = []
for field, data in field_stats.items():
    cnt = data["count"]
    confs = data["confidences"]
    mean_conf = statistics.mean(confs) if confs else None
    med_conf = statistics.median(confs) if confs else None
    src_counts = dict(data["sources"])
    low_examples = len(data["examples"])
    summary.append((field, cnt, mean_conf, med_conf, src_counts, low_examples))

summary_sorted = sorted(summary, key=lambda x: x[1], reverse=True)

print("Top fields by number of clauses (field, count, mean_conf, median_conf, sources, low_examples_collected):\n")
for field, cnt, mean_conf, med_conf, src_counts, low_examples in summary_sorted[:25]:
    mc = f"{mean_conf:.3f}" if mean_conf is not None else "N/A"
    md = f"{med_conf:.3f}" if med_conf is not None else "N/A"
    print(f"- {field:20} | count={cnt:5} | mean_conf={mc:>5} | median={md:>5} | sources={src_counts} | low_examples={low_examples}")
print("\n")

candidates = [(f, cnt, mean_conf, med_conf) for f, cnt, mean_conf, med_conf, _, le in summary_sorted if (mean_conf is None) or (mean_conf <= 0.65) or (med_conf is None) or (med_conf <= 0.5) or le >= 5]
candidates = sorted(candidates, key=lambda x: x[1], reverse=True)

print("FIELDS RECOMMENDED FOR IMMEDIATE HEURISTIC WORK (count, mean_conf, median_conf):")
for f, cnt, mean_conf, med_conf in candidates[:20]:
    mc = f"{mean_conf:.3f}" if mean_conf is not None else "N/A"
    md = f"{med_conf:.3f}" if med_conf is not None else "N/A"
    print(f" * {f}: count={cnt}, mean_conf={mc}, median_conf={md}")
print("\n")

top_fields = [f for f, _, _, _ in candidates[:6]]
for f in top_fields:
    print("=" * 80)
    print(f"FIELD: {f}")
    print(f"Total clauses: {field_stats[f]['count']}; source counts: {field_stats[f]['sources']}")
    print("Sample low-confidence examples (conf, text_span, truncated eligibility_raw):\n")
    for ex in field_stats[f]["examples"]:
        print(f" - conf={ex['conf']}, span='{ex['text_span']}'")
        print(f"   raw: {ex['eligibility_raw_snippet'][:400]}...\n")
    print("\n")

print("Diagnosis complete. Copy the list of recommended fields and a few examples above and paste them back here so I can give the single next step (regex patterns or prompt examples).")
