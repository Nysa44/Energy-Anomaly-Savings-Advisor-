# Energy Anomaly & Savings Advisor

A reproducible Python prototype that learns each building's typical hourly energy pattern, detects unusual readings, estimates potential waste, and creates evidence-grounded facility-manager recommendations.

> **Data honesty:** all readings are simulated. The generated metrics measure this detector against injected synthetic faults; they are not proof of real-world savings or customer performance.

## Features
- 5 simulated buildings, 90 days, hourly readings (10,800 rows), fixed random seed.
- Weekday/weekend occupancy patterns and temperature-related load.
- Three injected fault types: overnight cooling load, sensor spikes, gradual consumption drift.
- Per-building hour-of-week median baseline and robust MAD anomaly score.
- Estimates excess kWh, AED cost, and CO2e using explicit configurable assumptions.
- Advisor note with evidence fields, validation, one retry, deterministic template fallback, and human-review flag.
- CSV/JSON/Markdown outputs and a PNG chart.
- Eight pytest tests.

## Quick start
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
pytest -q
```

Outputs:
- `data/readings.csv` — generated input data and ground-truth labels
- `reports/scored_readings.csv` — baseline, robust score, anomaly flag, impact estimates
- `reports/anomaly_events.csv` — grouped anomaly events and advisor notes
- `reports/metrics.json` and `reports/summary.md` — evaluation metrics
- `charts/energy_anomalies.png` — chart

To choose another output folder: `python -m src.pipeline --output ./run_output`.
To change the simulation length: `python -m src.pipeline --days 60`.

## Detection method
For each building and hour-of-week bucket, calculate the median consumption and median absolute deviation (MAD). The robust score is:

`(observed_kWh - median_kWh) / (1.4826 * max(MAD, 1.0))`

A reading is flagged at robust score >= 5.0. The scale floor avoids unstable scores when a bucket has very low variance. This is a simple explainable prototype, not a production-grade time-series model.

## Impact assumptions
Defaults are deliberately visible in `src/config.py`:
- Electricity tariff: **AED 0.30/kWh** (illustrative, not a utility quote).
- Emissions factor: **0.40 kg CO2e/kWh** (illustrative placeholder; replace with a published UAE/grid-specific factor before external use).

These are assumptions for demonstrating the calculation. Do not present the AED or CO2e estimates as audited savings. Validate the tariff against the applicable customer bill and the emissions factor against a current authoritative published source before using the outputs in a business case.

## Advisor / LLM integration
The core pipeline uses a safe deterministic template by default, so it runs without API keys or network access. `src.advisor.make_advice(row, generator=callable)` accepts an optional LLM callable. The callable receives only the evidence dictionary (`building`, `timestamp`, `excess_kwh`, `likely_cause`). Its response must contain `Building:`, `Window:`, and `Recommendation:` and remain under 700 characters. Invalid output is retried once, then replaced by a template. Fallback and no-LLM notes are marked `needs_human_review=True`.

No LLM provider, API key, or external call is configured by default. This avoids pretending that an LLM was used when it was not.

## Evaluation definitions
- Fault-type detection rate: share of injected fault categories with at least one flagged reading.
- Precision/recall: calculated at the individual hourly-reading level against injected fault labels.
- False alerts per week: normal readings flagged divided by simulated weeks.
- These metrics are evaluated on the same simulated period used to construct the hour-of-week baseline, so treat them as a prototype demonstration rather than an unbiased out-of-sample benchmark.

## Project structure
```text
src/
  advisor.py
  config.py
  data_generator.py
  detector.py
  impact.py
  pipeline.py
tests/
  test_project.py
data/
reports/
charts/
```

## Limitations / next steps
- Validate on real, consented meter data and a chronological holdout period.
- Add building metadata (floor area, occupancy, HVAC schedules, meter type).
- Tune thresholds per building with facility-manager feedback.
- Replace illustrative tariff and emissions factor with sourced local values.
- Consider Isolation Forest or seasonal forecasting as a benchmark, not an automatic upgrade.
- Human review is required before operational changes.

## Reproducible baseline run (seed=42, 90 days)

The project was executed end-to-end and the eight-test suite passed. The measured results are:

| Metric | Result |
|---|---:|
| Hourly readings | 10,800 |
| Buildings | 5 |
| Injected fault categories detected | 3 / 3 (100%) |
| Flagged fault readings (TP) | 168 |
| False-positive readings | 0 |
| False alerts per week | 0.00 |
| Precision | 100.0% |
| Recall | 29.6% |
| Estimated excess in flagged readings | 2,994.99 kWh |
| Illustrative cost equivalent | AED 898.50 |
| Illustrative CO2e equivalent | 1,197.99 kg |
| Automated tests | 8 / 8 passed |

**Interpretation:** high precision and zero false positives were achieved on this seeded synthetic run, and at least one reading from every injected fault category was detected. Reading-level recall is only 29.6%, so the detector misses many injected-fault hours, especially within persistent/gradual events. Do not describe this as 100% detection of all fault hours. The AED and CO2e values are scenario estimates based on the illustrative assumptions above, not verified savings.
