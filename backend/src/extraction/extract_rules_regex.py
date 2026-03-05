import re

def extract_rules_regex(text):
    rules = []

    # ---------- RULE 1: STATE ----------
    m = re.search(r"(?:native of|resident of)\s+([A-Z][a-zA-Z]+)", text)
    if m:
        rules.append({
            "field": "state",
            "operator": "==",
            "value": m.group(1),
            "confidence": 0.9,
            "source": "regex",
            "text_span": m.group(0)
        })

    # ---------- RULE 2: OCCUPATION ----------
    if re.search(r"\bfarmer\b", text, re.IGNORECASE):
        rules.append({
            "field": "occupation",
            "operator": "==",
            "value": "Farmer",
            "confidence": 0.9,
            "source": "regex",
            "text_span": "Farmer"
        })

    # ---------- RULE 3: LAND AREA ----------
    land = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|hectares)", text)
    if land:
        rules.append({
            "field": "land_area",
            "operator": ">=",
            "value": float(land.group(1)),
            "confidence": 0.9,
            "source": "regex",
            "text_span": land.group(0)
        })

    return {"required": rules, "optional": []}
