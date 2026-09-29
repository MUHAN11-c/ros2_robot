# Python 与 NumPy 入门（面向机器人）

> 本章是"Python 与工具链"两章中的第一章。上一章你用 C++ 和 STL 写完了实战小项目——从这一章起，我们给工具箱添上第二件兵器。

## 本章导航

**上一章**：[STL 容器算法与实战小项目](../00_零基础入门/60_STL容器算法与实战小项目.md)

**本章讲什么？**
Python 语言的快速入门——但不从头讲起，而是全部用"和 C++ 对比"的方式讲：你已经会的概念一笔带过，只讲不一样的地方。然后是科学计算库 NumPy 和画图库 matplotlib。

**为什么要学它？**
机器人开发中，C++ 负责"跑在机器人身上的"实时控制，Python 负责"围在机器人周围的"一切：数据处理、仿真、画图、ROS2 工具链、强化学习，几乎全是 Python 的天下。不会 Python，等于一只手被绑住。

**学完能做什么？**
独立搭好 Python 环境；读懂并写出常见的 Python 小程序；用 NumPy 对传感器数据做统计和矩阵运算；画一张能放进实验报告的图。

**本章在路线图中的位置**

```
[00_零基础入门] ──► [02_C++基础与进阶] ──► [15_Python与工具链] ──► [07_机器人学导论]
   已完成              C++/STL 已完成         ★ 你在这里（本章 + 下一章）    下一步
```

| 学习方式 | 时间 | 适合谁 |
|---|---|---|
| 首次学习（边读边敲代码） | 3-4 小时 | 第一次系统接触 Python |
| 快速复习 | 45-60 分钟 | 学过 Python，主要来查 NumPy 用法 |

## 1. 为什么机器人开发离不开 Python

先看一组真实的使用场景，它们全部由 Python 完成：

- **写脚本**：批量重命名文件、把实验数据从一种格式转成另一种、一键跑完一整组实验
- **数据处理**：激光雷达、IMU 采回来的成千上万条读数，清洗、统计、分析
- **仿真与可视化**：生成测试数据、把结果画成曲线图
- **ROS2 工具链**：rqt 图形工具、数据录制回放等大量配套工具是 Python 写的
- **机器学习 / 强化学习**：PyTorch 等整个生态都以 Python 为主语言

那 C++ 呢？一句话回顾分工：**C++ 负责"跑在机器人身上的"，Python 负责"围在机器人周围的"**。

| 对比维度 | C++ | Python |
|---|---|---|
| 运行速度 | 快（编译成机器码） | 慢几十倍（解释执行） |
| 开发速度 | 慢（要声明类型、管内存） | 快（几行就能干活） |
| 1kHz 关节实时控制 | ✔ 首选 | 基本不行 |
| 数据分析、画图、脚本 | 很少用 | ✔ 首选 |
| 在 ROS2 中的角色 | 写核心节点（控制/感知算法） | 写节点、工具、实验脚本、测试 |

玩过《原神》的话可以这么记：C++ 是**重剑**，出手厚重、威力大，但挥起来费劲；Python 是**法器**，轻巧顺手、招式连发。练到后期的旅行者，从来都是两把武器都趁手。

> 📖 教材对照：《Python 编程：从入门到实践》第 1 章（起步与环境）

## 2. 环境安装：Miniconda 完整步骤

### 2.1 为什么要用 Miniconda

**Miniconda** 是一个精简版 Python 管理工具，自带 **conda** 这个包/环境管理器。它最大的价值是**环境隔离（environment isolation）**：每个项目一个独立环境，A 项目要 Python 3.11、B 项目要别的版本，互不打架。

| 概念 | 一句话解释 |
|---|---|
| **conda** | 管"环境"和"软件包"的工具（本章用它建环境） |
| **环境（environment）** | 一个独立的 Python 版本 + 一套独立的库，互不干扰 |
| **pip** | Python 官方的装库工具（本章用它装 numpy、matplotlib） |
| **镜像（mirror）** | 国内加速下载用的服务器副本 |

### 2.2 Windows 安装步骤

1. 浏览器打开 Miniconda 官网 `docs.conda.io`，下载 `Miniconda3-latest-Windows-x86_64.exe`（国内下载慢可去清华镜像 `mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/`）
2. 双击安装包 → I Agree → Next → **勾选 "Add Miniconda3 to my PATH environment variable"** → Install
   - 官方默认不勾这个选项，勾了会显示红字警告——那是怕和你已有的 Python 冲突。新电脑放心勾，这样任何终端都能直接用 conda
3. 打开一个**新的** cmd 或 PowerShell，验证安装：

```bash
conda --version        # 输出形如 conda 24.7.1，说明装好了
```

!!! warning
    如果提示"conda 不是内部或外部命令"：PATH 没勾成功。最简单的自救是改用开始菜单里的 "Anaconda Prompt (miniconda3)"，它天生能用。

### 2.3 创建环境并装库

接着在同一个终端里逐条执行：

```bash
conda create -n robot python=3.11   # 创建名为 robot 的环境，指定 Python 3.11
# -n 是 name（环境名）；问你 Proceed ([y]/n)? 时输 y 回车

conda activate robot                # 激活环境：提示符会从 (base) 变成 (robot)

pip install numpy matplotlib        # 在 robot 环境里装本章要用的两个库
# 国内网络慢可改用：pip install numpy matplotlib -i https://pypi.tuna.tsinghua.edu.cn/simple

python -c "import numpy, matplotlib; print(numpy.__version__, matplotlib.__version__)"
# 输出两个版本号（形如 2.1.1 3.10.1）即安装成功
```

!!! note
    每次新开终端都要重新 `conda activate robot`——这是特性不是故障：不激活时你处在"公共环境"里，避免项目互相污染。

!!! tip "Ubuntu / WSL2 用户"
    Linux 下安装方式：官网下载 `Miniconda3-latest-Linux-x86_64.sh`，然后 `bash Miniconda3-latest-Linux-x86_64.sh`。之后的命令和 Windows 完全一样。

## 3. Python 快速入门：和 C++ 对着学

你已经会 C++，所以本节不教"什么是变量"，只讲**写法差在哪里**。共 8 个知识点，每个都给 C++ / Python 双栏对照。

### 3.1 第一个程序：Hello, Robot!

=== "C++"

    ```cpp
    #include <iostream>              // 要先引入头文件

    int main() {                     // 要有 main 函数
        std::cout << "Hello, Robot!" << std::endl;  // 要写命名空间、分号
        return 0;
    }
    ```

=== "Python"

    ```python
    print("Hello, Robot!")           # 一行。没有 main、没有分号、没有 #include
    ```

运行方式：保存为 `hello.py`，在终端（robot 环境已激活）执行 `python hello.py`。

### 3.2 变量：不用声明类型

=== "C++"

    ```cpp
    int a = 3;          // 类型写在前面，写死不可变
    double b = 2.5;
    std::string s = "lidar";
    ```

=== "Python"

    ```python
    a = 3               # 直接赋值，不声明类型（动态类型）
    b = 2.5             # 这行自动就是小数
    s = "lidar"         # 字符串单双引号都行
    print(type(a))      # <class 'int'>：想看类型用 type() 函数
    ```

这叫**动态类型（dynamic typing）**：变量只是贴在值上的"名字标签"，类型跟着值走，而不是跟着名字走。

!!! warning
    Python 允许同一个名字先等于 `3` 再等于 `"abc"`（类型变了名字还在）。语法允许，但强烈建议别这么写——那是在给自己埋雷。

### 3.3 缩进就是语法

=== "C++"

    ```cpp
    if (v > 0.5) {
        stop();          // 用花括号划定"属于 if"的范围
    } else {
        go();
    }
    ```

=== "Python"

    ```python
    if v > 0.5:          # 行末冒号：下面进入 if 的地盘
        stop()           # 缩进 4 空格 = 属于 if
    else:
        go()
    ```

**缩进（indentation）** 在 Python 里不是"为了好看"，而是语法本身：缩进错一格，程序逻辑就变或直接报错。约定俗成用 4 个空格，不要用 Tab，更不要混用。

### 3.4 列表 list ↔ C++ 的 vector

=== "C++"

    ```cpp
    #include <vector>
    #include <iostream>

    int main() {
        std::vector<double> v = {0.1, 0.2, 0.3};  // 声明必须写元素类型
        v.push_back(0.4);                          // 末尾添加
        std::cout << v[0] << "\n";                 // 下标从 0 开始
        std::cout << v.size() << "\n";             // 个数：v.size()
        return 0;
    }
    ```

=== "Python"

    ```python
    v = [0.1, 0.2, 0.3]     # 列表（list）：不写类型，元素还能混着放
    v.append(0.4)           # 末尾添加
    print(v[0])             # 0.1：下标从 0 开始，和 C++ 一样
    print(v[-1])            # 0.4：-1 是最后一个（C++ 没有！）
    print(len(v))           # 4：个数用 len() 函数
    print(v[1:3])           # [0.2, 0.3]：切片，含头不含尾
    ```

| 你想做的事 | C++ 的 vector | Python 的 list |
|---|---|---|
| 声明 | `std::vector<double> v{...};` | `v = [...]` |
| 末尾添加 | `v.push_back(x);` | `v.append(x)` |
| 第一个元素 | `v[0]` | `v[0]` |
| 最后一个元素 | `v[v.size()-1]` | `v[-1]` |
| 元素个数 | `v.size()` | `len(v)` |
| 取中间一段 | 手写循环 | `v[1:3]` 切片 |
| 排序 | `std::sort(v.begin(), v.end());` | `v.sort()` |

### 3.5 字典 dict ↔ C++ 的 map

=== "C++"

    ```cpp
    #include <map>
    #include <string>
    #include <iostream>

    int main() {
        std::map<std::string, int> joint = {{"j1", 90}};  // 键 string 值 int
        joint["j2"] = -30;                // 插入或修改
        std::cout << joint["j1"] << "\n"; // 90
        return 0;
    }
    ```

=== "Python"

    ```python
    joint = {"j1": 90}          # 字典（dict）：花括号 + "键: 值"
    joint["j2"] = -30           # 插入和修改是同一个写法
    print(joint["j1"])          # 90
    print(joint.get("j3", 0))   # 安全取值：键不存在就返回默认值 0
                                # 直接写 joint["j3"] 会 KeyError 报错
    for name, angle in joint.items():   # 同时遍历键和值
        print(name, angle)
    ```

机器人里字典到处都是：关节名 → 角度、传感器名 → 读数、参数名 → 配置值。

### 3.6 循环与 range

=== "C++"

    ```cpp
    #include <iostream>

    int main() {
        for (int i = 0; i < 5; ++i) {   // 三段式：初值、条件、步进
            std::cout << i << "\n";     // 打印 0 1 2 3 4
        }
        return 0;
    }
    ```

=== "Python"

    ```python
    for i in range(5):        # range(5) 生成 0,1,2,3,4（不含 5）
        print(i)

    for angle in [90.0, -30.0, 45.0]:   # 直接遍历元素，不用下标
        print(angle)

    for i, angle in enumerate([90.0, -30.0]):  # 要下标时用 enumerate
        print(i, angle)                        # 0 90.0 / 1 -30.0
    ```

`range` 还能带步长：`range(2, 10, 3)` 生成 2, 5, 8（起始、终止、步长，同样不含终止值）。

### 3.7 函数 def

=== "C++"

    ```cpp
    #include <iostream>

    double square(double x) {     // 返回类型、参数类型都要声明
        return x * x;
    }

    int main() {
        std::cout << square(3.0) << "\n";   // 9
        return 0;
    }
    ```

=== "Python"

    ```python
    def square(x):            # def 定义函数：不写返回类型和参数类型
        return x * x          # def 行末冒号 + 函数体缩进，代替花括号

    def move(name, speed=0.5):          # 默认参数：不传就用 0.5
        return f"{name} 以 {speed} m/s 移动"   # f 字符串：{} 里可以直接放变量

    print(square(3.0))        # 9.0
    print(move("底盘"))       # 底盘 以 0.5 m/s 移动
    ```

Python 还能一次返回多个值：`return mean, std`，调用处 `m, s = statistics(d)` 直接拆开接住——后面 NumPy 一节就会用到这个习惯。

### 3.8 模块 import

=== "C++"

    ```cpp
    #include <cmath>                  // 预处理：把头文件内容复制进来
    #include <iostream>

    int main() {
        std::cout << std::sqrt(2.0);  // 要带命名空间前缀 std::
        return 0;
    }
    ```

=== "Python"

    ```python
    import math             # 导入整个模块，用"模块名.函数名"
    print(math.sqrt(2.0))   # 1.4142...

    import numpy as np      # 起别名：numpy 太常打，全世界都写成 np
    from math import sqrt   # 只导入一个函数，之后直接写 sqrt(2.0)
    ```

**模块（module）** 就是一个写好函数的 `.py` 文件；**包（package）** 是一堆模块的集合，用 `pip install` 安装。

| 你想做什么 | C++ 写法 | Python 写法 |
|---|---|---|
| 打印 | `std::cout << x << "\n";` | `print(x)` |
| 定义整数 | `int a = 3;` | `a = 3` |
| 注释 | `// 注释` | `# 注释` |
| 列表 | `std::vector<int> v{1, 2};` | `v = [1, 2]` |
| 键值对 | `std::map<std::string, int> m;` | `m = {}` |
| if 判断 | `if (x > 0) { ... }` | `if x > 0: ...` |
| 循环 5 次 | `for (int i = 0; i < 5; ++i) {...}` | `for i in range(5): ...` |
| 定义函数 | `double f(double x) {...}` | `def f(x): ...` |
| 引入库 | `#include <cmath>` | `import math` |
| 逻辑与 / 或 | `&&` 与 `\|\|` | `and` 与 `or` |
| 真假字面量 | `true` / `false` | `True` / `False` |

> 📖 教材对照：《Python 编程：从入门到实践》第 2 章（变量）、第 3-4 章（列表）、第 5 章（if）、第 6 章（字典）、第 7 章（while）、第 8 章（函数）

## 4. NumPy：把循环变成一行

**NumPy（Numerical Python）** 是 Python 的科学计算地基，核心是 **ndarray（N-dimensional array，N 维数组）**：一大块内存里排着的一组**同类型**数，可以整块参与运算。

为什么它对机器人工程师重要？因为传感器数据天然就是"一串数"，而 NumPy 能把 C++ 里要写循环的事变成一行。

### 4.1 创建数组和两个最重要的属性

```python
import numpy as np                          # 约定俗成起别名 np

a = np.array([1.0, 2.0, 3.0])               # 从列表创建数组
M = np.array([[1, 2, 3],                    # 二维数组：2 行 3 列
              [4, 5, 6]])

z = np.zeros(5)                             # 5 个 0.0
o = np.ones((2, 3))                         # 2 行 3 列全 1（形状要传元组 (2, 3)）
g = np.linspace(0.0, 1.0, 5)                # 0 到 1 均匀取 5 个点
t = np.arange(0, 10, 2)                     # 0,2,4,6,8（起始、终止、步长，不含终止）

print(a.shape)      # (3,)：形状——一维 3 个元素
print(M.shape)      # (2, 3)：2 行 3 列。shape 是排错第一利器，不确定就先 print 它
print(M.dtype)      # int64：元素类型（整个数组只能有一种类型）
print(g)            # [0.   0.25 0.5  0.75 1.  ]
```

### 4.2 逐元素运算：3 行 C++ vs 1 行 Python

=== "C++"

    ```cpp
    #include <vector>

    int main() {
        std::vector<double> d = {1.1, 2.2, 3.3};
        std::vector<double> r;
        for (double x : d) {            // 必须写循环，一个一个算
            r.push_back(x * 2 + 0.1);   // 每个元素乘 2 加 0.1
        }
        return 0;
    }
    ```

=== "Python"

    ```python
    import numpy as np

    d = np.array([1.1, 2.2, 3.3])
    r = d * 2 + 0.1              # 一行：运算自动作用在每个元素上
    print(r)                     # [2.3 4.5 6.7]
    ```

这叫**向量化（vectorization）**：没有 for 循环，运算自动"铺"到每个元素上。数据量大时 NumPy 底层是编译好的 C 代码在跑，比纯 Python 循环快几十倍。

!!! warning "新手第一大坑"
    Python 原生 list 的 `*` 不是逐元素：`[1, 2] * 2` 得到 `[1, 2, 1, 2]`（重复两遍）。只有 ndarray 的 `*` 才是逐元素乘。分不清时 `print(type(x))` 看一眼。

### 4.3 矩阵乘 @ 和逐元素乘 *：重点中的重点

NumPy 有两个"乘号"，含义完全不同：

```python
import numpy as np

A = np.array([[1.0, 2.0],
              [3.0, 4.0]])
B = np.array([[5.0, 6.0],
              [7.0, 8.0]])

C = A * B      # 逐元素乘：对应位置各自相乘
D = A @ B      # 矩阵乘：行乘列再求和（@ 读作"矩阵乘"）
```

**动手算一算**——先把 `C = A * B` 逐个位置乘出来：

```
C[0,0] = 1×5 = 5      C[0,1] = 2×6 = 12
C[1,0] = 3×7 = 21     C[1,1] = 4×8 = 32

C = [[ 5, 12],
     [21, 32]]
```

再把 `D = A @ B` 按"行乘列求和"算出来：

```
D[0,0] = A 第0行 · B 第0列 = 1×5 + 2×7 = 19
D[0,1] = A 第0行 · B 第1列 = 1×6 + 2×8 = 22
D[1,0] = A 第1行 · B 第0列 = 3×5 + 4×7 = 43
D[1,1] = A 第1行 · B 第1列 = 3×6 + 4×8 = 50

D = [[19, 22],
     [43, 50]]
```

| | `A * B` 逐元素乘 | `A @ B` 矩阵乘 |
|---|---|---|
| 规则 | 对应位置各自相乘 | 行乘列再求和 |
| 形状要求 | 一样或可广播 | A 的列数 = B 的行数 |
| 结果示例 | `[[5,12],[21,32]]` | `[[19,22],[43,50]]` |
| 机器人场景 | 多路传感器各自乘标定系数 | 旋转矩阵 @ 点坐标 = 旋转后的坐标 |

!!! warning
    实际工程里"NumPy 算出来结果不对"，一大半是把 `@` 误写成了 `*`。写矩阵运算时先默念一遍：**变换用 @，逐路标定用 \***。

### 4.4 索引与切片

```python
a = np.array([10, 20, 30, 40, 50])
print(a[0])        # 10：下标从 0 开始
print(a[-1])       # 50：最后一个
print(a[1:4])      # [20 30 40]：含头不含尾
print(a[::2])      # [10 30 50]：从头到尾步长 2

M = np.array([[1, 2, 3],
              [4, 5, 6]])
print(M[1, 2])     # 6：第 1 行第 2 列（行号、列号都从 0 数）
print(M[0, :])     # [1 2 3]：第 0 行整行（: 表示"全部"）
print(M[:, 0])     # [1 4]：第 0 列整列

d = np.array([1.0, 2.5, 3.1, 0.4])
print(d[d > 2.0])  # [2.5 3.1]：布尔掩码——条件当筛子用
```

布尔掩码（`d[d > 2.0]`）值得多看一眼：它一行就筛出所有大于 2 米的测距读数，机器人里天天这么用。

### 4.5 广播：形状不一样也能算

**广播（broadcasting）** 的直觉一句话：**形状不够的那一维，自动复制补齐再算**。

| A 的形状 | B 的形状 | 能算吗 | 结果形状 |
|---|---|---|---|
| (100,) | 标量 | ✔ | (100,) |
| (2, 3) | (3,) | ✔ | (2, 3) |
| (2, 3) | (2, 1) | ✔ | (2, 3) |
| (2, 3) | (4,) | ✘ 报错 | 尾维 3≠4 且都不是 1 |

最常见的用法——每一路传感器减去自己的零偏：

```python
samples = np.array([[1.0, 2.0, 3.0],   # 2 个采样时刻，各 3 路传感器
                    [4.0, 5.0, 6.0]])  # 形状 (2, 3)
bias = np.array([0.1, 0.0, -0.1])      # 3 路各自的零偏，形状 (3,)

fixed = samples - bias    # bias 沿行方向"复制"2 份，逐列对应相减
print(fixed)
# [[0.9 2.  3.1]
#  [3.9 5.  6.1]]
```

### 4.6 常用函数速览

```python
a = np.array([3.0, 1.0, 4.0, 1.5])

print(a.sum())     # 9.5：求和
print(a.mean())    # 2.375：均值
print(a.std())     # 1.13...：标准差（越大越离散）
print(a.min())     # 1.0：最小值
print(a.argmin())  # 1：最小值的下标（arg = 对应的下标）
```

| 函数 | 作用 | 记忆点 |
|---|---|---|
| `np.zeros(n)` / `np.ones((r,c))` | 全 0 / 全 1 数组 | 形状传元组 |
| `np.linspace(a, b, n)` | a 到 b 均匀取 n 个点 | **l**inear **space**，含两端 |
| `np.arange(a, b, s)` | a 到 b 步长 s | 不含 b |
| `a.mean()` / `a.std()` | 均值 / 标准差 | 统计三件套之二 |
| `a.sum()` / `a.min()` / `a.max()` | 求和 / 最小 / 最大 | 逐元素统计 |
| `a.argmin()` / `a.argmax()` | 最小/最大值的下标 | arg = 下标 |

### 4.7 随机数：模拟传感器噪声

真实传感器每次读数都带点抖动，仿真里我们用**高斯噪声（Gaussian noise）**模拟它——它的值围绕均值上下浮动，浮动幅度由标准差控制（就是"正态分布"那口钟的形状）。

```python
import numpy as np

np.random.seed(42)                       # 固定随机种子：每次运行"随机"数都一样
noise = np.random.normal(0.0, 0.05, 100) # 均值 0、标准差 0.05、生成 100 个
print(noise[:5])   # 前 5 个，形如 [ 0.0248 -0.0069  0.0324  0.0762 -0.0117]
```

- 第 1 参：均值 `loc`——噪声的中心位置
- 第 2 参：标准差 `scale`——抖得多厉害（0.05 米 = 5 厘米）
- 第 3 参：个数 `size`

固定种子后，你机器上每次运行结果完全一致——调 bug 和写论文时这是救命特性。

> 📖 教材对照：NumPy 官方文档《NumPy quickstart》（numpy.org/doc/stable/user/quickstart.html）

## 5. matplotlib：把数据画出来

**matplotlib** 是 Python 最经典的画图库，约定俗成导入为 `plt`。画图固定四步：**准备数据 → 画（plot/scatter）→ 加标注 → show**。

```python
# 文件名：plot_demo.py　运行环境：robot 环境已激活的终端
import numpy as np                    # 数值计算
import matplotlib.pyplot as plt       # 画图模块，别名 plt 是全世界的写法

t = np.linspace(0, 2 * np.pi, 200)    # 0 到 2π 之间均匀取 200 个时间点
y = np.sin(t)                         # 每个点求正弦——又是向量化，一行搞定

plt.plot(t, y, label="sin(t)")        # 折线图：200 个点连成光滑曲线
plt.scatter(t[::20], y[::20],         # 散点图：每隔 20 个点取一个画红点
            color="red", s=30, label="samples")   # s 是点的大小
plt.xlabel("time (s)")                # x 轴标签
plt.ylabel("amplitude")               # y 轴标签
plt.title("Sine wave demo")           # 标题
plt.legend()                          # 显示图例（label 的说明框）
plt.grid(True)                        # 打开网格线
plt.show()                            # 把图弹出来——脚本最后一定要有这句
```

运行 `python plot_demo.py`，预期效果（文字版）：弹出一个窗口，一条从 0 出发、升到 +1、回落、再下探到 -1 的平滑波浪线；线上叠着 10 个红色圆点；左上角有图例；底色带浅网格。窗口底部一排按钮可以缩放、平移、保存成 png。

!!! tip
    图里的文字先用英文——matplotlib 默认字体不含中文，写中文会显示成方块"□□□"。要显示中文需额外配置字体，初学阶段没必要折腾。

!!! tip "WSL2 用户注意"
    WSL2 里 `plt.show()` 弹窗需要 WSLg 支持（Windows 11 一般自带；Windows 10 常弹不出来）。弹不出就改用 `plt.savefig("demo.png")` 存成图片再看，效果相同。

## 6. 综合例程：100 次激光测距读数的统计与直方图

场景：激光传感器对着 2.5 米外的墙连续测了 100 次，每次读数都带 ±几厘米的噪声。我们用 NumPy 统计读数分布，再用 matplotlib 画成直方图。约 25 行，直接可跑：

```python
# 文件名：lidar_sim.py　运行环境：robot 环境（需 numpy、matplotlib）
"""模拟 100 次激光测距读数，统计并画直方图"""
import numpy as np                        # 数值计算
import matplotlib.pyplot as plt           # 画图

np.random.seed(42)                        # 固定种子：每次运行结果一致（可复现）

true_d = 2.50                             # 真实距离：2.5 米
n = 100                                   # 采集 100 次
noise = np.random.normal(0.0, 0.05, n)    # 高斯噪声：均值 0、标准差 5 厘米
measure = true_d + noise                  # 每次读数 = 真实值 + 噪声（向量化加法）

mean = measure.mean()                     # 样本均值：对真实距离的最好估计
std = measure.std()                       # 样本标准差：读数的离散程度
print(f"均值 = {mean:.3f} m，标准差 = {std:.3f} m")   # f 字符串：{x:.3f} 保留 3 位小数

plt.hist(measure, bins=20, edgecolor="black")         # 直方图：把范围切 20 个桶数个数
plt.axvline(true_d, color="red", linestyle="--",
            label="true distance")                    # 竖虚线标出真实值
plt.axvline(mean, color="green", label="mean")        # 竖实线标出均值
plt.xlabel("distance (m)")
plt.ylabel("count")
plt.title("100 lidar readings")
plt.legend()
plt.grid(True)
plt.show()
```

逐块讲解：

**第 1 块（import 与种子）**：`np.random.seed(42)` 固定随机种子。随机数程序必须可复现——否则今天跑出来是这个分布、明天变成另一个，你根本分不清是代码错了还是运气差了。

**第 2 块（建模真实世界）**：核心思想一行——`读数 = 真值 + 噪声`。真实世界永远是这样：你想要的是 `true_d`，你手里只有 `measure`。机器人学里一大类问题（滤波、标定、估计）都是在做"从 measure 里把 true_d 捞出来"。

**第 3 块（统计）**：`mean` 是 100 次读数的平均，`std` 衡量它们散得多开。运行后终端输出（实测值，固定种子下你机器上每次都一样）：

```
均值 = 2.495 m，标准差 = 0.045 m
```

均值 2.495 离真实值 2.500 只差 5 毫米——**多次带噪测量取平均，能把真值估计得很准**，这就是为什么实际标定都让你测很多次取平均。

**第 4 块（画图）**：`plt.hist` 画直方图——把读数范围切成 20 个"桶"（bins），数每桶掉进去几个读数；`plt.axvline` 画一条贯穿全高的竖参考线。

预期图形（文字版）：一座以 2.5 为中心的小山，20 根柱子，最高的柱子出现在 2.45-2.55 之间、高约二十多次；红色虚线立在 2.50（真值），绿色实线紧贴着它（均值），两线几乎重合。**山越"瘦"（std 越小），传感器越好**。

> 📖 教材对照：《Python 编程：从入门到实践》第 15 章（数据可视化）选读

## 7. 和机器人有什么关系：一天里什么时候写 Python、什么时候写 C++

把全章收进一张"工程师的一天"对照表：

| 一天中的任务 | 用什么 | 为什么 |
|---|---|---|
| 写 1kHz 关节实时控制节点 | C++ | 延迟要求高，Python 跟不上 |
| 从 rosbag 抽一段 IMU 数据存成 CSV | Python 脚本 | 三五行搞定，C++ 要写半天 |
| 给实验数据画对比曲线 | Python + matplotlib | 画图生态没有对手 |
| 批量生成仿真测试场景 | Python 脚本 | 灵活、改起来快 |
| 训练/微调一个 RL 策略 | Python + PyTorch | 整个生态都在 Python |
| 用 rqt 看话题、调试节点 | Python 写的工具（你先用起来） | 读懂它以后还能自己改 |

典型状态是：上午写 C++ 调实时性，下午写 Python 跑数据分析。两把武器都趁手，才算出师——本章你已经把第二把握在手里了。

## 8. 常见错误与自救

报错不是失败——它就像 Boss 战里的弱点提示，读懂一条，掉一条血。先学会看**报错最后一行**：错误类型 + 出错的文件和行号。

| 错误现象 | 原因 | 怎么改 |
|---|---|---|
| `IndentationError: unexpected indent` | 混用了 Tab 和空格，或缩进不一致 | 全文统一 4 空格；编辑器里设置 Tab=4 空格 |
| `ModuleNotFoundError: No module named 'numpy'` | 装到别的环境了，或忘了激活 | 先 `conda activate robot`，再 `pip install numpy` |
| `IndexError: list index out of range` | 下标越界（忘了从 0 开始） | `print(len(x))` 看看到底几个元素 |
| `A * B` 结果和手算矩阵乘不一样 | 想要矩阵乘却写了逐元素乘 | 改用 `A @ B` |
| `ValueError: shapes (2,3) and (4,) not aligned` | `@` 两边形状不匹配 | `print(A.shape)` 逐个查形状 |
| matplotlib 图没弹出来 | 忘了 `plt.show()`，或 WSL2 无 WSLg | 补上 show；或改 `plt.savefig("x.png")` |
| `conda` 提示不是内部或外部命令 | PATH 没配好 | 用开始菜单的 Anaconda Prompt，或重装勾选 PATH |
| `[1,2] * 2` 得到 `[1,2,1,2]` | 它是 list 不是 ndarray | `np.array([1,2]) * 2` |

## 9. 动手练习

练习 1（环境）：新建一个名为 `test` 的 conda 环境（Python 3.11），激活后打印 numpy 版本号。

??? details "练习 1 解答"

    ```bash
    conda create -n test python=3.11    # 一路 y
    conda activate test
    pip install numpy
    python -c "import numpy; print(numpy.__version__)"
    # 输出版本号（如 2.1.1）即成功
    ```

练习 2（Python 基础）：写函数 `to_fahrenheit(c_list)`，把摄氏温度列表转成华氏（F = C × 9/5 + 32），逐个打印。

??? details "练习 2 解答"

    ```python
    def to_fahrenheit(c_list):          # def + 冒号 + 缩进
        for c in c_list:                # 直接遍历元素
            f = c * 9 / 5 + 32
            print(f"{c}°C = {f}°F")     # f 字符串拼接

    to_fahrenheit([0, 25, 37, 100])
    # 0°C = 32.0°F / 25°C = 77.0°F / 37°C = 98.6°F / 100°C = 212.0°F
    ```

练习 3（NumPy）：给定 10 个角度（度）：`angles = np.array([0, 30, 45, 60, 90, 120, 135, 150, 180, 270])`。转成弧度，求 sin 值的最大值以及它出现在第几个元素（下标）。

??? details "练习 3 解答"

    ```python
    import numpy as np
    angles = np.array([0, 30, 45, 60, 90, 120, 135, 150, 180, 270])
    rad = angles * np.pi / 180          # 度转弧度（也可以用 np.deg2rad(angles)）
    s = np.sin(rad)                     # 向量化：10 个角度一次全算完
    print(s.max())                      # 1.0
    print(s.argmax())                   # 4：最大值在下标 4，即 90°
    ```

练习 4（@ vs \*）：设 `A = np.array([[2, 0], [0, 2]])`，`x = np.array([1, 3])`。先手算 `A @ x`，再用 NumPy 验证；再算 `A * x`，解释两者几何含义的差别。

??? details "练习 4 解答"

    手算 `A @ x`（矩阵乘，行乘列）：
    ```
    (A@x)[0] = 2×1 + 0×3 = 2
    (A@x)[1] = 0×1 + 2×3 = 6      → A @ x = [2, 6]
    ```
    几何含义：`A @ x` 把点 (1,3) 整体放大 2 倍到 (2,6)——这正是缩放矩阵的作用，机器人里坐标变换全靠它。
    而 `A * x`（广播逐元素乘）把 x 沿行复制 2 份：`[[2×1, 0×3], [0×1, 2×3]] = [[2,0],[0,6]]`——乘的是"列"，含义完全不同。

练习 5（综合）：模拟 50 次温度传感器读数（真实温度 25.0°C，噪声标准差 0.3°C），打印均值和标准差，画直方图并加一条真值竖线。

??? details "练习 5 解答"

    ```python
    import numpy as np
    import matplotlib.pyplot as plt

    np.random.seed(7)                          # 种子随意，固定即可复现
    temp = 25.0 + np.random.normal(0.0, 0.3, 50)   # 读数 = 真值 + 噪声
    print(f"均值 = {temp.mean():.3f} °C，标准差 = {temp.std():.3f} °C")

    plt.hist(temp, bins=10, edgecolor="black")
    plt.axvline(25.0, color="red", linestyle="--", label="true temp")
    plt.xlabel("temperature (C)")
    plt.ylabel("count")
    plt.legend()
    plt.show()
    # 均值应在 25.0 附近（±0.1 内），图形是一座以 25 为中心的小山
    ```

## 本章速查卡

**环境与运行**

| 命令 | 作用 |
|---|---|
| `conda create -n robot python=3.11` | 建独立环境 |
| `conda activate robot` | 激活（新终端要重新执行） |
| `pip install numpy matplotlib` | 装库 |
| `python 文件名.py` | 运行脚本 |

**Python 语法**

| 写法 | 作用 |
|---|---|
| `x = 3` / `s = "hi"` | 变量（不声明类型） |
| `v = [1, 2]` / `d = {"k": 1}` | 列表 / 字典 |
| `for i in range(5):` | 循环 0-4 |
| `def f(x): return x*x` | 函数 |
| `import numpy as np` | 导模块起别名 |

**NumPy / matplotlib**

| 写法 | 作用 |
|---|---|
| `np.array([...])` / `.shape` / `.dtype` | 建数组 / 形状 / 元素类型 |
| `a.mean()` `a.std()` `a.sum()` `a.argmax()` | 统计 |
| `np.linspace(a, b, n)` / `np.zeros((r, c))` | 均匀取点 / 全 0 |
| `np.random.normal(μ, σ, n)` | 高斯噪声（配 seed 复现） |
| `@` 矩阵乘 / `*` 逐元素乘 | 千万别混 |
| `plt.plot` / `plt.scatter` / `plt.hist` | 线 / 散点 / 直方图 |
| `xlabel → title → grid → show` | 画图收尾四件套 |

## 下一章预告

Python 这把法器到手了，但机器人代码几乎都活在 **Linux** 里，代码历史靠 **Git** 保管。下一章我们解决"机器人工程师的两个生存技能"：Linux 命令行与 Git——从装 WSL2 到把本章代码推上 GitHub，一条龙走完。见 [Linux 命令行与 Git 入门](./20_Linux命令行与Git入门.md)。
