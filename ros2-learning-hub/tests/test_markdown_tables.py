"""检查真实导出的GFM表格块，不把空行分隔的文字冒充可渲染表格。"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from book_export import expanded_markdown, markdown_table


class MarkdownTables(unittest.TestCase):
    def test_contiguous_rows_and_literal_pipe(self):
        table = dict(title='数据', columns=['输入', '单位'], rows=[['a|b', 'm/s'], ['两行\n数据', 's']])
        result = markdown_table(table)
        self.assertEqual(result, '| 输入 | 单位 |\n| --- | --- |\n| a\\|b | m/s |\n| 两行<br>数据 | s |')

    def test_section_and_api_exports_remain_single_blocks(self):
        table = dict(title='实测表', columns=['场景', '结果'], rows=[['paused', '0/8']], caption='仅本次输入')
        chapter = dict(sections=[dict(title='正文', tables=[table])], apiReferences=[table], exercises=[])
        markdown = '\n\n'.join(expanded_markdown(chapter))
        self.assertEqual(markdown.count('| 场景 | 结果 |\n| --- | --- |\n| paused | 0/8 |'), 2)
        self.assertNotIn('| 场景 | 结果 |\n\n| ---', markdown)


if __name__ == '__main__':
    unittest.main(verbosity=2)
