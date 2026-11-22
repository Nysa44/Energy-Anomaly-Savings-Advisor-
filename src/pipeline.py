from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .config import TARIFF_AED_PER_KWH, EMISSION_FACTOR_KG_CO2E_PER_KWH
from .data_generator import generate_readings
from .detector import add_baseline_and_anomalies
from .impact import estimate_impact
from .advisor import make_advice

def run(output_dir: str = ".", days: int = 90) -> dict:
    root = Path(output_dir)
    for folder in ("data", "reports", "charts"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    raw = generate_readings(days=days)
    raw.to_csv(root / "data/readings.csv", index=False)
    detected = add_baseline_and_anomalies(raw)
    scored = estimate_impact(detected, TARIFF_AED_PER_KWH, EMISSION_FACTOR_KG_CO2E_PER_KWH)
    scored.to_csv(root / "reports/scored_readings.csv", index=False)
    alerts = scored[scored["is_anomaly"]].copy()
    # Aggregate contiguous detections into event windows, preserving the evidence and impact.
    alerts["event_date"] = alerts["timestamp"].dt.floor("D")
    events = alerts.groupby(["building", "ground_truth", "event_date"], as_index=False).agg(
        start_time=("timestamp", "min"), end_time=("timestamp", "max"),
        alert_hours=("timestamp", "count"), excess_kwh=("excess_kwh", "sum"),
        estimated_cost_aed=("estimated_cost_aed", "sum"), estimated_co2e_kg=("estimated_co2e_kg", "sum"),
        likely_cause=("likely_cause", "first")
    )
    notes, review, modes = [], [], []
    for _, r in events.iterrows():
        row = {"building": r.building, "timestamp": f"{r.start_time} to {r.end_time}",
               "excess_kwh": float(r.excess_kwh), "likely_cause": r.likely_cause}
        note, human, mode = make_advice(row)
        notes.append(note); review.append(human); modes.append(mode)
    if len(events):
        events["advisor_note"] = notes
        events["needs_human_review"] = review
        events["advisor_mode"] = modes
    events.to_csv(root / "reports/anomaly_events.csv", index=False)
    # Fault-level detection metrics; a fault is caught if any injected-fault row is flagged.
    fault_rows = scored[scored.ground_truth != "normal"]
    caught_faults = int(fault_rows.groupby("ground_truth")["is_anomaly"].any().sum())
    total_fault_types = int(fault_rows.ground_truth.nunique())
    tp = int((scored.is_anomaly & (scored.ground_truth != "normal")).sum())
    fp = int((scored.is_anomaly & (scored.ground_truth == "normal")).sum())
    fn = int((~scored.is_anomaly & (scored.ground_truth != "normal")).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    weeks = days / 7
    metrics = {
        "readings": int(len(scored)), "buildings": int(scored.building.nunique()),
        "injected_fault_types": total_fault_types, "fault_types_caught": caught_faults,
        "fault_type_detection_rate": caught_faults / total_fault_types if total_fault_types else 0,
        "true_positive_readings": tp, "false_positive_readings": fp, "false_negative_readings": fn,
        "precision": precision, "recall": recall, "false_alerts_per_week": fp / weeks,
        "flagged_readings": int(scored.is_anomaly.sum()),
        "estimated_excess_kwh_in_alerts": round(float(alerts.excess_kwh.sum()), 2),
        "estimated_savings_aed": round(float(alerts.estimated_cost_aed.sum()), 2),
        "estimated_co2e_kg": round(float(alerts.estimated_co2e_kg.sum()), 2),
        "tariff_aed_per_kwh_assumption": TARIFF_AED_PER_KWH,
        "emission_factor_kg_co2e_per_kwh_assumption": EMISSION_FACTOR_KG_CO2E_PER_KWH
    }
    (root / "reports/metrics.json").write_text(__import__("json").dumps(metrics, indent=2))
    with open(root / "reports/summary.md", "w") as f:
        f.write("# Energy Anomaly & Savings Advisor — Run Summary\\n\\n")
        for k, v in metrics.items(): f.write(f"- **{k.replace('_',' ').title()}:** {v}\\n")
        f.write("\\nMetrics are from reproducible simulated data, not measured customer energy savings.\\n")
    # Chart: a representative 7-day section and detected points.
    sample = scored[scored.building == "Building-A"].tail(24*14)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(sample.timestamp, sample.kwh, label="Observed kWh", linewidth=1)
    ax.plot(sample.timestamp, sample.baseline, label="Hour-of-week baseline", linewidth=1)
    flagged = sample[sample.is_anomaly]
    ax.scatter(flagged.timestamp, flagged.kwh, label="Detected anomaly", s=22)
    ax.set_title("Building-A hourly consumption and detected anomalies")
    ax.set_ylabel("kWh per hour"); ax.set_xlabel("Timestamp")
    ax.legend(); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(root / "charts/energy_anomalies.png", dpi=150); plt.close(fig)
    return metrics

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Run the Energy Anomaly & Savings Advisor")
    parser.add_argument("--output", default=".")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.days), indent=2))
