import json
from typing import Dict, Any
from backend.src.profile.user_profile_model import UserProfile
from backend.src.rules.rule_evaluator import evaluate_scheme_rules

def print_evaluation_results(results: Dict[str, Any]) -> None:
    print("\n" + "="*50)
    print(f"Overall Score (R): {results['R']:.2f}")
    print("-"*50)
    print("\nRequired Rules:")
    print(f"  Score: {results['required']['score']:.2f} "
          f"(Matched: {results['required']['matched']}/"
          f"{results['required']['total']})")
    print("\nOptional Rules:")
    print(f"  Score: {results['optional']['score']:.2f} "
          f"(Matched: {results['optional']['matched']}/"
          f"{results['optional']['total']})")
    print("\nClause Summary:")
    print(f"  Matched: {len(results['matched_clauses'])}")
    print(f"  Unmet: {len(results['unmet_clauses'])}")
    print(f"  Unknown: {len(results['unknown_clauses'])}")
    print("="*50 + "\n")

def test_case_1() -> None:
    print("\n" + "="*20 + " TEST CASE 1: BASIC ELIGIBILITY " + "="*20)
    user_profile = UserProfile(
        state="Karnataka",
        age=30,
        gender="female",
        income_annual=450000,
        category="OBC",
        education_level="graduate"
    )
    eligibility_rules = {
        "required": [
            {"field": "state", "operator": "=", "value": "Karnataka",
             "text_span": "Must be a resident of Karnataka", "confidence": 0.95},
            {"field": "age", "operator": ">=", "value": 18,
             "text_span": "Must be at least 18 years old", "confidence": 0.98},
            {"field": "income_annual", "operator": "<", "value": 500000,
             "text_span": "Annual income less than ₹5,00,000", "confidence": 0.92}
        ],
        "optional": [
            {"field": "education_level", "operator": "in",
             "value": ["graduate", "postgraduate", "doctorate"],
             "text_span": "Preferred: Graduate or higher education", "confidence": 0.85}
        ]
    }
    results = evaluate_scheme_rules(eligibility_rules, user_profile.model_dump())
    print_evaluation_results(results)
    assert results["R"] == 1.0
    assert len(results["matched_clauses"]) == 4
    print("✅ Test Case 1 Passed: All conditions met")

def test_case_2() -> None:
    print("\n" + "="*20 + " TEST CASE 2: MIXED RESULTS " + "="*20)
    user_profile = UserProfile(
        state="Maharashtra",
        age=16,
        gender="male",
        category="General",
        education_level="12th"
    )
    eligibility_rules = {
        "required": [
            {"field": "state", "operator": "=", "value": "Karnataka",
             "text_span": "Must be a resident of Karnataka", "confidence": 0.95},
            {"field": "age", "operator": ">=", "value": 18,
             "text_span": "Must be at least 18 years old", "confidence": 0.98},
            {"field": "income_annual", "operator": "<", "value": 500000,
             "text_span": "Annual income less than ₹5,00,000", "confidence": 0.92}
        ],
        "optional": [
            {"field": "education_level", "operator": "in",
             "value": ["graduate", "postgraduate", "doctorate"],
             "text_span": "Preferred: Graduate or higher education", "confidence": 0.85}
        ]
    }
    results = evaluate_scheme_rules(eligibility_rules, user_profile.model_dump())
    print_evaluation_results(results)
    assert results["R"] < 0.5
    assert len(results["unmet_clauses"]) >= 2
    assert len(results["unknown_clauses"]) == 1
    print("✅ Test Case 2 Passed: Mixed results handled correctly")

def test_case_3() -> None:
    print("\n" + "="*20 + " TEST CASE 3: COMPLEX CONDITIONS " + "="*20)
    user_profile = UserProfile(
        state="Karnataka",
        age=45,
        gender="female",
        income_annual=750000,
        category="SC",
        farmer=True,
        land_area=2.5,
        established_date="2020-01-15"
    )
    eligibility_rules = {
        "required": [
            {"field": "state", "operator": "in",
             "value": ["Karnataka", "Andhra Pradesh", "Tamil Nadu"],
             "text_span": "Must be from specified states", "confidence": 0.97},
            {"field": "category", "operator": "in",
             "value": ["SC", "ST", "OBC"],
             "text_span": "Must belong to SC/ST/OBC category", "confidence": 0.99},
            {"field": "farmer", "operator": "=", "value": True,
             "text_span": "Must be a farmer", "confidence": 0.95},
            {"field": "land_area", "operator": "between",
             "value": {"min": 1, "max": 5},
             "text_span": "Land holding between 1-5 acres", "confidence": 0.90}
        ],
        "optional": [
            {"field": "established_date", "operator": ">=",
             "value": "2018-01-01",
             "text_span": "Established after 2018", "confidence": 0.88},
            {"field": "age", "operator": "<", "value": 50,
             "text_span": "Age below 50 years", "confidence": 0.95}
        ]
    }
    results = evaluate_scheme_rules(eligibility_rules, user_profile.model_dump())
    print_evaluation_results(results)
    assert abs(results["R"] - 0.6) < 0.01
    assert len(results["matched_clauses"]) == 4
    assert len(results["unmet_clauses"]) == 2
    print("✅ Test Case 3 Passed: Complex conditions evaluated correctly")

if __name__ == "__main__":
    test_case_1()
    test_case_2()
    test_case_3()
    print("\n" + "🎉 All test cases completed successfully!")
    print("\n👉 Stage 4 completed — Next stage")
