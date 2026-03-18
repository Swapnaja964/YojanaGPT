from typing import Dict, Any
from backend.src.parser.query_parser import parse_user_query


def build_search_query(profile: Dict[str, Any]) -> str:
    sector = "government welfare schemes"
    if profile.get("farmer"):
        sector = "farmer welfare subsidy schemes"
    if profile.get("occupation"):
        sector = f"{profile.get('occupation')} welfare schemes"
    query_parts = [
        sector,
        f"for {profile.get('category')} category" if profile.get("category") else "",
        f"in {profile.get('state')}" if profile.get("state") else "",
        f"income below {profile.get('income')}" if profile.get("income") else "",
        profile.get("intent") or "",
    ]
    return " ".join([p for p in query_parts if p])


if __name__ == "__main__":
    query = (
        "I am a 35 year old OBC farmer from Pune earning 5 lakh.\n"
        "What government subsidy schemes apply to me?"
    )
    profile = parse_user_query(query)
    search_query = build_search_query(profile)
    print("\nSearch Query:")
    print(search_query)
