---
title: "Core Script: publish_toolkit.py"
date: 2026-03-30
draft: false
---

# Core Script: publish_toolkit.py

```text
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
    
    # Use walk to find all files recursively
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            source_path = os.path.join(root, filename)
            
            # Determine relative path for better titling/structuring
            rel_path = os.path.relpath(source_path, source_dir)
            
            with open(source_path, "r", encoding="utf-8") as f:
                try:
                    content = f.read()
                except UnicodeDecodeError:
                    continue # Skip binary files
            
            # Wrap in Hugo Frontmatter
            display_title = rel_path.replace("\\", " / ")
            hugo_content = f"""---
title: "{title_prefix}: {display_title}"
date: {datetime.now().strftime('%Y-%m-%d')}
draft: false
---

# {title_prefix}: {display_title}

```text
{content}
```

---
*Published from .ai active toolkit.*
"""
            # Create subdirectories in output if needed
            target_rel_dir = os.path.dirname(rel_path)
            target_output_dir = os.path.join(output_dir, target_rel_dir)
            os.makedirs(target_output_dir, exist_ok=True)
            
            target_filename = filename + ".md" if not filename.endswith(".md") else filename
            with open(os.path.join(target_output_dir, target_filename), "w", encoding="utf-8") as f:
                f.write(hugo_content)
            print(f"📦 Published Toolkit Asset: {rel_path}")

if __name__ == "__main__":
    # Clean old toolkit docs
    if os.path.exists(TOOLKIT_OUTPUT):
        shutil.rmtree(TOOLKIT_OUTPUT)
    
    publish_assets(SKILLS_DIR, "skills", "Agent Skill")
    publish_assets(SCRIPTS_DIR, "scripts", "Core Script")

```

---
*Published from .ai active toolkit.*
