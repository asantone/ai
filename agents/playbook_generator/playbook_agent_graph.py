"""
MASR - Automated Sales Playbook Generator Architecture Layer
=============================================================================
File:        playbook_agent_graph.py
Description: Establishes the state management graph, file parsing utilities,
             and scoring matrices for extracting B2B GTM buying signals.
Engine:      LangGraph Framework orchestrated via local Ollama (Llama 3.1 8B).
Architecture:Privacy-first local intelligence aggregator.

Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

#import dependencies
import os
import csv
import re
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama

# Define the Global State Schema
# this just defines what we're going to need and the data types
class SalesAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    target_company: str
    is_current_customer: bool
    target_workload: str
    raw_intelligence_text: str
    is_former_customer_present: bool
    priority_tier: str
    final_playbook: str

# Instantiate our local llm; low temp so it doesn't hallucinate too much
local_llm = ChatOllama(model="llama3.1:8b", temperature=0.0)

# Parse CSV 
# the CSV has the company data (firmographics) so we'll bring in that data first
def account_directory_parser(state: SalesAgentState):
    company_query = state["target_company"].strip().lower()
    csv_file_path = "accounts.csv"
    
    # Defaults if not found
    is_customer = False
    workload = "General Enterprise Optimization"
    
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("company_name", "").strip().lower() == company_query:
                    is_customer = row.get("is_current_customer", "False").strip().lower() == "true"
                    workload = row.get("target_workload", workload)
                    break
                    
    return {
        "is_current_customer": is_customer,
        "target_workload": workload
    }

# Node B: Extract signals data from the intelligence dossier
# We want to know if the account is a current customer, if they're recently funded, if there are any C-suite changes
def intelligence_dossier_extractor(state: SalesAgentState):
    company_name = state["target_company"].strip()
    md_file_path = "intelligence.md"
    extracted_block = "No supplemental dossier intelligence found for this account."
    
    if os.path.exists(md_file_path):
        with open(md_file_path, mode="r", encoding="utf-8") as file:
            content = file.read()
            # Regex to find the markdown block corresponding to the account heading
            pattern = rf"(# {re.escape(company_name)}\b.*?)(?=\n# |\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                extracted_block = match.group(1).strip()
                
    return {"raw_intelligence_text": extracted_block}

# Evaluate Signals & Determine Lead Tier
# this is the decision layer where we evaluate the intelligence and rank the accounts 
# the ideal output is a targeted set of accounts with a high propensity to buy
def buying_signal_validator(state: SalesAgentState):
    intel_text = state["raw_intelligence_text"]
    is_customer = state["is_current_customer"]
    
    # Fallback to local LLM to extract boolean logic out of unstructured text block
    prompt = (
        f"Analyze the following text block. Does the executive or C-suite background "
        f"indicate that a new hire or current leader was a FORMER direct user or customer of our platform? "
        f"Respond with a single JSON object containing a boolean key 'former_customer' (true or false).\n\n"
        f"Text:\n{intel_text}"
    )
    
    json_llm = ChatOllama(model="llama3.1:8b", format="json", temperature=0.0)
    try:
        import json
        response = json_llm.invoke([("human", prompt)])
        data = json.loads(response.content)
        former_customer = data.get("former_customer", False)
    except Exception:
        former_customer = False

    # Establish Priority Framework Matrices
    tier = "STANDARD"
    if is_customer:
        tier = "ACCOUNT_MANAGEMENT_EXPANSION"
    elif former_customer and ("2026" in intel_text or "Series" in intel_text):
        tier = "ALPHA_PRIORITY"
    elif former_customer:
        tier = "BETA_HIGH_INTENT"

    return {
        "is_former_customer_present": former_customer,
        "priority_tier": tier
    }

# Generate a playbook
# The output file contains human-facing content to help land a deal
def playbook_synthesizer(state: SalesAgentState):
    company = state["target_company"]
    workload = state["target_workload"]
    intel = state["raw_intelligence_text"]
    tier = state["priority_tier"]
    
    prompt = (
        f"You are an expert Strategic Revenue Enablement AI. Generate a hyper-personalized Outbound "
        f"Sales Playbook for a target Account Executive targeting {company}.\n\n"
        f"--- TARGET METADATA ---\n"
        f"Assigned Strategy Tier: {tier}\n"
        f"Target Use Case/Workload: {workload}\n\n"
        f"--- INTEL DOSSIER ---\n{intel}\n\n"
        f"--- PLAYBOOK REQUIREMENTS ---\n"
        f"1. Executive Summary: Highlight the strategic value of their recent funding and why this tier was assigned.\n"
        f"2. Core Angle: If a former customer is present, weave a highly warm, specific contextual outreach hook highlighting their previous company background. If no former customer is found, lead heavily with competitor feature gaps.\n"
        f"3. Three Discovery Questions: Tailor specifically to exploit competitors mentioned and map directly to their workload.\n"
        f"4. First-Touch Outreach Email Draft: Write a short, crisp, non-generic message ready for human execution."
    )
    
    response = local_llm.invoke([("human", prompt)])
    return {"final_playbook": response.content}

# Workflow structure and logic
# this defines how the workflow, uh, flows
workflow = StateGraph(SalesAgentState)

workflow.add_node("parse_csv", account_directory_parser)
workflow.add_node("extract_md", intelligence_dossier_extractor)
workflow.add_node("validate_signals", buying_signal_validator)
workflow.add_node("synthesize_playbook", playbook_synthesizer)

workflow.set_entry_point("parse_csv")
workflow.add_edge("parse_csv", "extract_md")
workflow.add_edge("extract_md", "validate_signals")
workflow.add_edge("validate_signals", "synthesize_playbook")
workflow.add_edge("synthesize_playbook", END)

#LFG
app = workflow.compile()