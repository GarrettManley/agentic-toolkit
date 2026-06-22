"""sandbox_doctor — verify docker engine is reachable in WSL2 and base images are present.

Fail-closed: if `wsl -e docker info` fails, returns ok=False (callers must not run
sandboxed work). Missing images are pulled (Docker Hub — setup-time infrastructure)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
for _p in (str(SCRIPTS_DIR), str(SCRIPTS_DIR.parent / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sandbox._images import ECOSYSTEMS  # noqa: E402


def _run(runner, argv):
    return runner(["wsl", "-e", "docker", *argv], capture_output=True, text=True)


def sandbox_doctor(*, runner=subprocess.run) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    try:
        info = _run(runner, ["info"])
    except (FileNotFoundError, OSError) as e:
        return False, [f"docker not invokable via WSL2: {e}"]
    if getattr(info, "returncode", 1) != 0:
        return False, [f"docker daemon unreachable in WSL2: {getattr(info, 'stderr', '')[:200]}"]
    msgs.append("docker reachable in WSL2")

    for eco, meta in ECOSYSTEMS.items():
        image = meta["image"]
        inspect = _run(runner, ["image", "inspect", image])
        if getattr(inspect, "returncode", 1) != 0:
            pull = _run(runner, ["pull", image])
            if getattr(pull, "returncode", 1) != 0:
                return False, msgs + [f"failed to pull {image}: {getattr(pull, 'stderr', '')[:200]}"]
            msgs.append(f"pulled {image}")
        else:
            msgs.append(f"{image} present")
    return True, msgs


def main(argv=None) -> int:
    ok, msgs = sandbox_doctor()
    for m in msgs:
        print(("OK: " if ok else "") + m)
    if not ok:
        print("SANDBOX NOT READY — install docker engine in WSL2 (see "
              "docs/superpowers/specs/2026-06-22-stage4a-sandbox-design.md §8).", file=sys.stderr)
        return 1
    print("Sandbox ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
