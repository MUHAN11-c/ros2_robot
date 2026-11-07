#!/usr/bin/env python3
"""标准库读取已展开的小URDF，检查本章几何与对角惯量合同，不启动DDS。

输入：普通URDF（先展开Xacro）；输出树、尺寸、关节轴和惯量JSON。
边界：只处理盒体/圆柱与对角惯量；不是通用URDF验证器、碰撞或动力学仿真。
      check_urdf另用真正URDF解析器检查，几何正确仍需实际机械/标定验证。
"""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def values(text):
    result = [float(x) for x in text.split()]
    if not all(math.isfinite(x) for x in result):raise ValueError('数值必须有限')
    return result


def inspect_model(path):
    path = Path(path)
    if path.stat().st_size > 512 * 1024:raise ValueError('本例URDF不超过512KiB')
    model = ET.parse(path).getroot()
    if model.tag != 'robot':raise ValueError('需要普通robot根元素')
    links, joints = model.findall('link'), model.findall('joint')
    names = [x.get('name') for x in links]
    if not all(names) or len(set(names)) != len(names):raise ValueError('空或重复link')
    joint_names, children, adjacency, joint_rows = set(), set(), {}, []
    for joint in joints:
        name = joint.get('name')
        if not name or name in joint_names:raise ValueError('空或重复joint')
        joint_names.add(name)
        parent, child = joint.find('parent').get('link'), joint.find('child').get('link')
        if parent not in names or child not in names or child in children:raise ValueError('未知link或多父关系')
        children.add(child);adjacency.setdefault(parent, []).append(child)
        origin = joint.find('origin')
        xyz = values(origin.get('xyz', '0 0 0')) if origin is not None else [0.0]*3
        rpy = values(origin.get('rpy', '0 0 0')) if origin is not None else [0.0]*3
        if len(xyz) != 3 or len(rpy) != 3:raise ValueError('origin必须3维')
        axis = joint.find('axis')
        vector = values(axis.get('xyz')) if axis is not None else None
        if vector is not None and (len(vector) != 3 or not math.isclose(sum(x*x for x in vector), 1.0, abs_tol=1e-12)):
            raise ValueError('本例关节轴须显式单位向量')
        joint_rows.append(dict(name=name, type=joint.get('type'), parent=parent, child=child,
                               xyzM=xyz, rpyRad=rpy, axis=vector))
    roots = set(names) - children
    if len(roots) != 1:raise ValueError('不是单根树')
    visited, pending = set(), list(roots)
    while pending:
        node = pending.pop()
        if node in visited:raise ValueError('环')
        visited.add(node);pending.extend(adjacency.get(node, []))
    if visited != set(names):raise ValueError('存在不连通分支或环')
    inertias, geometry, no_inertia = [], [], []
    for link in links:
        for role in ('visual', 'collision'):
            for entry in link.findall(role):
                shape = entry.find('geometry')
                if shape is None or len(shape) != 1:raise ValueError('需单一盒体或圆柱geometry')
                item = list(shape)[0]
                dims = values(item.get('size')) if item.tag == 'box' else [float(item.get('radius')), float(item.get('length'))] if item.tag == 'cylinder' else []
                if len(dims) != (3 if item.tag == 'box' else 2) or not all(math.isfinite(x) and x > 0 for x in dims):raise ValueError('只检查正值盒体/圆柱')
                geometry.append(dict(link=link.get('name'), role=role, shape=item.tag, dimensionsM=dims))
        inertial = link.find('inertial')
        if inertial is None:no_inertia.append(link.get('name'));continue
        mass = float(inertial.find('mass').get('value'));tensor = inertial.find('inertia')
        diag = [float(tensor.get(n)) for n in ('ixx', 'iyy', 'izz')]
        off = [float(tensor.get(n)) for n in ('ixy', 'ixz', 'iyz')]
        if not math.isfinite(mass) or mass <= 0 or not all(math.isfinite(x) and x > 0 for x in diag):raise ValueError('质量/惯量须正且有限')
        if any(x != 0 for x in off):raise ValueError('本例仅检查对角惯量，不冒充一般特征值检验')
        if max(diag) > sum(diag) - max(diag) + 1e-12:raise ValueError('主惯量不满足三角关系')
        inertias.append(dict(link=link.get('name'), massKg=mass, diagonalKgM2=diag))
    return dict(root=next(iter(roots)), links=len(links), joints=joint_rows, inertias=inertias,
                frameLinksWithoutInertia=no_inertia, geometry=geometry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('urdf', type=Path)
    options = parser.parse_args()
    print(json.dumps(inspect_model(options.urdf), ensure_ascii=False, indent=2))


if __name__ == '__main__':main()
