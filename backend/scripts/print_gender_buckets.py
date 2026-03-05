from backend.src.ranking.ranking import rank_schemes, split_by_gender_buckets, set_schemes_path
from backend.src.retrieval.semantic_retrieval import set_index_paths
from backend.src.profile.user_profile_model import UserProfile

def main():
    set_schemes_path("backend/data/processed/schemes_with_rules_llm.parquet")
    set_index_paths("backend/data/embeddings/faiss_index_llm.bin", "backend/data/embeddings/scheme_ids_llm.npy")

    profile = UserProfile(
        state="Maharashtra",
        district="Kolhapur",
        income_annual=20000.0 * 12,
        occupation="Engineer",
        gender=None,
        age=42,
        farmer=False,
        land_area=None
    )

    ranked = rank_schemes(profile, free_text="subsidy for farm pond / individual farm pond / irrigation structure", top_k=200, w_r=0.667, w_s=0.333, w_f=0.05)
    buckets = split_by_gender_buckets(ranked)

    print("\n--- MALE: top 10 ---")
    for i, s in enumerate(buckets["male"][:10], start=1):
        print(f"{i}. {s.get('scheme_name')}  Match:{s.get('percent_match'):.1f}%  id:{s.get('scheme_id')}")

    print("\n--- FEMALE: top 10 ---")
    for i, s in enumerate(buckets["female"][:10], start=1):
        print(f"{i}. {s.get('scheme_name')}  Match:{s.get('percent_match'):.1f}%  id:{s.get('scheme_id')}")

if __name__ == "__main__":
    main()
