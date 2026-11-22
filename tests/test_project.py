import pandas as pd
from src.data_generator import generate_readings
from src.detector import add_baseline_and_anomalies
from src.impact import estimate_impact
from src.advisor import make_advice, template_advice

def test_generator_is_reproducible_and_has_expected_size():
    a, b = generate_readings(), generate_readings()
    assert len(a) == 5 * 90 * 24
    pd.testing.assert_frame_equal(a, b)

def test_baseline_columns_exist_and_are_finite():
    scored = add_baseline_and_anomalies(generate_readings())
    assert scored["baseline"].notna().all()
    assert scored["robust_z"].notna().all()

def test_overnight_fault_is_detected():
    scored = add_baseline_and_anomalies(generate_readings())
    fault = scored[scored.ground_truth == "overnight_ac"]
    assert fault["is_anomaly"].sum() > 0

def test_sensor_spikes_are_detected():
    scored = add_baseline_and_anomalies(generate_readings())
    fault = scored[scored.ground_truth == "sensor_spike"]
    assert fault["is_anomaly"].sum() >= 2

def test_clean_rows_do_not_all_trigger():
    scored = add_baseline_and_anomalies(generate_readings())
    clean = scored[scored.ground_truth == "normal"]
    assert clean["is_anomaly"].mean() < 0.10

def test_impact_calculation():
    df = pd.DataFrame({"excess_kwh": [10.0]})
    result = estimate_impact(df, 0.3, 0.4)
    assert result.loc[0, "estimated_cost_aed"] == 3.0
    assert result.loc[0, "estimated_co2e_kg"] == 4.0

def test_advisor_template_has_required_evidence_fields():
    row = {"building":"B1","timestamp":"2026-01-01 01:00","excess_kwh":12.5,"likely_cause":"overnight cooling"}
    note, human, mode = make_advice(row)
    assert all(x in note for x in ("Building:", "Window:", "Recommendation:"))
    assert human is True and mode == "template_no_llm_configured"

def test_invalid_llm_retries_once_then_falls_back():
    calls = []
    def broken(_):
        calls.append(1)
        return "unsupported"
    row = {"building":"B1","timestamp":"2026-01-01 01:00","excess_kwh":12.5,"likely_cause":"overnight cooling"}
    note, human, mode = make_advice(row, broken)
    assert len(calls) == 2
    assert human is True and mode == "template_fallback"
    assert "Building:" in note
