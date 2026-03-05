# extract_eligibility_rules.py
import os
import json
import logging
import re
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from backend.src.extraction.deterministic_patterns import extract_deterministic_rules
from backend.src.extraction.extract_rules_regex import extract_rules_regex
from backend.src.profile.profile_value_normalizers import normalize_state

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eligibility_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EligibilityExtractor:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'input_file': 'backend/data/processed/schemes_cleaned.parquet',
            'output_file': 'backend/data/processed/schemes_with_rules.parquet',
            'batch_size': 10,
            'max_retries': 3,
            'delay_between_requests': 1.0,
            'llm_fallback': False,
            'limit': None
        }
        self.df = None
        self.processed_count = 0
        self._llm_cache: Dict[str, Any] = {}
        
    def load_data(self) -> bool:
        """Load the input parquet file."""
        try:
            self.df = pd.read_parquet(self.config['input_file'])
            logger.info(f"Loaded {len(self.df)} schemes from {self.config['input_file']}")
            return True
        except Exception as e:
            logger.error(f"Error loading input file: {e}")
            return False

    def extract_rules(self) -> bool:
        """Extract rules for all schemes in the dataframe."""
        if self.df is None:
            logger.error("No data loaded. Call load_data() first.")
            return False

        # Process in batches
        batch_size = self.config.get('batch_size', 10)
        total_schemes = len(self.df)
        
        logger.info(f"Starting rule extraction for {total_schemes} schemes...")
        
        limit = self.config.get('limit')
        if isinstance(limit, int) and limit > 0:
            work_df = self.df.iloc[:limit]
        else:
            work_df = self.df
        for i in range(0, len(work_df), batch_size):
            batch = work_df.iloc[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_schemes + batch_size - 1)//batch_size}")
            
            for _, row in batch.iterrows():
                try:
                    rules = self._extract_rules_for_scheme(row)
                    if self.config.get('llm_fallback'):
                        rules = self._apply_llm_fallback_if_needed(row.get('scheme_id', ''), str(row.get('eligibility_raw') or ''), rules)
                    self.df.at[row.name, 'eligibility_structured'] = json.dumps(rules)
                    self.processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing scheme {row.get('scheme_id', 'unknown')}: {str(e)}")
                    self.df.at[row.name, 'eligibility_structured'] = json.dumps({
                        "required": [],
                        "optional": [],
                        "error": str(e)
                    })

        return True

    def _extract_rules_for_scheme(self, scheme_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured eligibility rules for a single scheme."""
        out = {
            "required": [],
            "optional": [],
            "notes": {},
            "source_text": (scheme_data.get('eligibility_raw', '') or '')[:500] + ("..." if len(scheme_data.get('eligibility_raw', '') or '') > 500 else "")
        }

        elig_text = str(scheme_data.get('eligibility_raw') or '')
        desc_text = str(scheme_data.get('description_raw') or '')
        combined_text = (elig_text + " " + desc_text).strip()

        # ---- begin: post-process OTHER clauses -> concrete fields ----
        def remap_other_clauses(clauses, text):
            """
            Remap clauses with field 'other' into more specific fields when patterns match.
            Returns new list of clauses (modifies confidence and source when remapped).
            """
            new_clauses = []
            for c in clauses:
                if c.get("field") != "other" or not c.get("text_span"):
                    new_clauses.append(c)
                    continue

                span = c.get("text_span", "") or ""
                lower = span.lower()
                remapped = False

                # 1) STATE / NATIVE
                m = re.search(r"(?:native|resident|resident of|domiciled in|resident of the state of)\s+([A-Za-z &.-]+)", span, re.I)
                if m:
                    state = m.group(1).strip()
                    new_clauses.append({**c, "field": "state", "value": state, "op": "==", "confidence": max(c.get("confidence",0.5), 0.9), "source":"heuristic_regex"})
                    remapped = True

                # 2) OCCUPATION
                if not remapped and re.search(r"\b(farmer|agriculturist|fisherman|worker|student|entrepreneur|artisan|micro|small)\b", lower):
                    occ = re.search(r"\b(farmer|agriculturist|fisherman|worker|student|entrepreneur|artisan|micro|small)\b", lower).group(1)
                    new_clauses.append({**c, "field":"occupation", "value": occ.capitalize(), "op":"==", "confidence": max(c.get("confidence",0.5), 0.85), "source":"heuristic_regex"})
                    remapped = True

                # 3) LAND AREA (hectare/ha)
                if not remapped:
                    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|ha)", span, re.I)
                    if m:
                        new_clauses.append({**c, "field":"land_area", "value": float(m.group(1)), "op": ">=", "confidence": max(c.get("confidence",0.5),0.9), "source":"heuristic_regex"})
                        remapped = True

                # 4) INCOME CAPS (₹ or numbers with 'income' context)
                if not remapped:
                    m = re.search(r"(?:annual\s+income|income|family income|household income)[^0-9₹RsRs.\d\n\r:]{0,20}[₹Rs\.\s]*([0-9,]+(?:\.\d+)?)", span, re.I)
                    if m:
                        val = float(m.group(1).replace(",",""))
                        new_clauses.append({**c, "field":"income_annual", "value": val, "op":"<=", "confidence": max(c.get("confidence",0.5),0.9), "source":"heuristic_regex"})
                        remapped = True

                # 5) AGE ranges / min-max
                if not remapped:
                    m = re.search(r"age\s*(?:group|between|from)?\s*(\d{1,3})(?:\s*(?:-|to)\s*(\d{1,3}))?", span, re.I)
                    if m:
                        if m.group(2):
                            new_clauses.append({**c, "field":"age", "value": {"min": int(m.group(1)), "max": int(m.group(2))}, "op":"between", "confidence": max(c.get("confidence",0.5),0.9), "source":"heuristic_regex"})
                        else:
                            new_clauses.append({**c, "field":"age", "value": int(m.group(1)), "op":">=", "confidence": max(c.get("confidence",0.5),0.85), "source":"heuristic_regex"})
                        remapped = True

                # 6) COMMUNITY / CATEGORY (SC/ST/OBC/Brahmin etc.)
                if not remapped:
                    m = re.search(r"\b(sc|st|obc|general|brahmin|minority|muslim|sikh|christian)\b", lower)
                    if m:
                        new_clauses.append({**c, "field":"category", "value": m.group(1).upper(), "op":"==", "confidence": max(c.get("confidence",0.5),0.85), "source":"heuristic_regex"})
                        remapped = True

                # 7) Default: keep as 'other' but reduce confidence so it won't dominate
                if not remapped:
                    c_mod = dict(c)
                    c_mod["confidence"] = min(c_mod.get("confidence",0.5), 0.6)
                    new_clauses.append(c_mod)

            return new_clauses
        # ---- end: post-process OTHER clauses ----

        # Prefer the simplified regex extractor first
        det_struct = extract_rules_regex(combined_text)
        required_rules = det_struct.get("required", []) if isinstance(det_struct, dict) else []
        optional_rules = det_struct.get("optional", []) if isinstance(det_struct, dict) else []

        if required_rules or optional_rules:
            def normalize_ops(rule):
                op = rule.get("operator")
                if op == "==":
                    rule["operator"] = "="
                # accept 'op' alias
                if not rule.get("operator") and rule.get("op"):
                    rule["operator"] = rule["op"].replace("==","=")
                # field/value normalization
                f = str(rule.get("field") or "").lower()
                v = rule.get("value")
                if f == "state" and isinstance(v, str):
                    rule["value"] = normalize_state(v) or v
                if f == "occupation" and isinstance(v, str):
                    rule["value"] = self.canonicalize_occupation(v)
                if f == "land_area":
                    rule = self.ensure_land_area_hectares(rule)
                return rule

            # Remap 'other' clauses before normalization
            req_remapped = remap_other_clauses(required_rules, elig_text or desc_text)
            opt_remapped = remap_other_clauses(optional_rules, elig_text or desc_text)

            out["required"] = [normalize_ops(r) for r in req_remapped]
            out["optional"] = [normalize_ops(r) for r in opt_remapped]
            out["notes"] = {"deterministic": True, "rule_count": len(out["required"]) + len(out["optional"]) }
            return out

        if not elig_text:
            out["notes"] = {"deterministic": False, "reason": "no_eligibility_text"}
            return out

    def _apply_llm_fallback_if_needed(self, scheme_id: str, elig_text: str, structured: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(structured, dict):
            return structured
        if not isinstance(structured.get('required'), list):
            structured['required'] = []
        if not isinstance(structured.get('optional'), list):
            structured['optional'] = []
        def best_conf(field: str) -> float:
            confs = []
            for c in structured.get('required', []):
                if isinstance(c, dict) and str(c.get('field')).lower() == field:
                    try:
                        confs.append(float(c.get('confidence', 0.0)))
                    except Exception:
                        pass
            for c in structured.get('optional', []):
                if isinstance(c, dict) and str(c.get('field')).lower() == field:
                    try:
                        confs.append(float(c.get('confidence', 0.0)))
                    except Exception:
                        pass
            return max(confs) if confs else 0.0
        def has_field(field: str) -> bool:
            return any(isinstance(c, dict) and str(c.get('field')).lower() == field for c in structured.get('required', [])) or any(isinstance(c, dict) and str(c.get('field')).lower() == field for c in structured.get('optional', []))
        llm_needed = []
        for f in ("state", "occupation", "land_area"):
            if (not has_field(f)) or (best_conf(f) < 0.75):
                llm_needed.append(f)
        if not llm_needed:
            return structured
        llm_json = self._call_llm_fallback(elig_text)
        validated = self._validate_and_canonicalize(llm_json, elig_text)
        if validated:
            for f in llm_needed:
                if f in validated:
                    use_clause = validated[f]
                    use_clause["source"] = (str(use_clause.get("source") or "") + "|llm_fallback").lstrip("|")
                    use_clause["confidence"] = max(0.75, float(use_clause.get("confidence", 0.75)))
                    structured["required"].append(use_clause)
            self._cache_llm_result(scheme_id, validated)
        # Gender fallback if missing or low-confidence
        if (not has_field("gender")) or (best_conf("gender") < 0.75):
            g_resp = self._call_llm_gender(elig_text)
            g_val = self._validate_and_canonicalize_gender_llm(g_resp or {})
            if g_val.get("gender") is not None and float(g_val.get("confidence", 0.0)) >= 0.75:
                structured["required"].append({
                    "field": "gender",
                    "operator": "=",
                    "value": g_val["gender"],
                    "text_span": g_val.get("evidence", ""),
                    "confidence": g_val.get("confidence", 0.75),
                    "source": g_val.get("source", "llm_fallback")
                })
        return structured

    def _call_llm_fallback(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            import os
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return None
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                "Extract structured eligibility clauses from this snippet. Return JSON with keys: required (list of {field, operator, value, text_span}), optional (same). "
                "Only include fields: state, occupation, land_area. Use canonical state names and land_area in hectares. If range, operator='between' and value=[min,max]. If none, omit.\nSnippet:\n" + text
            )
            resp = model.generate_content(prompt, generation_config={"temperature": 0.0})
            if not resp or not getattr(resp, "text", None):
                return None
            raw = resp.text.strip()
            data = json.loads(raw)
            return data
        except Exception:
            return None

    def _validate_and_canonicalize(self, data: Optional[Dict[str, Any]], raw_text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None
        req = data.get("required") or []
        if not isinstance(req, list):
            return None
        out: Dict[str, Dict[str, Any]] = {}
        for c in req:
            if not isinstance(c, dict):
                continue
            f = str(c.get("field") or "").lower()
            if f not in {"state", "occupation", "land_area"}:
                continue
            op = c.get("operator") or c.get("op") or "="
            if op == "==":
                op = "="
            val = c.get("value")
            span = c.get("text_span") or ""
            if f == "state" and isinstance(val, str):
                val = normalize_state(val) or val
            if f == "occupation" and isinstance(val, str):
                val = self.canonicalize_occupation(val)
            if f == "land_area":
                if isinstance(val, list) and len(val) == 2:
                    try:
                        a = float(val[0]); b = float(val[1])
                        op = "between"; val = [min(a,b), max(a,b)]
                    except Exception:
                        continue
                elif isinstance(val, (int, float, str)):
                    try:
                        vnum = float(val)
                        val = vnum
                        if op in {"<", "<=", "<=", "at most", "maximum"}:
                            op = "<="
                        else:
                            op = ">="
                    except Exception:
                        continue
                else:
                    continue
            out[f] = {"field": f, "operator": op, "value": val, "text_span": span}
        return out or None

    def _cache_llm_result(self, scheme_id: str, data: Dict[str, Any]) -> None:
        try:
            self._llm_cache[scheme_id] = data
            cache_path = Path("llm_cache.json")
            Path(cache_path.parent).mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self._llm_cache, f)
        except Exception:
            pass

    def _call_llm_gender(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            import os
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return None
            genai.configure(api_key=api_key)
            system_prompt = (
                "You are a high-precision extractor that converts human-written eligibility text into structured rules.\n"
                "Return ONLY a JSON object (no explanation) that contains any gender-related eligibility you can confidently infer.\n\n"
                "Rules:\n"
                "- Look only for explicit statements about gender in the input text.\n"
                "- Do NOT infer gender from program names (unless the text explicitly says \"for women\" / \"for men\").\n"
                "- If the text says \"women\", \"women only\", \"female\", \"female beneficiaries\", set gender = \"female\".\n"
                "- If the text says \"men\", \"male\", \"males\", \"men only\", set gender = \"male\".\n"
                "- If the text allows both or has no mention, return gender = null.\n"
                "- If the text has conditional text like \"women and men\", treat as null (no restriction).\n"
                "- Provide a short `evidence` string (text snippet from input) that justifies the extraction.\n"
                "- Assign a `confidence` value between 0.5 and 0.95 — be conservative. Use 0.90 for explicit exact matches (\"for women\", \"for men\"), 0.75 for ambiguous wording like \"targeting women\", and 0.5 for weak hints.\n"
                "- Use lower-case canonical values for gender: \"male\" or \"female\".\n"
                "- Output must be valid JSON with the exact keys: `gender`, `evidence`, `confidence`, `source`."
            )
            user_prompt = f"Here is the eligibility text to parse:\n\n{text}\n\nReturn the JSON object now."
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content([
                {"role": "system", "parts": [system_prompt]},
                {"role": "user", "parts": [user_prompt]},
            ], generation_config={"temperature": 0.0})
            if not resp or not getattr(resp, "text", None):
                return None
            raw = resp.text.strip()
            return json.loads(raw)
        except Exception:
            return None

    def _validate_and_canonicalize_gender_llm(self, llm_resp: dict) -> dict:
        out = {"gender": None, "evidence": "", "confidence": 0.0, "source": "llm_fallback"}
        if not isinstance(llm_resp, dict):
            return out
        gender = llm_resp.get("gender")
        if isinstance(gender, str):
            g = gender.strip().lower()
            if g in ("female", "women", "woman"):
                out["gender"] = "female"
            elif g in ("male", "men", "man"):
                out["gender"] = "male"
            else:
                out["gender"] = None
        evidence = llm_resp.get("evidence")
        if isinstance(evidence, str):
            out["evidence"] = evidence.strip()
        try:
            conf = float(llm_resp.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        out["confidence"] = max(0.0, min(0.95, conf))
        src = llm_resp.get("source") or "llm_fallback"
        out["source"] = str(src)
        return out

        try:
            text = elig_text
            clauses = re.split(r'(?<=[.!?])\s+', text)
            for clause in clauses:
                clause = clause.strip()
                if not clause:
                    continue
                rule = self._parse_rule(clause)
                if any(word in clause.lower() for word in ["must", "require", "shall", "need to"]):
                    out["required"].append(rule)
                else:
                    out["optional"].append(rule)

                m = re.search(r"(?:native|resident)\s+of\s+([A-Za-z ]+)", clause, re.I)
                if m:
                    out["required"].append({
                        "field": "state",
                        "operator": "=",
                        "value": m.group(1).strip(),
                        "text_span": m.group(0),
                        "confidence": 0.9,
                        "source": "regex"
                    })

                m = re.search(r"(?:applicant|beneficiary|farmer|worker|student)[^.,;]*\b(?:should be|must be|shall be)\s+(?:an?|the)?\s*([A-Za-z ]+)", clause, re.I)
                if m:
                    occ = m.group(1).strip()
                    out["required"].append({
                        "field": "occupation",
                        "operator": "=",
                        "value": occ,
                        "text_span": m.group(0),
                        "confidence": 0.9,
                        "source": "regex"
                    })

                m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|ha)", clause, re.I)
                if m:
                    out["required"].append({
                        "field": "land_area",
                        "operator": ">=",
                        "value": float(m.group(1)),
                        "text_span": m.group(0),
                        "confidence": 0.9,
                        "source": "regex"
                    })

                m = re.search(r"(?:income|annual income)[^0-9]*?(\d{2,7})", clause, re.I)
                if m:
                    out["required"].append({
                        "field": "income_annual",
                        "operator": "<=",
                        "value": float(m.group(1)),
                        "text_span": m.group(0),
                        "confidence": 0.9,
                        "source": "regex"
                    })
        except Exception as e:
            logger.error(f"Error in rule extraction: {e}")
            out["error"] = str(e)
            # Remap 'other' clauses and normalize ops for fallback rules
            out["required"] = remap_other_clauses(out["required"], elig_text or desc_text)
            out["optional"] = remap_other_clauses(out["optional"], elig_text or desc_text)

            def normalize_ops_fallback(rule):
                if rule.get("operator") == "==":
                    rule["operator"] = "="
                if not rule.get("operator") and rule.get("op"):
                    rule["operator"] = rule["op"].replace("==","=")
                f = str(rule.get("field") or "").lower()
                v = rule.get("value")
 pipeline...*** End Patch}…** continuous?** 
