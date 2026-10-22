"""Unit tests for checks/fragments.py. Pure stdlib: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checks.fragments import fragments  # noqa: E402


class FragmentScreening(unittest.TestCase):
    def segs(self, text, **kw):
        return {seg for _, seg, _ in fragments(text, **kw)}

    def test_rule28_samples_flagged(self):
        text = ("被认成她……我不亏\n"
                "公司的那些问题，我都看到了\n"
                "这个需求，先欠着\n"
                "哪句还像AI，直接指出来\n"
                "哼，等你")
        segs = self.segs(text)
        for want in ("被认成她", "我不亏", "我都看到了", "先欠着", "直接指出来", "等你"):
            self.assertIn(want, segs)

    def test_whitelisted_replies_not_flagged(self):
        self.assertEqual(self.segs("好的，没问题，先这样。嗯嗯，可以的。"), set())

    def test_all_shows_whitelist(self):
        segs = self.segs("好的，没问题。", whitelist=frozenset())
        self.assertIn("好的", segs)
        self.assertIn("没问题", segs)

    def test_expanded_sentence_passes(self):
        # rule 28's blessed rewrite: full joints, nothing to flag
        self.assertEqual(self.segs("如果有哪句还像AI，请你们直接指出来，谢谢你们。"), set())

    def test_non_cjk_skipped(self):
        self.assertEqual(self.segs("OK，fine，666，qaq。"), set())

    def test_limit_adjustable(self):
        text = "这四个字"
        self.assertEqual(self.segs(text, limit=3), set())
        self.assertIn("这四个字", self.segs(text, limit=4))

    def test_context_carries_the_line(self):
        hits = list(fragments("哪句还像AI，直接指出来"))
        ctx = {seg: c for _, seg, c in hits}["直接指出来"]
        self.assertIn("直接指出来", ctx)


if __name__ == "__main__":
    unittest.main()
