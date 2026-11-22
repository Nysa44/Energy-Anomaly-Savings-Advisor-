from __future__ import annotations
import re

REQUIRED = ("Building:", "Window:", "Recommendation:")

def _valid(text: str) -> bool:
    return isinstance(text, str) and all(x in text for x in REQUIRED) and len(text) < 700

def template_advice(row: dict) -> str:
    return (
        f"Building: {row['building']}\n"
        f"Window: {row['timestamp']}\n"
        f"Recommendation: Investigate {row['likely_cause']}; review the meter trend and operating schedule. "
        f"Potential excess is {row['excess_kwh']:.1f} kWh. Confirm on site before changing controls."
    )

def make_advice(row: dict, generator=None) -> tuple[str, bool, str]:
    """Use an optional LLM callable; validate, retry once, then safely fall back."""
    if generator is None:
        return template_advice(row), True, "template_no_llm_configured"
    evidence = {k: row[k] for k in ("building", "timestamp", "excess_kwh", "likely_cause")}
    for attempt in range(2):
        try:
            candidate = generator(evidence)
            if _valid(candidate):
                return candidate, False, "llm_validated"
        except Exception:
            pass
    return template_advice(row), True, "template_fallback"
