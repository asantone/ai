"""
streamlit_app.py

Interactive front end for the Q2C Deal Reviewer.

Lets a user play with deal terms (value, discount, term, add-ons) and see
the policy engine's decision in real time, including a coaching note
authored by a local LLM (Ollama, llama3.1:8b) that runs after the
deterministic policy decision has already been made.

Run with:
    streamlit run streamlit_app.py

Requires `ollama serve` running locally with llama3.1:8b pulled
(`ollama pull llama3.1:8b`) for the LLM guidance step. If Ollama isn't
reachable, the app still works: the deterministic decision and
next-best-action are unaffected, and the LLM panel shows a clear
fallback message instead of failing the whole page.
"""

from __future__ import annotations

import streamlit as st

from agent_workflow import POLICY_CONFIG, run_deal

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

BACKGROUND = "#FFFFFF"
CARD_BG = "#FFFFFF"
TEXT_PRIMARY = "#22262B"     
TEXT_MUTED = "#22262B"
ACCENT_GREEN = "#39AC62"     
ACCENT_GREEN_BG = "#E4F2E9"
ACCENT_AMBER = "#B8860B"
ACCENT_AMBER_BG = "#FBF1DC"
ACCENT_RED = "#DB4C2F"
ACCENT_RED_BG = "#F8E7E2"
BORDER = "#DEDBD2"

STATUS_STYLES = {
    "APPROVED": (ACCENT_GREEN, ACCENT_GREEN_BG),
    "FLAGGED": (ACCENT_AMBER, ACCENT_AMBER_BG),
    "ERROR": (ACCENT_RED, ACCENT_RED_BG),
}

st.set_page_config(page_title="Q2C Deal Reviewer", page_icon=None, layout="centered")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND};
        color: {TEXT_PRIMARY};
    }}
    h1, h2, h3, h4, p, label, span {{
        color: {TEXT_PRIMARY};
    }}
    .subtitle {{
        color: {TEXT_MUTED};
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }}
    .card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }}
    .status-badge {{
        display: inline-block;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        margin-bottom: 0.75rem;
    }}
    .llm-note {{
        border-left: 4px solid {ACCENT_GREEN};
        padding-left: 0.9rem;
        color: {TEXT_PRIMARY};
        font-style: italic;
    }}
    .stButton > button {{
        background-color: {ACCENT_GREEN};
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: #336F49;
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Q2C Deal Reviewer")
st.markdown(
    '<p class="subtitle">Check a deal against policy before it ever reaches Deal Desk.</p>',
    unsafe_allow_html=True,
)

with st.form("deal_form"):
    col1, col2 = st.columns(2)

    with col1:
        deal_id = st.text_input("Deal ID", value="DEAL-DEMO")
        deal_value = st.number_input(
            "Deal value ($)", min_value=0.0, value=48000.0, step=1000.0, format="%.2f"
        )
        discount_percent = st.slider(
            "Discount requested (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5
        )

    with col2:
        term_months = st.slider(
            "Term (months)", min_value=1, max_value=240, value=12, step=1
        )
        addons = st.multiselect(
            "Add-ons included",
            options=["premium_support", "dedicated_csm"],
            default=[],
            help=(
                "Required automatically once term reaches "
                f"{POLICY_CONFIG['multi_year_term_threshold_months']} months."
            ),
        )

    submitted = st.form_submit_button("Check deal")

if submitted:
    deal_input = {
        "deal_id": deal_id or "DEAL-DEMO",
        "deal_value": deal_value,
        "discount_percent": discount_percent,
        "term_months": term_months,
        "addons": addons,
    }

    with st.spinner("Running policy check and generating coaching note..."):
        result = run_deal(deal_input)

    status = result.get("status", "ERROR")
    color, bg = STATUS_STYLES.get(status, STATUS_STYLES["ERROR"])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        f'<span class="status-badge" style="color:{color}; background-color:{bg};">'
        f"{status}</span>",
        unsafe_allow_html=True,
    )

    if status == "ERROR":
        st.write(result.get("validation_message", "Validation failed."))
        for v in result.get("violations", []):
            st.write(f"- {v}")
    else:
        summary = result.get("deal_summary", {})
        st.write(
            f"**{deal_input['deal_id']}** — "
            f"${summary.get('deal_value', 0):,.2f}, "
            f"{summary.get('discount_percent', 0)}% discount, "
            f"{summary.get('term_months', 0)} months, "
            f"add-ons: {', '.join(summary.get('addons', [])) or 'none'}"
        )

        violations = result.get("violations", [])
        if violations:
            st.markdown("**Policy violations:**")
            for v in violations:
                st.write(f"- {v}")
        else:
            st.write("No policy violations. This deal looks good.")

        st.markdown("**Deterministic next best action:**")
        st.write(result.get("next_best_action", ""))

    st.markdown("</div>", unsafe_allow_html=True)

    if status != "ERROR":
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Coaching note: **")
        st.markdown(
            f'<p class="llm-note">{result.get("llm_guidance", "")}</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Raw JSON result"):
        st.json(result)
