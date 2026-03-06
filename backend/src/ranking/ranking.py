from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from backend.src.profile.user_profile_model import UserProfile
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global cache for schemes data
_schemes_df = None
SCHEMES_PATH = "backend/data/processed/schemes_with_rules.parquet"

# Import with error handling to avoid circular imports
try:
    from backend.src.rules.rule_evaluator import evaluate_scheme_rules
    from backend.src.retrieval.semantic_retrieval import semantic_search
except ImportError as e:
    logger.warning(f"Could not import dependencies: {e}. Some functions may not work.")
    evaluate_scheme_rules = None  # type: ignore
    semantic_search = None  # type: ignore

def set_schemes_path(path: str) -> None:
    global SCHEMES_PATH, _schemes_df
    SCHEMES_PATH = path
    _schemes_df = None

def load_schemes_data() -> pd.DataFrame:
    """Load and cache the schemes data."""
    global _schemes_df
    if _schemes_df is None:
        try:
            from pathlib import Path
            p = Path(SCHEMES_PATH)
            if not p.exists():
                alt = Path("schemes_with_rules.parquet")
                p = alt if alt.exists() else p
            _schemes_df = pd.read_parquet(str(p))
            logger.info(f"Loaded {len(_schemes_df)} schemes from {SCHEMES_PATH}")
        except Exception as e:
            logger.error(f"Failed to load schemes data: {e}")
            _schemes_df = pd.DataFrame()  # Return empty DataFrame on error
    return _schemes_df

def compute_freshness_penalty(last_updated: Optional[str], today: Optional[datetime] = None) -> float:
    """
    Compute freshness penalty factor F in [0, 0.1].
    
    Args:
        last_updated: Last update date string in YYYY-MM-DD format
        today: Reference date (defaults to current date)
        
    Returns:
        float: Freshness penalty between 0.0 and 0.1
    """
    if today is None:
        today = datetime.now()
    
    # Handle missing or invalid dates
    if not last_updated or not isinstance(last_updated, str):
        return 0.05
    
    try:
        # Try parsing the date
        updated_date = datetime.strptime(str(last_updated).split('T')[0], '%Y-%m-%d')
        days_old = (today - updated_date).days
        
        # Return penalty based on age
        if days_old <= 365:  # Within 1 year
            return 0.0
        else:
            return 0.1
    except (ValueError, TypeError) as e:
        logger.debug(f"Invalid date format for last_updated '{last_updated}': {e}")
        return 0.05

def rank_schemes(
    profile: UserProfile,
    free_text: str = "",
    top_k: int = 10,
    w_r: float = 0.6,
    w_s: float = 0.4,
    w_f: float = 0.1
) -> List[Dict]:
    """
    Rank schemes based on rule matching, semantic similarity, and freshness.
    
    Args:
        profile: User profile containing demographic and other relevant information
        free_text: Free-text query from the user
        top_k: Number of top results to return
        w_r: Weight for rule-based score (R)
        w_s: Weight for semantic score (S)
        w_f: Weight for freshness penalty (F)
        
    Returns:
        List[Dict]: Ranked list of schemes with scores and metadata
    """
    # Validate weights
    if not (0 <= w_r <= 1 and 0 <= w_s <= 1 and 0 <= w_f <= 1):
        raise ValueError("Weights must be between 0 and 1")

    # Ensure weights are valid and sum to 1.0 (normalize if not)
    # Place this after w_r, w_s, w_f are read/defined.
    _total_rs = (w_r or 0.0) + (w_s or 0.0)
    if abs(_total_rs - 1.0) > 1e-9:
        # If both w_r and w_s are zero, fall back to semantic-heavy default
        if _total_rs == 0.0:
            w_r = 0.6
            w_s = 0.3
            w_f = 0.1
            logger.warning("Weights were zero — using defaults w_r=0.6, w_s=0.3, w_f=0.1")
        else:
            # Normalize proportionally so w_r + w_s == 1.0, keep w_f as-is (freshness treated separately)
            w_r = float(w_r) / _total_rs
            w_s = float(w_s) / _total_rs
            logger.warning("Normalized weights so (w_r + w_s) == 1.0 (new w_r=%.3f, w_s=%.3f)", w_r, w_s)
    # Optional: clamp to [0,1]
    w_r = max(0.0, min(1.0, w_r))
    w_s = max(0.0, min(1.0, w_s))
    
    # Load schemes data
    schemes_df = load_schemes_data()
    if schemes_df.empty:
        logger.error("No schemes data available")
        return []
    
    # Get semantic search results
    retrieved_schemes = []
    if semantic_search is not None:
        try:
            retrieved_schemes = semantic_search(profile, free_text, top_k=min(50, len(schemes_df)))
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            retrieved_schemes = []
    else:
        logger.error("Semantic search is unavailable (missing dependency).")
    
    results = []
    today = datetime.now()
    
    # Process each candidate scheme
    for item in retrieved_schemes:
        try:
            scheme_id = item.get("scheme_id")
            S = float(item.get("similarity", 0.0))
            scheme_data_dict = item.get("scheme_data") or {}

            # Fallback to dataframe if scheme_data missing
            scheme_row = None
            if scheme_data_dict:
                scheme_row = pd.Series(scheme_data_dict)
            else:
                try:
                    if scheme_id in schemes_df.get('scheme_id', []).values:
                        scheme_row = schemes_df[schemes_df['scheme_id'] == scheme_id].iloc[0]
                except Exception:
                    scheme_row = None
            if scheme_row is None:
                logger.warning(f"Scheme {scheme_id} not found or missing data")
                continue
            
            # Evaluate rules to get R score
            eligibility_structured = scheme_row.get('eligibility_structured', {})
            try:
                # Parse JSON string if needed
                if isinstance(eligibility_structured, str):
                    eligibility_structured = json.loads(eligibility_structured)
                rule_result = evaluate_scheme_rules(eligibility_structured, profile.model_dump())
                R = rule_result.get('R', rule_result.get('score', 0.0))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse eligibility_structured JSON for scheme {scheme_id}: {e}")
                R = 0.0
                rule_result = {"score": 0.0, "breakdown": {"error": "Invalid rule format"}}
            except Exception as e:
                logger.error(f"Error evaluating rules for scheme {scheme_id}: {e}")
                R = 0.0
                rule_result = {"score": 0.0, "breakdown": {"error": str(e)}}

            # Compute freshness penalty
            last_updated = scheme_row.get('last_updated')
            F = compute_freshness_penalty(last_updated, today)

            # Calculate final score (clamped to [0, 1]) using existing weighted formula
            final_score = max(0.0, min(1.0, w_r * R + w_s * S - w_f * F))
            percent_match = round(final_score * 100, 1)

            # Prepare result entry
            result = {
                'scheme_id': scheme_id,
                'scheme_name': scheme_row.get('scheme_name', 'N/A'),
                'R': round(R, 4),
                'S': round(S, 4),
                'F': round(F, 4),
                'final_score': round(final_score, 4),
                'percent_match': percent_match,
                'rule_breakdown': rule_result.get('breakdown', {}),
                'source_url': scheme_row.get('source_url', ''),
                'description': scheme_row.get('description_raw', '')[:200] + '...',
                'eligibility_structured': eligibility_structured
            }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing scheme {scheme_id}: {e}", exc_info=True)
            continue
    
    # Sort by final score (descending)
    results.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Debug print top 5 schemes
    print("\nTop 5 ranked schemes (name, Final, R, S, F):")
    for s in results[:5]:
        print(f"{s['scheme_name']} | Final={s['final_score']:.4f} | R={s['R']:.4f} | S={s['S']:.4f} | F={s['F']:.4f}")
    
    # Return top_k results
    return results[:top_k]

def _extract_scheme_gender(eligibility_structured: Dict[str, Any]) -> Optional[str]:
    try:
        if not eligibility_structured:
            return None
        req = eligibility_structured.get("required", [])
        for clause in req:
            if clause.get("field") == "gender":
                val = clause.get("value")
                if val is None:
                    return None
                v = str(val).strip().lower()
                if v in ("female", "f", "women", "woman", "mahila"):
                    return "female"
                if v in ("male", "m", "man", "men"):
                    return "male"
                return None
    except Exception:
        return None
    return None

def split_by_gender_buckets(ranked_schemes: List[Dict]) -> Dict[str, List[Dict]]:
    male: List[Dict] = []
    female: List[Dict] = []
    for s in ranked_schemes:
        elig = s.get("eligibility_structured") or {}
        scheme_gender = _extract_scheme_gender(elig)
        if scheme_gender == "female":
            female.append(s)
            continue
        if scheme_gender == "male":
            male.append(s)
            continue
        male.append(s)
        female.append(s)
    return {"male": male, "female": female}

# Example usage
if __name__ == "__main__":
    # Example user profile
    profile = UserProfile(
        state="Maharashtra",
        district="Pune",
        age=35,
        category="OBC",
        income_annual=250000,
        occupation="Farmer",
        farmer=True,
        business_type="Agriculture"
    )
    
    # Example search
    ranked_schemes = rank_schemes(
        profile=profile,
        free_text="Looking for agricultural subsidies and farming equipment support",
        top_k=5,
        w_r=0.6,
        w_s=0.3,
        w_f=0.1
    )
    
    # Print results
    print("\nTop matching schemes:")
    for i, scheme in enumerate(ranked_schemes, 1):
        print(f"\n{i}. {scheme['scheme_name']}")
        print(f"   Scheme ID: {scheme['scheme_id']}")
        print(f"   Match: {scheme['percent_match']}%")
        print(f"   R: {scheme['R']:.3f}, S: {scheme['S']:.3f}, F: {scheme['F']:.3f}")
        print(f"   URL: {scheme.get('source_url', 'N/A')}")
