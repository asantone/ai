"""
main.py

Demo / CLI entry point for the Q2C Policy Interceptor.

Run directly to see the graph evaluate a "Pass" scenario and a "Fail"
scenario back to back, or import `evaluate_deal` into another script /
dashboard backend.
"""

from __future__ import annotations

import json
import sys

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


def _cli() -> None:
    """Optional CLI mode: pass a JSON file path or a raw JSON string as
    argv[1] to evaluate a custom deal, e.g.:

        python main.py '{"deal_id": "D-1", "deal_value": 5000, \
"discount_percent": 15, "term_months": 6}'
    """
    raw = sys.argv[1]
    try:
        deal = json.loads(raw)
    except json.JSONDecodeError:
        with open(raw, "r", encoding="utf-8") as f:
            deal = json.load(f)

    print(json.dumps(evaluate_deal(deal), indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _cli()
    else:
        demo()
