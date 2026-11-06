#!/usr/bin/env python3
"""Build only the design-review figure metadata; leave textbook artifacts intact."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'source/design-figures.json'
data=json.loads(source.read_text())['figures'] if source.exists() else []
for f in data:
    path=ROOT/'dist'/f['file']
    ET.parse(path)
    assert f['placements'] and f['caption'] and f['alt'],f['id']
    assert '<script' not in path.read_text(),f['id']
(ROOT/'dist/preview/figure-data.js').write_text('/* Original diagrams for the design-review preview. */\nwindow.PreviewFigureData = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n')
print(json.dumps({'staticFigures':len(data),'interactiveFigures':2}))
