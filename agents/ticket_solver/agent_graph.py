"""
Multi-Agent Support Router (MASR) - Local Architecture Layer
=============================================================================
File:        agent_graph.py
Description: Defines the topological state graph, node execution blocks, 
             and conditional routing pathways for an on-premises multi-agent
             customer ticket triage and retrieval system.
Engine:      LangGraph Framework orchestration via local Ollama inference 
             (Llama 3.1 8B).
Architecture:Privacy-first, isolated multi-agent memory state machine.
             Ensures local data governance by confining processing boundaries
             entirely to host machine resources.

Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

#import libraries
from typing import Annotated, TypedDict
import json
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage

# Agent Logic
# Define the System Memory State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    routing_decision: str
    technical_notes: str
    final_response: str

# Instantiate our Local Ollama Engine
# A low temperature (0.0) for the router and analyzer ensures deterministic logic (low creativity).
# A relatively small model was chosen for running locally without a dedicated GPU.
# There is no format enforced here (see JSON instance which does enforce a JSON format)
local_llm = ChatOllama(model="llama3.1:8b", temperature=0.0)

# Define the Router Node 
def routing_agent(state: AgentState):
    latest_ticket = state['messages'][-1].content
    
    #single quotes here so the sent message ignores line breaks
    system_prompt = (
        "You are an intake triage coordinator. First, analyze the incoming customer support ticket. "
        "Second, respond with a single JSON object containing the key 'route' with one of three values: "
        "'technical', 'billing', or 'bug'."
    )
    
    # Enforce JSON formatting on the Ollama instance
    json_llm = ChatOllama(model="llama3.1:8b", format="json", temperature=0.0)
    
    #call the json LLM to work on the system prompt and the ticket 
    response = json_llm.invoke([
        ("system", system_prompt),
        ("human", latest_ticket)
    ])
    
    # Parse the local model's JSON response securely
    try:
        data = json.loads(response.content)
        decision = data.get("route", "technical")
    except Exception:
        decision = "technical" # Fallback safety

    #return the decision    
    return {"routing_decision": decision}

# Define the Local RAG Technical Sub-Agent
def technical_agent(state: AgentState):
    latest_ticket = state['messages'][-1].content
    
    # --- SIMULATED CHROMADB LOCAL SEARCH ---
    # This example is not connected to a database with tickets so we're just simulating it here
    # In a full setup, this would query a vector store using ChromaDB here
    # Expanded high-fidelity knowledge asset for local RAG simulation
    # this is the CONTEXT LAYER that supports concrete advice
    retrieved_wiki_context = """
    =============================================================================
    INTERNAL WIKI KNOWLEDGE BASE | DOCUMENT #442
    Title:          Legacy Platform API Dropouts & Gateway Timeout Resolution
    Category:       Infrastructure / Client-Side Architecture
    Last Modified:  May 2026
    =============================================================================
    
    [Issue Description]
    Persistent 504 Gateway Timeout errors and unhandled connection drops have 
    been observed during high-throughput API traffic. This behavior isolates 
    primarily to legacy platform endpoints accessed by older client builds.
    
    [Root Cause Analysis]
    The upstream gateway restricts persistent connections on outdated keep-alive 
    handshakes. This occurs exclusively on client application builds older than 
    version 2.4 (Client Versions less than 2.4).
    
    [Diagnostic Footprint]
    - HTTP Status Code: 504 Gateway Timeout
    - Error Signature:  "upstream_connect_time_out" or "ECONNRESET"
    - Target Path:      /api/v1/legacy/*
    
    [Standard Resolution Pathways]
    The system engineer or client administrator must execute one of the following:
    
    Option A: Configuration Update
    1. Open the local environment configuration deployment file ('settings.env').
    2. Force a manual environment variables flush by appending the following flag:
       API_TIMEOUT_OVERRIDE=true
    3. Restart the localized client daemon thread to pull the configuration.
    
    Option B: Client-Side Cache Eviction
    1. Flush the edge gateway and client memory caches entirely.
    2. Purge local sessions to force a fresh TLS handshake negotiation on the 
       next request sequence.
    
    [Escalation Metrics]
    If the client build cannot be upgraded immediately and environmental overrides 
    fail, route the ticket directly to the Infrastructure Operations tier.
    =============================================================================
    """
    # --------------------------------------

    prompt = (
        f"You are a Technical Support Agent. Review this ticket and the local wiki search for necessary context. "
        f"Draft an assessment for the root cause behind the user's stated problem.\n\n"
        f"Ticket: {latest_ticket}\n"
        f"Local Wiki Knowledge: {retrieved_wiki_context}"
    )
    
    #call the local (non-JSON) llm for help. return the technical support agent output (assessment). 
    response = local_llm.invoke([("human", prompt)])
    return {"technical_notes": response.content}

# Define the Synthesis Agent
# This agent writes a nice note back to the user who submitted the ticket. 
def synthesis_agent(state: AgentState):
    ticket = state['messages'][-1].content
    notes = state['technical_notes']
    
    prompt = (
        f"Create a brief, friendly email response to the customer using "
        f"the provided internal technical notes. Do not invent details.\n\n"
        f"Original Ticket: {ticket}\n"
        f"Internal Tech Notes: {notes}"
    )
    
    #create a final response using the non-JSON llm
    response = local_llm.invoke([("human", prompt)])
    return {"final_response": response.content}

# Build the Stateful Routing Logic Function
# logic to choose the correct agent to handle the problem
# right now, we direct traffic to the technical agent which has the context
def route_next_node(state: AgentState):
    if state["routing_decision"] == "technical":
        return "technical_agent"
    # Placeholder branches for other endpoints
    return "technical_agent" 

# Orchestrate the LangGraph State Machine
# this ties the agents together (routing for step 1 triage, technical step 2 review, and generative messaging in step 3 for the customer-facing response)
workflow = StateGraph(AgentState)

# add the agents
workflow.add_node("router", routing_agent)
workflow.add_node("technical_agent", technical_agent)
workflow.add_node("synthesis_agent", synthesis_agent)

# identify the first one
workflow.set_entry_point("router")

#the flow definition -- from router to the technical agent)
workflow.add_conditional_edges(
    "router",
    route_next_node,
    {"technical_agent": "technical_agent"}
)

#add more flow definitions -- from technical to synthesis; synthesis to end
workflow.add_edge("technical_agent", "synthesis_agent")
workflow.add_edge("synthesis_agent", END)

#execution layer -- runs the app
app = workflow.compile()