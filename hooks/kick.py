#!/usr/bin/env python3
"""Post-compaction kick.

Runs as a Claude Code PostCompact hook. Compaction replaces the context
with a summary - the moment the recipe combo gets wiped out - so this hook
drops a flag that makes the next UserPromptSubmit anchor carry the FULL
combo (forced read + score + fresh nonce), regardless of size or cadence.

Deliberately trivial: touch one flag file, exit.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_FLAG = os.path.join(REPO, "build", ".reanchor-force")


def main():
    try:
        os.makedirs(os.path.dirname(FORCE_FLAG), exist_ok=True)
        with open(FORCE_FLAG, "w", encoding="utf-8") as f:
            f.write("kick")
    except Exception:
        pass  # fail-open: worst case the next anchor comes on cadence
    sys.stdin.read()  # consume payload, ignore
    return 0


if __name__ == "__main__":
    sys.exit(main())
