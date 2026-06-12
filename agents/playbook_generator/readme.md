# Automated Sales Playbook Generator

A secure, localized multi-agent Go-To-Market (GTM) intelligence system built with **LangGraph** and **Ollama**. The application reads structural operational metrics and unstructured competitor dashboards to automatically rank sales priorities and generate tailormade account outbound sequences.

## Intent Architecture

The machine tracks high-value revenue signals based on a predictive prioritization loop:
* **ALPHA PRIORITY:** Accounts that have secured recent funding, are *not* current active clients, and have a newly placed executive who was a former software platform user.
* **BETA HIGH INTENT:** Accounts containing a former user in the leadership profile, without verifiable funding cycles.
* **ACCOUNT MANAGEMENT:** Existing paying accounts, routed away from outbound sales toward internal expansion methodologies.

## Core Component Workflows

1. **`Account Directory Parser`**: Parses `accounts.csv` to match firmographic markers and pull current client operational boundaries.
2. **`Intelligence Dossier Extractor`**: Scans `intelligence.md` using target regular expressions to extract structured subsets of competitor profiles and recent hiring blocks.
3. **`Buying Signal Validator`**: Utilizes an Ollama JSON mode model framework to calculate if executive names overlap with legacy client infrastructure parameters.
4. **`Playbook Synthesizer`**: Compiles aggregated internal data fields into a final, crisp text manual complete with tailored discovery tracks and an outreach email prototype.

## Execution Matrix

To initialize the multi-agent signal runner locally, deploy your execution script via:

```bash
python run_playbook_generator.py
```