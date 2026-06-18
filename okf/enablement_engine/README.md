# OKF Enablement Engine

The **Open Knowledge Format (OKF) Enablement Engine** is a stateful, agentic pipeline for revenue enablement. It moves beyond static training documentation by treating institutional knowledge as a dynamic data graph that evolves based on learner progress and manager feedback.

## The Problem
Traditional enablement documentation is often "dead content"—static, unsearchable, and disconnected from the daily workflow of the sales team. It fails to personalize training or track real-world competency.

## The Solution
The OKF Engine bridges the gap between raw data and actionable coaching:
* **Structured Dossiers:** Uses Markdown with YAML frontmatter to map personas to specific skills and team segments.
* **Agentic Orchestration:** Integrates local LLM inference (via Ollama) to synthesize hyper-personalized coaching insights tailored to the learner's specific role and the company's playbook standards.
* **Stateful Feedback Loops:** Implements a bi-directional workflow where manager review notes ingested from generated reports automatically update the learner's skill profile, ensuring the training engine remains current.

## Project Structure
```text
.
├── engine.py              # Core orchestration pipeline
├── personas/              # Learner dossiers (YAML + Markdown)
├── playbooks/             # Institutional knowledge base
└── recommendations/       # Generated coaching reports (feedback loop)