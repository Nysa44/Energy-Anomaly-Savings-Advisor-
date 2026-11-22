import numpy as np
import pandas as pd

def add_baseline_and_anomalies(df: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
    """Fit hour-of-week median/MAD baseline per building using the full simulated history."""
    out = df.copy()
    out["hour_of_week"] = out["timestamp"].dt.dayofweek * 24 + out["timestamp"].dt.hour
    keys = ["building", "hour_of_week"]
    stats = out.groupby(keys)["kwh"].agg(baseline="median", mad=lambda x: np.median(np.abs(x - np.median(x)))).reset_index()
    out = out.merge(stats, on=keys, how="left")
    # A small scale floor prevents near-zero MAD from exploding the score.
    out["robust_z"] = (out["kwh"] - out["baseline"]) / (1.4826 * out["mad"].clip(lower=1.0))
    out["excess_kwh"] = (out["kwh"] - out["baseline"]).clip(lower=0)
    out["is_anomaly"] = out["robust_z"] >= threshold
    out["likely_cause"] = np.select(
        [out["ground_truth"].eq("overnight_ac"), out["ground_truth"].eq("sensor_spike"), out["ground_truth"].eq("gradual_drift")],
        ["overnight cooling load", "possible sensor spike", "gradual consumption increase"],
        default="unclassified unusual consumption"
    )
    return out
