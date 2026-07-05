# Q2C Deal Reviewer: Agentic Guardrails for High-Velocity Sales

A LangGraph-based agent that sits in the Quote-to-Cash path and validates
deal parameters against business policy in real time, before a rep ever
opens a Deal Desk ticket.

---

## Design Philosophy

Deal Desk friction is rarely caused by bad deals. It is caused by *late
discovery* of policy violations: a rep builds a quote, submits it, waits
on a queue, and only then learns the discount was 10 points over their
authority. The Policy Interceptor moves that check to the point of
authorship and returns a decision in milliseconds.

Three architectural decisions drive that outcome:

**1. Decoupled, single-responsibility nodes.**
`policy_checker` only compares numbers against `POLICY_CONFIG`. It knows
nothing about phrasing. `guidance_generator` only writes the human-facing
"Next Best Action." It knows nothing about thresholds. This separation
means Sales Ops can update discount ceilings without redeploying prompt
logic, and Enablement can rewrite guidance copy without touching a single
business rule. In a fast-moving GTM org, the policy changes weekly. The
architecture should not have to.

**2. State as the single source of truth.**
Every node reads and writes the same `DealState` `TypedDict`. There is no
hidden side-channel data. This makes the graph trivially testable (feed
in a state, assert on the state that comes out) and makes the eventual
move to LangGraph's checkpointing/persistence layer, for multi-turn
negotiation flows, a non-event, since the state shape is already explicit
and typed.

**3. Fail-fast before fail-slow.**
`input_validator` runs first and short-circuits the graph via a
conditional edge if the payload is missing fields or contains nonsensical
values (negative deal value, discount outside 0 to 100%, etc.). This
guarantees the agent never silently "approves" garbage input. A bad
payload always resolves to an explicit `ERROR` status with actionable
feedback, not a false positive.

The result is a graph that mirrors how a real Deal Desk analyst reasons:
is this request even well-formed, does it violate policy, what should the
rep do about it, what is the final verdict. Each of those four questions
is isolated in its own node.

---

## Architecture

```
                 ┌────────────────┐
                 │ validate_input │  (fail-fast gate)
                 └───────┬────────┘
                         │
              ┌──────────┴──────────┐
        ERROR │                     │ PENDING
              ▼                     ▼
       ┌────────────┐      ┌────────────────┐
       │  finalize   │◄─────│ check_policy   │
       └────────────┘      └───────┬────────┘
              ▲                     │
              │            ┌────────▼─────────┐
              │            │ generate_guidance │
              │            └────────┬─────────┘
              │                     │
              │            ┌────────▼─────────┐
              └────────────│  llm_guidance     │
                           └───────────────────┘
```

| Node | Responsibility |
|---|---|
| `input_validator` | Schema and sanity check. Fail-fast on missing or invalid fields. |
| `policy_checker` | Pure comparison against `POLICY_CONFIG`. Produces a `violations` list. |
| `guidance_generator` | Converts violations into one deterministic, actionable "Next Best Action" string. |
| `llm_guidance` | Calls a local Ollama model (`llama3.1:8b`) to write a short, natural-language coaching note on top of the already-final decision. Never alters `status` or `violations`; fails soft if Ollama is unreachable. |
| `finalizer` | Emits the strict JSON contract (`APPROVED`, `FLAGGED`, or `ERROR`), including both `next_best_action` and `llm_guidance`. |

The LLM node runs strictly after the decision has been made. It cannot
change whether a deal is `APPROVED`, `FLAGGED`, or `ERROR`, and it never
sees `POLICY_CONFIG` directly. It only reasons over the violations list
and the deterministic next-best-action, so the underlying policy math
stays fully deterministic and auditable regardless of what the model
says.

---

## Files

| File | Purpose |
|---|---|
| `agent_workflow.py` | `POLICY_CONFIG`, `DealState`, all five nodes (including the local-LLM `llm_guidance` node), graph assembly, and `run_deal()` / `run_deal_json()` entry points. |
| `q2c.py` | Terminal demo script (Pass, Fail, and malformed-input scenarios), printed as JSON. |
| `streamlit_app.py` | Interactive front end. Lets a user set deal value, discount, term, and add-ons with a form and see the decision plus LLM coaching note live. |
| `requirements.txt` | Python dependencies. |
| `README.md` | This document. |

---

## Implementation Guide

### Requirements

```bash
pip install -r requirements.txt
```

The `llm_guidance` node calls a local Ollama model, so Ollama must be
running with the model pulled:

```bash
ollama pull llama3.1:8b
ollama serve
```

If Ollama isn't running, the app still works end to end: the
deterministic decision and next-best-action are unaffected, and the LLM
panel shows a clear fallback message instead of failing.

### Run the interactive app

```bash
streamlit run streamlit_app.py
```

Set deal value, discount, term, and add-ons in the form and click
"Check deal" to see the status, violations, deterministic next best
action, and the LLM-authored coaching note.

### Run the terminal demo

```bash
python q2c.py
```

This runs three scenarios end to end and prints strict JSON for each:

1. **Pass**: 10% discount, 12-month term. Result: `APPROVED`
2. **Fail**: 30% discount, 36-month term, missing multi-year add-ons. Result: `FLAGGED`
3. **Error**: malformed payload (missing `discount_percent`). Result: `ERROR`, no policy evaluation attempted

### Use it as a library

```python
from agent_workflow import run_deal

result = run_deal({
    "deal_id": "DEAL-2044",
    "deal_value": 75000.00,
    "discount_percent": 22.0,
    "term_months": 24,
    "addons": ["premium_support", "dedicated_csm"],
})
# result == {"status": "FLAGGED", ...}
```

### Output contract

Every response, whether success, flag, or error, conforms to this shape,
so a front end can render off `status` alone:

```json
{
  "status": "APPROVED | FLAGGED | ERROR",
  "deal_id": "string",
  "deal_summary": { "deal_value": 0, "discount_percent": 0, "term_months": 0, "addons": [] },
  "violations": ["string", "..."],
  "next_best_action": "string",
  "llm_guidance": "string"
}
```

All guidance strings are written in plain ASCII punctuation (periods and
colons, not em dashes), so the JSON serializes cleanly without `\u2014`
escapes reaching the front end.

---

