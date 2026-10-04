"""Unit tests for checks/lint.py. Pure stdlib: python3 -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checks.lint import (  # noqa: E402
    compile_rows,
    lint_text,
    load_combo,
    parse_lint_blocks,
    parse_word_tables,
)


class ComboLoading(unittest.TestCase):
    def setUp(self):
        self.files = load_combo()
        self.rows = compile_rows(parse_word_tables(self.files))
        self.patterns = parse_lint_blocks(self.files)

    def test_combo_has_layers(self):
        self.assertGreaterEqual(len(self.files), 5)

    def test_word_rules_loaded(self):
        self.assertGreaterEqual(len(self.rows), 20)

    def test_lint_patterns_loaded(self):
        self.assertGreaterEqual(len(self.patterns), 15)


class WordTableLint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = compile_rows(parse_word_tables(load_combo()))
        cls.patterns = parse_lint_blocks(load_combo())

    def hit_levels(self, text):
        return [h[0] for h in lint_text(text, self.rows, self.patterns)]

    def test_banned_word_hits_error(self):
        self.assertIn("error", self.hit_levels("这个方案没坑，直接干。"))

    def test_label_condition_enforced_mechanically(self):
        # "结论" is banned only as a label - now a named condition, decidable.
        hits = lint_text("结论：方案可行。", self.rows, self.patterns)
        errors = [h for h in hits if h[0] == "error" and "结论" in h[3]]
        self.assertTrue(errors)

    def test_label_condition_plain_mention_passes(self):
        hits = lint_text("这个结论要讲证据。", self.rows, self.patterns)
        errors = [h for h in hits if h[0] == "error" and "结论" in h[3]]
        self.assertEqual(errors, [])

    def test_real_order_condition_word_family_still_banned(self):
        # the single-character row was pardoned; the compounds stay banned
        self.assertIn("error", self.hit_levels("先聊两句，这事就成了。"))

    def test_fenced_code_skipped(self):
        text = "正文干净。\n```\n这个方案没坑\n```\n结尾也干净。"
        self.assertEqual(lint_text(text, self.rows, self.patterns), [])

    def test_quoted_span_exempt_from_word_table(self):
        # discussing / quoting the banned word itself is the documented boundary
        hits = lint_text("词表里「门禁」这一条说的是机制名。", self.rows, self.patterns)
        errors = [h for h in hits if h[0] == "error"]
        self.assertEqual(errors, [])

    def test_unquoted_word_still_hits(self):
        self.assertIn("error", self.hit_levels("这个方案没坑，直接干。"))


class LintBlockLint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = parse_lint_blocks(load_combo())
        cls.rows = compile_rows(parse_word_tables(load_combo()))

    def test_balance_sentence_candidate(self):
        hits = lint_text("这不是配置的问题，而是权限的问题。", self.rows, self.patterns)
        self.assertTrue(any("第1条" in h[3] and h[0] == "review" for h in hits))

    def test_fake_article(self):
        hits = lint_text("对这一份配置做一次检查。", self.rows, self.patterns)
        self.assertTrue(any("假冠词" in h[3] for h in hits))

    def test_gongwen_jinxing(self):
        hits = lint_text("对配置进行了一次检查。", self.rows, self.patterns)
        self.assertTrue(any("进行" in h[3] for h in hits))


class ThirdPartyLayer(unittest.TestCase):
    """A hand-written layer with a table and a lint block must load as-is."""

    def test_tmp_layer(self):
        with tempfile.TemporaryDirectory() as d:
            layer = os.path.join(d, "my-layer.md")
            with open(layer, "w", encoding="utf-8") as f:
                f.write(
                    "# 测试层\n\n| 禁 | 改成 |\n|------|------|\n"
                    "| 芝士（一切组合） | 写具体的知识 |\n\n"
                    "```lint\n芝士 ## 第1条 测试 ## review\n```\n"
                )
            rows = compile_rows(parse_word_tables([layer]))
            patterns = parse_lint_blocks([layer])
            self.assertEqual(len(rows), 1)
            hits = lint_text("这真是芝士。", rows, patterns)
            self.assertTrue(any(h[0] == "error" for h in hits))


if __name__ == "__main__":
    unittest.main()
