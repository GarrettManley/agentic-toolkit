import os
import shutil
from datetime import datetime

# Configuration
WORKSPACE_ROOT = r"C:\Users\Garre\Workspace"
SKILLS_DIR = os.path.join(WORKSPACE_ROOT, ".ai", "skills")
SCRIPTS_DIR = os.path.join(WORKSPACE_ROOT, ".ai", "scripts")
TOOLKIT_OUTPUT = os.path.join(WORKSPACE_ROOT, "site", "content", "docs", "toolkit")

def publish_assets(source_dir, sub_path, title_prefix):
    output_dir = os.path.join(TOOLKIT_OUTPUT, sub_path)
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(source_dir):
        source_path = os.path.join(source_dir, filename)
        if os.path.isfile(source_path):
            with open(source_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Wrap in Hugo Frontmatter
            hugo_content = f"""---
title: "{title_prefix}: {filename}"
date: {datetime.now().strftime('%Y-%m-%d')}
draft: false
---

# {title_prefix}: {filename}

```text
{content}
```

---
*Published from .ai active toolkit.*
"""
            target_filename = filename + ".md" if not filename.endswith(".md") else filename
            with open(os.path.join(output_dir, target_filename), "w", encoding="utf-8") as f:
                f.write(hugo_content)
            print(f"📦 Published Toolkit Asset: {filename}")

if __name__ == "__main__":
    # Clean old toolkit docs
    if os.path.exists(TOOLKIT_OUTPUT):
        shutil.rmtree(TOOLKIT_OUTPUT)
    
    publish_assets(SKILLS_DIR, "skills", "Agent Skill")
    publish_assets(SCRIPTS_DIR, "scripts", "Core Script")
