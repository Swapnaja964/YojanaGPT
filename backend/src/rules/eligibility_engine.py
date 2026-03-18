import pandas as pd


class EligibilityEngine:
    def __init__(self, dataset_path):
        try:
            self.df = pd.read_parquet(dataset_path)
        except Exception:
            self.df = pd.DataFrame()

    def check_income(self, scheme, user_income):
        max_income = scheme.get("max_income")
        if pd.isna(max_income):
            return True
        return user_income <= max_income

    def check_category(self, scheme, user_category):
        allowed = scheme.get("eligible_categories")
        if pd.isna(allowed):
            return True
        allowed = str(allowed).lower()
        return user_category.lower() in allowed

    def check_state(self, scheme, user_state):
        scheme_state = scheme.get("state")
        if pd.isna(scheme_state):
            return True
        return user_state.lower() in str(scheme_state).lower()

    def is_eligible(self, scheme, profile):
        checks = [
            self.check_income(scheme, profile["income"]),
            self.check_category(scheme, profile["category"]),
        ]
        if profile["state"]:
            checks.append(self.check_state(scheme, profile["state"]))
        return all(checks)

    def filter_schemes(self, scheme_ids, profile):
        if self.df is None or self.df.empty:
            return []
        results = []
        for sid in scheme_ids:
            scheme = self.df[self.df["scheme_id"] == sid]
            if scheme.empty:
                continue
            scheme = scheme.iloc[0]
            if self.is_eligible(scheme, profile):
                results.append(scheme)
        return results
