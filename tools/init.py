#!/usr/bin/env python3
"""Generate the starter build/ from example/ - no hand-copying, ever.

For each of combo.json / bans.md / voice.md / policy.json: copy example ->
build only when missing; existing files are never touched (they are your
canon). Prints what it created and what it left alone, then reminds you to
bake. TODO.md and runtime state files are yours alone, not scaffolded.

Usage: python3 tools/init.py
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTERS = ["combo.json", "bans.md", "voice.md", "policy.json"]


def init(example_dir=None, build_dir=None):
    example_dir = example_dir or os.path.join(REPO, "example")
    build_dir = build_dir or os.path.join(REPO, "build")
    created, kept = [], []
    os.makedirs(build_dir, exist_ok=True)
    for name in STARTERS:
        src = os.path.join(example_dir, name)
        dst = os.path.join(build_dir, name)
        if not os.path.exists(src):
            continue
        if os.path.exists(dst):
            kept.append(name)
        else:
            shutil.copyfile(src, dst)
            created.append(name)
    return created, kept


def main():
    created, kept = init()
    for name in created:
        print(f"已生成 build/{name}（抄自 example，改成你自己的）")
    for name in kept:
        print(f"已存在，未动：build/{name}")
    if created:
        print("下一步：改 combo.json → python3 tools/bake.py")
    else:
        print("build/ 齐了。要重新生成跑 python3 tools/bake.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
