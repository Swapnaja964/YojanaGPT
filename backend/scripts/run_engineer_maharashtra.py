from backend.src.profile.user_profile_model import UserProfile
from backend.src.ranking.ranking import rank_schemes, set_schemes_path
from backend.src.retrieval.semantic_retrieval import set_index_paths

def main():
    set_schemes_path("backend/data/processed/schemes_with_rules_llm.parquet")
    set_index_paths("backend/data/embeddings/faiss_index_llm.bin", "backend/data/embeddings/scheme_ids_llm.npy")

    profile = UserProfile(
        state="Maharashtra",
        district="Mumbai",
        age=30,
        gender="male",
        category="General",
        income_annual=20000.0 * 12,
        occupation="Engineer",
        farmer=False,
        land_area=None,
        land_type=None,
    )

    query = "I am an engineer from Maharashtra with a monthly salary of 20000; suggest schemes for me"
    results = rank_schemes(profile=profile, free_text=query, top_k=10, w_r=0.667, w_s=0.333, w_f=0.05)

    print("\n=== Engineer (Maharashtra, ₹20,000/month) — Top 10 ===")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['scheme_name']}\n   Match: {r['percent_match']:.1f}%  R:{r['R']:.3f}  S:{r['S']:.3f}  F:{r['F']:.3f}\n   id: {r.get('scheme_id')}\n")

if __name__ == "__main__":
    main()
