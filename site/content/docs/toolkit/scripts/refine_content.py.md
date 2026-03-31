---
title: "Core Script: refine_content.py"
date: 2026-03-30
draft: false
---

# Core Script: refine_content.py

```text
import ollama
import os
import json
import re
import concurrent.futures
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
CONTENT_DIR = os.path.join(WORKSPACE_ROOT, "site", "content", "docs")
PERSONA_MATRIX_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "context", "maintenance", "refinement-personas.md")

# Models
LOCAL_AUDITOR = "MFDoom/deepseek-r1-tool-calling:8b"
MAX_PARALLEL = 4

def get_persona_rubrics():
    with open(PERSONA_MATRIX_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    personas = {}
    blocks = re.split(r"### 🎭 ", content)
    for block in blocks[1:]:
        lines = block.split("\n")
        name = lines[0].split("(")[0].strip()
        checklist = "\n".join([l for l in lines if l.startswith("- [ ]") or l.startswith("- **New Rule**")])
        personas[name] = checklist
    return personas

def local_audit(content, persona_name, rubric):
    """Local DeepSeek identifies flaws without modifying content."""
    prompt = f"""
    You are {persona_name}. Technical Auditor.
    Rubric: {rubric}
    
    TASK: Find technical gaps, voice drift, or structural flaws in the content below.
    If perfect, respond 'STATUS: SATISFIED'. 
    Otherwise, provide a BRUTAL bulleted list of fixes. Do not offer solutions, only identify the problems.
    
    Content:
    {content}
    """
    try:
        response = ollama.chat(model=LOCAL_AUDITOR, messages=[{"role": "user", "content": prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Error auditing {persona_name}: {str(e)}"

def hybrid_refine(file_path, rubrics):
    filename = os.path.basename(file_path)
    print(f"🧬 HYBRID REFINEMENT: {filename}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # 1. LOCAL AUDIT PHASE (Parallel)
    print(f"  🔍 Collecting local critiques from 8 personas...")
    all_critiques = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {executor.submit(local_audit, original_content, name, rubrics[name]): name for name in rubrics}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            critique = future.result()
            if "STATUS: SATISFIED" not in critique:
                all_critiques.append(f"CRITIQUE FROM {name}:\n{critique}")

    if not all_critiques:
        print(f"  ✅ {filename} is already perfect. Skipping cloud rewrite.")
        return

    # 2. CLOUD SYNTHESIS PHASE
    print(f"  ☁️ Sending critiques to Gemini 2.0 Pro for authoritative synthesis...")
    # NOTE: The actual rewrite call will be performed by the 'Gemini CLI' orchestrator
    # This script will output the 'Synthesis Prompt' for the main agent to handle.
    
    synthesis_prompt = f"""
    You are Garrett Manley. Expert Agentic Architect.
    
    TASK: Rewrite the following documentation to satisfy the expert critiques provided.
    
    STRICT CONSTRAINTS:
    - Voice: Direct, technical, minimalist, authoritative.
    - Format: High-fidelity Markdown. No preambles like "Here is the fixed version."
    - Authorship: Must be 'Garrett Manley'. Remove all agent footers.
    - Commands: Use PowerShell 7 syntax.
    
    CRITIQUES TO ADDRESS:
    {chr(10).join(all_critiques)}
    
    ORIGINAL CONTENT:
    {original_content}
    """
    
    # Save the prompt for the main agent to execute (since this script is local)
    prompt_path = os.path.join(WORKSPACE_ROOT, ".ai", "logs", f"synthesis_prompt_{filename}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(synthesis_prompt)
    
    print(f"  📦 Synthesis Prompt saved to {prompt_path}. Main agent must execute.")

if __name__ == "__main__":
    rubrics = get_persona_rubrics()
    docs = [os.path.join(CONTENT_DIR, f) for f in os.listdir(CONTENT_DIR) if f.endswith(".md")]
    for doc in docs:
        hybrid_refine(doc, rubrics)

```

---
*Published from .ai active toolkit.*
