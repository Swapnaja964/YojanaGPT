import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from pathlib import Path
from backend.src.profile.user_profile_model import UserProfile

# Global model instance for reuse
_model = None
_index = None
_scheme_ids = None
_index_path_override = None
_ids_path_override = None

def _get_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/paraphrase-mpnet-base-v2")
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
    # Build and embed user document
    user_doc = build_user_doc(profile, free_text)
    query_embedding = embed_user_doc(user_doc)
    
    # Get index and search
    index, scheme_ids = _get_index()
    
    # Search the index
    distances, indices = index.search(query_embedding, k=min(top_k, index.ntotal))
    
    # Convert to list of dicts
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0:  # Valid index
            results.append({
                "scheme_id": str(scheme_ids[idx]),
                "similarity": float(dist)  # Convert numpy types to native Python types
            })
    
    return results

# Example usage
if __name__ == "__main__":
    # Example profile
    profile = UserProfile(
        state="Maharashtra",
        district="Pune",
        age=35,
        category="OBC",
        income_annual=500000,
        occupation="Farmer",
        farmer=True,
        business_type="Agriculture"
    )
    
    results = semantic_search(profile, "Looking for farmer welfare schemes", top_k=5)
    for result in results:
        print(f"Scheme ID: {result['scheme_id']}, Similarity: {result['similarity']:.4f}")
