"""Unit tests for hooks/gate.py. Pure stdlib: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks import gate, reanchor  # noqa: E402


class Decide(unittest.TestCase):
    """decide() with hand-made rows/patterns: no repo state involved."""

    ROWS = [("bans.md", "坑", __import__("re").compile("坑"))]
    PATTERNS = []

    def test_off_or_already_blocked_passes(self):
        text = "这个方案有坑。"
        ok, _ = gate.decide(text, True, True, "ab12cd", self.ROWS, self.PATTERNS, already_blocked=True)
        self.assertFalse(ok)

    def test_empty_text_fails_open(self):
        ok, _ = gate.decide("", True, True, "ab12cd", self.ROWS, self.PATTERNS, False)
        self.assertFalse(ok)

    def test_banned_word_blocks(self):
        ok, reason = gate.decide("这个方案有坑。", False, False, "", self.ROWS, self.PATTERNS, False)
        self.assertTrue(ok)
        self.assertIn("坑", reason)

    def test_clean_anchor_without_token_blocks(self):
        ok, reason = gate.decide("干净的回复。", True, True, "ab12cd", self.ROWS, self.PATTERNS, False)
        self.assertTrue(ok)
        self.assertIn("暗语", reason)

    def test_clean_anchor_with_token_passes(self):
        text = "自评上一轮语气对了，记号 ab12cd。\n\n正文。"
        ok, _ = gate.decide(text, True, True, "ab12cd", self.ROWS, self.PATTERNS, False)
        self.assertFalse(ok)

    def test_old_token_does_not_pass(self):
        text = "自评记号 ff99ee 是旧的。\n\n正文。"
        ok, _ = gate.decide(text, True, True, "ab12cd", self.ROWS, self.PATTERNS, False)
        self.assertTrue(ok)

    def test_non_anchor_turn_needs_no_token(self):
        ok, _ = gate.decide("干净的回复。", False, True, "ab12cd", self.ROWS, self.PATTERNS, False)
        self.assertFalse(ok)


class NonceChain(unittest.TestCase):
    def test_gate_recomputes_reanchors_nonce(self):
        # what reanchor printed at prompt time must equal what the gate expects
        sid, n = "session-x", 4
        self.assertEqual(reanchor.derive_nonce(sid, n), reanchor.derive_nonce(sid, n))


if __name__ == "__main__":
    unittest.main()
