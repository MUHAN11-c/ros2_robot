# 数组、string 与 vector：给数据找房子

> **教材锚点**：C++ Primer 第5版 第3章 | **前置**：第 20 章《控制流、函数与程序结构》

---

## 本章导航

**上一章**：[20_控制流_函数与程序结构](./20_控制流_函数与程序结构.md)

**这章讲什么？** 之前你的每个变量只能装**一个**数。但机器人一帧激光雷达有 720 个距离值、一段轨迹有几百个路径点——本章学习 C++ 的三种"容器"：最原始的 **数组（Array）**、管理文字的 **字符串（String）**（即 `std::string`）、以及现代 C++ 首选的 **向量（Vector）**（即 `std::vector`）。

**为什么要学它？** 容器是所有机器人软件的地基：传感器读数是一串数，路径规划是一串点，地图是一张二维网格。不会容器，就写不出任何真实的机器人程序。

**学完能做什么？** 能定义、遍历、增删容器里的数据；能把一帧雷达数据统计出最大/最小/平均距离；能建一张二维栅格地图；能对路径点做插值。

**本章在路线图中的位置**：

```text
00_零基础入门
├── 10_环境搭建与第一个程序
├── 20_控制流_函数与程序结构        ← 上一章
├── 30_数组_string与vector          ← 你在这里（数据有了"房子"）
├── 40_指针_引用与内存模型          ← 下一章（房子住了谁、门牌号是什么）
├── 50_类与对象初步
└── 60_STL容器算法与实战小项目
```

| 学习方式 | 时间 | 适合谁 |
|---|---|---|
| 首次学习（跟做练习） | 3-4 小时 | 第一次接触该主题 |
| 快速复习 | 40-60 分钟 | 学过但遗忘，查漏补缺 |

**运行环境**：任意操作系统 + g++ 9 以上（或 MSVC / Clang）。统一用 `g++ 文件名.cpp -o 程序名 -std=c++17` 编译。

---

## 1. 从生活到概念：一个变量只能装一个数，那一千个数怎么办？

回忆上一章：`int score = 95;` 一个变量装一个数。现在要记录全班 30 个同学的成绩，难道写 30 个变量？`int score0 = 90, score1 = 85, score2 = 77;`……写到 `score29`，光是打字就想放弃。

生活中我们有**鸡蛋盒**：一个盒子 30 个格子，每个格子放一个鸡蛋，盒子上还有编号。程序里对应的工具就是**容器（Container）**——一块连续的、编了号的存储空间。

> ⚠ **类比在哪里失效**：鸡蛋盒格子数是固定的，而 C++ 的 `vector` 是**可以变大变小**的"伸缩盒"；另外鸡蛋盒格子编号从 1 开始数，C++ 容器的编号（**下标（Index）**）**从 0 开始**——这是新手最常摔的一跤。

本章按"从原始到现代"的顺序讲三种容器：C 风格数组 → `std::string` → `std::vector`。前一种的痛点，正好是后一种存在的理由。

---

## 2. C 风格数组：最原始的收纳盒

> 📖 教材对照：C++ Primer 第5版 §3.5

### 2.1 定义与初始化

**数组（Array）** 是"同一种类型的 N 个变量，肩并肩挤在一块连续内存里"。

```cpp
#include <iostream>
using namespace std;   // 允许直接写 cout、endl 而不用写 std::cout

int main() {
    int scores[5] = {90, 85, 77, 60, 100};  // 定义：类型 名字[长度] = {初值列表}
    int lucky[4] = {7, 8};                  // 只给前 2 个初值，剩下自动填 0

    cout << "第 1 个成绩: " << scores[0] << endl;  // 下标从 0 开始！
    cout << "第 5 个成绩: " << scores[4] << endl;  // 最后一个下标是 长度-1
    cout << "lucky[3] = " << lucky[3] << endl;     // 没给初值的格子是 0
    return 0;
}
```

```text
第 1 个成绩: 90
第 5 个成绩: 100
lucky[3] = 0
```

### 2.2 遍历：挨个拜访每个格子

**遍历（Traversal）** 就是"从头到尾把每个元素过一遍"，用 `for` 循环配合下标完成：

```cpp
#include <iostream>
using namespace std;

int main() {
    int scores[5] = {90, 85, 77, 60, 100};
    int total = 0;

    for (int i = 0; i < 5; i++) {         // i 从 0 数到 4，正好 5 个格子
        cout << "scores[" << i << "] = " << scores[i] << endl;
        total += scores[i];               // 边遍历边累加
    }
    cout << "总分 = " << total << endl;
    return 0;
}
```

```text
scores[0] = 90
scores[1] = 85
scores[2] = 77
scores[3] = 60
scores[4] = 100
总分 = 412
```

### 2.3 越界：数组最大的坑

数组的格子数在定义时就**写死了**，而 C++ 编译器**不会**替你检查下标是否越过了边界：

```cpp
#include <iostream>
using namespace std;

int main() {
    int arr[3] = {1, 2, 3};   // 合法下标只有 0、1、2

    cout << arr[2] << endl;   // 合法
    // 把下一行的注释去掉试试——编译照样通过！
    // cout << arr[5] << endl;

    cout << "程序跑完了" << endl;
    return 0;
}
```

```text
3
程序跑完了
```

把 `arr[5]` 那行解开后会发生什么？答案是：**谁也说不准**。可能打印垃圾值，可能崩溃，也可能"看起来正常"。这叫**未定义行为（Undefined Behavior, UB）**——C++ 新手程序"偶尔崩溃、时好时坏"的头号来源。**自救口诀：下标范围永远是 0 到 长度-1。**

### 2.4 数组的三个硬伤（为 vector 铺路）

| 硬伤 | 具体表现 | 后果 |
|---|---|---|
| 长度固定 | 定义时必须写死 `[5]`，之后不能变 | 数据多少未知时只能"往大了开"，浪费或不够用 |
| 不能直接整体赋值/比较 | `a = b;`、`a == b` 对数组都不合法 | 只能写循环逐个搬 |
| 传给函数会"退化" | 数组传参时丢失长度信息 | 函数不知道数组有几个元素，越界高发 |

这三个硬伤，正是标准库 `vector` 要解决的问题。

---

## 3. std::string：管理文字的现代工具

> 📖 教材对照：C++ Primer 第5版 §3.2

**字符串（String）** 就是"一串字符"。C 语言里字符串是 `char` 数组，用起来处处踩坑（拼接要 `strcat`、比较要 `strcmp`）；C++ 标准库提供了 `std::string`，让文字用起来像"一个变量"那么自然。

### 3.1 初始化、拼接与比较

```cpp
#include <iostream>
#include <string>        // 使用 string 必须包含这个头文件
using namespace std;

int main() {
    string s1 = "robot";          // 方式一：等号给一个字面量
    string s2("ics");             // 方式二：括号写法
    string s3;                    // 方式三：空字符串（什么都没有）

    s3 = s1 + " " + s2;           // 拼接：直接用 + 号，比 C 的 strcat 舒服太多
    cout << s3 << endl;
    cout << "长度 = " << s3.length() << endl;   // length() 返回字符个数（含空格）

    if (s1 == s2) {               // string 可以直接用 == 比较（C 数组不行！）
        cout << "相同" << endl;
    } else {
        cout << "不同" << endl;
    }
    if (s1 < s2) {                // 也能用 < > 比较，规则是字典序（逐字符比）
        cout << s1 << " 排在 " << s2 << " 前面" << endl;
    } else {
        cout << s2 << " 排在 " << s1 << " 前面" << endl;
    }
    return 0;
}
```

```text
robot ics
长度 = 9
不同
ics 排在 robot 前面
```

为什么 `ics` 排在 `robot` 前面？字典序是先比第 1 个字符：`'i'` 的编码（105）小于 `'r'`（114），所以整串就分出大小了，后面的字符不用再看。

### 3.2 子串 substr 与查找 find

```cpp
#include <iostream>
#include <string>
using namespace std;

int main() {
    string topic = "C++ for Robotics";
    // 下标：      0123456789...   （从 0 开始数！）
    // find：查找子串第一次出现的位置；找不到时返回特殊值 string::npos
    size_t pos = topic.find("for");       // size_t 可理解为"不会是负数的下标类型"
    cout << "for 的起始下标: " << pos << endl;

    // substr(起点下标, 取几个字符)：截取子串
    string word = topic.substr(4, 3);     // 从下标 4 起取 3 个字符
    cout << "取出的词: " << word << endl;
    string head = topic.substr(0, 3);     // 从头取 3 个
    cout << "head: " << head << endl;

    if (topic.find("Python") == string::npos) {   // npos = "没找到"的记号
        cout << "这句话里没有 Python" << endl;
    }
    return 0;
}
```

```text
for 的起始下标: 4
取出的词: for
head: C++
这句话里没有 Python
```

### 3.3 string 与数字互转：to_string / stoi / stod

机器人日志里全是数字，但日志文件读进来的都是 `string`；打印时又常想把数字拼进句子。互转是高频操作：

```cpp
#include <iostream>
#include <string>
using namespace std;

int main() {
    // 数字 -> string：to_string
    double dist = 3.75;
    int n = 42;
    string s1 = to_string(dist);     // 把 double 变成 string
    string s2 = to_string(n);        // 把 int 变成 string
    cout << "距离是 " + s1 + " 米" << endl;    // 变成 string 后就能用 + 拼接
    cout << "编号 " + s2 << endl;

    // string -> 数字：stoi（string to int）、stod（string to double）
    string a = "17";
    string b = "2.5";
    int x = stoi(a);                 // "17" -> 17，之后能做算术
    double y = stod(b);              // "2.5" -> 2.5
    cout << x * 2 << endl;
    cout << y + 0.5 << endl;
    return 0;
}
```

```text
距离是 3.750000 米
编号 42
34
3
```

> ◇ 两个细节：`to_string(3.75)` 固定保留 6 位小数（所以是 `3.750000`）；`stoi`/`stod` 遇到"完全不是数字"的串会直接报错终止程序，读取外部数据前要心里有数。

---

## 4. std::vector：现代 C++ 的首选容器

> 📖 教材对照：C++ Primer 第5版 §3.3

**向量（Vector）**（`std::vector`）可以理解为"会自动扩容的数组"：装多少元素不用提前决定，用 `push_back` 往里塞就行。

### 4.1 为什么推荐 vector 而不是数组

| 对比项 | C 风格数组 | std::vector |
|---|---|---|
| 长度 | 定义时写死 | 随时 `push_back` 增长 |
| 知道自己有几个元素 | 不知道（要自己另存） | `.size()` 一问便知 |
| 整体赋值/比较 | 不支持 | `a = b;` `a == b` 直接用 |
| 越界保护 | 毫无反应 | `.at()` 越界会明确报错 |
| 传给函数 | 退化为指针，丢长度 | 完整传递（下一章学"零拷贝"写法） |
| 场景 | 底层嵌入式、面试题 | **日常写代码一律用它** |

数组并没有"错"，嵌入式底层仍会用到它；但在本课程里，**默认写 vector**。

### 4.2 创建 vector 的四种方式

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    vector<int> v1;                        // 方式一：空容器，0 个元素
    vector<int> v2(3);                     // 方式二：3 个元素，每个都是 0
    vector<int> v3(3, 7);                  // 方式三：3 个元素，每个都是 7
    vector<int> v4 = {90, 85, 77};         // 方式四：用列表给出全部初值（最常用）
    vector<string> v5 = {"imu", "lidar"};  // 尖括号里换成什么类型，就装什么

    cout << "v3 的内容: ";
    for (int x : v3) {                     // 范围 for：依次取出每个元素（见 4.5）
        cout << x << " ";
    }
    cout << endl;
    cout << "v4 有 " << v4.size() << " 个元素" << endl;
    cout << "v4[0] = " << v4[0] << endl;          // 下标访问
    cout << "v4.at(1) = " << v4.at(1) << endl;    // at() 访问
    return 0;
}
```

```text
v3 的内容: 7 7 7
v4 有 3 个元素
v4[0] = 90
v4.at(1) = 85
```

注意 `vector<int> v2(3)`（3 个 0）和 `vector<int> v2 = {3}`（1 个 3）含义完全不同——括号是"几个、初值是啥"，花括号是"逐个列出"。

### 4.3 增、删、问：push_back / pop_back / size

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    vector<double> dists;          // 空的"距离列表"
    dists.push_back(1.2);          // push_back：在末尾追加一个元素
    dists.push_back(0.8);
    dists.push_back(2.5);
    cout << "size = " << dists.size() << endl;         // 3

    dists.pop_back();              // pop_back：删掉末尾那一个元素
    cout << "删掉一个后 size = " << dists.size() << endl;
    cout << "最后一个元素 = " << dists.back() << endl;  // back()：末尾元素的快捷方式

    for (double d : dists) {
        cout << d << " ";
    }
    cout << endl;
    return 0;
}
```

```text
size = 3
删掉一个后 size = 2
最后一个元素 = 0.8
1.2 0.8
```

### 4.4 下标 [] 与 .at()：越界时的两种反应

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    vector<int> v = {10, 20, 30};      // 合法下标只有 0、1、2

    cout << v[2] << endl;              // 合法访问

    // v[99]：越界访问。编译器不报错，运行结果是未定义行为（垃圾值/崩溃/看似正常）
    // v.at(99)：越界访问。程序立刻停止，并明确提示 out_of_range

    cout << "程序正常走到结尾" << endl;
    return 0;
}
```

```text
30
程序正常走到结尾
```

| 写法 | 越界时 | 适用 |
|---|---|---|
| `v[i]` | 未定义行为，无声无息 | 已确认下标合法、追求速度 |
| `v.at(i)` | 报 `out_of_range` 错误并终止 | 调试阶段、下标来自外部数据 |

学习阶段建议多用 `.at()`：宁可程序当场死掉，也不要带着看不见的 bug 继续跑。用 `[]` 的前提是你能保证下标合法。

### 4.5 范围 for：遍历的现代写法

上面反复出现的 `for (double d : dists)` 叫**范围 for（Range-based for）**，读作"对 dists 里的每个元素 d，执行循环体"。它和下标循环的对应关系：

```cpp
// 写法一：下标循环 —— 需要知道/使用下标时用
for (int i = 0; i < (int)v.size(); i++) { cout << v[i] << " "; }
// 写法二：范围 for —— 只关心"每个元素"本身时更简洁
for (int x : v) { cout << x << " "; }
```

> ◇ `(int)v.size()` 里的 `(int)` 是把 `size()` 返回的无符号类型转成 int，避免 `i < v.size()` 在空容器时的边界怪病（无符号数 `0-1` 不等于 -1，详见下一章）。范围 for 没有这个坑。

### 4.6 二维 vector：建一张 grid

**二维 vector（2D Vector）** 是"vector 里装 vector"：外层是行，内层是每行的格子。机器人栅格地图就长这样。

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    int rows = 3, cols = 4;                       // 3 行 4 列

    // 第 1 步：建好 3 行，每行还是一个"空的 vector<int>"
    vector<vector<int>> grid(rows);

    // 第 2 步：给每一行塞进"4 个 0"
    for (int i = 0; i < rows; i++) {
        grid[i] = vector<int>(cols, 0);           // 用方式三：4 个 0
    }
    // 合并惯用写法：vector<vector<int>> grid(rows, vector<int>(cols, 0));

    // 第 3 步：改某个格子。grid[行][列]，行、列都从 0 数起
    grid[1][2] = 9;

    // 第 4 步：双层循环打印整张表
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            cout << grid[i][j] << " ";
        }
        cout << endl;                             // 每打印完一行换行
    }
    return 0;
}
```

```text
0 0 0 0
0 0 9 0
0 0 0 0
```

### 4.7 容量增长直觉：vector 是怎么"变大"的

一句话直觉：**vector 内部其实也是一块连续内存，快装满时就申请一块翻倍大的新内存，把旧数据整体搬家**。所以它的**容量（Capacity）**总是翻着倍涨、只增不减：

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    vector<int> v;
    for (int i = 1; i <= 9; i++) {
        v.push_back(i);
        cout << "size=" << v.size() << "  capacity=" << v.capacity() << endl;
    }
    return 0;
}
```

```text
size=1  capacity=1
size=2  capacity=2
size=3  capacity=4
size=4  capacity=4
size=5  capacity=8
size=6  capacity=8
size=7  capacity=8
size=8  capacity=8
size=9  capacity=16
```

（GCC 下的典型输出；MSVC 的扩容倍数不同，数字会略有差异，但"翻倍增长、只增不减"的直觉一致。）现阶段你只需记住：**size 是"实际装了几个"，capacity 是"房子里总共有几个床位"**，扩容有成本，但vector 替你处理得很好，放心用。

---

## 5. 和机器人有什么关系：容器就是机器人的"数据口粮"

### 5.1 一帧激光雷达 = `std::vector<double>`

一帧 720 线的激光雷达扫描，本质就是 720 个距离值排成一串——这就是 `vector<double>`。最常见的处理：统计最大、最小、平均距离（最小距离直接决定"会不会撞"）。

**先手动演算一遍**，拿 3 个数 `{1.0, 0.5, 2.0}` 走一遍算法，看清每一步：

| 步骤 | 取到的数 | minD（最小） | maxD（最大） | sum（累加和） |
|---|---|---|---|---|
| 初始 | — | 1.0（取第 1 个） | 1.0 | 0.0 |
| 第 1 轮 | 1.0 | 1.0 < 1.0？否 | 1.0 > 1.0？否 | 0.0+1.0=1.0 |
| 第 2 轮 | 0.5 | 0.5 < 1.0？是→0.5 | 0.5 > 1.0？否 | 1.0+0.5=1.5 |
| 第 3 轮 | 2.0 | 2.0 < 0.5？否 | 2.0 > 1.0？是→2.0 | 1.5+2.0=3.5 |
| 收尾 | — | 0.5 | 2.0 | 3.5÷3≈1.167 |

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    // 模拟一帧 720 线激光雷达：每个角度一个距离值（米）
    // 真实数据来自雷达驱动，这里造一点有起伏的假数据
    vector<double> scan(720);              // 720 个元素，初值全是 0

    for (int i = 0; i < 720; i++) {
        scan[i] = 1.0 + (i % 100) * 0.01;  // 距离在 1.00 ~ 1.99 米之间波动
    }

    double minD = scan[0];   // 先假设第 0 个最小（不能设成 0！0 不是有效距离）
    double maxD = scan[0];   // 同理，先假设第 0 个最大
    double sum = 0.0;        // 累加器：所有距离之和

    for (double d : scan) {  // 范围 for：720 个数挨个过一遍
        if (d < minD) minD = d;    // 发现更小的 → 更新最小值
        if (d > maxD) maxD = d;    // 发现更大的 → 更新最大值
        sum += d;                  // 累加
    }

    double avg = sum / scan.size();      // 均值 = 总和 ÷ 个数

    cout << "本帧点数: " << scan.size() << endl;
    cout << "最近距离: " << minD << " 米" << endl;
    cout << "最远距离: " << maxD << " 米" << endl;
    cout << "平均距离: " << avg << " 米" << endl;
    return 0;
}
```

```text
本帧点数: 720
最近距离: 1 米
最远距离: 1.99 米
平均距离: 1.48389 米
```

> ⚠ 求最值时初值必须取"第一个元素"，不能取 0：距离本来就没有 0，若 `minD` 初始为 0，结果永远是 0。这是统计题的经典陷阱。

### 5.2 机器人轨迹点序列 = `vector<vector<double>>`

一段轨迹是很多个路径点的序列，每个路径点又是 `{x, y}` 两个数——"列表的列表"正好派上用场：

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    // 内层 vector 是"一个点"，外层 vector 是"整条轨迹"
    vector<vector<double>> traj = {
        {0.0, 0.0},     // 起点：原点
        {1.0, 0.0},     // 向东 1 米
        {1.0, 1.0},     // 向北 1 米
        {2.0, 1.5}      // 斜着走
    };

    for (vector<double> point : traj) {   // 外层循环每次取出"一个点"（拷贝一份）
        cout << "(" << point[0] << ", " << point[1] << ")" << endl;
    }
    cout << "共 " << traj.size() << " 个路径点" << endl;
    return 0;
}
```

```text
(0, 0)
(1, 0)
(1, 1)
(2, 1.5)
共 4 个路径点
```

> ◇ 这里每次拷贝的点只有 2 个 double（16 字节），代价可忽略。等下一章学了**引用（Reference）**，就能写成"只递门牌号、不拷贝数据"的零拷贝遍历——处理大点云时那才是必需品。

### 5.3 路径点插值：在 A、B 之间均匀补点

机器人执行路径时需要"每 25% 走一段"的中间点。**线性插值（Linear Interpolation）** 的公式：第 k 个点的比例 `t = k / 总段数`，坐标 = 起点 + t ×（终点 − 起点）。

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    double ax = 0.0, ay = 0.0;    // 起点坐标（米）
    double bx = 2.0, by = 1.0;    // 终点坐标（米）

    vector<vector<double>> path;
    // 在 A、B 之间均匀取 5 个点（含 A、B 本身）：t = 0, 0.25, 0.5, 0.75, 1
    for (int k = 0; k <= 4; k++) {
        double t = k / 4.0;                  // 注意写 4.0！写 4 会变成整数除法
        double x = ax + t * (bx - ax);       // 沿直线走 t 的比例
        double y = ay + t * (by - ay);
        path.push_back({x, y});              // 用花括号直接拼出一个点
    }

    for (vector<double> p : path) {
        cout << "(" << p[0] << ", " << p[1] << ")" << endl;
    }
    return 0;
}
```

```text
(0, 0)
(0.5, 0.25)
(1, 0.5)
(1.5, 0.75)
(2, 1)
```

> ⚠ `k / 4.0` 若写成 `k / 4`：整数除法直接砍掉小数，t 只会是 0 或 1——"插值插出一堆重复点"的经典事故。

---

## 6. 常见错误与自救

| 错误现象 | 原因 | 怎么改 |
|---|---|---|
| 循环最后一个元素永远读不到 / 读到垃圾 | 循环写成 `i <= v.size()`（多走一步，越界） | 改成 `i < v.size()` |
| 程序"时好时坏"地崩溃 | `[]` 越界（未定义行为） | 用 `.at()` 定位越界点；检查下标来源 |
| 求最小值结果永远是 0 | minD 初值设成了 0 | 初值取"第一个元素" |
| 插值结果只有起点终点 | `k / 4` 整数除法 | 至少一边写成小数：`k / 4.0` |
| `string a = b + c` 报错 | `b` 是字面量 `"abc"`，字面量之间不能用 `+` | 至少一个操作数是 string 变量 |
| 两个数死活不相等（如 0.1+0.2） | 浮点数有微小误差 | 比较时判断差值 `< 1e-9` 而非 `==` |
| 二维 vector 打印全是 0 | 只建了外层，忘了给每行塞内层 | 用 `grid(rows, vector<int>(cols, 0))` 一行建好 |

---

## 7. 动手练习

**练习 1**：温度数组 `{21, 23, 25, 24, 22, 20, 19}`，求最高温度和它是第几天（第几天按人类习惯从 1 数起）。

**练习 2**：文件名 `string name = "robot_config.yaml";`，用 `find` 和 `substr` 取出 `"yaml"`（不含点）。

**练习 3**：成绩 vector `{78, 92, 85, 61, 90}`，用范围 for 求平均分。

**练习 4**：用一行惯用写法建 3×3 单位矩阵（对角线是 1，其余是 0）并打印。

??? details "练习解答"

    **练习 1**：
    ```cpp
    #include <iostream>
    using namespace std;

    int main() {
        int temp[7] = {21, 23, 25, 24, 22, 20, 19};
        int maxT = temp[0];
        int maxDay = 1;                       // 记录"第几天"（从 1 数起）
        for (int i = 1; i < 7; i++) {
            if (temp[i] > maxT) {
                maxT = temp[i];
                maxDay = i + 1;               // 下标 i 对应第 i+1 天
            }
        }
        cout << "最高温 " << maxT << " 度，是第 " << maxDay << " 天" << endl;
        return 0;
    }
    ```

    ```text
    最高温 25 度，是第 3 天
    ```

    **练习 2**：
    ```cpp
    #include <iostream>
    #include <string>
    using namespace std;

    int main() {
        string name = "robot_config.yaml";
        int dot = name.find('.');             // 找到点的下标（int 装下标够用）
        string ext = name.substr(dot + 1);    // 从点的下一个字符取到结尾
        cout << ext << endl;                  // substr 只给起点 = 取到末尾
        return 0;
    }
    ```

    ```text
    yaml
    ```

    **练习 3**：
    ```cpp
    #include <iostream>
    #include <vector>
    using namespace std;

    int main() {
        vector<int> scores = {78, 92, 85, 61, 90};
        int total = 0;
        for (int s : scores) {
            total += s;
        }
        cout << "平均分 " << (double)total / scores.size() << endl;  // (double)：先转小数再除
        return 0;
    }
    ```

    ```text
    平均分 81.2
    ```

    **练习 4**：
    ```cpp
    #include <iostream>
    #include <vector>
    using namespace std;

    int main() {
        // 先建一张 3x3 的全 0 表
        vector<vector<int>> eye(3, vector<int>(3, 0));
        for (int i = 0; i < 3; i++) {
            eye[i][i] = 1;                    // 对角线位置：行号 == 列号
        }
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                cout << eye[i][j] << " ";
            }
            cout << endl;
        }
        return 0;
    }
    ```

    ```text
    1 0 0
    0 1 0
    0 0 1
    ```

---

## 本章速查卡

| 想做的事 | 写法 |
|---|---|
| 定义 C 数组 | `int a[5] = {1, 2, 3, 4, 5};` |
| 定义空 vector / 定长 vector | `vector<int> v;` / `vector<int> v(3, 0);` |
| 列表初始化 | `vector<int> v = {1, 2, 3};` |
| 追加 / 删末尾 / 问个数 | `v.push_back(x);` / `v.pop_back();` / `v.size()` |
| 取末尾元素 | `v.back()` |
| 访问（快/危险） | `v[i]`；带越界检查用 `v.at(i)` |
| 遍历 | `for (int x : v) { ... }` |
| 二维建表 | `vector<vector<int>> g(r, vector<int>(c, 0));` |
| string 拼接 / 比较 | `s = a + b;` / `a == b`、`a < b` |
| 长度 / 子串 / 查找 | `s.length()` / `s.substr(起, 长)` / `s.find(串)` |
| 数字→串 / 串→数字 | `to_string(x)` / `stoi(s)`、`stod(s)` |
| 容量直觉 | size=实际数量；capacity=床位（翻倍增长） |

---

## 下一章预告

下一章 [40_指针_引用与内存模型](./40_指针_引用与内存模型.md) 揭开容器底下的世界：变量住在哪里（地址）、`&` 和 `*` 到底是什么、为什么函数改不了外面的变量、以及"传大数据千万别拷贝"的铁律——这是从"会写代码"迈向"看懂 ROS 代码"的关键一步。
