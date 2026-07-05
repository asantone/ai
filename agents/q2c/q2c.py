"""
q2c.py

Demo entry point for the Q2C Deal Reviewer.

Run directly to see the graph evaluate a "Pass" scenario, a "Fail"
scenario, and a malformed-input scenario back to back, printing the full
result -- including the deterministic decision and the local-LLM
coaching note -- as JSON for each.

For an interactive front end, use `streamlit run streamlit_app.py`
instead. This script is just a quick sanity check from the terminal.
"""

from __future__ import annotations

import json

from agent_workflow import run_deal


def evaluate_deal(deal: dict) -> dict:
    """Thin pass-through so external callers don't need to know the
    module is backed by LangGraph at all."""
    return run_deal(deal)


def _print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo() -> None:
    # --- Scenario 1: PASS ---------------------------------------------
    # Standard discount, standard term, no policy conflicts.
    pass_scenario = {
        "deal_id": "DEAL-1001",
        "deal_value": 48000.00,
        "discount_percent": 10.0,
        "term_months": 12,
        "addons": [],
    }

    _print_section("SCENARIO 1: PASS (10% discount, 12-month term)")
    result = evaluate_deal(pass_scenario)
    print(json.dumps(result, indent=2))

    # --- Scenario 2: FAIL -----------------------------------------------
    # Discount exceeds standard authority AND multi-year add-ons missing.
    fail_scenario = {
        "deal_id": "DEAL-1002",
        "deal_value": 120000.00,
        "discount_percent": 30.0,
        "term_months": 36,
        "addons": [],
    }

    _print_section("SCENARIO 2: FAIL (30% discount, 36-month term, missing add-ons)")
    result = evaluate_deal(fail_scenario)
    print(json.dumps(result, indent=2))

    # --- Scenario 3: ERROR (fail-fast) ----------------------------------
    # Missing required field. Should short-circuit before policy checks.
    malformed_scenario = {
        "deal_id": "DEAL-1003",
        "deal_value": 50000.00,
        # discount_percent intentionally omitted
        "term_months": 12,
    }

    _print_section("SCENARIO 3: ERROR (malformed payload, fail-fast)")
    result = evaluate_deal(malformed_scenario)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    demo()
