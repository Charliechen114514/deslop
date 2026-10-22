#!/usr/bin/env python3
"""Short-fragment screener: list segments of <=N chars (default 5) between
punctuation, for human review. Companion to anti-ai rule 28 (应答残句).

checks/lint.py judges word FORMS; this one surfaces SHAPE candidates:
answers compressed to a few characters ("先欠着" "我不亏" "直接指出来"),
subject / conditional / politeness words all gone. A short segment is not
a crime (chat lives on "好" "先这样" and the rhythm layer allows natural
short sentences), so everything printed here is a candidate, a human
decides. Exit code is 0 either way.

Usage:
  python3 checks/fragments.py some.txt        # screen a file
  cat some.txt | python3 checks/fragments.py  # screen stdin
  python3 checks/fragments.py -n 4 some.txt   # tighten the threshold
  python3 checks/fragments.py --all some.txt  # include whitelisted replies
"""
import argparse
import re
import sys

# 两个标点之间算一段。省略号、破折号、波浪线、空格（字幕时间戳混排用）都当分隔符。
SPLIT = re.compile(r"[，。！？；：、…—～\t 　]+")

# 引号和括号贴在段边上时剥掉再数。
TRIM = "「」『』“”\"'（）()<>《》"

# 常规短应答，聊天里活得很好，默认不列（--all 可见）。
WHITELIST = frozenset("""
好 好的 好吧 好嘞 好家伙 有点东西 走起 得嘞 来了 来啦
行 行吧 行嘛
对 对的 对呢 也对 那倒是
嗯 嗯嗯 唔 哦 噢 喔 呃 咳 哇 喂 嘿 哼
是 是的 不 不用 不用啦 没错
没事 没问题 可以 可以的 收到 明白 懂了 知道了 晓得
谢谢 多谢 谢谢你 谢谢你们 辛苦 辛苦了 抱歉 对不起
就这样 先这样 那就这样 回头说 回头聊 拜拜 晚安
等等 等一下 我想想 怎么说呢 这个嘛 随便 看情况 说不定 有道理
""".split())

CJK = re.compile(r"[一-鿿]")


def fragments(text, limit=5, whitelist=WHITELIST):
    """Yield (lineno, segment, context) for short CJK segments.

    Segments with no CJK character (numbers, latin, kaomoji) are skipped:
    the disease being screened is compressed Chinese answers.
    """
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        for raw in SPLIT.split(line):
            seg = raw.strip().strip(TRIM).strip()
            if not seg or len(seg) > limit:
                continue
            if not CJK.search(seg):
                continue
            if seg in whitelist:
                continue
            yield lineno, seg, _context(line, raw.strip())


def _context(line, seg, window=14):
    """±window chars around the first occurrence of seg in line."""
    pos = line.find(seg)
    if pos < 0:
        pos = 0
    start = max(0, pos - window)
    end = min(len(line), pos + len(seg) + window)
    out = line[start:end].strip()
    return ("…" if start > 0 else "") + out + ("…" if end < len(line) else "")


def main():
    ap = argparse.ArgumentParser(description="短残句筛查（只列候选，人工定夺）")
    ap.add_argument("file", nargs="?", help="不填则读 stdin")
    ap.add_argument("-n", "--limit", type=int, default=5,
                    help="两个标点之间的字数阈值，默认 5")
    ap.add_argument("--all", action="store_true",
                    help="连白名单里的常规应答一起列")
    args = ap.parse_args()

    whitelist = frozenset() if args.all else WHITELIST

    if args.file and args.file != "-":
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    hits = list(fragments(text, args.limit, whitelist))
    for lineno, seg, ctx in hits:
        print(f"第{lineno}行 「{seg}」 ← {ctx}")
    if hits:
        print(f"\n共 {len(hits)} 个候选。短句不是罪（节奏档允许自然短句），逐条人工定夺。")
    else:
        print("干净：阈值内没有白名单外的短段。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
