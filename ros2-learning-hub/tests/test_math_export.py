"""Check offline mathematical content survives both export paths."""
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import book_export

class MathExportTests(unittest.TestCase):
    def setUp(self):
        self.equation = dict(tex=r'p_B=R(\theta)p_L+t', label='刚体变换',
                            explanation='先旋转，再平移；坐标量均以米计。',
                            symbols=[dict(symbol='t', meaning='平移向量', unit='m')])
        self.chapter = dict(sections=[dict(title='推导', paragraphs=['同一物理点的两种坐标。'],
                            equations=[self.equation])])

    def test_markdown_preserves_formula_symbols_and_explanation(self):
        result='\n'.join(book_export.expanded_markdown(self.chapter))
        self.assertIn('$$\n'+self.equation['tex']+'\n$$',result)
        self.assertIn('平移向量',result)
        self.assertIn(self.equation['explanation'],result)

    def test_mathml_is_standalone_and_accessible(self):
        import math_render
        formula=math_render.render_math(r'\begin{bmatrix}1&2\\3&4\end{bmatrix}x=\frac{a}{b}', '矩阵方程')
        root=ET.fromstring(formula)
        self.assertTrue(root.tag.endswith('math'))
        self.assertEqual(root.get('aria-label'),'矩阵方程')
        self.assertTrue(any(x.tag.endswith('mfrac') for x in root.iter()))
        self.assertNotIn('<script',formula)

if __name__=='__main__':unittest.main()
