# Q2C Deal Reviewer: Real-Time Deal Guardrails for Sales

A tool that checks a sales deal against company policy the moment a rep
is putting the numbers together, instead of after they've already
submitted it. It gives an instant answer, approved, flagged, or invalid,
along with a plain-language explanation of what to do next.

---

## The Problem This Solves

Deal Desk teams can get bogged down because problems are found too late. A rep builds
a quote, submits it, waits in a review queue, and only then finds out
the discount was too aggressive or the contract term needs an add-on it
doesn't have. That delay costs time for the rep, the customer, and the
Deal Desk team reviewing something that should have been caught earlier.

This tool moves that check to the moment the rep is setting the terms,
so they find out while they're speaking with the customer.

## How It's Built, and Why

Three decisions shaped this design:

**1. Each step has one job, and only one job.**
The piece that checks the numbers against policy doesn't know or care
how the explanation gets worded. The piece that writes the explanation
doesn't know or care what the actual thresholds are. Keeping these
separate means the sales operations team can change a discount limit
without needing anyone to touch how the messaging is written, and
whoever owns the wording can improve it without any risk of accidentally
changing a business rule. Policy changes often, sometimes weekly. The
tool is built so that changing a number doesn't require touching the
logic around it.

**2. Every step passes along one shared, complete record of the deal.**
Think of it like a form that gets handed from person to person, where
each person adds their piece of the answer to the same form rather than
keeping their own private notes. Nothing is hidden or tracked
separately off to the side. This makes the tool easy to verify: you
can hand it a deal and check exactly what came out at each step, which
matters for something that needs to be auditable rather than a black
box.

**3. Bad input is caught immediately, before anything else runs.**
If a deal is missing information or has a nonsensical value, like a
negative dollar amount, the tool stops right there and says so clearly.
It never tries to evaluate a deal that doesn't make sense and never lets
something slip through by accident. A broken input always comes back as
a clear error, not a false approval.

Put together, the tool asks the same four questions a Deal Desk analyst
would ask, in order: is this request even valid, does it break any
policy, what should the rep do about it, and what's the final answer.
Each question is handled by its own isolated step, so nothing gets
tangled together.

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

| Step | What it does |
|---|---|
| Validate input | Checks the deal has all required fields and the numbers make sense. Stops immediately if not. |
| Check policy | Compares the deal's numbers against the policy rules. Produces a list of anything that's out of bounds. |
| Generate guidance | Turns that list into one clear, consistent "here's what to do next" message. |
| LLM coaching note | A local AI model reads the finished decision and writes a short, natural-sounding note explaining it in plain language. |
| Finalize | Packages everything into one clean result: approved, flagged, or invalid, plus the explanation and the coaching note. |

### Where AI fits in, and where it doesn't

It's worth being precise about this, since "agent" can sound like the AI
is making the call. It isn't. The actual decision, whether a deal is
approved, flagged, or invalid, is made by plain rule-based logic: is
this number bigger than that limit, yes or no. No model is involved in
that step, on purpose. A decision that affects revenue and gets audited
later needs to be consistent and explainable every time, not something
a model infers.

The AI model only gets involved after the decision is already locked in.
Its one job is to take that finished decision and write a short,
human-sounding explanation of it, the way a helpful colleague might
translate a policy printout into a quick heads-up. It can't change the
verdict and never sees the underlying policy thresholds directly. If the
AI model isn't available for any reason, the tool still works;
it just falls back to the plain rule-based explanation instead of the
AI-written one.

So the honest description is: a rule-based decision engine with an AI
explanation layer on top, not an AI making judgment calls.

---

## Files

| File | Purpose |
|---|---|
| `agent_workflow.py` | The policy rules, the step-by-step decision logic, and the AI coaching step. |
| `q2c.py` | A quick terminal demo that runs three example deals through the tool. |
| `streamlit_app.py` | The interactive app: a form where you can set deal terms and see the decision live. |
| `requirements.txt` | Python packages needed to run the tool. |
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

---

## Where This Could Go Next

This version is intentionally small and self-contained, so the core idea
could be proven out before investing in bigger infrastructure. A few
natural next steps, and the reasoning behind each:

- **Connect it to a real sales system.** Right now the tool takes deal
  information directly. In a production setting, it would instead pull
  the deal straight from the CPQ system (like Salesforce CPQ), so it
  reacts automatically the moment a rep changes a number, rather than
  needing someone to feed it information manually.

- **Make policy lookups smarter.** Policy rules currently live in a
  simple settings file. As a company's policy grows more complex across
  regions or product lines, this could instead search a knowledge base
  of policy documents to find the rule that actually applies to a given
  deal, so updates don't require a code change every time.

- **AI-written coaching (already built).** The tool already uses a
  local AI model to turn the finished decision into a natural-sounding
  explanation. Because that step only runs after the decision is final,
  it can improve the wording without ever being able to change the
  outcome. Swapping the local model for a larger hosted one later would make sense once this leaves a laptop demo and moves into a live environment.

- **Keep a record of every decision.** Adding a persistence layer would
  let every past deal evaluation be looked back on later, which matters
  for compliance and audit purposes. It would also support a rep
  revising a flagged deal and getting a quick re-check, rather than
  starting over from scratch.

- **Make it available as a shared service.** The core decision logic is
  already written so it could sit behind a simple web endpoint, letting
  a sales dashboard or a CPQ system call it directly and get an answer
  back.
