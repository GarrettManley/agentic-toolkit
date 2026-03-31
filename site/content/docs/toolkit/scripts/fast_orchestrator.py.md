---
title: "Core Script: fast_orchestrator.py"
date: 2026-03-30
draft: false
---

# Core Script: fast_orchestrator.py

```text
import ollama
import json
import subprocess
import os
import re
from datetime import datetime

# Direct Configuration
MODEL = "qwen-orchestrator"
WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"

# Persistent State
state = {"cwd": WORKSPACE_ROOT}

SYSTEM_PROMPT = """
You are a high-fidelity Agentic Builder. 
Execute exactly one task at a time using JSON tool-calls.
Format: {"name": "host-shell.execute_command", "arguments": {"command": "X", "args": ["Y"]}}
Wait for results. Do not explain.
"""

def extract_json(text):
    # Find the outermost { and } to capture the full object
    start = text.find("{")
    if start == -1:
        return text.strip()
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                # Found the true end of the first object
                return text[start:i+1]
    
    return text[start:].strip()

def execute_host_command(command, args=None):
    full_args = args or []
    if command == "cd" and full_args:
        new_path = os.path.abspath(os.path.join(state["cwd"], full_args[0]))
        if os.path.exists(new_path):
            state["cwd"] = new_path
            return {"stdout": f"Changed directory to {new_path}", "exit_code": 0}
        return {"error": f"Directory not found: {new_path}"}

    full_cmd = f"{command} {' '.join(full_args)}"
    print(f"🛠️ Executing: {full_cmd} in {state['cwd']}")
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=state["cwd"], shell=True)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def fast_loop(prompt, max_rounds=10):
    print(f"⚡ Fast-Path: {MODEL}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    for i in range(max_rounds):
        print(f"🔄 Round {i+1}...")
        response = ollama.chat(model=MODEL, messages=messages)
        content = response['message']['content']
        
        json_str = extract_json(content)
        
        if '"name":' in json_str:
            try:
                tool_call = json.loads(json_str)
                name = tool_call["name"]
                args = tool_call.get("arguments", {})
                
                result = execute_host_command(args.get("command"), args.get("args"))
                messages.append(response['message'])
                messages.append({"role": "user", "content": f"Tool Result: {json.dumps(result)}"})
                continue
            except Exception as e:
                print(f"❌ Parse Error: {e}")
                print(f"DEBUG JSON: {json_str}")
        
        return content

if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "Build the site"
    print(fast_loop(p))

```

---
*Published from .ai active toolkit.*
