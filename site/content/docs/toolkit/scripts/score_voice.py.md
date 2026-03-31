---
title: "Core Script: score_voice.py"
date: 2026-03-30
draft: false
---

# Core Script: score_voice.py

```text
import os
import json
from datetime import datetime

# NOTE: This script will be invoked by the main agent using the 'generalist' 
# or direct cloud tool to avoid local model bias in qualitative scoring.

def get_vibe_score(content):
    """
    PROMPT FOR CLOUD MODEL (Gemini 2.0 Pro):
    Analyze the following documentation for 'Agent-Cluster Vibe'.
    Score 0-100 on these dimensions:
    1. Cohesion (Does it flow like a single human author?)
    2. Authority (Does it sound like a Senior Architect?)
    3. Directness (Is it free of flowery preambles and conclusion filler?)
    
    Return a JSON object: {"total_score": X, "flaws": ["..."], "agentisms": ["..."]}
    """
    pass # To be executed via the agent's cloud context

def audit_site_vibe():
    content_dir = r"C:\Users\Garre\Workspace\site\content\docs"
    # Placeholder for the resulting report
    report = {
        "timestamp": datetime.now().isoformat(),
        "scores": []
    }
    # (Logic to read files and trigger cloud audit...)
    print("🚀 Qualitative Vibe Audit Initialized.")

if __name__ == "__main__":
    audit_site_vibe()

```

---
*Published from .ai active toolkit.*
