#!/usr/bin/env python3
"""Stop-gate: hard enforcement of the combo at turn end.

Runs as a Claude Code Stop hook. When the assistant finishes a turn, this
gate inspects the final output and can BLOCK the stop, feeding violations
back so the model rewrites. Fail-open by design: any internal error lets
the turn through - the gate must never brick a session.

Thin by design - it owns only what nobody else owns:
  - reading the transcript (only texts after the last real user message),
  - waiting for a reply to finish streaming (transcripts flush progressively;
    the codeword rides near the tail, so a half-flushed text is structurally
    missing it - we require ~1s of quiescence before trusting a new text),
  - the per-turn block cap (build/.gate-state),
  - the block/pass decision.
Everything else is imported: policy/counter/nonce/codeword from
hooks.reanchor, word-form hits from checks.lint (in-process).

Enforced (all switches in build/policy.json, gate block):
  1. banned_words: error-level word-table hits -> block.
  2. fragments: mechanical counters (compression fragments, dash quota).
  3. score_nonce: on anchor turns, the codeword / nonce must be present,
     searched across ALL texts after the last user message (a reply may be
     split across transcript entries).
"""
import hashlib
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from hooks import reanchor  # noqa: E402
from checks import lint  # noqa: E402

STATE_FILE = os.path.join(REPO, "build", ".gate-state")


def texts_after_last_user(transcript_path):
    """All assistant texts after the last real user message.

    Judging must not reach across the last user turn: an anchor arrives with
    a user message, and everything before it was judged in earlier turns.
    Tool-result pseudo-user entries carry no text and never count.
    """
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return []
    last_user = -1
    for i, line in enumerate(lines):
        try:
            j = json.loads(line)
        except Exception:
            continue
        if j.get("type") != "user":
            continue
        c = j.get("message", {}).get("content")
        if isinstance(c, str) and c.strip():
            last_user = i
        elif isinstance(c, list) and any(
                isinstance(x, dict) and x.get("type") == "text" and x.get("text", "").strip() for x in c):
            last_user = i
    out = []
    for line in lines[last_user + 1:]:
        try:
            j = json.loads(line)
        except Exception:
            continue
        if j.get("type") != "assistant":
            continue
        content = j.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                out.append(c["text"])
    return out


def newest_after_last_user(transcript_path):
    texts = texts_after_last_user(transcript_path)
    return texts[-1] if texts else ""


def _hash(text):
    return hashlib.sha1(text.encode()).hexdigest() if text.strip() else ""


def fetch_unjudged(transcript_path, judged_hash, tries=8, delay=0.25, stable_needed=4):
    """Wait for a COMPLETE, never-judged reply.

    A candidate counts only after `stable_needed` consecutive identical
    re-reads (~1s of quiescence) - stream pauses shorter than that must not
    be mistaken for "done writing". If nothing stable and new appears, the
    caller passes - the gate must never block twice on the same old message.
    """
    text = newest_after_last_user(transcript_path)
    h = _hash(text)
    stable = 0
    for _ in range(tries):
        time.sleep(delay)
        text2 = newest_after_last_user(transcript_path)
        h2 = _hash(text2)
        if h2 == h:
            stable += 1
        else:
            stable = 0
            text, h = text2, h2
        if text.strip() and h != judged_hash and stable >= stable_needed:
            return text, h
    return text, h


def lint_error_hits(text, rows, patterns, include_fragments=False):
    """Error-level word-form hits; with include_fragments, also the two
    mechanical counters (compression fragments, dash quota)."""
    hits = lint.lint_text(text, rows, patterns)
    out = [f"「{frag}」 ← {ref}" for level, _, frag, ref in hits if level == "error"]
    if include_fragments:
        out += [f"「{frag}」 ← {ref}" for level, _, frag, ref in hits
                if level == "review" and ("压缩碎片" in ref or "破折号超限" in ref)]
    return out


def has_token(text, nonce):
    """Compliance proof present: the codeword (woven into prose), the
    plaintext nonce (fallback), or a legacy zero-width blob."""
    if reanchor.codeword_for(nonce) in text:
        return True
    if nonce in text:
        return True
    return reanchor.decode_blob(text) == nonce


def decide(text, anchored, score_on, nonce, rows, patterns, already_blocked):
    """Return (block, reason). Pure-ish logic, unit-testable."""
    if already_blocked or not text.strip():
        return False, ""  # nothing readable to judge -> fail open
    violations = []
    hits = lint_error_hits(text, rows, patterns)
    if hits:
        violations.append("判死词命中，逐条改掉再交：\n" + "\n".join(hits))
    if anchored and score_on and not has_token(text, nonce):
        violations.append(
            f"这一轮是锚后轮，回复里该把本轮暗语（锚里给的那个词）自然织进任意一句，"
            f"或附上记号 {nonce}。漏了算漏评。")
    if violations:
        return True, "【门禁打回】" + "\n".join(violations)
    return False, ""


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    policy = reanchor.load_policy()
    gp = policy.get("gate", {})
    if not gp.get("enabled", False):
        return

    sid = str(payload.get("session_id", ""))
    n = reanchor.read_counter(sid)
    nonce = reanchor.derive_nonce(sid, n)
    anchored = False
    for tier in policy.get("tiers", []):
        when = tier.get("when", {})
        if when.get("force"):
            continue
        if "beat" in when and n > 0 and (n - 1) % int(when["beat"]) == 0:
            anchored = True
    anchored = anchored and n > 0

    state = {"key": "", "blocks": 0, "judged": ""}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = {**state, **json.load(f)}
    except Exception:
        pass

    transcript = payload.get("transcript_path", "")
    text, h = fetch_unjudged(transcript, state.get("judged", ""))

    def save_state(blocks=None):
        try:
            st = {"key": f"{sid} {n}",
                  "blocks": blocks if blocks is not None else state.get("blocks", 0),
                  "judged": h}
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False)
        except Exception:
            pass

    if not text.strip() or h == state.get("judged", ""):
        return  # nothing new to judge - never re-block an already-judged reply
    max_block = int(gp.get("max_block", 1))
    if state.get("key") == f"{sid} {n}" and int(state.get("blocks", 0)) >= max_block:
        save_state()  # cap reached for this turn; record and pass
        return

    try:
        rows = lint.compile_rows(lint.parse_word_tables(lint.load_combo()))
        patterns = lint.parse_lint_blocks(lint.load_combo())
    except Exception:
        rows, patterns = [], []

    violations = []
    frags = bool(gp.get("fragments", False))
    if gp.get("banned_words", True) or frags:
        hits = lint_error_hits(text, rows, patterns, include_fragments=frags)
        if hits:
            violations.append("词形与计数体检命中，逐条改掉再交：\n" + "\n".join(hits))
    if anchored and policy.get("score", True) \
            and gp.get("score_nonce", True) and not has_token(text, nonce):
        time.sleep(1.0)  # codeword rides near the tail: re-read once more
        joined = "\n".join(texts_after_last_user(transcript))
        if not has_token(joined, nonce):
            violations.append(
                f"这一轮是锚后轮，回复里该把本轮暗语（锚里给的那个词）自然织进任意一句，"
                f"或附上记号 {nonce}。漏了算漏评。")
    if violations:
        blocks = int(state.get("blocks", 0)) + 1 if state.get("key") == f"{sid} {n}" else 1
        save_state(blocks)
        reason = ("【门禁打回】" + "\n".join(violations) +
                  "\n旧的已经上屏，就让它留在那，不要整段重发修正版造成双胞胎，不要解释被什么拦住，不要碎碎念犯了什么错。简短接续往下说就好，只有当修正版承载着对方还没看到的必要信息时才重发。")
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return
    save_state(0)


if __name__ == "__main__":
    main()
