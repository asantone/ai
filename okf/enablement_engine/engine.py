"""
Open Knowledge Format (OKF) Enablement Engine
=============================================================================
File:        engine.py
Description: This script serves as an automated revenue enablement pipeline. It ingests 
             structured persona dossiers and playbook content to generate personalized 
             coaching reports via local LLM orchestration. It implements a stateful feedback 
             loop allowing managers to update learner competency profiles directly through the 
             generated reports.
Engine:      Llama 3.1 8B via Ollama
Architecture:Privacy-first, isolated multi-agent memory state machine.
             Ensures local data governance by confining processing boundaries
             entirely to host machine resources.
Author:      Adam Santone, PhD
Date:        June 2026
License:     MIT License
=============================================================================
"""

import os
import ollama

def simple_parse_md(filepath):
    """
    Parses Markdown files with YAML frontmatter.
    
    Extracts metadata keys and values, and preserves the document body 
    for LLM context.
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    metadata = {}
    body_start = 0
    in_frontmatter = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                body_start = i + 1
                break
        
        if in_frontmatter and ':' in line:
            key, val = line.split(':', 1)
            metadata[key.strip()] = val.strip().replace('[', '').replace(']', '').replace(',', '').strip()
                
    body = "".join(lines[body_start:])
    metadata['body'] = body
    return metadata

def process_manager_feedback():
    """
    Stateful Feedback Ingestion:
    Scans the /recommendations directory for manager-approved status updates.
    Updates the underlying persona YAML metadata to reflect competency mastery.
    """
    rec_dir = 'recommendations'
    for f in os.listdir(rec_dir):
        if f.endswith('_recommendations.md'):
            rec_path = os.path.join(rec_dir, f)
            with open(rec_path, 'r') as file:
                content = file.read()
            
            # Logic: Parse status tags to update learner state
            if "[STATUS: COMPLETED]" in content:
                skill_name = "cold_calling" 
                
                # Persistence: Update the source of truth (persona file)
                persona_path = os.path.join('personas', 'sdr.md')
                with open(persona_path, 'r') as p_file:
                    p_lines = p_file.readlines()
                
                with open(persona_path, 'w') as p_file:
                    for line in p_lines:
                        if 'target_skills' in line:
                            line = line.replace(skill_name, '').replace('[]', '').replace(',', '')
                        p_file.write(line)
                
                print(f"Feedback ingested: {skill_name} marked as complete for persona.")

def generate_markdown_recommendations():
    """
    Orchestration Pipeline:
    1. Ensures environment requirements are met.
    2. Processes manager feedback to update learner status.
    3. Synthesizes coaching insights using local LLM inference.
    4. Writes final instructional reports to the /recommendations directory.
    """
    # Initialize workspace
    if not os.path.exists('recommendations'):
        os.makedirs('recommendations')

    # Update state via feedback loop
    process_manager_feedback()
    
    # Load knowledge base
    personas = [simple_parse_md(os.path.join('personas', f)) for f in os.listdir('personas') if f.endswith('.md')]
    playbooks = [simple_parse_md(os.path.join('playbooks', f)) for f in os.listdir('playbooks') if f.endswith('.md')]

    # Generate personalized recommendations
    for p in personas:
        name = p.get('name')
        manager = p.get('manager', 'Not Assigned')
        md_content = f"# Personalized Recommendations for {name}\n\n"
        skills = p.get('target_skills', '').split()
        
        for skill in skills:
            for pb in playbooks:
                if pb.get('skill') == skill and pb.get('segment') == p.get('team'):
                    
                    print(f"Invoking AI Coach: {name} | Skill: {skill}...")
                    prompt = f"Write a 2-sentence coaching tip for a {p.get('role')} about {skill}."
                    
                    # Inference: Generate insights based on playbook context
                    response = ollama.chat(model='llama3.1:8b', messages=[{'role': 'user', 'content': prompt}])
                    ai_insight = response['message']['content']

                    md_content += f"### Recommended: {pb.get('skill').replace('_', ' ').title()}\n"
                    md_content += f"- **AI Coach Insight:** {ai_insight}\n\n"
                    md_content += f"- **Playbook Details:** {pb.get('body', '').strip()}\n\n"
            
        # Append managerial alignment section
        md_content += "\n---\n## Manager Review & Coaching Notes\n"
        md_content += f"**Reviewer:** {manager}\n\n"
        md_content += "> [!NOTE]\n"
        md_content += f"> Please schedule a 1:1 with {manager} by EOD Friday to discuss these recommendations. "
        md_content += "Use the 'AI Coach Insights' above as a starting point for your development plan.\n"
        
        # Write output
        output_path = os.path.join('recommendations', f"{name.lower()}_recommendations.md")
        with open(output_path, 'w') as f:
            f.write(md_content)
        
        print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    generate_markdown_recommendations()