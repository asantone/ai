"""
agent_workflow.py

Q2C Deal Reviewer: Agentic Guardrail Engine
====================================================

Implements a LangGraph state machine that intercepts a deal payload before it
reaches Deal Desk, validates it against a versioned policy config, and emits
a structured, UI-consumable decision (APPROVED / FLAGGED / ERROR).

Design intent: each node does exactly one job (validate -> check policy ->
generate guidance -> finalize), so policy owners, prompt engineers, and
front-end consumers can each iterate on their layer independently.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Optional, TypedDict

import requests
from langgraph.graph import StateGraph, END


# ---------------------------------------------------------------------------
# 1a. LOCAL LLM CONFIGURATION (Ollama)
# ---------------------------------------------------------------------------
# This is the seam the README's "LLM-authored guidance" future-scalability
# note pointed at. It is intentionally isolated to a single node: the LLM
# never sees POLICY_CONFIG and never touches the violations list before it
# has already been computed deterministically. It can only add coaching
# color on top of a decision that has already been made.

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

#adjust here if model times out and does not return answers
OLLAMA_TIMEOUT_SECONDS = 120


# ---------------------------------------------------------------------------
# 1. POLICY CONFIGURATION
# ---------------------------------------------------------------------------
# In production this dictionary is the seam where a live CPQ policy service
# or a RAG-backed policy store would be swapped in (see README, "Future
# Scalability"). Keeping it declarative, not procedural, means Deal Desk
# can hand-edit thresholds without touching graph logic.

POLICY_CONFIG: dict[str, Any] = {
    "max_discount_percent": 20.0,
    "max_discount_percent_with_vp_approval": 35.0,
    "min_deal_value": 1000.0,
    "max_term_months": 60,
    "multi_year_term_threshold_months": 24,
    "multi_year_required_addons": ["premium_support", "dedicated_csm"],
    "escalation_contact": "deal-desk@company.com",
}


# ---------------------------------------------------------------------------
# 2. STATE DEFINITION
# ---------------------------------------------------------------------------

DealStatus = Literal["PENDING", "APPROVED", "FLAGGED", "ERROR"]


class DealState(TypedDict, total=False):
    """Shared state threaded through every node in the graph.

    total=False lets us construct partial/invalid inputs on purpose so the
    fail-fast validator has something real to reject.
    """

    # --- inputs (rep-supplied) ---
    deal_id: str
    deal_value: float
    discount_percent: float
    term_months: int
    addons: list[str]

    # --- computed / derived ---
    status: DealStatus
    violations: list[str]
    validation_message: str
    next_best_action: str
    llm_guidance: str

    # --- terminal output ---
    result: dict[str, Any]


# ---------------------------------------------------------------------------
# 3. NODES
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ("deal_value", "discount_percent", "term_months")


def input_validator(state: DealState) -> DealState:
    """Fail-fast gate. Rejects missing, non-numeric, or nonsensical input
    before it ever reaches policy logic, so a malformed payload from the
    front end never silently falls through as "approved".
    """
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in state or state[field] is None:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return {
            **state,
            "status": "ERROR",
            "violations": errors,
            "validation_message": "Deal payload failed schema validation.",
        }

    # Type / sanity checks. Only run once presence is confirmed.
    numeric_checks = {
        "deal_value": state["deal_value"],
        "discount_percent": state["discount_percent"],
        "term_months": state["term_months"],
    }
    for field, value in numeric_checks.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"Field '{field}' must be numeric, got {type(value).__name__}")

    if not errors:
        if state["deal_value"] <= 0:
            errors.append("deal_value must be greater than 0.")
        if not (0 <= state["discount_percent"] <= 100):
            errors.append("discount_percent must be between 0 and 100.")
        if not (1 <= state["term_months"] <= 240):
            errors.append("term_months must be between 1 and 240.")

    if errors:
        return {
            **state,
            "status": "ERROR",
            "violations": errors,
            "validation_message": "Deal payload failed sanity validation.",
        }

    # Normalize optional fields so downstream nodes never KeyError.
    return {
        **state,
        "addons": state.get("addons", []),
        "status": "PENDING",
        "violations": [],
    }


def policy_checker(state: DealState) -> DealState:
    """Evaluates the (already-validated) deal against POLICY_CONFIG.

    Pure comparison logic, no message-writing here. Keeping "what broke"
    (this node) separate from "what to say about it" (guidance_generator)
    means a change in phrasing/tone never risks touching rule evaluation.
    """
    violations: list[str] = []
    cfg = POLICY_CONFIG

    deal_value = state["deal_value"]
    discount = state["discount_percent"]
    term = state["term_months"]
    addons = state.get("addons", [])

    if deal_value < cfg["min_deal_value"]:
        violations.append(
            f"Deal value ${deal_value:,.2f} is below the minimum "
            f"threshold of ${cfg['min_deal_value']:,.2f}."
        )

    if discount > cfg["max_discount_percent_with_vp_approval"]:
        violations.append(
            f"Discount of {discount}% exceeds the absolute ceiling of "
            f"{cfg['max_discount_percent_with_vp_approval']}%, even with VP approval."
        )
    elif discount > cfg["max_discount_percent"]:
        violations.append(
            f"Discount of {discount}% exceeds standard rep authority "
            f"({cfg['max_discount_percent']}%) and requires VP escalation."
        )

    if term > cfg["max_term_months"]:
        violations.append(
            f"Term of {term} months exceeds the maximum allowable term "
            f"of {cfg['max_term_months']} months."
        )

    if term >= cfg["multi_year_term_threshold_months"]:
        missing_addons = [a for a in cfg["multi_year_required_addons"] if a not in addons]
        if missing_addons:
            violations.append(
                "Multi-year term requires the following add-on(s) that are "
                f"missing from the quote: {', '.join(missing_addons)}."
            )

    return {**state, "violations": violations}


def guidance_generator(state: DealState) -> DealState:
    """Synthesizes a single, actionable 'Next Best Action' string for the
    rep. This is the only node concerned with human-facing language, which
    means Sales Enablement can iterate on tone/wording without ever
    touching policy_checker's business logic.
    """
    violations = state.get("violations", [])

    if not violations:
        return {
            **state,
            "next_best_action": "No action needed. Deal is within policy. Proceed to send.",
        }

    escalation_hint = (
        f"If exception is warranted, escalate to {POLICY_CONFIG['escalation_contact']} "
        "with business justification."
    )
    action = " ".join(violations) + f" {escalation_hint}"

    return {**state, "next_best_action": action}


def llm_guidance_node(state: DealState) -> DealState:
    """Calls a local Ollama model to author a rep-facing coaching note.

    This node runs strictly after policy_checker and guidance_generator,
    and only ever reads their outputs (violations, next_best_action). It
    cannot change the deal's status or violations list, so the underlying
    decision remains fully deterministic and auditable; the LLM is only
    adding tone and business framing on top of a verdict that has already
    been reached.

    Fails soft: if Ollama isn't running or the call errors out, the
    deterministic next_best_action still stands on its own downstream, so
    a rep is never blocked by an LLM outage.
    """
    violations = state.get("violations", [])
    deal_id = state.get("deal_id", "unknown")

    if violations:
        violation_text = "\n".join(f"- {v}" for v in violations)
    else:
        violation_text = "None. The deal is fully within policy."

    prompt = (
        "You are a sales coach helping a rep understand a Quote-to-Cash "
        "policy check result. Do not invent new numbers, thresholds, or "
        "policy rules beyond what is given below. Do not contradict the "
        "verdict. In 2-3 short sentences, explain the result in plain, "
        "encouraging, direct language a rep could read in 10 seconds, and "
        "suggest a next step. Use plain ASCII punctuation, no em dashes.\n\n"
        f"Deal ID: {deal_id}\n"
        f"Deal value: ${state.get('deal_value')}\n"
        f"Discount requested: {state.get('discount_percent')}%\n"
        f"Term: {state.get('term_months')} months\n"
        f"Add-ons: {', '.join(state.get('addons', [])) or 'none'}\n"
        f"Policy violations found:\n{violation_text}\n"
        f"Deterministic next best action: {state.get('next_best_action', '')}\n"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        guidance = response.json().get("response", "").strip()
        if not guidance:
            guidance = "(LLM returned an empty response.)"
    except requests.exceptions.RequestException as exc:
        guidance = (
            "LLM guidance unavailable: could not reach Ollama at "
            f"{OLLAMA_URL} ({exc.__class__.__name__}). Is `ollama serve` "
            "running with the model pulled? Falling back to the "
            "deterministic next-best-action above."
        )

    return {**state, "llm_guidance": guidance}


def finalizer(state: DealState) -> DealState:
    """Terminal node. Emits the strict JSON contract consumed by the
    front-end UI. This is the ONLY node allowed to set the final `result`
    payload, so the schema has a single point of enforcement.
    """
    if state.get("status") == "ERROR":
        result = {
            "status": "ERROR",
            "deal_id": state.get("deal_id"),
            "validation_message": state.get("validation_message", "Unknown validation error."),
            "violations": state.get("violations", []),
            "next_best_action": "Correct the payload and resubmit.",
        }
        return {**state, "result": result}

    violations = state.get("violations", [])
    final_status: DealStatus = "FLAGGED" if violations else "APPROVED"

    result = {
        "status": final_status,
        "deal_id": state.get("deal_id"),
        "deal_summary": {
            "deal_value": state.get("deal_value"),
            "discount_percent": state.get("discount_percent"),
            "term_months": state.get("term_months"),
            "addons": state.get("addons", []),
        },
        "violations": violations,
        "next_best_action": state.get("next_best_action", ""),
        "llm_guidance": state.get("llm_guidance", ""),
    }
    return {**state, "status": final_status, "result": result}


# ---------------------------------------------------------------------------
# 4. CONDITIONAL ROUTING
# ---------------------------------------------------------------------------

def route_after_validation(state: DealState) -> str:
    """Fail-fast branch: skip policy evaluation entirely on invalid input."""
    return "error_exit" if state.get("status") == "ERROR" else "check_policy"


# ---------------------------------------------------------------------------
# 5. GRAPH ASSEMBLY
# ---------------------------------------------------------------------------

def build_graph():
    """Compiles the LangGraph StateGraph. Exposed as a factory function so
    callers (e.g. a dashboard backend) can rebuild the graph after hot-
    swapping POLICY_CONFIG without restarting the process.
    """
    graph = StateGraph(DealState)

    graph.add_node("validate_input", input_validator)
    graph.add_node("check_policy", policy_checker)
    graph.add_node("generate_guidance", guidance_generator)
    graph.add_node("llm_guidance", llm_guidance_node)
    graph.add_node("finalize", finalizer)

    graph.set_entry_point("validate_input")

    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "check_policy": "check_policy",
            "error_exit": "finalize",
        },
    )

    graph.add_edge("check_policy", "generate_guidance")
    graph.add_edge("generate_guidance", "llm_guidance")
    graph.add_edge("llm_guidance", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def run_deal(deal_input: dict[str, Any]) -> dict[str, Any]:
    """High-velocity entry point: takes a raw deal dict, runs the compiled
    graph synchronously, and returns strict JSON-serializable output.

    This is the function a sales dashboard or Slack bot would import
    directly. No LangGraph internals leak past this boundary.
    """
    app = build_graph()
    final_state = app.invoke(dict(deal_input))
    return final_state["result"]


def run_deal_json(deal_input: dict[str, Any]) -> str:
    """Convenience wrapper returning a serialized JSON string, for
    front-ends that consume the response over HTTP/websocket as text."""
    return json.dumps(run_deal(deal_input), indent=2)
