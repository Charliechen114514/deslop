#!/usr/bin/env python3
"""Bake build/style.md from build/combo.json - the compiler for your combo.

style.md used to be hand-written: routing header plus @-pointer lines
maintained by hand, and they drifted (the header said one thing, the
pointer list another). Now combo.json is the single source of truth and
this script compiles the finished bundle: an auto-generated routing header
followed by the FULL TEXT of every chosen layer, lint blocks stripped.
The model (or a tool importing the file) reads ONE file instead of
thirteen. Compile-time checks enforce the constitution:

  - a tone dimension may only have one dial (mutual exclusion is structural),
  - persona is a single card name under build/personas/ (you wear one at a time),
  - every referenced file must exist,
  - unknown dimensions / dials / layers are hard errors,
  - a tone dimension you did not pick is reported (that just means no opinion).

Usage:
  python3 tools/bake.py          # write build/style.md
  python3 tools/bake.py --check  # validate only, write nothing

The generated file is a build artifact: never hand-edit it, edit
build/combo.json and re-bake.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBO = os.path.join(REPO, "build", "combo.json")
STYLE = os.path.join(REPO, "build", "style.md")

BASE_CLARITY = os.path.join(REPO, "recipes", "base", "clarity.md")
FLAWS_DIR = os.path.join(REPO, "recipes", "flaws")
TONES_DIR = os.path.join(REPO, "recipes", "tones")
SCENES_DIR = os.path.join(REPO, "recipes", "scenes")
PERSONAL_DIR = os.path.join(REPO, "build")

PRIORITY_LINE = "冲突时：我当场说的话 > 宿主项目规则 > 这套配方。"

LINT_BLOCK = re.compile(r"```lint\n.*?\n```", re.S)
LINT_PLACEHOLDER = "（机械判罚块，略）"
# "## 来源" sections are provenance for maintainers; the canon lives in
# ACKNOWLEDGMENTS.md and must not ride the model context.
SOURCE_SECTION = re.compile(r"\n## 来源\n.*?(?=\n## |\n----- |\Z)", re.S)


def strip_meta(text):
    """Remove content that is for maintainers, not for the wearing model."""
    text = LINT_BLOCK.sub(LINT_PLACEHOLDER, text)
    return SOURCE_SECTION.sub("", text)


def discover_tone_dims(tones_dir=None):
    """Scan tones/ into {dimension: {dial: path}}; new dials are picked up automatically."""
    tones_dir = tones_dir or TONES_DIR
    dims = {}
    for fn in sorted(os.listdir(tones_dir)):
        if not fn.endswith(".md") or "-" not in fn:
            continue
        stem = fn[:-3]
        dim, dial = stem.split("-", 1)
        dims.setdefault(dim, {})[dial] = os.path.join(tones_dir, fn)
    return dims


def layer_desc(path):
    """One-line description from the layer title: after '：', before '（'."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    title = line[1:].strip()
                    if "：" in title:
                        title = title.split("：", 1)[1]
                    if "（" in title:
                        title = title.split("（", 1)[0]
                    return title.strip()
    except OSError:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def resolve(combo, repo=None):
    """Turn combo.json into an ordered [(group, desc, path)] list. Raises on violations."""
    repo = repo or REPO
    tones_dir = os.path.join(repo, "recipes", "tones")
    tone_dims = discover_tone_dims(tones_dir)
    errors = []

    def must_exist(path, what):
        if not os.path.isfile(path):
            errors.append(f"{what} 不存在：{path}")

    out = [("基座", "clarity（宪法加通则）", os.path.join(repo, "recipes", "base", "clarity.md"))]

    persona = combo.get("persona")
    if persona:
        if not isinstance(persona, str):
            errors.append("persona 是单值键（一次只穿一套人格），收到列表或对象")
        else:
            p = os.path.join(repo, "build", "personas", persona + ".md")
            must_exist(p, f"人格卡 {persona}")
            out.append(("人格", layer_desc(p), p))

    for name in combo.get("flaws", []):
        p = os.path.join(repo, "recipes", "flaws", name + ".md")
        must_exist(p, f"病灶层 {name}")
        out.append(("病灶", layer_desc(p), p))

    tones = combo.get("tones", {})
    for dim in tones:
        if dim not in tone_dims:
            errors.append(f"未知腔调维度：{dim}（可用：{ '、'.join(sorted(tone_dims)) }）")
    for dim, dials in sorted(tone_dims.items()):
        pick = tones.get(dim)
        if pick is None:
            continue  # no opinion on this dimension - legal, reported by caller
        if not isinstance(pick, str) or pick not in dials:
            errors.append(f"{dim} 没有档位 {pick}（可选：{'、'.join(sorted(dials))}）")
            continue
        p = dials[pick]
        out.append(("腔调", layer_desc(p), p))

    for name in combo.get("scenes", []):
        p = os.path.join(repo, "recipes", "scenes", name + ".md")
        must_exist(p, f"场景层 {name}")
        out.append(("场景", layer_desc(p), p))

    for name in combo.get("personal", []):
        p = os.path.join(repo, "build", name + ".md")
        must_exist(p, f"个人层 {name}")
        out.append(("个人层", layer_desc(p), p))

    if errors:
        raise ValueError("；".join(errors))
    unpicked = [d for d in sorted(tone_dims) if d not in tones]
    return out, unpicked


def render_style(files):
    """Assemble the baked bundle: routing header + full text of every layer."""
    lines = ["# 组合（由 tools/bake.py 生成；改 build/combo.json 再重跑，别手改本文件）", ""]
    by_group = {}
    for group, desc, _ in files:
        by_group.setdefault(group, []).append(desc)
    route = "；".join(f"{g}：{'、'.join(ds)}" for g, ds in by_group.items())
    lines.append(f"路由：{route}。{PRIORITY_LINE}")
    lines.append("")
    for group, desc, p in files:
        lines.append(f"----- {desc}（{os.path.basename(p)}）-----")
        try:
            with open(p, encoding="utf-8") as f:
                content = f.read().rstrip()
        except OSError:
            content = f"（读不到：{p}）"
        lines.append(strip_meta(content))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    check_only = "--check" in sys.argv
    try:
        with open(COMBO, encoding="utf-8") as f:
            combo = json.load(f)
    except Exception as err:
        print(f"combo.json 读不到或不是合法 JSON：{err}", file=sys.stderr)
        return 2
    try:
        files, unpicked = resolve(combo)
    except ValueError as err:
        print("编译失败：" + str(err), file=sys.stderr)
        return 2
    if unpicked:
        print("提示：这些维度没选，等于没意见：" + "、".join(unpicked))
    if check_only:
        print(f"检查通过：{len(files)} 层。")
        return 0
    with open(STYLE, "w", encoding="utf-8") as f:
        f.write(render_style(files))
    print(f"已生成 {STYLE}（{len(files)} 层）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
