"""以临时目录验证教材文件写入失败、备份保护和路径边界。"""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import local_editions as editions


class EditionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ros2-file-edition-unit-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "dist").mkdir()
        self.chapter = {"id": "architecture", "title": "原文", "sections": []}
        (self.root / "dist/content.js").write_text("window.ROS2Hub = " + json.dumps({"lessons": [self.chapter], "figures": []}) + ";\n")
        self.original = {"title": "原文", "html": "<h1>原文</h1><p>原段落</p>", "markdown": "# 原文\n\n原段落\n"}

    def payload(self, revision=None, text="修改段落"):
        return {"chapterId": "architecture", "baseChapter": self.chapter, "expectedRevision": revision,
                "original": self.original, "document": {"title": "原文", "html": f"<h1>原文</h1><p>{text}</p>", "markdown": f"# 原文\n\n{text}\n"}}

    def test_backup_failure_before_write(self):
        with patch.object(editions, "atomic_write", side_effect=OSError("备份失败")):
            with self.assertRaisesRegex(OSError, "备份失败"):
                editions.save_edition(self.root, self.payload())
        self.assertFalse((self.root / "source/local-edits.json").exists())
        self.assertFalse((self.root / "dist/chapters/architecture.md").exists())

    def test_output_failure_rolls_back_all_changed_files(self):
        first = editions.save_edition(self.root, self.payload())
        files = first["files"]
        before = [(self.root / name).read_bytes() for name in files]
        original_write = editions.atomic_write
        injected = False

        def write(path, data):
            nonlocal injected
            if path.name == "local-edits.js" and not injected:
                injected = True
                raise OSError("末尾写入失败")
            original_write(path, data)

        with patch.object(editions, "atomic_write", side_effect=write):
            with self.assertRaisesRegex(OSError, "末尾写入失败"):
                editions.save_edition(self.root, self.payload(first["record"]["revision"], "待回滚"))
        self.assertEqual([(self.root / name).read_bytes() for name in files], before)
        self.assertEqual((self.root / "backups/local-edits/original/architecture/chapter.md").read_text(), self.original["markdown"])

    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / "architecture.md"
            path.write_text("其他文件")
            (self.root / "dist/chapters").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "符号链接"):
                editions.save_edition(self.root, self.payload())
            self.assertEqual(path.read_text(), "其他文件")

    def test_chapter_and_active_html_rejected(self):
        for payload in [{**self.payload(), "chapterId": "../architecture"}, self.payload(text="<script>bad()</script>")]:
            with self.assertRaises(ValueError):
                editions.save_edition(self.root, payload)
        self.assertFalse((self.root / "source/local-edits.json").exists())

    def test_markdown_chapter_title_preserves_code(self):
        doc = {"title": "标题", "markdown": "# 标题\n## 节\n```python\n# 中文注释：../dist/\n```\n![图](../dist/preview/figures/test.svg)\n",
               "html": '<pre><code>src="../dist/data"</code></pre><img src="../dist/preview/figures/test.svg">'}
        self.assertEqual(editions.edition_markdown(doc, 1), "## 1. 标题\n### 节\n```python\n# 中文注释：../dist/\n```\n![图](../preview/figures/test.svg)")
        page = editions.chapter_page(doc).decode()
        self.assertIn('<pre><code>src="../dist/data"', page)
        self.assertIn('<img src="../preview/figures/test.svg">', page)


if __name__ == "__main__":
    unittest.main()
