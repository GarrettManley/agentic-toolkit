---
title: "Core Script: evolve_personas.py"
date: 2026-03-30
draft: false
---

# Core Script: evolve_personas.py

```text
import ollama
import os
import re
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
PERSONA_MATRIX_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "context", "maintenance", "refinement-personas.md")
DETAIL_LOG_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "logs", "refinement_details.log")

def evolve():
    print("🧠 Starting Meta-Learning: Evolving Persona Rubrics...")
    
    if not os.path.exists(DETAIL_LOG_PATH):
        print("❌ No audit logs found to learn from.")
        return

    with open(DETAIL_LOG_PATH, "r", encoding="utf-8") as f:
        logs = f.read()
        
    with open(PERSONA_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = f.read()

    # TASK: Analyze logs and propose new rubric items
    evolution_prompt = f"""
    You are the Meta-Architect. 
    Review the following adversarial audit logs and the current Persona Matrix.
    
    LOGS:
    {logs[:5000]} # Truncated for token safety
    
    MATRIX:
    {matrix}
    
    TASK:
    Identify new, specific validation rules that should be added to each persona's rubric based on their recent critiques. 
    Focus on closing the gaps they identified (e.g., missing verification commands, vague business value).
    
    Format your response as a series of specific rubric updates.
    """
    
    response = ollama.chat(model="MFDoom/deepseek-r1-tool-calling:8b", messages=[{"role": "user", "content": evolution_prompt}])
    suggestions = response['message']['content']
    
    print("✨ New insights identified by local model.")
    
    # Surgical update of the matrix
    # For the MVP, we append the "Lessons Learned" to the matrix
    with open(PERSONA_MATRIX_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n\n## Evolution Log: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(suggestions)
        
    print(f"✅ Persona Matrix evolved and saved to {PERSONA_MATRIX_PATH}")

if __name__ == "__main__":
    evolve()

```

---
*Published from .ai active toolkit.*
