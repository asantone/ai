"""
Product Enablement Sandbox Builder Architecture Layer
=============================================================================
File:        enablement_graph.py
Description: Compiles an intelligent enablement pipeline that transforms raw 
             engineering specifications into structured sales training tools.
Engine:      LangGraph Framework orchestrated via local Ollama (Llama 3.1 8B).
Architecture:Deterministic execution graph utilizing isolated reasoning nodes.

Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

# import dependencies
import os
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama

# Define the Enablement State Schema
class EnablementState(TypedDict):
    messages: Annotated[list, add_messages]
    feature_id: str
    raw_spec_text: str
    translated_value_metrics: str
    final_sales_sandbox: str

# define the LLM of choice; allows some creativity (non-zero temp)
local_llm = ChatOllama(model="llama3.1:8b", temperature=0.2)

# Node A: Ingest Raw Specification Document
# reads the engineering specifications in the .md technical doc -- could be replaced with Jira content
def engineering_spec_ingestor(state: EnablementState):
    feature_query = state["feature_id"].strip().lower()
    spec_file_path = "engineering_specs.md"
    extracted_text = "Error: Targeted feature specification document not found."
    
    if os.path.exists(spec_file_path):
        with open(spec_file_path, mode="r", encoding="utf-8") as file:
            content = file.read()
            # If the specific feature block matches our query, ingest the text
            if feature_query in content.lower():
                extracted_text = content.strip()
                
    return {"raw_spec_text": extracted_text}

# Node B: Translate Jargon into Commercial Value Metrics
# this is the core enablement work -- make Engineering speak in Sales language
def commercial_value_translator(state: EnablementState):
    raw_text = state["raw_spec_text"]
    
    prompt = (
        f"You are an elite Product Marketing Manager and GTM Enablement Executive. "
        f"Your task is to review this raw, highly technical engineering specification document "
        f"and translate the technical features into commercial business outcomes.\n\n"
        f"--- RAW ENGINEERING SPECIFICATION ---\n{raw_text}\n\n"
        f"--- TRANSLATION DIRECTIONS ---\n"
        f"Identify the 3 most impactful technical features and map them out exactly like this:\n"
        f"- The Technical Blueprint: (What the feature actually does in simple terms)\n"
        f"- The Business Outcome: (How this impacts a company's bottom line, revenue, or customer retention)\n"
        f"- The Commercial Value Hook: (The exact phrases or statistics an Account Executive can use to spark interest)"
    )
    
    response = local_llm.invoke([("human", prompt)])
    return {"translated_value_metrics": response.content}

# Node C: Generate Sales Enablement Training Sandbox
# create the output in Sales-ready language
def sales_sandbox_generator(state: EnablementState):
    feature = state["feature_id"]
    value_metrics = state["translated_value_metrics"]
    
    prompt = (
        f"You are a Product Enablement Specialist. Use the following commercial value translation "
        f"to build a high-impact Sales Enablement Training Guide for Account Executives (AEs) "
        f"covering the upcoming launch of [{feature}].\n\n"
        f"--- COMMERCIAL VALUE MATRIX ---\n{value_metrics}\n\n"
        f"--- STRUCTURE REQUIREMENTS ---\n"
        f"1. FEATURE BRIEF IN A NUTSHELL: A 3-sentence summary an AE can use to explain the launch to a client.\n"
        f"2. THE ROBUST VALUE HOOK: Build a strong competitive angle focusing on speed, reliability, and cost-savings.\n"
        f"3. OBJECTION HANDLING SANDBOX: Draft 2 highly common customer objections (e.g., 'Why do we need this if our current setup works?' or 'Is the migration going to cause disruption?') and provide the exact response scripts an AE should use.\n"
        f"4. SALES READINESS QUIZ: Create a 3-question multiple-choice readiness quiz based on the value metrics to test the AE's positioning skills. Include an answer key at the bottom."
    )
    
    response = local_llm.invoke([("human", prompt)])
    return {"final_sales_sandbox": response.content}

# Assemble LangGraph Topography
# this is the workflow in LangGraph 
workflow = StateGraph(EnablementState)

workflow.add_node("ingest_spec", engineering_spec_ingestor)
workflow.add_node("translate_value", commercial_value_translator)
workflow.add_node("generate_sandbox", sales_sandbox_generator)

workflow.set_entry_point("ingest_spec")
workflow.add_edge("ingest_spec", "translate_value")
workflow.add_edge("translate_value", "generate_sandbox")
workflow.add_edge("generate_sandbox", END)

#LFG
app = workflow.compile()