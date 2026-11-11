"""Stub child hook: sleep for argv[1] seconds, then print argv[2] (or 'slept')."""
import sys
import time

time.sleep(float(sys.argv[1]))
sys.stdout.write(sys.argv[2] if len(sys.argv) > 2 else "slept")
sys.exit(0)
