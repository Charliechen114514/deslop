#!/usr/bin/env python3
"""Mechanical word-form linter engine. Follows the combo in build/style.md.

Usage:
  python3 checks/lint.py some.md       # lint a file against the current combo
  cat some.md | python3 checks/lint.py
  python3 checks/lint.py --layers a.md,b.md some.md   # ad-hoc layers, skip style.md
  python3 checks/lint.py --self-test
  python3 checks/lint.py --report

The engine only understands two kinds of data, both living in markdown:
  1. Word tables - any table with a "禁 | 改成" header, one rule per row
     (error level: hit means rewrite).
  2. lint blocks - a ```lint fence, one rule per line:
     regex ## rule note ## level  (level: review = candidate, semantics decide;
     error = hard hit).
Only installed layers are linted. Third-party layers ship their own lint
blocks and are picked up automatically, no code changes.
"md is the canon, the script is the executor."
Exit codes: 0 clean or review-only, 2 has error hits, 3 self-test failed.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE = os.path.join(REPO, "build", "style.md")
COMBO = os.path.join(REPO, "build", "combo.json")

# Rows whose banned cell carries a semantic condition are skipped here:
# they are the model's job, not regex's.
SEMANTIC_MARKERS = ("当标签用",)
LINT_FENCE = re.compile(r"```lint\n(.*?)```", re.S)


# Named condition vocabulary: mechanical refinements the table can cite.
# Unknown names degrade the row to semantic (skipped mechanically) with a warning.
import warnings

CONDITIONS = {
    "仅当标签": lambda line: re.search(r"结论[：:]", line) is not None,
    "除非真实顺序": lambda line: not re.search(r"先.{0,12}再", line),
}


def load_combo():
    """Active layer files: combo.json resolved via tools.bake (canon), else
    legacy @-pointer lines of style.md."""
    if os.path.exists(COMBO):
        try:
            sys.path.insert(0, REPO)
            from tools.bake import resolve
            with open(COMBO, encoding="utf-8") as f:
                combo = json.load(f)
            files, _ = resolve(combo)
            return [p for _, _, p in files]
        except Exception as err:
            print(f"（警告：combo.json 解析失败，回退 @ 指针：{err}）", file=sys.stderr)
    files = []
    if os.path.exists(STYLE):
        with open(STYLE, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith("@"):
                    p = s[1:].strip()
                    if os.path.exists(p):
                        files.append(p)
                    else:
                        print(f"（警告：指针指向不存在的文件，跳过 {p}）", file=sys.stderr)
    return files


def parse_word_tables(files):
    """Extract "禁 | 改成" tables from layer files into word-form rules."""
    rules = []
    for path in files:
        in_code = False
        header_seen = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or not line.strip().startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0] == "禁" and "改成" in cells[1]:
                    header_seen = True
                    continue
                if not header_seen:
                    continue
                if set(cells[0]) <= {"-", ":"} or not cells[0]:
                    continue
                if any(m in cells[0] for m in SEMANTIC_MARKERS):
                    continue  # semantic condition, not mechanically decidable
                cond_name = cells[2].strip() if len(cells) > 2 else ""
                if cond_name and cond_name not in CONDITIONS:
                    print(f"（警告：未知条件「{cond_name}」，该行降回语义层）", file=sys.stderr)
                    continue
                parts = re.split(r"[（）、，]", cells[0])
                words = {p.strip() for p in parts
                         if p.strip() and "一切" not in p and "任何" not in p and "单字" not in p}
                if words:
                    rules.append((os.path.basename(path), cells[0],
                                  sorted(words, key=len, reverse=True),
                                  CONDITIONS.get(cond_name)))
    return rules


def parse_lint_blocks(files):
    """Extract ```lint fenced blocks from layer files into regex rules."""
    rules = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in LINT_FENCE.finditer(text):
            for line in m.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("##")]
                if len(parts) != 3:
                    continue
                pattern, note, level = parts
                try:
                    rules.append((note, re.compile(pattern), level, os.path.basename(path)))
                except re.error as err:
                    print(f"（警告：{path} 里坏正则，跳过：{pattern}（{err}）", file=sys.stderr)
    return rules


def compile_rows(word_rules):
    """Compile word lists into one alternation regex per table row."""
    out = []
    for row in word_rules:
        src, cell, words = row[0], row[1], row[2]
        cond = row[3] if len(row) > 3 else None
        pat = re.compile("|".join(re.escape(w) for w in words))
        out.append((src, cell, pat, cond))
    return out


QUOTE_SPAN = re.compile(r"「[^」]*」|“[^”]*”|\"[^\"]*\"|`[^`]*`")


def lint_text(text, rows, patterns):
    """Return hits as [(level, lineno, matched_text, source)]. Skips fenced code.

    Quoted spans (「…」, curly quotes, straight quotes, backticks) are exempt
    from word-TABLE checks only - quoting and discussing the words themselves
    is the documented boundary - while pattern checks (review) still apply.
    """
    hits = []
    in_code = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        quote_free = QUOTE_SPAN.sub("", line)
        for row in rows:
            src, cell, pat = row[0], row[1], row[2]
            cond = row[3] if len(row) > 3 else None
            for m in pat.finditer(quote_free):
                if cond is not None and not cond(line):
                    continue
                hits.append(("error", lineno, m.group(0), f"{src} 词表：{cell}"))
        for note, pat, level, src in patterns:
            for m in pat.finditer(line):
                hits.append((level, lineno, m.group(0), f"{src} {note}"))
    # 破折号限额：anti-ai 第10条"单用一轮最多一次"，数数即可执行
    code_stripped = "\n".join(l for l in text.splitlines()
                              if not l.strip().startswith("```"))
    total_dashes = code_stripped.count("——")
    if total_dashes > 1:
        hits.append(("review", 1, f"——×{total_dashes}", "破折号超限（一轮最多一次）｜anti-ai 第10条"))

    seen, dedup = set(), []
    for h in hits:
        key = (h[1], h[2], h[3])
        if key not in seen:
            seen.add(key)
            dedup.append(h)
    return dedup


def build(args):
    """Assemble (rows, patterns, remaining_args) from --layers or the combo."""
    if "--layers" in args:
        i = args.index("--layers")
        files = [p for p in args[i + 1].split(",") if os.path.exists(p)]
        rest = args[:i] + args[i + 2:]
    else:
        files = load_combo()
        rest = args
    return compile_rows(parse_word_tables(files)), parse_lint_blocks(files), rest


def self_test(rows, patterns):
    ok = True

    def expect(name, cond):
        nonlocal ok
        print(("  ✓ " if cond else "  ✗ ") + name)
        ok = ok and cond

    print(f"组合加载：词表规则 {len(rows)} 行，lint 正则 {len(patterns)} 条")
    expect("词表 ≥ 20 行", len(rows) >= 20)
    expect("lint 正则 ≥ 10 条", len(patterns) >= 10)

    samples = [
        ("我们先说结论：这个方案没坑，直接干。", "error", "先"),
        ("这不是配置的问题，而是权限的问题。", "review", "平衡"),
        ("综上所述，未来充满无限可能。", "review", "综上"),
        ("本周持续赋能业务，拉通上下游。", "review", "赋能"),
        ("这方案清晰、简洁、有力、专业。", "review", "串珠"),
        ("对这一份配置文件进行了一次检查。", "review", "假冠词"),
    ]
    for text, want_level, want_word in samples:
        hits = lint_text(text, rows, patterns)
        got = any(want_word in h[3] or want_word in h[2] for h in hits)
        level_ok = any(h[0] == want_level for h in hits) or want_level == "review"
        print(f"  样本：{text}")
        expect(f"  命中 [{want_word}] 且存在 {want_level} 级", got and level_ok)
    return ok


def main():
    args = sys.argv[1:]
    rows, patterns, args = build(args)

    if "--report" in args:
        print(f"词表规则 {len(rows)} 行：")
        names = {fn: n for n, fn in CONDITIONS.items()}
        for src, cell, pat, cond in rows:
            suffix = f"（{names.get(cond, cond)}）" if cond else ""
            print(f"  [{src}] {cell}{suffix}")
        print(f"\nlint 正则 {len(patterns)} 条：")
        for note, pat, level, src in patterns:
            print(f"  [{src}] {note}（{level}）")
        return 0

    if "--self-test" in args:
        return 0 if self_test(rows, patterns) else 3

    if args and args[0] != "-":
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    hits = lint_text(text, rows, patterns)
    errors = [h for h in hits if h[0] == "error"]
    for level, lineno, frag, ref in hits:
        print(f"[{level}] 第{lineno}行 「{frag}」 ← {ref}")
    if not hits:
        print("干净：词形层无命中。注意句式语义层仍需模型走查。")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
