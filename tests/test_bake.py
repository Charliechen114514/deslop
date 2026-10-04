"""Unit tests for tools/bake.py. Pure stdlib: python3 -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import bake  # noqa: E402


def make_repo(root):
    """Minimal repo skeleton with one dial per dimension."""
    dirs = ["recipes/base", "recipes/flaws", "recipes/tones", "recipes/scenes", "build"]
    for d in dirs:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    files = {
        "recipes/base/clarity.md": "# 基座：说清楚\n",
        "recipes/flaws/anti-ai.md": "# 病灶：AI 味\n",
        "recipes/tones/rhythm-mixed.md": "# 腔调档：节奏·交错（rhythm-mixed）\n",
        "recipes/tones/rhythm-tight.md": "# 腔调档：节奏·紧凑（rhythm-tight）\n",
        "recipes/tones/density-full.md": "# 腔调档：密度·舒展（density-full）\n",
        "recipes/tones/density-tight.md": "# 腔调档：密度·紧凑（density-tight）\n",
        "recipes/scenes/artifacts.md": "# 场景：工件（commit、README）\n",
        "build/bans.md": "# 我的判死词表（个人层）\n",
    }
    for rel, text in files.items():
        with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
            f.write(text)
    return root


class Resolve(unittest.TestCase):
    def test_full_combo_resolves_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(d)
            combo = {
                "flaws": ["anti-ai"],
                "tones": {"rhythm": "mixed", "density": "full"},
                "scenes": ["artifacts"],
                "personal": ["bans"],
            }
            files, unpicked = bake.resolve(combo, repo=root)
            self.assertEqual(files[0][0], "基座")
            # tone dials are emitted in dimension-name order (deterministic)
            self.assertEqual([f[1] for f in files if f[0] == "腔调"], ["密度·舒展", "节奏·交错"])
            self.assertEqual(unpicked, [])

    def test_unknown_dial_is_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(d)
            with self.assertRaises(ValueError) as ctx:
                bake.resolve({"tones": {"rhythm": "bouncy"}}, repo=root)
            self.assertIn("没有档位", str(ctx.exception))

    def test_unknown_dimension_is_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(d)
            with self.assertRaises(ValueError):
                bake.resolve({"tones": {"vibe": "mixed"}}, repo=root)

    def test_missing_file_is_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(d)
            with self.assertRaises(ValueError):
                bake.resolve({"flaws": ["ghost"]}, repo=root)

    def test_unpicked_dimension_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_repo(d)
            files, unpicked = bake.resolve({"tones": {"rhythm": "mixed"}}, repo=root)
            self.assertIn("density", unpicked)
            self.assertEqual(len(files), 2)  # base + rhythm only


class Render(unittest.TestCase):
    def test_baked_bundle_inlines_full_text_and_strips_lint(self):
        with tempfile.TemporaryDirectory() as d:
            layer = os.path.join(d, "rhythm-mixed.md")
            with open(layer, "w", encoding="utf-8") as f:
                f.write("# 腔调档：节奏·交错\n\n规则一。\n\n```lint\nfoo ## 第1条 ## review\n```\n\n## 来源\n\n出处注记。\n\n## 机械判罚块\n\n```lint\nbar ## 第2条 ## review\n```\n")
            files = [
                ("基座", "clarity（宪法加通则）", os.path.join(d, "clarity.md")),
                ("腔调", "节奏·交错", layer),
            ]
            text = bake.render_style(files)
            self.assertIn("由 tools/bake.py 生成", text)
            self.assertIn("路由：基座：", text)
            self.assertIn(bake.PRIORITY_LINE, text)
            self.assertIn("规则一。", text)          # full text inlined
            self.assertNotIn("foo ## 第1条", text)   # lint block stripped
            self.assertNotIn("出处注记", text)        # source section stripped
            self.assertNotIn("@/", text)             # no pointer lines left
            self.assertIn("----- 节奏·交错（rhythm-mixed.md）-----", text)


if __name__ == "__main__":
    unittest.main()
