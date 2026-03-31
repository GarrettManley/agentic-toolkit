---
title: "Core Script: scrub_emojis.py"
date: 2026-03-30
draft: false
---

# Core Script: scrub_emojis.py

```text
import os
import re

# Comprehensive Emoji Regex
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map symbols
    "\U0001f1e0-\U0001f1ff"  # flags (iOS)
    "\U00002702-\U000027b0"
    "\U000024c2-\U0001f251"
    "]+", flags=re.UNICODE
)

# Configuration
CONTENT_DIR = r"C:\Users\Garre\Workspace\site\content"

def scrub_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove emojis
    clean_content = EMOJI_PATTERN.sub("", content)
    
    # Remove any resulting double spaces or weird artifacts from emoji removal
    clean_content = re.sub(r'  +', ' ', clean_content)
    
    if clean_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_content)
        print(f"✨ Scrubbed: {file_path}")

if __name__ == "__main__":
    for root, dirs, files in os.walk(CONTENT_DIR):
        for file in files:
            if file.endswith(".md"):
                scrub_file(os.path.join(root, file))

```

---
*Published from .ai active toolkit.*
