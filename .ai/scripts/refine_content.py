import ollama
import os
import json
import re
import concurrent.futures
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
CONTENT_DIR = os.path.join(WORKSPACE_ROOT, "site", "content", "docs")
LOG_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "logs", "refinement_progress.json")
PERSONA_MATRIX_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "context", "maintenance", "refinement-personas.md")

REASONER_MODEL = "MFDoom/deepseek-r1-tool-calling:8b"
FIXER_MODEL = "qwen-orchestrator:latest"
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

def audit_and_fix(page_data, persona_name, rubric):
    """Atomic unit of work for one persona on one page."""
    filename = page_data["filename"]
    content = page_data["content"]
    
    satisfied = False
    rounds = 0
    while not satisfied and rounds < 3:
        rounds += 1
        print(f"  [RUNNING] {filename} | {persona_name} | Round {rounds}")
        
        audit_prompt = f"You are {persona_name}. Rubric: {rubric}\nAudit this: {content}\nIf perfect, respond 'STATUS: SATISFIED'. Round 1 MUST find 3 flaws."
        
        try:
            response = ollama.chat(model=REASONER_MODEL, messages=[{"role": "user", "content": audit_prompt}])
            critique = response['message']['content']
            
            if "STATUS: SATISFIED" in critique and rounds > 1:
                satisfied = True
            else:
                fix_prompt = f"Apply these fixes from {persona_name}: {critique}\nContent: {content}"
                fix_res = ollama.chat(model=FIXER_MODEL, messages=[{"role": "user", "content": fix_prompt}])
                content = fix_res['message']['content']
        except Exception as e:
            return {"status": "Error", "msg": str(e)}

    return {"status": "Complete", "persona": persona_name, "final_content": content}

def refine_page_parallel(file_path, rubrics):
    filename = os.path.basename(file_path)
    print(f"🚀 Starting Parallel Refinement: {filename}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        current_content = f.read()

    page_data = {"filename": filename, "content": current_content}
    
    # Run all 8 personas in parallel batches
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = [executor.submit(audit_and_fix, page_data, name, rubric) for name, rubric in rubrics.items()]
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res["status"] == "Complete":
                # Note: In a true multi-agent system, we would resolve conflicts.
                # For this MVP, we update the content sequentially from results.
                current_content = res["final_content"]
                print(f"  ✅ {filename} | {res['persona']} Finished.")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(current_content)

if __name__ == "__main__":
    rubrics = get_persona_rubrics()
    docs = [os.path.join(CONTENT_DIR, f) for f in os.listdir(CONTENT_DIR) if f.endswith(".md")]
    
    for doc in docs:
        refine_page_parallel(doc, rubrics)
    print("✅ All pages refined via Parallel Orchestration.")
