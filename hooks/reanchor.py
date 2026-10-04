#!/usr/bin/env python3
"""Tone anchor hook: policy-driven tethering of the recipe combo.

Used as a Claude Code UserPromptSubmit hook. Pure stdlib; stdout is added to
the model context. All strategy lives in build/policy.json (see
tools/init.py to generate a starter): which tiers exist, when each fires,
what it says. This file is only the engine - a small vocabulary:

  when:  every_turn | beat:N | min_size:S | force
  action: say:<text-key>  |  anchor:[score, voice, routing, read]

Counter is per-session (resets when session_id changes). The score nonce is
derived from (session_id, n) so the Stop gate can recompute it. Fail-open:
any config error falls back to the built-in default policy.
"""
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE = os.path.join(REPO, "build", "style.md")
COUNT_FILE = os.path.join(REPO, "build", ".reanchor-count")
CONFIG_FILE = os.path.join(REPO, "build", "reanchor.json")
POLICY_FILE = os.path.join(REPO, "build", "policy.json")

LINT_BLOCK = re.compile(r"```lint\n.*?\n```", re.S)
LINT_PLACEHOLDER = "（机械判罚块，略）"

DEFAULT_TEXTS = {
    "light": "【绳】配方在身：开口先对上用户一贯的语气（助词、密度、承接），回复第一句就带上。",
    "score": (
        "【自评】在思考里给你最近几轮自己的输出挑一处做得好、一处犯规"
        "（各限一处，犯规引用你自己的原句，没有就直说没有，上一轮漏评的先认）。"
        "认完做一步展开练习：把最近最压缩的那句（名词短语排队、临场缩略语）"
        "在心里重写成全量句，主语、连接词、虚词齐全的那种。刚拉伸过的手感会传给下一段。"
        "自评不写进正文，一个字都不露。回复里把本轮暗语自然地织进任意一句，"
        "它是个普通词，别点破、别解释、别放在开头标签位，漏织算漏评。"
        "会话刚开场没有历史，也要织。然后正常回答用户。"
    ),
    "voice": (
        "开口先定声音：看用户一贯的画风——他的助词、他的密度、他的承接"
        "（最近一条偏干不算数，按整体画风来），你回复的第一句就要带上，不是最后一段才想起来。"
    ),
    "read": (
        "【重锚·强迫阅读】回答之前，先用 Read 工具完整读取以下文件，"
        "按其全量执行（文件末尾 ```lint 块是给判罚脚本的，忽略即可）："
    ),
}

DEFAULT_POLICY = {
    "score": True,
    "texts": {},
    "tiers": [
        {"name": "重锤", "when": {"force": True},
         "action": {"anchor": ["score", "voice", "routing", "read"]}},
        {"name": "开场绳", "when": {"first_turn": True},
         "action": {"anchor": ["score", "voice", "routing", "read"]}},
        {"name": "中绳", "when": {"beat": 3, "min_size": 150000},
         "action": {"anchor": ["score", "voice", "routing", "read"]}},
        {"name": "常绳", "when": {"every_turn": True}, "action": {"say": "light"}},
    ],
    "gate": {"enabled": True, "banned_words": True, "score_nonce": True, "max_block": 1},
}


def load_policy(path=None):
    """Merge build/policy.json over the defaults; legacy reanchor.json keys
    (every/score/gate/size_threshold) are honored when policy.json is absent."""
    policy = json.loads(json.dumps(DEFAULT_POLICY))  # deep copy
    src = path or (POLICY_FILE if os.path.exists(POLICY_FILE) else CONFIG_FILE)
    try:
        with open(src, encoding="utf-8") as f:
            user = json.load(f)
    except Exception:
        return policy
    if "tiers" not in user and "every" in user:
        # legacy reanchor.json -> synthesize tiers from its flat keys
        policy["score"] = bool(user.get("score", policy["score"]))
        beat = int(user.get("every", 3))
        size = int(user.get("size_threshold", 150000))
        for tier in policy["tiers"]:
            if "beat" in tier["when"]:
                tier["when"]["beat"] = beat
                tier["when"]["min_size"] = size
        policy["gate"]["enabled"] = bool(user.get("gate", policy["gate"]["enabled"]))
        return policy
    for key in ("score", "tiers", "gate"):
        if key in user:
            policy[key] = user[key]
    policy["texts"] = {**DEFAULT_TEXTS, **user.get("texts", {})}
    return policy


def texts_of(policy):
    return {**DEFAULT_TEXTS, **policy.get("texts", {})}


def _load_counts(path=None):
    try:
        with open(path or COUNT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def bump_counter(path=None, session_id=""):
    """Increment THIS session's prompt count. All sessions share one file,
    each under its own key - concurrent sessions never stomp each other."""
    path = path or COUNT_FILE
    counts = _load_counts(path)
    n = counts.get(session_id, 0) + 1
    counts[session_id] = n
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(counts, f, ensure_ascii=False)
    except Exception:
        pass
    return n


def read_counter(session_id, path=None):
    """This session's current count (0 when unknown)."""
    return int(_load_counts(path).get(session_id, 0))


def derive_nonce(session_id, n):
    """Per-turn score token, recomputable by the gate from the same inputs."""
    return hashlib.sha1(f"{session_id}|{n}".encode()).hexdigest()[:6]


CODEWORDS = [
    "琥珀", "砚台", "鸢尾", "舵手", "灯塔", "松针", "麦芒", "潮汐",
    "橘子", "井盖", "瓦片", "风铃", "砚墨", "藤椅", "渔火", "雪松",
    "青苔", "帆布", "陶罐", "铜锣", "纸鹤", "木梳", "竹篮", "蓑衣",
    "石阶", "柳絮", "荷塘", "牧笛", "山泉", "谷仓", "门环", "窗棂",
    "油纸", "炭火", "粗瓷", "麻绳", "芦苇", "银杏", "皂角", "槐花",
]


def codeword_for(nonce):
    """Deterministic per-turn codeword derived from the nonce:
    a normal word the model copies flawlessly and the reader can't spot."""
    return CODEWORDS[int(hashlib.sha1(f"cw|{nonce}".encode()).hexdigest(), 16) % len(CODEWORDS)]


ZW_BITS = {"0": "\u200b", "1": "\u200c"}  # legacy cloak, kept for decode only


def encode_nonce(nonce):
    """Invisible cloak for the token: hex -> bits -> zero-width chars.
    Renders as nothing in terminals, decodable from raw text."""
    bits = "".join(bin(int(c, 16))[2:].zfill(4) for c in nonce)
    return "".join(ZW_BITS[b] for b in bits)


def decode_blob(text):
    """Decode the last zero-width run in text back to hex, or None."""
    import re as _re
    runs = _re.findall("[\u200b\u200c]{4,}", text)
    if not runs:
        return None
    bits = "".join("0" if ch == "\u200b" else "1" for ch in runs[-1])
    try:
        return "".join(hex(int(bits[i:i + 4], 2))[2:] for i in range(0, len(bits), 4))
    except ValueError:
        return None


def strip_lint_blocks(text):
    return LINT_BLOCK.sub(LINT_PLACEHOLDER, text)


def read_style_targets(path=None):
    path = path or STYLE
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    targets = [ln[1:].strip() for ln in lines if ln.strip().startswith("@")]
    return targets if targets else [path]


def read_style_header(path=None):
    path = path or STYLE
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("@") or s.startswith("-----"):
                break
            out.append(line.rstrip("\n"))
    return "\n".join(x for x in out if x.strip())


def evaluate(n, size, force, policy):
    """Return the matching tier's action dict for this prompt.

    Tiers are consulted in listed order; first match wins, so put specific
    tiers (force) above the catch-all (every_turn). Unknown when-keys or
    action fields fall through to the next tier.
    """
    for tier in policy.get("tiers", []):
        when = tier.get("when", {})
        ok = True
        for key, val in when.items():
            if key == "every_turn":
                ok = ok and bool(val)
            elif key == "beat":
                ok = ok and n > 0 and (n - 1) % int(val) == 0
            elif key == "min_size":
                ok = ok and (size is None or size >= int(val))
            elif key == "first_turn":
                ok = ok and bool(val) and n == 1
            elif key == "force":
                ok = ok and bool(val) and force
            else:
                ok = False  # unknown condition -> this tier never matches
            if not ok:
                break
        if ok:
            action = tier.get("action", {})
            if "anchor" in action or "say" in action:
                return tier
    return None


def render(path=None, parts=None, nonce=None, score=None, texts=None, header=None):
    """Assemble the full anchor from named parts."""
    texts = texts or DEFAULT_TEXTS
    if parts is None:
        parts = ["score", "voice", "routing", "read"]
    out = ["【语气锚】本轮起按以下配方说话："]
    if "score" in parts and score is not False:
        prompt = texts["score"]
        if nonce:
            prompt += f"本轮暗语：{codeword_for(nonce)}"
        out.append(prompt)
    if "voice" in parts:
        out.append(texts["voice"])
    if "routing" in parts:
        h = header if header is not None else read_style_header(path)
        if h:
            out.append(h)
    if "read" in parts:
        out.append(texts["read"])
        out.extend("- " + t for t in read_style_targets(path))
    return "\n".join(out)


def force_flag_present():
    return os.path.exists(os.path.join(REPO, "build", ".reanchor-force"))


def clear_force_flag():
    try:
        os.remove(os.path.join(REPO, "build", ".reanchor-force"))
    except OSError:
        pass


def transcript_size(session_id):
    if not session_id:
        return None
    base = os.path.expanduser("~/.claude/projects")
    sanitized = os.getcwd().replace("/", "-")
    try:
        return os.path.getsize(os.path.join(base, sanitized, session_id + ".jsonl"))
    except OSError:
        return None


def main():
    payload = {}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    sid = str(payload.get("session_id", ""))
    force = force_flag_present()
    if force:
        try:
            counts = _load_counts()
            counts[sid] = 0
            os.makedirs(os.path.dirname(COUNT_FILE), exist_ok=True)
            with open(COUNT_FILE, "w", encoding="utf-8") as f:
                json.dump(counts, f, ensure_ascii=False)
        except Exception:
            pass
        clear_force_flag()
    n = bump_counter(session_id=sid)
    policy = load_policy()
    size = transcript_size(sid)
    tier = evaluate(n, size, force, policy)
    texts = texts_of(policy)
    if tier is None or "say" in tier.get("action", {}):
        key = (tier or {}).get("action", {}).get("say", "light")
        print(texts.get(key, texts["light"]))
        return
    try:
        parts = tier["action"]["anchor"]
        print(render(parts=parts, nonce=derive_nonce(sid, n),
                     score=policy.get("score", True), texts=texts))
    except Exception as err:
        print(f"【绳】{texts['light']}（全量锚组装失败：{err}）")


if __name__ == "__main__":
    main()
