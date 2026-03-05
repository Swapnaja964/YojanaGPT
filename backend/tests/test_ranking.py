import argparse
from backend.src.profile.user_profile_model import UserProfile
from backend.src.ranking.ranking import rank_schemes, set_schemes_path
from backend.src.retrieval.semantic_retrieval import set_index_paths

def test_karnataka_farmer():
    print("\n" + "="*80)
    print("TEST CASE 1: KARNATAKA FARMER")
    print("="*80)
    profile = UserProfile(
        state="Karnataka",
        district="Tumkur",
        age=45,
        gender="male",
        category="SC",
        income_annual=120000,
        occupation="Farmer",
        farmer=True,
        land_area=2.5,
        land_type="agricultural"
    )
    query = "looking for subsidy for irrigation"
    print(f"Testing ranking for: {query}")
    print("Profile:", profile.model_dump())
    print("-" * 80)
    results = rank_schemes(
        profile=profile,
        free_text=query,
        top_k=5,
        w_r=0.6,
        w_s=0.3,
        w_f=0.1
    )
    for i, scheme in enumerate(results, 1):
        print(f"\n{i}. {scheme['scheme_name']}")
        print(f"   Match: {scheme['percent_match']}%")
        print(f"   R: {scheme['R']:.3f} (Rules), S: {scheme['S']:.3f} (Semantic), F: {scheme['F']:.3f} (Freshness)")
        print(f"   Scheme ID: {scheme.get('scheme_id', 'N/A')}")
        print(f"   URL: {scheme.get('source_url', 'N/A')}")
        print(f"   Description: {scheme.get('description', 'No description')}")

def test_rajasthan_farmer():
    print("\n" + "="*80)
    print("TEST CASE 2: RAJASTHAN FARMER (DIGGY)")
    print("="*80)
    profile_rj = UserProfile(
        state="Rajasthan",
        district="Jaipur",
        age=40,
        gender="male",
        category="General",
        income_annual=150000.0,
        occupation="Farmer",
        farmer=True,
        land_area=1.0,
        land_type="agricultural"
    )
    query_rj = "looking for subsidy for irrigation structures / water storage"
    print(f"Testing ranking for: {query_rj}")
    print(f"Profile: {profile_rj.model_dump()}")
    print("-" * 80)
    results_rj = rank_schemes(
        profile=profile_rj,
        free_text=query_rj,
        top_k=5,
        w_r=0.6,
        w_s=0.3,
        w_f=0.1
    )
    for i, scheme in enumerate(results_rj, 1):
        print(f"\n{i}. {scheme['scheme_name']}")
        print(f"   Match: {scheme['percent_match']}%")
        print(f"   R: {scheme['R']:.3f} (Rules), S: {scheme['S']:.3f} (Semantic), F: {scheme['F']:.3f} (Freshness)")
        print(f"   Scheme ID: {scheme.get('scheme_id', 'N/A')}")
        print(f"   URL: {scheme.get('source_url', 'N/A')}")
    if results_rj:
        top = results_rj[0]
        rb = top.get('rule_breakdown', {})
        print("\n" + "-"*40 + " RULE BREAKDOWN " + "-"*40)
        print("Required summary:", rb.get("required", "N/A"))
        print("Optional summary:", rb.get("optional", "N/A"))
        print()
        print("Matched REQUIRED clauses:")
        for clause in rb.get("matched_clauses", []):
            if clause.get("scope") == "required":
                print(f"  - {clause.get('field', 'N/A')} {clause.get('operator', 'N/A')} {clause.get('value', 'N/A')} | user_value={clause.get('user_value', 'N/A')}")
        print("\nUnmet REQUIRED clauses:")
        for clause in rb.get("unmet_clauses", []):
            if clause.get("scope") == "required":
                print(f"  - {clause.get('field', 'N/A')} {clause.get('operator', 'N/A')} {clause.get('value', 'N/A')} | user_value={clause.get('user_value', 'N/A')}")
        print("\nUnknown REQUIRED clauses:")
        for clause in rb.get("unknown_clauses", []):
            if clause.get("scope") == "required":
                print(f"  - {clause.get('field', 'N/A')} {clause.get('operator', 'N/A')} {clause.get('value', 'N/A')} | user_value={clause.get('user_value', 'N/A')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--faiss", dest="faiss", default=None)
    parser.add_argument("--schemes", dest="schemes", default=None)
    parser.add_argument("--ids", dest="ids", default=None)
    args = parser.parse_args()
    if args.schemes:
        set_schemes_path(args.schemes)
    if args.faiss:
        ids_path = args.ids if args.ids else ("scheme_ids_llm.npy" if "llm" in args.faiss else "faiss_index/scheme_ids.npy")
        set_index_paths(args.faiss, ids_path)
    test_karnataka_farmer()
    test_rajasthan_farmer()
    print("\n=== MAHARASHTRA SMOKE TEST ===")
    maharashtra_farmer = {
        "user_id": None,
        "state": "Maharashtra",
        "district": "Kolhapur",
        "pincode": None,
        "age": 42,
        "gender": "male",
        "category": "General",
        "income_annual": 90000.0,
        "occupation": "Farmer",
        "education_level": None,
        "farmer": True,
        "land_area": 0.6,
        "land_type": "agricultural",
        "disability": None,
        "documents": {},
        "extra_flags": {}
    }
    query = "subsidy for farm pond / individual farm pond / irrigation structure"
    print("Profile:", maharashtra_farmer)
    print("Query:", query)
    profile_obj = UserProfile(**{k: v for k, v in maharashtra_farmer.items() if k in UserProfile.model_fields})
    results = rank_schemes(
        profile=profile_obj,
        free_text=query,
        top_k=10,
        w_r=0.667,
        w_s=0.333,
        w_f=0.05
    )
    print("\nTop results (Maharashtra test):")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['scheme_name']}\n   Match: {r['percent_match']:.1f}%  R:{r['R']:.3f}  S:{r['S']:.3f}  F:{r['F']:.3f}\n   id: {r.get('scheme_id')}\n")
