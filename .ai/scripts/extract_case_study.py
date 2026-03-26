import os
import re
import json
from datetime import datetime

WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
ADR_DIR = os.path.join(WORKSPACE_ROOT, ".ai", "adr")
PERFORMANCE_LOG = os.path.join(WORKSPACE_ROOT, ".ai", "context", "maintenance", "model-performance.md")

def extract_trace(adr_id):
    """
    Parses an ADR and substantiates it with execution evidence 
    and citations for high-fidelity documentation.
    """
    adr_file = f"{adr_id}.md" if not adr_id.endswith(".md") else adr_id
    path = os.path.join(ADR_DIR, adr_file)
    
    if not os.path.exists(path):
        return {"error": f"ADR {adr_id} not found."}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Extract Core Metadata
    title = re.search(r"# (.*)", content).group(1)
    status = re.search(r"Status:\s*(.*)", content).group(1)
    
    # 2. Extract Evidence & Citations
    evidence = re.search(r"## Verification \(The Proof\)\n(.*?)\n##", content, re.DOTALL)
    citations = re.search(r"### Scientific Substantiation.*?\n(.*?)\n##", content, re.DOTALL)

    trace = {
        "title": title,
        "adr_id": adr_id,
        "status": status,
        "substantiation": {
            "evidence": evidence.group(1).strip() if evidence else "Pending verification.",
            "citations": citations.group(1).strip() if citations else "Baseline standard."
        },
        "extracted_at": datetime.now().isoformat()
    }
    
    return trace

if __name__ == "__main__":
    # Test with ADR 002 (our most substantiated record)
    result = extract_trace("002-local-orchestration.md")
    print(json.dumps(result, indent=2))
