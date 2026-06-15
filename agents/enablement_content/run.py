"""
Product Enablement Sandbox Builder Execution Runtime
=============================================================================
File:        run.py
Description: Triggers the localized enablement pipeline, passing raw internal
             documentation through cognitive translation layers to output code-free
             sales enablement training modules.
Engine:      LangGraph Framework orchestrated via local Ollama.

Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

#import dependencies
import os
from enablement_graph import app

FEATURE_TARGET = "v4.0"
OUTPUT_FILE = "product_enablement_guide.txt"

initial_state = {
    "feature_id": FEATURE_TARGET,
    "raw_spec_text": "",
    "translated_value_metrics": "",
    "final_sales_sandbox": ""
}

print("====================================================")
print("Initializing Product Enablement Sandbox Builder...")
print(f"Target Feature Specification Look-up: [{FEATURE_TARGET}]")
print("====================================================\n")

final_state_data = {}

# Stream the processing blocks live to verify local system performance
for event in app.stream(initial_state):
    for node_name, state_updates in event.items():
        print(f"✦ Active Node Processing: [{node_name.upper()}]")
        for key, value in state_updates.items():
            if value is not None:
                final_state_data[key] = value
                preview = str(value)[:80].replace("\n", " ")
                print(f"  └─ Documented [{key}]: {preview}...")
        print()

print("====================================================")
print("Processing complete. Exporting compiled enablement files...")
print("====================================================")

try:
    enablement_text = final_state_data.get("final_sales_sandbox", "Error: Enablement pipeline failed.")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as text_file:
        text_file.write(enablement_text)
        
    print(f"✔ Success! Ready-to-use sales content generated at:\n  {os.path.abspath(OUTPUT_FILE)}")
    print("====================================================")
    
except Exception as e:
    print(f"✘ An error occurred exporting the text file: {str(e)}")