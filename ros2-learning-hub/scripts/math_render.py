"""Build-time TeX to native MathML; the delivered site needs no math runtime."""
from html import escape
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from latex2mathml.converter import convert

ET.register_namespace('', 'http://www.w3.org/1998/Math/MathML')

def render_math(tex, label='公式'):
    result = ET.fromstring(convert(tex, display='block'))
    result.set('aria-label', label)
    return ET.tostring(result, encoding='unicode')

def prepare_equations(chapters):
    count = 0
    for chapter in chapters:
        number = 0
        for section in chapter.get('sections', []):
            for eq in section.get('equations', []):
                number += 1
                eq['number'] = number
                eq['mathml'] = render_math(eq['tex'], eq.get('label', '公式'))
                assert eq.get('explanation'), (chapter['id'], eq['tex'])
                count += 1
    return count

def equation_html(eq):
    symbols = ''.join('<tr><td><code>'+escape(str(s['symbol']))+'</code></td><td>'+escape(str(s['meaning']))+'</td><td>'+escape(str(s.get('unit','—')))+'</td></tr>' for s in eq.get('symbols',[]))
    mathml = eq.get('mathml') or render_math(eq['tex'], eq.get('label','公式'))
    return ('<figure class="equation"><figcaption>'+escape(eq.get('label','公式'))+'</figcaption>'
            '<div class="math-scroll">'+mathml+'</div><p>'+escape(eq['explanation'])+'</p>'
            + ('<div class="table-scroll"><table class="symbol-table"><thead><tr><th>符号</th><th>含义</th><th>单位／维度</th></tr></thead><tbody>'+symbols+'</tbody></table></div>' if symbols else '')
            +'<details class="formula-source"><summary>查看 LaTeX 公式源码</summary><pre><code>'+escape(eq['tex'])+'</code></pre></details></figure>')

def equation_markdown(eq):
    out=['#### '+eq.get('label','公式'),'$$\n'+eq['tex']+'\n$$',eq['explanation']]
    out.extend('- `'+s['symbol']+'`：'+s['meaning']+'；单位／维度：'+s.get('unit','—') for s in eq.get('symbols',[]))
    return out
