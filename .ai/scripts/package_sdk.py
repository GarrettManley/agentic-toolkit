import os
import json
import shutil
from datetime import datetime

WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
MANIFEST_PATH = os.path.join(WORKSPACE_ROOT, "ai-workspace-manifest.json")
PACKAGE_DIR = os.path.join(WORKSPACE_ROOT, "dist", "agentic-sdk")

def package():
    print("📦 Packaging Agentic SDK for export...")
    
    if not os.path.exists(PACKAGE_DIR):
        os.makedirs(PACKAGE_DIR)
        
    # 1. Load Manifest
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
        
    # 2. Copy Core Directories
    core_paths = [".ai/context", ".ai/adr", ".ai/skills", ".ai/scripts"]
    for path in core_paths:
        src = os.path.join(WORKSPACE_ROOT, path)
        dst = os.path.join(PACKAGE_DIR, path)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"✅ Bundled: {path}")

    # 3. Add Timestamp
    manifest["packaged_at"] = datetime.now().isoformat()
    with open(os.path.join(PACKAGE_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"🚀 SDK packaged successfully at {PACKAGE_DIR}")

if __name__ == "__main__":
    package()
