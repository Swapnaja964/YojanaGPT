import pandas as pd
from backend.src.ranking.ranking import split_by_gender_buckets

def test_gender_bucket_split_smoke():
    ranked_results = [
        {
            "scheme_id": "female_only",
            "scheme_name": "Women Only Scheme",
            "match": 0.9,
            "eligibility_structured": {
                "required": [
                    {"field": "gender", "operator": "=", "value": "female", "confidence": 0.9, "text_span": "for women"}
                ],
                "optional": []
            }
        },
        {
            "scheme_id": "no_gender",
            "scheme_name": "Open Scheme",
            "match": 0.85,
            "eligibility_structured": {
                "required": [],
                "optional": []
            }
        },
        {
            "scheme_id": "male_only",
            "scheme_name": "Men Only Scheme",
            "match": 0.86,
            "eligibility_structured": {
                "required": [
                    {"field": "gender", "operator": "=", "value": "male", "confidence": 0.9, "text_span": "for men"}
                ],
                "optional": []
            }
        },
    ]

    buckets = split_by_gender_buckets(ranked_results)

    female_ids = [s['scheme_id'] for s in buckets['female']]
    male_ids = [s['scheme_id'] for s in buckets['male']]

    assert "female_only" in female_ids
    assert "female_only" not in male_ids

    assert "male_only" in male_ids
    assert "male_only" not in female_ids

    assert "no_gender" in male_ids and "no_gender" in female_ids
