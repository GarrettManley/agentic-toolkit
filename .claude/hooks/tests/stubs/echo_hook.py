import sys
data = sys.stdin.buffer.read().decode("utf-8", "replace")
import os
sys.stdout.write(f"echo:len={len(data)}:cpd={os.environ.get('CLAUDE_PROJECT_DIR','')}")
sys.exit(0)
