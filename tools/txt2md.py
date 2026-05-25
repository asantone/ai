import os
import ollama

# Configuration
INPUT_DIR = "./txt"   # Path to your converted files
OUTPUT_DIR = "./markdown" # Where you want the fixed files to go
MODEL_NAME = "gemma3:4b"             # The Ollama model you want to use

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# System prompt to give the local LLM its instructions
# SYSTEM_PROMPT = """
#You are a precise technical content engineer. Your job is to take poorly formatted, messy text extracted from a corporate document and convert it into clean, well-structured Markdown.

#Strict Rules:
#1. Identify natural sections (e.g., about the company, job requirements, benefits) and use appropriate markdown headers (##, ###).
#2. Fix broken bulleted or numbered lists. If lines are meant to be list items but lack syntax, format them cleanly using '*' or numbers.
#3. Fix arbitrary line breaks or text that got smashed together.
#4. DO NOT change, rewrite, summarize, or omit any words or content. Only fix the structural layout and markdown syntax.
#5. Return ONLY the final markdown content. Do not include introductory text, conversational fluff, or markdown code block backticks (```).
#"""

SYSTEM_PROMPT = """
Convert this raw text into clean Markdown by finding and formatting the headings and bullet points. Be sure to include the Company name, the job title, the salary range (if known), and whether the position is remote, hybrid, or on-site. Do not add commentary or introductory text. Just output the clean markdown.
"""

def clean_file(file_path, file_name):
    print(f"Processing: {file_name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        messy_text = f.read()

    # Construct the user prompt using file details for context
    user_content = f"File context: {file_name}\n\n--- MESSY TEXT START ---\n{messy_text}\n--- MESSY TEXT END ---"

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            options={
                "temperature": 0.1,    # Keeps it strict and accurate
                "num_ctx": 4096,       # Caps the look-back memory
                "num_predict": 1500    # <-- CRITICAL: Prevents it from running away forever
            }
        )
        
        cleaned_text = response['message']['content']
        
        # Save the clean file
        output_path = os.path.join(OUTPUT_DIR, file_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        print(f"Successfully cleaned and saved to {output_path}")

    except Exception as e:
        print(f"Error processing {file_name}: {e}")

def main():
    for file_name in os.listdir(INPUT_DIR):
        # Process files (assuming you ran them through pandoc/txt conversion first)
        if file_name.endswith(('.md', '.txt')):
            file_path = os.path.join(INPUT_DIR, file_name)
            clean_file(file_path, file_name)

if __name__ == "__main__":
    main()