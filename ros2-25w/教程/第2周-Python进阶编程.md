# 第2章 Python 进阶编程（函数/类/异常/并发）

> 本章对应课程第 2 周：把「会写脚本」升级为「会写工程代码」——函数封装、类与对象、异常处理、文件与 JSON、多进程/多线程。这些正是 rclpy 节点代码的骨架。

## 2.1 案例以及案例分析

**需求**：为机器人编写可复用的代码单元——运动指令封装（多值传参）、传感器家族（类 + 继承 + 多态）、配置读写（异常 + JSON）、并发采集（线程）。

## 2.2 知识点与实现

### 2.2.1 函数与传参

- `return x, y` 本质返回元组，可拆包接收；
- 不可变对象「传值效果」、可变对象「传引用效果」——函数内 `append` 外部可见；
- 缺省参数必须指向不可变对象（禁 `def f(lst=[])`）；
- `*args` 收集位置参数成元组、`**kwargs` 收集关键字参数成字典；`lambda` 用于短小回调。

### 2.2.2 类与三大特性

- 类 = 属性 + 方法；`__init__` 初始化；实例方法首参 `self`；
- 封装：`self.__x` 私有约定，公有方法控制访问；
- 继承：`class 子类(父类)` + `super().__init__()`；传递性/覆盖性/扩展性；
- 多态：鸭子类型——同名方法即可统一调用；
- 类属性（共享）/类方法（`@classmethod` 工厂）/静态方法（`@staticmethod` 工具）。

### 2.2.3 异常、文件与 JSON

- `try/except 类型 as e/else/finally`；`raise ValueError("速度不能为负")` 主动抛出；
- `with open(path, encoding="utf-8") as f:` 自动关文件；
- `json.load/dump(ensure_ascii=False, indent=2)`——机器人配置存取的标准做法。

### 2.2.4 多进程与多线程

- `multiprocessing.Process` 资源隔离（CPU 密集）；`threading.Thread` 共享内存（I/O 密集）；
- 多进程代码必须放在 `if __name__ == "__main__":` 内；
- GIL：CPU 密集任务多线程不会更快；共享数据用 `Lock` 或 `queue.Queue`。

## 2.3 运行效果（实测）

传感器家族综合案例（封装 + 继承 + 多态）：

```text
lidar0 校准完成
lidar0 [1.0, 2.0, 3.0]
imu0 校准完成
imu0 {'ax': 0.0, 'ay': 0.0, 'az': 9.8}
```

## 2.4 端到端实战（实测）：WaypointManager

> **视频对照**：课程 `类综合练习` 的 Game 类（类属性 `top_score` + 类方法 + 实例方法）已按视频逐字复现，输出与课程终端一致（`帮助信息 / 0 / 小明开始了游戏。得分为120 / 当前最高分120`），见《端到端核对报告》基础篇表。

把函数、类、异常、JSON 串成完整程序：类封装航点表，重复名/非法坐标抛异常，`dumps/loads` 演示 JSON 持久化语义（工程中把快照写入磁盘文件即可）。

```python
# manager.py（节选核心）
import json

class WaypointManager:
    def __init__(self):
        self.waypoints = {}                      # name -> (x, y)

    def add(self, name, x, y):
        if name in self.waypoints:
            raise ValueError(f"航点 {name} 已存在")
        if x < 0 or y < 0:
            raise ValueError("坐标必须非负")
        self.waypoints[name] = (x, y)

    def list_sorted(self):
        return sorted(self.waypoints.items(), key=lambda kv: kv[1][0])

    def dumps(self):
        return json.dumps({k: list(v) for k, v in self.waypoints.items()},
                          ensure_ascii=False, indent=2)

    def loads(self, text):
        data = json.loads(text)
        self.waypoints = {k: (float(v[0]), float(v[1])) for k, v in data.items()}

if __name__ == "__main__":
    mgr = WaypointManager()
    mgr.add("w0", 0.0, 0.0)
    mgr.add("w1", 1.5, 0.0)
    try:
        mgr.add("w1", 2.0, 2.0)                  # 重复名 -> 异常
    except ValueError as e:
        print("捕获:", e)
    try:
        mgr.add("w2", -1.0, 0.0)                 # 非法坐标 -> 异常
    except ValueError as e:
        print("捕获:", e)
    snapshot = mgr.dumps()                       # 序列化快照
    print("快照字节 =", len(snapshot.encode()))
    mgr2 = WaypointManager()                     # 新实例反序列化恢复
    mgr2.loads(snapshot)
    for name, (x, y) in mgr2.list_sorted():
        print(f"  {name}: ({x:.2f}, {y:.2f})")
```

实测（Python 3.12）：

```text
捕获: 航点 w1 已存在
捕获: 坐标必须非负
快照字节 = 66
  w0: (0.00, 0.00)
  w1: (1.50, 0.00)
```

> 提示：写入磁盘时把 `dumps()` 的结果用 `open(path, "w", encoding="utf-8")` 落盘即可；对外部传入的路径应先规范化并校验其落在允许目录内（防路径穿越），这是工程上的标准做法。

## 2.5 本章小结

- 类与继承是 rclpy 节点的直接原型（`class MyNode(Node)`、`super().__init__()`）；
- 异常保证节点不死：回调里 `try/except` 兜底并记日志，而不是把 executor 带崩；
- JSON/YAML 配置 + 异常处理是参数管理的模板；
- 摄像头等 I/O 采集放独立线程、主线程跑 spin——本周并发知识在 ROS2 里的直接落点。
