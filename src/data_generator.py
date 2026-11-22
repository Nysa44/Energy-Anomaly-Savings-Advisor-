from __future__ import annotations
import numpy as np
import pandas as pd
from .config import BUILDINGS, DAYS, RANDOM_SEED

def generate_readings(days: int = DAYS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate reproducible hourly readings and ground-truth fault labels."""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2026-01-01", periods=days * 24, freq="h")
    rows = []
    for bi, building in enumerate(BUILDINGS):
        for ts in timestamps:
            hour, dow = ts.hour, ts.dayofweek
            weekend = dow >= 5
            # Building-specific load with occupancy schedule and temperature-like effect.
            base = [34, 27, 42, 22, 31][bi]
            occupancy = 1.0 if (not weekend and 7 <= hour <= 19) else (0.62 if weekend and 9 <= hour <= 16 else 0.38)
            daily_temp = 0.5 + 0.5 * np.sin((hour - 7) * np.pi / 12)
            seasonal_temp = 0.5 + 0.5 * np.sin((ts.dayofyear - 20) * 2 * np.pi / 365)
            temperature = 24 + 8 * daily_temp + 5 * seasonal_temp
            normal = base * (0.55 + occupancy) + max(0, temperature - 23) * (0.55 + bi * 0.08)
            normal += 2.2 * np.sin(hour * np.pi / 12)
            value = max(2.0, normal + rng.normal(0, 1.8))
            fault = "normal"
            # Fault 1: overnight cooling left on for 6 hours on 10 consecutive nights.
            if building == "Building-A" and pd.Timestamp("2026-02-10") <= ts.normalize() <= pd.Timestamp("2026-02-19") and 0 <= hour <= 5:
                value += 23
                fault = "overnight_ac"
            # Fault 2: isolated sensor spikes.
            if building == "Building-C" and ts in [pd.Timestamp("2026-02-25 14:00"), pd.Timestamp("2026-03-12 11:00"), pd.Timestamp("2026-03-25 16:00")]:
                value += 75
                fault = "sensor_spike"
            # Fault 3: slow upward drift over the final 21 days.
            if building == "Building-E" and ts >= pd.Timestamp("2026-03-11"):
                value += ((ts - pd.Timestamp("2026-03-11")).total_seconds() / 3600 / (21*24)) * 15
                fault = "gradual_drift"
            rows.append((ts, building, round(value, 3), round(temperature, 2), fault))
    return pd.DataFrame(rows, columns=["timestamp", "building", "kwh", "temperature_c", "ground_truth"])
