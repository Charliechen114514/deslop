"""Unit tests for hooks/reanchor.py (policy engine). Pure stdlib."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks import reanchor  # noqa: E402


class StripLintBlocks(unittest.TestCase):
    def test_lint_block_replaced(self):
        text = "规则正文\n\n```lint\n乱七八糟的正则 ## 第1条 ## review\n```\n\n结尾"
        out = reanchor.strip_lint_blocks(text)
        self.assertNotIn("乱七八糟的正则", out)
        self.assertIn(reanchor.LINT_PLACEHOLDER, out)

    def test_other_fences_kept(self):
        text = "```text\n@/some/path.md\n```"
        self.assertEqual(reanchor.strip_lint_blocks(text), text)


class Policy(unittest.TestCase):
    def test_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = reanchor.load_policy(os.path.join(d, "none.json"))
            self.assertTrue(p["score"])
            self.assertEqual(len(p["tiers"]), 4)  # 重锤/开场绳/中绳/常绳

    def test_file_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "policy.json")
            with open(f, "w", encoding="utf-8") as fh:
                json.dump({"score": False, "texts": {"light": "我的绳"},
                           "tiers": [{"name": "只常绳", "when": {"every_turn": True},
                                      "action": {"say": "light"}}]}, fh)
            p = reanchor.load_policy(f)
            self.assertFalse(p["score"])
            self.assertEqual(p["texts"]["light"], "我的绳")
            self.assertEqual(len(p["tiers"]), 1)

    def test_legacy_reanchor_json_synthesizes_tiers(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "reanchor.json")
            with open(f, "w", encoding="utf-8") as fh:
                json.dump({"every": 5, "score": True, "gate": True, "size_threshold": 90000}, fh)
            p = reanchor.load_policy(f)
            beats = [t["when"]["beat"] for t in p["tiers"] if "beat" in t["when"]]
            self.assertEqual(beats, [5])
            sizes = [t["when"]["min_size"] for t in p["tiers"] if "min_size" in t["when"]]
            self.assertEqual(sizes, [90000])


class Evaluate(unittest.TestCase):
    def test_force_beats_everything(self):
        tier = reanchor.evaluate(2, 10, True, reanchor.DEFAULT_POLICY)
        self.assertEqual(tier["name"], "重锤")

    def test_beat_matches_on_cadence(self):
        self.assertEqual(reanchor.evaluate(4, 200000, False, reanchor.DEFAULT_POLICY)["name"], "中绳")
        self.assertEqual(reanchor.evaluate(2, 200000, False, reanchor.DEFAULT_POLICY)["name"], "常绳")

    def test_small_size_falls_to_light(self):
        self.assertEqual(reanchor.evaluate(4, 1000, False, reanchor.DEFAULT_POLICY)["name"], "常绳")

    def test_unknown_size_degrades_to_beat(self):
        self.assertEqual(reanchor.evaluate(4, None, False, reanchor.DEFAULT_POLICY)["name"], "中绳")

    def test_unknown_condition_never_matches(self):
        policy = {"tiers": [
            {"name": "坏档", "when": {"vibe": 1}, "action": {"say": "light"}},
            {"name": "常绳", "when": {"every_turn": True}, "action": {"say": "light"}}]}
        self.assertEqual(reanchor.evaluate(1, None, False, policy)["name"], "常绳")


class Counter(unittest.TestCase):
    def test_counts_are_per_session(self):
        with tempfile.TemporaryDirectory() as d:
            cnt = os.path.join(d, "count")
            self.assertEqual(reanchor.bump_counter(cnt, session_id="a"), 1)
            self.assertEqual(reanchor.bump_counter(cnt, session_id="a"), 2)
            # 另一个会话踩不踩都不影响 a 的拍数
            reanchor.bump_counter(cnt, session_id="b")
            self.assertEqual(reanchor.read_counter("a", cnt), 2)
            self.assertEqual(reanchor.read_counter("b", cnt), 1)

    def test_unknown_session_reads_zero(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(reanchor.read_counter("ghost", os.path.join(d, "count")), 0)


class Render(unittest.TestCase):
    def _style(self, d):
        layer = os.path.join(d, "base-x.md")
        with open(layer, "w", encoding="utf-8") as f:
            f.write("# 基座X\n\n规则一。\n")
        style = os.path.join(d, "style.md")
        with open(style, "w", encoding="utf-8") as f:
            f.write("# 组合\n\n路由：写着什么层。\n\n@" + layer + "\n")
        return style

    def test_full_parts_and_nonce(self):
        with tempfile.TemporaryDirectory() as d:
            style = self._style(d)
            out = reanchor.render(style, nonce="ab12cd")
            self.assertIn("【自评】", out)
            self.assertIn(reanchor.codeword_for("ab12cd"), out)
            self.assertNotIn("ab12cd", out)  # plaintext nonce never shown
            self.assertIn("路由：写着什么层。", out)
            self.assertIn("强迫阅读", out)

    def test_parts_subset_omits_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            style = self._style(d)
            out = reanchor.render(style, parts=["voice"], texts={"voice": "只定声音。"})
            self.assertIn("只定声音。", out)
            self.assertNotIn("【自评】", out)
            self.assertNotIn("强迫阅读", out)

    def test_custom_texts_used(self):
        with tempfile.TemporaryDirectory() as d:
            style = self._style(d)
            texts = dict(reanchor.DEFAULT_TEXTS, light="我的常绳")
            self.assertIn("我的常绳", texts["light"])


class Init(unittest.TestCase):
    def test_creates_missing_never_overwrites(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tinit", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "init.py"))
        tinit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tinit)
        with tempfile.TemporaryDirectory() as ex, tempfile.TemporaryDirectory() as bd:
            with open(os.path.join(ex, "combo.json"), "w") as f:
                f.write("{}")
            os.makedirs(bd, exist_ok=True)
            with open(os.path.join(bd, "combo.json"), "w") as f:
                f.write("已有")
            created, kept = tinit.init(ex, bd)
            self.assertEqual(created, [])
            self.assertEqual(kept, ["combo.json"])
            with open(os.path.join(ex, "voice.md"), "w") as f:
                f.write("模板")
            created, kept = tinit.init(ex, bd)
            self.assertEqual(created, ["voice.md"])


class NonceChain(unittest.TestCase):
    def test_deterministic_and_fresh(self):
        self.assertEqual(reanchor.derive_nonce("s1", 4), reanchor.derive_nonce("s1", 4))
        self.assertNotEqual(reanchor.derive_nonce("s1", 4), reanchor.derive_nonce("s1", 7))

    def test_zero_width_cloak_round_trip(self):
        blob = reanchor.encode_nonce("df85e2")
        self.assertEqual(reanchor.decode_blob("正文。\n" + blob), "df85e2")
        self.assertEqual(reanchor.decode_blob("no blob here"), None)
        self.assertEqual(reanchor.decode_blob(reanchor.encode_nonce("ab12cd") + "尾巴"), "ab12cd")

    def test_codeword_stable_and_from_nonce(self):
        self.assertEqual(reanchor.codeword_for("b0ef21"), reanchor.codeword_for("b0ef21"))
        self.assertNotEqual(reanchor.codeword_for("b0ef21"), reanchor.codeword_for("b0ef22"))

    def test_render_carries_codeword_not_plaintext(self):
        with tempfile.TemporaryDirectory() as d:
            layer = os.path.join(d, "base-x.md")
            with open(layer, "w", encoding="utf-8") as f:
                f.write("# 基座X\n\n规则一。\n")
            style = os.path.join(d, "style.md")
            with open(style, "w", encoding="utf-8") as f:
                f.write("# 组合\n\n@" + layer + "\n")
            out = reanchor.render(style, nonce="df85e2")
            self.assertNotIn("df85e2", out)                        # plaintext never shown
            self.assertIn(reanchor.codeword_for("df85e2"), out)    # codeword shown


if __name__ == "__main__":
    unittest.main()
