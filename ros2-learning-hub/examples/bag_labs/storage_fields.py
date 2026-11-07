#!/usr/bin/env python3
"""写入两个单消息bag，区分Header、接收记录时间和发送记录时间。

输入：尚不存在的输出子目录；不启动DDS、不接设备。
输出：两个实际文件及其字段检查结果。时间均为整数ns。
这是显式四参数Writer的受控输入，不能冒充网络传输延迟测量。
MCAP解析器仅支持本例noChunking小文件；通用读取用inspect_bag.py。
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tempfile


def mcap_messages(file: Path):
    """按MCAP v0记录头读取无分块Message；不解压、不读取外部引用。"""
    if file.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('只允许本例不超过2MiB的文件')
    raw = file.read_bytes()
    magic = b'\x89MCAP0\r\n'
    if not raw.startswith(magic) or not raw.endswith(magic):
        raise ValueError('不是预期MCAP v0文件')
    offset, messages = len(magic), []
    while offset < len(raw) - len(magic):
        if offset + 9 > len(raw) - len(magic):raise ValueError('记录头截断')
        opcode, length = struct.unpack_from('<BQ', raw, offset)
        offset += 9
        end = offset + length
        if end > len(raw) - len(magic):raise ValueError('记录长度越界')
        if opcode == 0x06:raise ValueError('本例不处理Chunk；检查noChunking配置')
        if opcode == 0x05:
            if length < 22:raise ValueError('Message记录不足22字节')
            channel, sequence, log_ns, publish_ns = struct.unpack_from('<HIQQ', raw, offset)
            messages.append(dict(channel=channel, sequence=sequence, logTimeNs=log_ns,
                                 publishTimeNs=publish_ns,
                                 payloadSha256=hashlib.sha256(raw[offset + 22:end]).hexdigest()))
        offset = end
    return messages


def probe(directory: Path):
    """两个插件使用同一序列化载荷，避免把不同消息当成格式差异。"""
    import rosbag2_py
    from geometry_msgs.msg import PointStamped
    from rclpy.serialization import serialize_message
    from inspect_bag import read_closed_bag
    # CLI也允许相对新目录；先转绝对路径，后续只读SQLite URI才有明确定义。
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    message = PointStamped()
    message.header.frame_id = 'synthetic_frame'
    message.header.stamp.sec = 7  # Header采样时间7s，故意不同于下面两个记录时间。
    message.point.x = 1.0  # 合成位置m，非设备测量。
    payload = serialize_message(message)
    recv_ns, send_ns = 10_000_000_000, 9_000_000_000
    result = dict(headerNs=7_000_000_000, explicitReceivedNs=recv_ns, explicitSentNs=send_ns,
                  payloadSha256=hashlib.sha256(payload).hexdigest(), storages={})
    for storage in ('sqlite3', 'mcap'):
        target = directory / storage
        options = rosbag2_py.StorageOptions(uri=str(target), storage_id=storage)
        if storage == 'mcap':
            options.storage_config_uri = str(Path(__file__).with_name('mcap_no_chunk.yaml'))
        writer = rosbag2_py.SequentialWriter()
        writer.open(options, rosbag2_py.ConverterOptions('', ''))
        try:
            writer.create_topic(rosbag2_py.TopicMetadata(0, '/bag_lab/input',
                                'geometry_msgs/msg/PointStamped', 'cdr'))
            writer.write('/bag_lab/input', payload, recv_ns, send_ns)
        finally:
            writer.close()  # 关闭后才读取metadata/文件；不靠析构时机刷新。
        readback = read_closed_bag(target, storage)
        assert readback['metadataCount'] == len(readback['records']) == 1
        item = readback['records'][0]
        assert item['receivedNs'] == recv_ns and item['headerNs'] == result['headerNs']
        assert item['payloadSha256'] == result['payloadSha256']
        data = dict(readback=readback)
        if storage == 'sqlite3':
            # URI只读模式，不修改数据库；当前messages表仅存一个timestamp。
            db = next(target.glob('*.db3'))
            with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as connection:
                columns = [r[1] for r in connection.execute('PRAGMA table_info(messages)')]
                rows = list(connection.execute('SELECT timestamp,data FROM messages'))
            assert columns == ['id', 'topic_id', 'timestamp', 'data']
            assert len(rows) == 1 and rows[0][0] == recv_ns and rows[0][1] == payload
            data.update(columns=columns, storedTimestampNs=rows[0][0], hasSeparateSentColumn=False)
        else:
            messages = mcap_messages(next(target.glob('*.mcap')))
            assert len(messages) == 1
            assert messages[0]['logTimeNs'] == recv_ns and messages[0]['publishTimeNs'] == send_ns
            assert messages[0]['payloadSha256'] == result['payloadSha256']
            data['messages'] = messages
        result['storages'][storage] = data
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='尚不存在的新目录；省略则在/tmp中新建')
    options = parser.parse_args()
    output = options.output or Path(tempfile.mkdtemp(prefix='ros2-bag-fields-')) / 'fields'
    if output.exists():parser.error('输出目录已存在，避免覆盖实验')
    print(json.dumps(probe(output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
