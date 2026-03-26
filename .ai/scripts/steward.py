import os
import re
import subprocess
from datetime import datetime

WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
CONTEXT_DIR = os.path.join(WORKSPACE_ROOT, ".ai", "context")
TEMPLATE_PATH = os.path.join(WORKSPACE_ROOT, ".ai", "templates", "morning-briefing.md")
BRIEFING_DIR = os.path.join(WORKSPACE_ROOT, "docs", "superpowers", "maintenance")

def run_audit():
    print("🚀 Starting Nightly Steward Audit (Python)...")
    
    verified_files = []
    drifts = []
    
    if not os.path.exists(BRIEFING_DIR):
        os.makedirs(BRIEFING_DIR)

    # 1. Perform Drift Check
    for root, _, files in os.walk(CONTEXT_DIR):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract verification_cmd using regex
                match = re.search(r'verification_cmd:\s*"(.*)"', content)
                if match:
                    cmd = match.group(1)
                    print(f"🔍 Verifying: {file} -> {cmd}")
                    
                    try:
                        # Execute command via PowerShell on Windows for better compatibility
                        full_cmd = f'powershell -ExecutionPolicy Bypass -Command "{cmd}"' if os.name == "nt" else cmd
                        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            verified_files.append(f"- [x] {file}: Verified successfully.")
                        else:
                            raise Exception(result.stderr or result.stdout)
                    except Exception as e:
                        print(f"⚠️ Drift detected in {file}")
                        drifts.append({
                            "file": file,
                            "issue": f"Verification failed: {str(e).strip()}",
                            "fix": "Manual review required to update Truth File or fix code."
                        })

    # 2. Horizon Scan
    try:
        from scan_horizon import scan
        horizon_results = scan()
    except Exception as e:
        horizon_results = f"Horizon scan failed: {str(e)}"

    # 3. Generate Morning Briefing
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            report = f.read()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        status = "✅ PASS" if not drifts else "⚠️ DRIFT"
        
        report = report.replace("{{DATE}}", now)
        report = report.replace("{{AUDIT_STATUS}}", status)
        
        verified_str = "\n".join(verified_files) if verified_files else "No files verified."
        report = report.replace("- [ ] {{FILE_NAME}}: {{SUMMARY_OF_CHANGE}}", verified_str)
        
        report = report.replace("- [ ] {{DISCOVERY_NAME}}: {{DISCOVERY_URL}}", horizon_results)
        
        drift_str = ""
        if drifts:
            for d in drifts:
                drift_str += f"- **Issue**: {d['issue']}\n  - **Source**: {d['file']}\n  - **Proposed Fix**: {d['fix']}\n\n"
        else:
            drift_str = "No drift detected."
        
        report = report.replace("- **Issue**: {{DRIFT_DESCRIPTION}}\n- **Source**: {{FILE_PATH}}\n- **Proposed Fix**: {{FIX_PLAN}}", drift_str)
        
        briefing_file = os.path.join(BRIEFING_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-briefing.md")
        with open(briefing_file, "w", encoding="utf-8") as f:
            f.write(report)
            
        print(f"✅ Audit complete. Morning Briefing generated at {briefing_file}")
    else:
        print(f"❌ Error: Template not found at {TEMPLATE_PATH}")

if __name__ == "__main__":
    run_audit()
