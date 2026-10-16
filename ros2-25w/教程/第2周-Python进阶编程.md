# 第2章 Python 进阶编程（函数/类/异常/并发）

> 本章对应课程第 2 周：把「会写脚本」升级为「会写工程代码」——函数封装、类与对象、异常处理、文件与 JSON、多进程/多线程。这些正是 rclpy 节点代码的骨架。
>
> 所属阶段：阶段1 ROS2 开发必备基础之 Python 数据处理与计算机视觉 ｜ 视频 62 个 ｜ 时长约 7h12m ｜ 难度：进阶

## 2.1 本周概览与课时结构

本周把「会写脚本」升级为「会写工程代码」：用函数（function）封装可复用逻辑、用类（class）组织数据与行为、用异常（exception）让程序健壮、用文件与 JSON 做持久化、用多进程/多线程做并发。这些正是 ROS2 节点代码的骨架——rclpy 节点是一个类，回调是方法，参数配置走 JSON/YAML，图像采集常跑在独立线程里。学完本周，你能把上周的成绩统计脚本重构成「类 + 配置文件 + 异常处理 + 并发录入」的完整小程序。

读完本章，你应当达到四条验收线：

1. 会用函数（缺省参数、`*args`/`**kwargs`、`lambda`）封装可复用逻辑；
2. 会用类 + 封装/继承/多态描述「机器人、传感器」这类事物；
3. 会用 `try/except` 与 `raise` 让程序优雅降级，用 JSON 做配置持久化；
4. 会区分多进程与多线程的适用场景，并知道 `if __name__ == "__main__":` 为什么必写。

本章课程共 5 课 / 62 个视频 / 约 7h12m，结构如下：

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 函数传参深度剖析与多值传参技巧 | 1 节（13 个视频） | 1h18m | 函数定义与返回值、全局/局部变量、缺省参数、`*args`/`**kwargs` 与 lambda |
| 第2课 面向对象编程之"类"的详解与实战 | 1 节（9 个视频） | 1h25m | 类与对象、初始化方法，跑步/家具摆放/吃鸡案例层层实战 |
| 第3课 私有特性、继承机制与多态性全面解析 | 2 节（14 个视频） | 1h32m | 私有属性方法、继承三特性（传递/覆盖/扩展）、多态、类属性与类方法 |
| 第4课 异常处理策略与文件操作 | 2 节（15 个视频） | 1h43m | try-except 体系、主动抛出、模块导入、文件读写与 JSON 读写 |
| 第5课 多任务、多进程与多线程 | 2 节（11 个视频） | 1h12m | 多任务概念、multiprocessing 与 threading、传参与结束时机 |

学习节奏建议：第 1 课的传参细节（可变对象、缺省参数）和第 5 课的 GIL/竞态是最容易「看懂但写错」的部分，务必对照 2.3 与 2.7 自测；第 2-3 课的类案例建议在 IDE 里完整敲一遍再继续。

## 2.2 知识点梳理

### 2.2.1 第1课 函数传参深度剖析与多值传参技巧

- **核心概念**：函数（function）把一段有名字的代码打包，`def 函数名(参数):` 定义、`函数名(实参)` 调用。价值是**提高效率与代码重用**——写一次、到处调用，改一处、处处生效。
- **参数与返回值**：形参（定义处）与实参（调用处）一一对应；`return` 返回结果并结束函数，`return` 后可跟多个值（本质是元组）：`return x, y` → `a, b = f()`；不写 `return` 或裸 `return` 则返回 `None`。
- **函数嵌套与作用域**：函数内部可以调用其他函数；变量分全局（global，模块顶层）与局部（函数内），局部变量随函数调用创建、调用结束销毁，函数内默认只能读全局变量；要改全局用 `global 变量名` 声明。**能不用 global 就不用**，优先用参数和返回值传递数据。
- **传参细节**：数字、字符串等不可变对象「传值效果」——函数内改了不影响外部；列表、字典等可变对象「传引用效果」——函数内 `append` 外部可见。这与第 1 周的可变/不可变呼应，是排查 bug 的关键直觉。
- **缺省参数（default arguments）**：`def move(speed, dist=1.0):`，调用时可省略 `dist`。注意缺省值必须指向不可变对象（绝不要写 `def f(lst=[])`），且缺省参数必须放在非缺省参数之后。
- **多值传参**：`*args` 收集位置参数成元组，`**kwargs` 收集关键字参数成字典；`def f(a, *args, **kwargs):`。调用侧可用 `f(*lst)`、`f(**dic)` 反向解包。这是阅读 ROS2/框架源码（大量 `*args, **kwargs` 透传）的必备能力。
- **匿名函数 lambda**：`lambda 参数: 表达式`，适合做 `sorted(key=lambda x: x[1])`、`map`/`filter` 里的短小函数；复杂逻辑仍应写 `def`。

### 2.2.2 第2课 面向对象编程之"类"的详解与实战

- **核心概念**：类（class）= 属性（数据）+ 方法（行为）的模板，对象（object/实例）是按模板造出来的具体事物。「万物皆对象」：一台机器人有 `name/speed` 属性与 `move/stop` 方法，就是 `Robot` 类的实例。
- **基本语法**：`class Robot:` 下定义方法，所有实例方法第一个参数是 `self`（代表调用者自己）；创建实例 `r = Robot()`，调用方法 `r.move()`，访问属性 `r.name`。
- **初始化函数 `__init__`**：构造方法，创建实例时自动调用，用来初始化属性：`def __init__(self, name): self.name = name`。它是「每个对象出生时的登记表」。
- **类的练习主线**（跑步、家具摆放、吃鸡案例）：从「给对象加属性、调方法」到「多个对象互相配合」（家具摆放：房间对象聚合多个家具对象；吃鸡案例：玩家、武器、背包的组合与状态变化）——本质是练习「用对象描述世界」的建模思维，也为后面阶段把「机器人、传感器、任务」建模成类打样。
- **建模三问**：这个事物有哪些属性（名词）？有哪些行为（动词）？和其他事物是什么关系（组合/继承）？

### 2.2.3 第3课 私有特性、继承机制与多态性全面解析

- **核心概念**：封装（Encapsulation）、继承（Inheritance）、多态（Polymorphism）是面向对象三大特性。
- **私有属性与私有方法**：名字以双下划线开头（`self.__score`、`def __check(self)`）约定为私有，类外不能直接访问（Python 通过名称改写 `_类名__score` 实现，是约定而非强约束）。公有方法内部调用私有方法，形成「外部只看接口、内部随意改」的封装。提供 getter/setter（或 `@property`）控制访问与校验。
- **继承**：`class 子类(父类):` 获得父类属性方法，减少重复代码；`super().__init__()` 调父类初始化。三大特性：
  - **传递性**：孙子类自动继承爷爷类的能力；
  - **覆盖性（重写 override）**：子类同名方法优先执行子类版本；
  - **扩展性**：子类在父类基础上新增属性与方法。
- **父类私有成员**：子类不能直接访问父类的私有属性/方法，只能通过父类的公有方法间接使用。
- **多态**：不同子类对同一方法名给出不同实现，调用方按统一接口使用（如 `def make_sound(animal): animal.speak()`，猫狗各有实现）。Python 的多态靠「鸭子类型（duck typing）」：只要有同名方法就能统一调用，无需显式声明接口。
- **类的补充**：
  - **类属性**：定义在类中、所有实例共享（`Robot.count = 0`），适合存「共性数据」；实例属性则每个对象一份。
  - **类方法**：`@classmethod` 修饰，第一个参数是 `cls`（类本身），用 `Robot.create_from_dict(d)` 这类「工厂方法」最合适。
  - **记录实例化次数**：在 `__init__` 里对类属性 `count` 累加，是类属性的经典用法。
  - **静态方法**：`@staticmethod` 修饰，不需要 `self`/`cls`，就是「放在类里的普通工具函数」（如单位换算）。

### 2.2.4 第4课 异常处理策略与文件操作

- **核心概念**：异常（exception）是运行时错误；不处理就崩溃，处理了程序可以优雅降级。
- **try-except 体系**：`try:` 放可能出错的代码，`except 错误类型 as e:` 捕获并处理，`else:` 无异常时执行，`finally:` 无论如何都执行（适合释放资源）。可以多个 `except` 分别处理 `ValueError`、`ZeroDivisionError`、`FileNotFoundError` 等；`except Exception` 兜底但不宜滥用。
- **异常的传递**：函数内未捕获的异常会沿调用栈向上传递，直到被捕获或程序终止；因此「底层函数抛异常、上层统一处理」是常见分层策略。
- **主动抛出**：`raise ValueError("速度不能为负")`，常用于参数校验；自定义异常继承 `Exception`。
- **模块与包**：`import 模块`、`from 模块 import 名字`（部分导入）、`import 包.模块`；`as` 起别名（`import numpy as np` 是行业惯例）；`if __name__ == "__main__":` 保护「被导入时不执行测试代码」——多进程编程中更是必写。
- **文件读写**：
  - `f = open(path, "r"/"w"/"a")`，模式 r 读、w 覆写（文件不存在则创建）、a 追加；推荐 `with open(...) as f:` 自动关文件；
  - `f.read()` 全读、`f.readline()` 逐行、`f.readlines()` 读成行列表、`for line in f:` 逐行迭代（大文件首选）；
  - 写：`f.write(字符串)`、`f.writelines(列表)`，注意写入不含换行符需自己加 `\n`；
  - `encoding="utf-8"` 显式指定编码，避免中文乱码。
- **JSON 读写**：`import json`；`json.load(f)` 读文件 / `json.loads(s)` 读字符串 / `json.dump(data, f, ensure_ascii=False, indent=2)` 写文件。JSON 只认 dict/list/str/int/float/bool/None，元组会被转成列表。机器人配置（速度上限、PID 参数、航点表）用 JSON 存取是标准做法。

### 2.2.5 第5课 多任务、多进程与多线程

- **核心概念**：多任务（multitasking）指同时推进多件事；并发的实现有进程（process）与线程（thread）两条路。
- **`__name__` 属性**：直接运行脚本时为 `"__main__"`，被导入时为模块名。多进程（Windows/macOS 上的 spawn 启动方式）要求创建子进程的代码必须放在 `if __name__ == "__main__":` 内，否则无限递归创建进程。
- **多进程**：`from multiprocessing import Process`，`p = Process(target=函数, args=(参数,))`，`p.start()` 启动、`p.join()` 等待结束。进程有独立 PID（`os.getpid()`），资源隔离、稳定性好，但创建/切换开销大、进程间通信（IPC）要借助队列/管道。
- **多进程传参与结束时机**：位置参数用 `args=(元组,)`，关键字参数用 `kwargs={字典}`；主进程默认等子进程结束才退出，`p.terminate()` 可强制结束；守护进程 `p.daemon = True` 随主进程退出。
- **多线程**：`import threading`，`t = threading.Thread(target=函数, args=(...))`，同样有 `start()/join()/daemon`。线程共享进程内存、开销小，适合 I/O 密集任务（网络收发、读传感器、录视频）。
- **GIL 与执行顺序**：CPython 有全局解释器锁（GIL），同一时刻只有一个线程执行字节码，**CPU 密集任务多线程不会更快**（用多进程或 NumPy 向量化替代）；线程启动顺序不保证、执行顺序无序，需要顺序性时用 `join()`、`Queue` 或锁（`threading.Lock()`）保护共享数据。

两类并发模型的选型对照：

| 维度 | multiprocessing（进程） | threading（线程） |
|---|---|---|
| 内存 | 隔离，通信靠队列/管道 | 共享，需 Lock/Queue 保护 |
| 开销 | 创建/切换大 | 小 |
| 适用 | CPU 密集（大量计算） | I/O 密集（网络、磁盘、摄像头读帧） |
| 必写 | `if __name__ == "__main__":` | 建议写（防导入副作用） |

## 2.3 重点与难点

1. **可变对象作函数参数**：函数内修改列表/字典会影响调用方；不想影响就先 `copy()`。缺省参数写 `def f(lst=[])` 会让默认列表「越用越长」，必须写 `def f(lst=None): lst = [] if lst is None else lst`。
2. **`self` 到底是什么**：`r.move()` 等价于 `Robot.move(r)`，`self` 就是实例自己；初学者最常见的报错 `missing 1 required positional argument: 'self'` 就是用类名直接调用了实例方法。
3. **私有是约定不是铁律**：Python 的 `__xxx` 只做名称改写（`_类__xxx`），外部仍可强行访问；尊重约定是团队协作的基本素养。
4. **except 要具体**：捕获 `Exception` 会把 bug 也吞掉；先分类型捕获并记录 `str(e)`，最后才考虑兜底。
5. **多线程的竞态条件（race condition）**：两个线程同时 `count += 1` 会丢更新，需用 `Lock()` 或改用 `queue.Queue`（线程安全）传递数据。

> **注意：** 多进程代码必须放在 `if __name__ == "__main__":` 里，Windows/macOS 用户漏写会得到「无限创建子进程直到死机」的经典事故。

## 2.4 代码与命令实战

```python
# 示例1（场景：多值传参与缺省参数 —— 通用的机器人运动指令封装）
def send_cmd(linear=0.0, angular=0.0, *log_tags, **extra):
    """linear: m/s, angular: rad/s; 额外标签与参数仅做演示打印。"""
    msg = f"cmd: linear={linear:.2f}, angular={angular:.2f}"
    if log_tags:
        msg += f" tags={log_tags}"            # *args 是元组
    if extra:
        msg += f" extra={extra}"              # **kwargs 是字典
    print(msg)

send_cmd(1.0, 0.5)                            # 用缺省值
send_cmd(0.5, 0.0, "slow", "safe", level=3)   # 多值传参
opts = {"linear": 0.2, "angular": -0.1}
send_cmd(**opts)                              # 字典解包
```

```python
# 示例2（场景：类与封装/继承/多态 —— 传感器家族）
class Sensor:
    def __init__(self, name, rate_hz):
        self.name = name
        self.rate_hz = rate_hz
        self.__calibrated = False            # 私有属性

    def calibrate(self):                     # 公有方法操作私有属性
        self.__calibrated = True
        print(f"{self.name} 校准完成")

    def read(self):                          # 多态接口：子类各自实现
        raise NotImplementedError

class Lidar(Sensor):
    def read(self):
        return [1.0, 2.0, 3.0]

class Imu(Sensor):
    def read(self):
        return {"ax": 0.0, "ay": 0.0, "az": 9.8}

def report(sensor):                          # 统一接口，多态生效
    print(sensor.name, sensor.read())

for s in (Lidar("lidar0", 10), Imu("imu0", 100)):
    s.calibrate()
    report(s)
```

```python
# 示例3（场景：类属性/类方法/静态方法 —— 记录实例化次数）
class Robot:
    count = 0                                # 类属性：所有实例共享

    def __init__(self, name):
        Robot.count += 1
        self.name = name

    @classmethod
    def create_pair(cls):                    # 工厂方法
        return cls("r1"), cls("r2")

    @staticmethod
    def deg2rad(deg):                        # 与实例无关的工具函数
        return deg * 3.14159265 / 180.0

r1, r2 = Robot.create_pair()
print(Robot.count, Robot.deg2rad(90))        # 2 1.570796325
```

```python
# 示例4（场景：异常处理 + JSON 配置读写）
import json

DEFAULT = {"max_speed": 1.5, "rate_hz": 20}

def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print("配置不存在，使用默认值")
        cfg = DEFAULT.copy()
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件损坏: {e}")
    if cfg.get("max_speed", 0) <= 0:
        raise ValueError("max_speed 必须为正数")
    return cfg

cfg = load_config("robot_config.json")       # 文件不存在也安全
with open("robot_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)   # 写回 JSON
print(cfg)
```

```python
# 示例5（场景：多线程并发采集 —— 必须放在 __main__ 保护下）
import threading, time

def collect(name, n):
    for i in range(n):
        print(f"[{name}] sample {i}")
        time.sleep(0.1)                      # 模拟 I/O 等待

if __name__ == "__main__":
    ts = [threading.Thread(target=collect, args=(f"cam{i}", 3)) for i in range(2)]
    for t in ts:
        t.start()                            # 启动顺序不等于执行顺序
    for t in ts:
        t.join()                             # 等两个采集线程都结束
    print("采集完成")
```

```bash
# 示例6（场景：命令行验证脚本可运行）
$ python3 week2_demo.py
$ python3 -c "import json; print(json.loads('{\"a\": 1}'))"
```

## 2.5 运行效果（实测）

传感器家族综合案例实测（对应 2.4 示例2：封装 + 继承 + 多态）：

```text
lidar0 校准完成
lidar0 [1.0, 2.0, 3.0]
imu0 校准完成
imu0 {'ax': 0.0, 'ay': 0.0, 'az': 9.8}
```

把函数、类、异常、JSON 串成完整程序的端到端实战——WaypointManager：类封装航点表，重复名/非法坐标抛异常，`dumps/loads` 演示 JSON 持久化语义（工程中把快照写入磁盘文件即可）。

> **视频对照**：课程 `类综合练习` 的 Game 类（类属性 `top_score` + 类方法 + 实例方法）已按视频逐字复现，输出与课程终端一致（`帮助信息 / 0 / 小明开始了游戏。得分为120 / 当前最高分120`），见《端到端核对报告》基础篇表。

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

读输出要点：两条 `ValueError` 分别对应「重复名」与「非法坐标」校验；`快照字节 = 66` 即 `dumps()` 序列化后的 JSON 文本长度，`mgr2.loads(snapshot)` 在全新实例上完整恢复了 `w0/w1`——这就是 JSON 持久化「存 → 读」的最小闭环。

> 提示：写入磁盘时把 `dumps()` 的结果用 `open(path, "w", encoding="utf-8")` 落盘即可；对外部传入的路径应先规范化并校验其落在允许目录内（防路径穿越），这是工程上的标准做法。

## 2.6 与 ROS2 / 机器人开发的关联

1. **rclpy 节点就是类**：`class MinimalPublisher(Node)` 继承自 `rclpy.node.Node`，`super().__init__('node_name')`、实例属性存状态、方法作回调——本周的类与继承知识直接对口；自定义节点间的复用关系（如「巡检节点继承移动基类」）靠继承与多态扩展。
2. **回调与多值传参**：话题回调 `def listener_cb(self, msg)` 中的 `msg` 是消息类实例；写工具函数时常要 `*args, **kwargs` 透传 QoS 配置（`QoSProfile(depth=10, ...)`），看懂框架源码离不开多值传参。
3. **异常保证节点不死**：传感器读数失败、服务调用超时、参数非法都要 `try/except` 兜底并 `get_logger().error()` 记录，而不是让回调抛异常把整个 executor 带崩。
4. **JSON/YAML 配置与参数**：机器人的 PID 参数、航点、阈值常存 JSON/YAML，节点启动时加载、运行中更新保存——本周的 `json.load/dump` + 异常处理就是模板。`launch` 文件启动时传参也常用 JSON 文件。
5. **多线程与图像采集**：摄像头采集（17m06s 的「摄像头和视频」在第 3 周展开）常放独立线程，主线程跑 `rclpy.spin()`；注意 GIL 下图像处理交给 OpenCV/NumPy 的 C 实现，线程只做 I/O；共享变量用 `Lock` 或 `queue.Queue`，避免回调与采集线程抢数据。

## 2.7 自测与练习（含参考答案要点）

1. **题目**：写一个函数 `stats(*values, unit="m")`，返回 `(个数, 最大值, 最小值)`，并在无参数时返回 `(0, None, None)`；解释为什么 `return a, b, c` 可以被 `n, hi, lo = stats(1, 2, 3)` 拆包。
2. **题目**：`def add(item, bucket=[])` 有什么隐患？给出正确写法。
3. **动手任务**：把上周的「航点管理」升级为 `WaypointManager` 类：属性存字典，方法有 `add(name, x, y)`、`remove(name)`、`list_sorted()`，`name` 重复时 `raise ValueError`；再写一个 JSON 持久化 `save(path)/load(path)`。验收标准：非法输入被异常捕获并给出提示，`save` 后重启脚本能 `load` 回原数据。
4. **题目**：两个线程各对共享变量 `count` 做 10 万次 `count += 1`，为什么结果常常小于 20 万？如何修正？

> 参考答案要点：1) `def stats(*values, unit="m")` 中 `*values` 是元组，空元组时返回 `(0, None, None)`；多值返回本质是元组，元组可直接拆包；2) 默认列表只在函数定义时创建一次，多次调用共享同一个列表，应写 `def add(item, bucket=None): bucket = [] if bucket is None else bucket`；3) 类中用 `self.waypoints` 字典 + `if name in self.waypoints: raise ValueError`，`json.dump/load` 存取，`try/except (ValueError, FileNotFoundError)` 处理；4) 竞态条件：`count += 1` 不是原子操作，需 `lock = threading.Lock()` 并在 `with lock:` 中累加，或用 `multiprocessing`/NumPy 向量化规避 GIL。

## 2.8 常见问题（FAQ）

- **Q：`*args` 和 `**kwargs` 到底怎么用？** A：定义时收集富余参数（元组/字典），调用时解包（`f(*lst)`、`f(**dic)`）。记法：一个星号管位置参数，两个星号管关键字参数。
- **Q：`global` 声明是必须的吗？** A：读全局变量不需要；在函数内**重新绑定**全局变量才需要 `global`。但更推荐用参数和返回值传数据，全局变量越少越好。
- **Q：`__init__` 和 `__str__` 有什么区别？** A：`__init__` 是构造初始化，创建实例时自动调用；`__str__` 定义 `print(实例)` 的输出文本。二者都是「魔法方法」，由解释器在特定时机自动调用。
- **Q：多进程和多线程怎么选？** A：CPU 密集（大量计算）→ 多进程；I/O 密集（网络、磁盘、摄像头读帧）→ 多线程。Python 里想榨干 CPU，首选 NumPy 向量化而不是开线程。
- **Q：为什么文件操作要用 `with`？** A：`with open(...)` 在代码块结束（包括发生异常时）自动关闭文件，避免忘记 `f.close()` 导致句柄泄漏或数据没刷盘。

## 2.9 本章小结

- 类与继承是 rclpy 节点的直接原型（`class MyNode(Node)`、`super().__init__()`）；
- 异常保证节点不死：回调里 `try/except` 兜底并记日志，而不是把 executor 带崩；
- JSON/YAML 配置 + 异常处理是参数管理的模板；
- 摄像头等 I/O 采集放独立线程、主线程跑 spin——本周并发知识在 ROS2 里的直接落点。

下一章把 Python 用到真正的「数据」上：NumPy 数组与 OpenCV 图像，打开机器人感知层的大门。
