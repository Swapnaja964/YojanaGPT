import json
from backend.src.parser.query_parser import parse_user_query
from backend.src.retrieval.query_builder import build_search_query
from backend.src.rules.eligibility_engine import EligibilityEngine


def main():
    description = (
        "I am a 35 year old OBC farmer from Pune Maharashtra earning 5 lakh annually. "
        "What government subsidy schemes apply to me?"
    )

    structured_profile = {
        "state": "Maharashtra",
        "district": "Pune",
        "age": 35,
        "income": 500000,
        "category": "OBC",
        "gender": "Male",
        "occupation": "Farmer",
    }
    profile = parse_user_query(structured_profile, description)

    print("\nParsed Profile")
    print(profile)

    # Build search query
    search_query = build_search_query(profile)
    print("\nGenerated Search Query")
    print(search_query)

    # Temporary mock retriever
    scheme_ids = ["SCHEME001", "SCHEME002"]
    print("\nRetrieved Scheme IDs")
    print(scheme_ids)

    # Eligibility filtering
    engine = EligibilityEngine("backend/data/processed/schemes_with_rules.parquet")
    eligible_schemes = engine.filter_schemes(scheme_ids, profile)

    print("\nEligible Schemes")
    if not eligible_schemes:
        print("None")
    else:
        for s in eligible_schemes:
            try:
                print(s["scheme_name"])
            except Exception:
                print("<scheme name unavailable>")


if __name__ == "__main__":
    main()
