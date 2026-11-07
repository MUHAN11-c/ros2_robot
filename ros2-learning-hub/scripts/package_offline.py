#!/usr/bin/env python3
"""生成便携教材与原创工程包；第三方原始资料继续独立保存。"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

def allowed(path):
    """输入为相对路径；排除缓存、编译产物和本机身份配置。"""
    return not any(p.startswith('.') or p in ('__pycache__', 'build', 'install', 'log', 'node_modules')
                   or p.endswith('.egg-info') for p in path.parts) and path.suffix != '.pyc'

def archive_tree(source,target,prefix,overrides=None):
    # overrides 只替换归档内内容，不改工作区：便携包旁边未必有原始资料。
    count=0
    overrides=overrides or {}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            relative=path.relative_to(source)
            if path.is_file() and allowed(relative) and relative.name!='reader-preview.html':
                name=(Path(prefix)/relative).as_posix()
                if relative.as_posix() in overrides:archive.writestr(name,overrides[relative.as_posix()])
                else:archive.write(path,name)
                count+=1
    return count

def main():
    data=json.loads((DIST/'content.js').read_text().split('window.ROS2Hub = ',1)[1].rsplit(';',1)[0])
    overview=f"包含 {len(data['lessons'])} 章、{len(data['comparisons'])} 组实现对照、{len(data['apiReferences'])} 组 API 表、{data['meta']['equationCount']} 个附解释公式、{data['meta']['exerciseCount']} 道练习与答案及原创图解。"
    (DIST/'downloads').mkdir(exist_ok=True)
    examples=archive_tree(ROOT/'examples',DIST/'downloads/atlas_examples.zip','atlas_examples')
    foundation=archive_tree(ROOT/'foundation-examples',DIST/'downloads/foundation_examples.zip','foundation_examples')
    archive_tree(ROOT/'validation-evidence',DIST/'downloads/validation-evidence.zip','validation-evidence')
    (DIST/'VALIDATION.md').write_text((ROOT/'VALIDATION.md').read_text(),encoding='utf-8')
    (DIST/'README.md').write_text('''# ROS 2 综合离线教材

双击 index.html 打开左侧章节树与正文阅读器；双击 book.html 连续阅读全书，后者无需 JavaScript。
__CONTENT_OVERVIEW__

downloads/ 提供 Markdown 全文、章节代码、通信与数值实验工程、10 包基础工作空间、来源索引和验证记录。
代码保留中文注释，标明完整文件、局部片段、终端命令或概念示意。运行依赖和验证边界请先读工程 README。
control-lab/ 是配套 ros2_control 工坊，来源与许可独立。

浏览器若限制本地文件，可在本目录执行 python3 -m http.server 8766 --bind 127.0.0.1，然后打开 http://127.0.0.1:8766 。

学习进度保存在浏览器，可在“我的进度”导入导出 JSON。
便携包只含教材、原创示例与原始资料元数据；不含 ROS 安装器、仿真镜像和第三方数 GiB 源码。
如需原始资料，额外复制工作区的 references、ros2_tutorial、ROS2_Tuition、Robotics_Tutorial 等独立参考目录；
在完整工作区运行 python3 ros2-learning-hub/scripts/serve_local.py 可在站内查看其文件。
参考内容对应表标明核读范围，主题映射不表示原始全文已逐段编入教材。
验证范围见 downloads/validation-evidence.zip 与示例 README；本轮未运行完整 Nav2/Gazebo/MoveIt 仿真或硬件。

来源与许可见 THIRD_PARTY_NOTICES.md 和 LICENSE。
'''.replace('__CONTENT_OVERVIEW__',overview))
    output=ROOT/'deliverables'
    output.mkdir(exist_ok=True)
    target=output/'ros2-learning-hub-offline.zip'
    files=archive_tree(DIST,target,'ros2-learning-hub',{
        'environment.js':'/* 便携阅读包：第三方原始资料需另外复制。 */\nwindow.ROS2Environment = {workspace:false};\n'
    })
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/'SHA256SUMS').write_text(digest+'  '+target.name+'\n')
    print(json.dumps(dict(archive=str(target),bytes=target.stat().st_size,siteFiles=files,exampleFiles=examples,foundationFiles=foundation,sha256=digest)))

if __name__=='__main__':main()
