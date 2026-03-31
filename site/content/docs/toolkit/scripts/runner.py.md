---
title: "Core Script: runner.py"
date: 2026-03-30
draft: false
---

# Core Script: runner.py

```text
import json
import requests
import time

BRIDGE_URL = "http://localhost:8000/api/chat"

def run_loop(model, prompt, max_rounds=5):
    print(f"🚀 Starting Local Agent Loop for: {model}")
    messages = [{"role": "user", "content": prompt}]
    
    for i in range(max_rounds):
        print(f"🔄 Round {i+1}...")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        response = requests.post(BRIDGE_URL, json=payload, timeout=120)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
            
        res_data = response.json()
        content = res_data["message"]["content"]
        
        # In a real 'Loop Driver', we would check for tool_calls metadata.
        # But since our bridge returns JSON in content, we parse the content.
        if content.strip().startswith("{") and '"name":' in content:
            try:
                # This is where the magic happens: the runner executes the tool
                # and feeds it back. For this setup, we'll return the intent
                # to show the 'Cloud Architect' what was planned.
                print(f"🛠️ Agent requested: {content}")
                return content
            except:
                pass
        
        if "I cannot" not in content and "Error" not in content:
            return content
            
        messages.append(res_data["message"])
        
    return "Loop limit reached."

if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Build the site"
    print(run_loop("qwen-orchestrator", prompt))

```

---
*Published from .ai active toolkit.*
