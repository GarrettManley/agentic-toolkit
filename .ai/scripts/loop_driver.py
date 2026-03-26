import requests
import json
import time

BRIDGE_URL = "http://localhost:8000/api/chat"

def run_agentic_task(model, prompt, max_rounds=5):
    print(f"🤖 Starting autonomous task with {model}...")
    messages = [{"role": "user", "content": prompt}]
    
    for round_num in range(max_rounds):
        print(f"🔄 Round {round_num + 1}...")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        response = requests.post(BRIDGE_URL, json=payload, timeout=60)
        if response.status_code != 200:
            return f"❌ Bridge Error: {response.status_code}"
            
        result = response.json()
        message = result.get("message", {})
        content = message.get("content", "")
        
        # Check if the content is a JSON tool call
        try:
            tool_call = json.loads(content)
            if "name" in tool_call and "arguments" in tool_call:
                print(f"🛠️ Tool Call Detected: {tool_call['name']}")
                
                # Execute the tool via the bridge (if the bridge supports direct tool execution)
                # Note: Since the bridge is a proxy, we actually need to send the tool call to the /mcp/execute endpoint if available
                # or handle it via the specialized tool-calling logic.
                
                # To be "Best-in-Class", we'll feed this back to the user/cloud agent 
                # OR if the bridge doesn't execute, we'll need to call the MCP server directly here.
                
                # FOR NOW: We return the tool call to the cloud agent to show we detected the intent.
                return content
        except:
            pass
            
        # If it's final text, we're done
        if not content.startswith("{"):
            print("✅ Task Complete.")
            return content
            
        messages.append(message)
        
    return "⚠️ Loop Limit Reached."

if __name__ == "__main__":
    # Example usage
    print(run_agentic_task("qwen-orchestrator", "List files in workspace."))
