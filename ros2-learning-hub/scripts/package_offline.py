#!/usr/bin/env python3
"""Package a portable static site and examples without caches or credentials."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'

def allowed(path):
    return not any(p.startswith('.') or p in ('__pycache__','build','install','log') or p.endswith('.egg-info') for p in path.parts) and path.suffix!='.pyc'

def archive_tree(source,target,prefix):
    count=0
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            relative=path.relative_to(source)
            if path.is_file() and allowed(relative):
                archive.write(path,str(Path(prefix)/relative))
                count+=1
    return count

def main():
    (DIST/'downloads').mkdir(exist_ok=True)
    examples=archive_tree(ROOT/'examples',DIST/'downloads/atlas_examples.zip','atlas_examples')
    (DIST/'README.md').write_text('''# ROS 2 综合离线教材

双击 index.html 打开交互教材，或双击 book.html 连续阅读全部正文。两个入口都无需互联网。book.html 还可在关闭 JavaScript 时阅读。

downloads/ 提供 Markdown、来源清单、完整通信工程和各章代码文件。control-lab/ 是配套 ros2_control 工坊。

浏览器若限制本地文件，可在本目录执行 python3 -m http.server 8766 --bind 127.0.0.1，然后打开 http://127.0.0.1:8766 。

学习进度保存在当前浏览器，可在“我的学习记录”导入导出。软件安装器、仿真环境、模型与数据需要单独准备；本包是离线教材，不是整个 ROS 2 软件镜像。

来源与许可见 THIRD_PARTY_NOTICES.md 和 LICENSE。
''')
    output=ROOT/'deliverables'
    output.mkdir(exist_ok=True)
    target=output/'ros2-learning-hub-offline.zip'
    files=archive_tree(DIST,target,'ros2-learning-hub')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/'SHA256SUMS').write_text(digest+'  '+target.name+'\n')
    print(json.dumps(dict(archive=str(target),bytes=target.stat().st_size,siteFiles=files,exampleFiles=examples,sha256=digest)))

if __name__=='__main__':main()
