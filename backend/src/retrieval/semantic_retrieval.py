import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from backend.src.profile.user_profile_model import UserProfile
from backend.src.retrieval.query_builder import build_search_query
from backend.src.parser.query_parser import parse_user_query
from backend.src.rules.eligibility_engine import EligibilityEngine

# Global model instance for reuse
_model = None
_index = None
_scheme_ids = None
_index_path_override = None
_ids_path_override = None

def build_user_query(profile: UserProfile, description: str) -> str:
    state = getattr(profile, "state", None)
    district = getattr(profile, "district", None)
    age = getattr(profile, "age", None)
    occupation = getattr(profile, "occupation", None)
    income = getattr(profile, "income_annual", None)
    category = getattr(profile, "category", None)
    farmer = getattr(profile, "farmer", None)
    business_type = getattr(profile, "business_type", None)
    def _s(v):
        return "" if v is None else str(v)
    parts = [
        "User Profile:",
        f"State: {_s(state)}",
        f"District: {_s(district)}",
        f"Age: {_s(age)}",
        f"Occupation: {_s(occupation)}",
        f"Income: {_s(income)}",
        f"Category: {_s(category)}",
        f"Farmer: {_s(farmer)}",
        f"Business Type: {_s(business_type)}",
        "",
        "User Request:",
        _s(description),
    ]
    return "\n".join(parts)

def _get_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        print("Embedding model successfully switched to BGE-large.")
    return _model

def _get_index():
    """Lazy load the FAISS index and scheme IDs."""
    global _index, _scheme_ids
    if _index is None or _scheme_ids is None:
        # Prefer LLM-updated index if available
        preferred_index = Path("backend/data/embeddings/faiss_index_llm.bin")
        preferred_ids = Path("backend/data/embeddings/scheme_ids_llm.npy")
        if _index_path_override and _ids_path_override:
            index_path = Path(_index_path_override)
            ids_path = Path(_ids_path_override)
        elif preferred_index.exists() and preferred_ids.exists():
            index_path = preferred_index
            ids_path = preferred_ids
        else:
            index_path = Path("backend/data/embeddings/faiss_index.bin")
            ids_path = Path("backend/data/embeddings/scheme_ids.npy")

        if not index_path.exists() or not ids_path.exists():
            raise FileNotFoundError(
                f"FAISS index or scheme IDs not found at {index_path} or {ids_path}. "
                "Please run build_faiss_index.py first."
            )

        _index = faiss.read_index(str(index_path))
        _scheme_ids = np.load(ids_path, allow_pickle=False)
    
    return _index, _scheme_ids

def set_index_paths(index_path: str, ids_path: str) -> None:
    global _index_path_override, _ids_path_override, _index, _scheme_ids
    _index_path_override = index_path
    _ids_path_override = ids_path
    # Reset loaded index so it reloads on next call
    _index = None
    _scheme_ids = None

def build_user_doc(profile: UserProfile, free_text: str = "") -> str:
    """Create a text representation of the user profile and query."""
    def safe_str(value) -> str:
        return str(value) if value is not None else ""

    profile_parts = [
        "User profile:",
        f"State: {safe_str(profile.state)}",
        f"District: {safe_str(profile.district)}",
        f"Age: {safe_str(profile.age)}",
        f"Category: {safe_str(profile.category)}",
        f"Income (annual): {safe_str(profile.income_annual)}",
        f"Occupation: {safe_str(profile.occupation)}",
        f"Farmer: {safe_str(profile.farmer)}",
        f"Business type: {safe_str(profile.business_type)}",
        "",
        f"User need: {free_text}"
    ]
    
    return "\n".join(profile_parts)

def embed_user_doc(user_doc: str) -> np.ndarray:
    """Convert user document text to a normalized embedding vector."""
    model = _get_model()
    # Get embedding and normalize in one step
    embedding = model.encode(
        user_doc,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embedding.reshape(1, -1)  # Ensure 2D array

def expand_query(description: str) -> str:
    """
    Expand user description with generic scheme-related terms 
    to improve semantic retrieval.
    """
    if not description:
        return ""
    expansion_terms = [
        "government scheme",
        "government subsidy",
        "financial assistance",
        "benefit program",
        "support scheme",
    ]
    expanded = description + "\n" + "\n".join(expansion_terms)
    return expanded

def semantic_search(profile: UserProfile, free_text: str = "", top_k: int = 50) -> List[Dict[str, Any]]:
    """
    Find top-k most similar schemes for the given user profile and query.
    
    Args:
        profile: UserProfile object containing user details
        free_text: Optional free text query from the user
        top_k: Number of results to return
        
    Returns:
        List of dicts with scheme_id and similarity score, sorted by score (descending)
    """
    # Build and embed user query
    expanded_text = expand_query(free_text)
    user_query = build_user_query(profile, expanded_text)
    print("\n===== EXPANDED USER QUERY =====")
    print(user_query)
    print("================================\n")
    query_embedding = embed_user_doc(user_query)
    
    # Get index and search
    index, scheme_ids = _get_index()
    
    # Search the index
    distances, indices = index.search(query_embedding, k=min(50, index.ntotal))
    
    # Initialize eligibility engine
    eligibility_engine = EligibilityEngine("backend/data/processed/schemes_with_rules.parquet")
    
    # Collect retrieved scheme IDs
    retrieved_ids = [str(scheme_ids[i]) for i in indices[0] if i >= 0]
    
    # Apply eligibility filtering
    try:
        eligible_schemes = eligibility_engine.filter_schemes(retrieved_ids, profile.model_dump())
        print("\nEligible Schemes After Rule Filtering:\n")
        for s in eligible_schemes[:5]:
            try:
                print(s["scheme_name"])
            except Exception:
                pass
    except Exception:
        pass
    
    # Load schemes data
    df = pd.read_parquet("backend/data/processed/schemes_with_rules.parquet")
    id_to_row = None
    if "scheme_id" in df.columns:
        try:
            id_to_row = df.set_index("scheme_id")
        except Exception:
            id_to_row = None
    
    retrieved_schemes = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0:  # Valid index
            sid = str(scheme_ids[idx])
            scheme_name = "N/A"
            scheme_row_dict: Dict[str, Any] = {}
            try:
                if id_to_row is not None and sid in id_to_row.index:
                    row = id_to_row.loc[sid]
                    scheme_name = str(row.get("scheme_name", "N/A"))
                    scheme_row_dict = row.to_dict()
                else:
                    match = df[df.get("scheme_id") == sid] if "scheme_id" in df.columns else None
                    if match is not None and not match.empty:
                        row = match.iloc[0]
                        scheme_name = str(row.get("scheme_name", "N/A"))
                        scheme_row_dict = row.to_dict()
            except Exception:
                pass
            print(f"{scheme_name} - {float(dist):.4f}")
            retrieved_schemes.append({
                "scheme_id": sid,
                "scheme_name": scheme_name,
                "similarity": float(dist),
                "scheme_data": scheme_row_dict
            })
    
    return retrieved_schemes

# Example usage
if __name__ == "__main__":
    # Build search query from natural language input
    user_query = """
    I am a 35 year old OBC farmer from Pune earning 5 lakh annually.
    What government subsidy schemes apply to me?
    """
    profile_dict = parse_user_query(user_query)
    search_query = build_search_query(profile_dict)
    print("\n===== FINAL SEARCH QUERY =====")
    print(search_query)
    print("==============================\n")

    # Convert parsed profile dict to UserProfile model and run search
    profile = UserProfile(**profile_dict)
    results = semantic_search(profile, search_query, top_k=5)
    for result in results:
        print(f"Scheme ID: {result['scheme_id']}, Similarity: {result['similarity']:.4f}")
