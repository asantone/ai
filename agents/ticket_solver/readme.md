# Multi-Agent Support Router (MASR)

A localized, privacy-first multi-agent system built to automate customer support ticket triage, internal technical data retrieval (RAG), and response drafting. Powered by **LangGraph** and running entirely on local hardware via **Ollama**, this application eliminates external API dependency and ensures sensitive organizational data never leaves your infrastructure.

---

## Architecture Overview

MASR uses a coordinated multi-agent state machine topology. Instead of relying on a single large language model to handle multiple tasks sequentially, the workflow passes a shared state through distinct, specialized nodes.

```
       [Incoming Customer Ticket]
                   │
                   ▼
         ┌───────────────────┐
         │   Routing Agent   │ (Classifies ticket intent to JSON)
         └─────────┬─────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  ┌─────────────┐     ┌─────────────┐
  │  Technical  │     │   Billing   │ (Specialized Domain Sub-Agents)
  │  RAG Agent  │     │  Sub-Agent  │
  └──────┬──────┘     └──────┬──────┘
         │                   │
         └─────────┬─────────┘
                   ▼
         ┌───────────────────┐
         │  Synthesis Agent  │ (Drafts unified customer response)
         └─────────┬─────────┘
                   │
                   ▼
       [Final Draft Email Output]

```

---

## How Each Component Works

### 1. Central Memory Management (`AgentState`)

The bedrock of the application is a unified, stateful `TypedDict` memory layer. As execution moves through the graph, each agent appends or overwrites specific fields within this state. This ensures token usage remains optimized, as individual sub-agents only read the specific context fields relevant to their domain rather than processing a monolithic prompt chain.

### 2. The Routing Agent

* **Role:** Intake Coordinator
* **Mechanism:** Acts as the entry point of the graph. It inspects the text of the incoming customer issue and utilizes Ollama’s native structured JSON mode to categorize the issue.
* **Output:** Updates the `routing_decision` state variable to a deterministic value (e.g., `"technical"`). This structural output triggers conditional branching edges in LangGraph to dynamically route the execution payload to the correct expert node.

### 3. Specialized Sub-Agents (Domain Experts)

* **Role:** Deep-Dive Investigation
* **Mechanism:** These nodes execute in isolation based on the router's decision.
* **Technical RAG Agent:** Pulls context directly from local storage configurations (such as an on-premise vector index or documentation dump). It maps the customer's symptom against known system workarounds or technical specifications.


* **Output:** Generates dense internal diagnostic summaries, updating fields like `technical_notes` in the global state, keeping engineering facts isolated from customer-facing formatting constraints.

### 4. The Synthesis Agent

* **Role:** Communicator & Writer
* **Mechanism:** The final active node in the graph state machine. It consumes the cumulative internal state (the original ticket description concatenated with the structural diagnostic summaries produced by the sub-agents). It is prompted with strict guardrails to prevent hallucination.
* **Output:** Structures a clear, professional, and empathetic response draft tailored to the user's issue, populating the `final_response` payload before reaching the termination endpoint (`END`).

---

## File Structure

The workspace is split into two modules to separate application architecture from execution logic:

* **`agent_graph.py`**: Defines the data models, state schema, agent nodes, prompt templates, and compiles the topological execution graph.
* **`run_resolver.py`**: The ingestion endpoint. Imports the compiled graph framework, injects the mock or live ticket payloads, executes the workflow state machine, and prints the synthesized response.

---

## Getting Started

### Prerequisites

1. **Ollama**: Install and run Ollama locally on your machine.
2. **Local Model**: Pull the recommended model framework:
```bash

```



ollama pull llama3.1:8b

```

### Installation

Install the open-source python orchestration libraries:

```bash
pip install langchain-ollama langgraph

```

### Execution

To run a diagnostic triage simulation across the local multi-agent topology, execute the runner script from your terminal:

```bash
python run_resolver.py

```