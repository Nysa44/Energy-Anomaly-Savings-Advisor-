import pandas as pd

def estimate_impact(df: pd.DataFrame, tariff_aed_per_kwh: float, emission_factor_kg_per_kwh: float) -> pd.DataFrame:
    out = df.copy()
    out["estimated_cost_aed"] = out["excess_kwh"] * tariff_aed_per_kwh
    out["estimated_co2e_kg"] = out["excess_kwh"] * emission_factor_kg_per_kwh
    return out
