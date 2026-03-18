import json
import re
from typing import Dict, Any
try:
    from transformers import pipeline as hf_pipeline
except Exception:
    hf_pipeline = None

def _default_schema() -> Dict[str, Any]:
    return {
        "state": "",
        "district": "",
        "age": None,
        "occupation": "",
        "income": None,
        "category": "",
        "farmer": None,
        "business_type": "",
        "intent": "",
    }

INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
    "Uttarakhand","West Bengal","Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli and Daman and Diu",
    "Delhi","Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"
]

COMMON_DISTRICTS = ["Pune","Mumbai","Nagpur","Nashik","Aurangabad"]

def _build_prompt(user_query: str) -> str:
    schema = json.dumps(_default_schema(), ensure_ascii=False)
    return (
        "Extract the following fields from the user's query and return ONLY valid JSON with exactly these keys.\n"
        "If a field is unknown, set it to null for numbers/booleans, or empty string for text.\n"
        "Fields: state, district, age, occupation, income, category, farmer, business_type, intent.\n"
        f"Schema:\n{schema}\n"
        "User query:\n"
        f"{user_query}\n"
        "Return only the JSON."
    )

def _try_hf_llm(prompt: str) -> str:
    try:
        from transformers import pipeline
        generator = pipeline("text-generation", model="google/flan-t5-small")
        out = generator(prompt, max_new_tokens=256, temperature=0.0)
        text = out[0]["generated_text"]
        return text
    except Exception:
        return ""

def _coerce_json(text: str) -> Dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            return json.loads(snippet)
    except Exception:
        pass
    return {}

def extract_location(text: str) -> Dict[str, str]:
    found_state = ""
    found_district = ""
    t = text.lower()
    for s in INDIAN_STATES:
        if re.search(rf"\b{re.escape(s.lower())}\b", t):
            found_state = s
            break
    for d in COMMON_DISTRICTS:
        if re.search(rf"\b{re.escape(d.lower())}\b", t):
            found_district = d
            break
    return {"state": found_state, "district": found_district}

def _fallback_parse(user_query: str) -> Dict[str, Any]:
    data = _default_schema()
    q = user_query.lower()
    age_match = re.search(r"(\d{1,3})\s*year", q)
    if age_match:
        try:
            data["age"] = int(age_match.group(1))
        except Exception:
            data["age"] = None
    income_match = re.search(r"(\d+(\.\d+)?)\s*lakh", q)
    if income_match:
        try:
            lakhs = float(income_match.group(1))
            data["income"] = int(lakhs * 100000)
        except Exception:
            data["income"] = None
    if "farmer" in q:
        data["farmer"] = True
        data["occupation"] = data["occupation"] or "Farmer"
    cat = None
    for c in ["sc", "st", "obc", "ews", "general"]:
        if re.search(rf"\b{c}\b", q):
            cat = c.upper() if c != "general" else "General"
            break
    if cat:
        data["category"] = cat
    intent_match = re.search(r"(what .*?schemes.*|looking for .*schemes.*|need .*scheme.*)", q)
    data["intent"] = intent_match.group(1) if intent_match else user_query.strip()
    return data

try:
    intent_model = hf_pipeline(
        "text2text-generation",
        model="google/flan-t5-small"
    ) if hf_pipeline else None
except Exception:
    intent_model = None

def normalize_intent(text: str) -> str:
    text = text.lower()

    # remove common filler phrases
    text = re.sub(r"\b(i want|i need|looking for|show me|tell me|get|find)\b", "", text)

    # remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    # keep important keywords only
    keywords = []
    for word in text.split():
        if word in [
            "agriculture","farmer","farming","subsidy","scheme","schemes",
            "loan","business","education","scholarship","housing"
        ]:
            keywords.append(word)

    return " ".join(keywords[:5])

def parse_user_query(structured_profile: Dict[str, Any], description: str) -> Dict[str, Any]:
    """
    structured_profile : dict from frontend
    description : free text
    """

    # Always initialize intent
    intent = normalize_intent(description)

    prompt = f"""
You convert a user request into a normalized intent phrase.

Rules:
- Return ONLY a short phrase (3–5 words)
- No sentences
- No punctuation
- Use lowercase words
- Focus on scheme category

User request:
{description}

Examples:
"I want subsidy schemes for farming"
→ agriculture subsidy schemes

"I need loan schemes for small business"
→ small business loan schemes

"I am looking for scholarship programs"
→ education scholarship schemes

Normalized intent:
"""

    if intent_model:
        try:
            result = intent_model(
                prompt,
                max_new_tokens=20,
                do_sample=False
            )

            raw_intent = result[0]["generated_text"]
            cleaned_intent = normalize_intent(raw_intent)

            # Only overwrite if model produced something meaningful
            if cleaned_intent:
                intent = cleaned_intent

        except Exception:
            pass

    profile = {
        "state": structured_profile.get("state", ""),
        "district": structured_profile.get("district", ""),
        "age": structured_profile.get("age", None),
        "occupation": structured_profile.get("occupation", ""),
        "income": structured_profile.get("income", None),
        "category": structured_profile.get("category", ""),
        "gender": structured_profile.get("gender", ""),
        "farmer": (
            "farmer" in (description or "").lower()
            or "farming" in (description or "").lower()
            or structured_profile.get("occupation", "").lower() == "farmer"
        ),
        "business_type": "",
        "intent": intent,
    }

    return profile

if __name__ == "__main__":
        structured_profile = {
            "state": "Maharashtra",
            "district": "Pune",
            "age": 35,
            "income": 500000,
            "category": "OBC",
            "gender": "Male",
            "occupation": "Farmer",
        }
        description = "I want government subsidy schemes for farming"
        profile = parse_user_query(structured_profile, description)
        print("\nParsed Profile\n")
        print(profile)
