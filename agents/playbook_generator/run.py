"""
MASR - Automated Sales Playbook Generator Execution Runtime
=============================================================================
File:        run.py
Description: Invokes the localized multi-agent sales signal engine. Searches 
             target structures, compiles metrics, and outputs a custom playbook.
Engine:      LangGraph Framework orchestrated via local Ollama.

Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

import os
from playbook_agent_graph import app

# Define target company input for testing
# Options based on mock data: "Echo Corp", "Delta Solutions", "Omega Health"
TARGET_ACCOUNT = "Echo Corp"
OUTPUT_FILE = "generated_sales_playbook.txt"

# Prepare initial memory footprint
initial_state = {
    "target_company": TARGET_ACCOUNT,
    "is_current_customer": False,
    "target_workload": "",
    "raw_intelligence_text": "",
    "is_former_customer_present": False,
    "priority_tier": "STANDARD",
    "final_playbook": ""
}

print("====================================================")
print("Initializing Automated Sales Playbook Generator...")
print(f"Target Profile Selected: [{TARGET_ACCOUNT}]")
print("====================================================\n")

final_extracted_data = {}

# Stream graph nodes live to prevent visual lag
for event in app.stream(initial_state):
    for node_name, state_updates in event.items():
        print(f"✦ Processing Node: [{node_name.upper()}]")
        for key, value in state_updates.items():
            if value is not None:
                final_extracted_data[key] = value
                # Simple string preview handling
                preview = str(value)[:80].replace("\n", " ")
                print(f"  └─ Documented [{key}]: {preview}...")
        print()

print("====================================================")
print("Pipeline complete. Rendering final playbook file...")
print("====================================================")

try:
    playbook_text = final_extracted_data.get("final_playbook", "Error: No playbook generated.")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as text_file:
        text_file.write(playbook_text)
        
    print(f"✔ Playbook successfully exported to:\n  {os.path.abspath(OUTPUT_FILE)}")
    print("====================================================")
    
except Exception as e:
    print(f"✘ An error occurred exporting the file: {str(e)}")