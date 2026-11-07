#!/usr/bin/env python3
"""只读检查已关闭的小型教学bag，不启动ROS节点或DDS。

输入：bag目录、显式mcap/sqlite3插件以及最多读取的消息数。
输出：JSON元数据、每条接收时间ns、载荷SHA及白名单消息字段。
顺序：解析帮助→打开Reader→检查大小/数量→读回→finally关闭。
边界：调用者先停止录制器；metadata存在本身不能证明写入已经停止。
      只解释本例三种标准类型，不动态导入任意bag声明的类型。
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read_closed_bag(directory: Path, storage: str, max_messages: int = 1000):
    """接收时间为存储记录的ns，不把Header、发送时间或墙上经过时间混用。"""
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from geometry_msgs.msg import PointStamped
    from std_msgs.msg import Int32, String

    directory = directory.resolve(strict=True)
    if storage not in ('mcap', 'sqlite3') or not 1 <= max_messages <= 10000:
        raise ValueError('只允许两个插件及1..10000条读取上限')
    if not (directory / 'metadata.yaml').is_file():
        raise ValueError('需要已关闭录制的metadata.yaml')
    # 限制本例输入大小；这不是通用大规模数据工具或不可信文件沙箱。
    if sum(p.stat().st_size for p in directory.iterdir() if p.is_file()) > 16 * 1024 * 1024:
        raise ValueError('教学探针只读取总量不超过16MiB的单目录bag')
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(directory), storage_id=storage),
                rosbag2_py.ConverterOptions('', ''))
    try:
        meta = reader.get_metadata()
        types = {t.name: t.type for t in reader.get_all_topics_and_types()}
        known = {'geometry_msgs/msg/PointStamped': PointStamped,
                 'std_msgs/msg/Int32': Int32, 'std_msgs/msg/String': String}
        records = []
        while reader.has_next():
            if len(records) >= max_messages:
                raise ValueError('实际消息超过读取上限；不将截断数据称为完整检查')
            topic, raw, received_ns = reader.read_next()
            item = dict(topic=topic, receivedNs=received_ns,
                        payloadSha256=hashlib.sha256(raw).hexdigest())
            if types[topic] not in known:
                raise ValueError('本例未解释的消息类型：' + types[topic])
            message = deserialize_message(raw, known[types[topic]])
            if isinstance(message, PointStamped):
                item.update(sequence=int(message.point.x), xM=message.point.x, yM=message.point.y, zM=message.point.z,
                            headerNs=message.header.stamp.sec * 10**9 + message.header.stamp.nanosec,
                            frameId=message.header.frame_id)
            else:
                item['data'] = message.data
            records.append(item)
        counts = Counter(r['topic'] for r in records)
        return dict(storageId=meta.storage_identifier, metadataCount=meta.message_count,
                    startNs=meta.starting_time.nanoseconds, durationNs=meta.duration.nanoseconds,
                    metadataTopics={t.topic_metadata.name: t.message_count for t in meta.topics_with_message_count},
                    files=list(meta.relative_file_paths), counts=dict(counts), records=records)
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--storage', choices=['mcap', 'sqlite3'], required=True)
    parser.add_argument('--max-messages', type=int, default=1000)
    options = parser.parse_args()  # --help不需要安装ROS Python模块。
    if not 1 <= options.max_messages <= 10000:
        parser.error('max-messages必须在1..10000')
    print(json.dumps(read_closed_bag(options.directory, options.storage, options.max_messages),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
