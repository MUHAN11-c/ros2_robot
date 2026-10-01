# STL 容器与算法：用工具箱武装你的机器人

> **教材锚点**：C++ Primer 第5版 第10、11章（直觉版） | **前置**：第 50 章《类与对象初步》

---

## 本章导航

**上一章**：[50_类与对象初步](./50_类与对象初步.md)

**这章讲什么？** C++ 的**标准模板库（STL, Standard Template Library）** 是随编译器附赠的"工具箱"：几种现成的容器（`vector`、`map`、`set`）、几十个现成的算法（`sort`、`find`、`count_if`……）和连接两者的**迭代器（Iterator）**。学完直接进入实战：写一个约 120 行的**命令行机器人状态监控器**。

**为什么要学它？** STL 是 C++ 机器人代码的"普通话"：ROS 2 的参数表是 `map`，点云滤波用 `find`/`count_if` 的思路，路径平滑离不开 `sort`。会用工具箱，你的开发效率直接翻十倍。

**学完能做什么？** 能按场景选对容器；能用迭代器与常用算法组合出统计逻辑；能独立写出"读入数据 → 分桶 → 统计 → 找异常 → 排序出报表"的完整小项目。

**本章在路线图中的位置**：

```text
00_入门
├── 10_环境搭建与第一个程序
├── 20_控制流_函数与程序结构
├── 30_数组_string与vector
├── 40_指针_引用与内存模型
├── 50_类与对象初步            ← 上一章
└── 60_STL容器算法与实战小项目 ← 你在这里（入门篇收官！）
```

| 学习方式 | 时间 | 适合谁 |
|---|---|---|
| 首次学习（跟做练习） | 4-5 小时 | 第一次接触该主题（含实战项目） |
| 快速复习 | 60 分钟 | 学过但遗忘，查漏补缺 |

**运行环境**：任意操作系统 + g++ 9 以上。统一用 `g++ 文件名.cpp -o 程序名 -std=c++17` 编译。

---

## 1. 从生活到概念：STL 是一个工具箱

回想第 30 章：`vector` 会自动扩容、知道自己有几个元素——但你有没有想过，"排序""查找""统计"这些活儿是不是也得自己写循环？不用。标准库作者早就替你写好了，打包成 STL。

| 工具箱里的东西 | STL 对应 | 本章涉及 |
|---|---|---|
| 各种收纳盒 | 容器：`vector` / `map` / `set` | 全部 |
| 量尺、取物夹 | 迭代器：`begin()` / `end()` | 第 4 节 |
| 电动工具 | 算法：`sort` / `find` / `count_if` / `accumulate` | 第 5 节 |
| 万能转接头 | `auto`、lambda | 第 4、5 节 |

就像打开背包前先想清楚要什么——派蒙也帮不了不报 `#include` 的旅行者：每个工具都要先包含对应头文件（`<map>`、`<set>`、`<algorithm>`、`<numeric>`）。

> ⚠ **类比在哪里失效**：工具箱不会管你"用哪把工具"，但 STL 的容器是有性格的——`vector` 擅长按下标快取，`map` 擅长按键查找，选错容器代码照样能跑，只是慢。选型直觉见第 7 节速查卡。

---

## 2. map：按"名字"查东西的容器

> 📖 教材对照：C++ Primer 第5版 §11.1、§11.2

**映射（Map）** 存的不是一串元素，而是**键值对（Key-Value Pair）**：每个"键"（Key，如单词、名字）对应一个"值"（Value，如次数、价格）。就像字典：按词（键）翻到释义（值）。

```cpp
#include <iostream>
#include <string>
#include <map>
using namespace std;

int main() {
    map<string, double> price;       // 键=配件名，值=价格（元）
    price["battery"] = 120.5;        // 用 [] 插入或覆盖：键不存在就自动创建
    price["lidar"] = 999.0;
    price["battery"] = 118.0;        // 键已存在：覆盖旧值

    cout << price["battery"] << endl;    // 按键取值，O(log N) 很快
    cout << price.size() << endl;        // 2 个键值对（battery、lidar）
    return 0;
}
```

```text
118
2
```

map 最经典的应用是**统计频次**。先手动演算，看清 `count[w] += 1` 每一步发生了什么（初始 `{imu, lidar, imu, cam, lidar, imu}`）：

| 步骤 | 取到的词 | 此刻 map 的状态（词:次数） |
|---|---|---|
| 初始 | — | （空） |
| 1 | imu | imu:1（键不存在→自动创建并 +1） |
| 2 | lidar | imu:1, lidar:1 |
| 3 | imu | imu:2, lidar:1 |
| 4 | cam | cam:1, imu:2, lidar:1 |
| 5 | lidar | cam:1, imu:2, lidar:2 |
| 6 | imu | cam:1, imu:3, lidar:2 |

```cpp
#include <iostream>
#include <string>
#include <map>
#include <vector>
using namespace std;

int main() {
    vector<string> words = {"imu", "lidar", "imu", "cam", "lidar", "imu"};
    map<string, int> count;

    for (const string& w : words) {
        count[w] += 1;               // 不存在则先创建成 0，再 +1
    }

    for (const auto& kv : count) {   // 遍历出来的是 pair：kv.first 键, kv.second 值
        cout << kv.first << " 出现 " << kv.second << " 次" << endl;
    }
    return 0;
}
```

```text
cam 出现 1 次
imu 出现 3 次
lidar 出现 2 次
```

> ◇ 注意输出**按键的字典序自动排好**（cam < imu < lidar）——map 内部是有序结构，这是它"顺便白送"的能力，报表功能直接受益。

---

## 3. set：自动去重的花名册

> 📖 教材对照：C++ Primer 第5版 §11.2

**集合（Set）** 只记"有哪些、没有重复"：同一元素插一万遍也只算一个，而且始终自动排序。典型用途：机器人清单里到底有哪几**种**传感器？

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <set>
using namespace std;

int main() {
    vector<string> tags = {"imu", "cam", "imu", "lidar", "cam", "imu"};

    set<string> unique;              // 空 set
    for (const string& t : tags) {
        unique.insert(t);            // insert：重复的插不进去，也不报错
    }

    cout << "去重后有 " << unique.size() << " 种传感器" << endl;
    for (const string& t : unique) { // 打印时已按字典序排好
        cout << t << " ";
    }
    cout << endl;
    return 0;
}
```

```text
去重后有 3 种传感器
cam imu lidar
```

`set` 和 `map` 是一家：set 相当于"只存键、不存值"的 map，同样自动有序、同样 O(log N) 查询。

---

## 4. 迭代器与 auto：容器的"通用取物夹"

> 📖 教材对照：C++ Primer 第5版 §3.4（迭代器）、§2.5.2（auto）

**迭代器（Iterator）** 是"指向容器中某个位置"的东西，行为很像上一章的指针：`*it` 取出它指的元素，`++it` 挪到下一个。每个容器都有 `begin()`（起点）和 `end()`（终点之后的位置）：

```text
vector:  [10] [20] [30]
          ↑                ↑
        begin()          end()（注意：end 不指向任何元素，
                            它是"最后一个元素之后"的记号）
```

```cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    vector<int> v = {10, 20, 30};

    // 写法一：范围 for —— 你一直在用的糖
    for (int x : v) {
        cout << x << " ";
    }
    cout << endl;

    // 写法二：迭代器循环 —— 范围 for 在底层就是它
    for (vector<int>::iterator it = v.begin(); it != v.end(); ++it) {
        cout << *it << " ";       // it 像指针：*it 取元素，++it 下一个
    }
    cout << endl;
    return 0;
}
```

```text
10 20 30
10 20 30
```

`vector<int>::iterator` 这串类型名太长——**自动类型推导（Auto，`auto` 关键字）** 让编译器从右边的表达式自己推出类型：

```cpp
#include <iostream>
#include <vector>
#include <map>
#include <string>
using namespace std;

int main() {
    vector<int> v = {10, 20, 30};
    map<string, double> m;
    m["battery"] = 1.2;

    auto x = 42;            // 从 42 推出：x 是 int
    auto it = v.begin();    // 完整类型 vector<int>::iterator，auto 替你写
    auto kv = m.begin();    // map 的迭代器：更长的类型串，auto 价值更大

    cout << x << " " << *it << " " << kv->first << endl;
    return 0;
}
```

```text
42 10 battery
```

> ◇ `kv->first`：map 的迭代器指向一个 pair，`->` 直接取它的成员（上一章的箭头语法）。**auto 的使用原则**：类型名太长或一眼可见时用它（迭代器、范围 for 的元素）；类型不明显、影响阅读时写出真名。

---

## 5. 常用算法：四把电动工具

> 📖 教材对照：C++ Primer 第5版 §10.2（初识泛型算法）、§10.3（定制操作）

算法的统一用法：`算法名(起点迭代器, 终点迭代器, 其他参数)`。四个最常用的，每个都给完整程序。

### 5.1 sort：排序（含 lambda 初见）

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>     // sort 在这里
using namespace std;

int main() {
    vector<int> scores = {88, 72, 95, 60};
    sort(scores.begin(), scores.end());       // 默认：从小到大
    for (int s : scores) cout << s << " ";
    cout << endl;

    // 进阶：想"从大到小"排？给 sort 一个自定义比较规则
    vector<pair<string, int>> power = {       // 机器人名字:电量
        {"alpha", 90}, {"beta", 75}, {"gamma", 98}
    };
    // lambda：现场写的小匿名函数。[] 是捕获列表（这里为空），
    // (a, b) 是待比较的两个元素，返回"true 表示 a 应排在 b 前面"
    sort(power.begin(), power.end(),
         [](const pair<string, int>& a, const pair<string, int>& b) {
             return a.second > b.second;      // 电量大的在前：从大到小
         });
    for (const auto& p : power) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}
```

```text
60 72 88 95
gamma 98
alpha 90
beta 75
```

**lambda 表达式（Lambda Expression）** 就是"随写随用的小函数"，最常见的用场正是给 sort 这类算法提供比较规则。`> b.second` 表示"a 的值更大就算 a 在前"，于是从大到小。

### 5.2 find：查找

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    vector<string> sensors = {"cam", "imu", "lidar"};

    // find：从头找到尾，返回指向目标的迭代器；找不到返回 end()
    auto pos = find(sensors.begin(), sensors.end(), "imu");

    if (pos != sensors.end()) {
        cout << "找到了，下标: " << pos - sensors.begin() << endl;  // 迭代器相减=下标
    } else {
        cout << "没找到" << endl;
    }
    return 0;
}
```

```text
找到了，下标: 1
```

### 5.3 count_if：按条件计数

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    vector<double> dists = {0.3, 1.2, 0.8, 2.5, 0.45, 3.0};

    // count_if：统计满足条件的元素个数；条件用 lambda 表达
    int n = count_if(dists.begin(), dists.end(),
                     [](double d) { return d < 1.0; });   // 距离 < 1 米算"近障碍"

    cout << "近障碍点有 " << n << " 个" << endl;
    return 0;
}
```

```text
近障碍点有 3 个
```

（0.3、0.8、0.45 三个点满足 `< 1.0`。）这也是激光雷达避障里"统计近距离障碍点数"的雏形。

### 5.4 accumulate：求和

```cpp
#include <iostream>
#include <vector>
#include <numeric>       // accumulate 在这里（不在 algorithm！）
using namespace std;

int main() {
    vector<double> temp = {25.0, 26.0, 24.0};

    // accumulate：范围累加；第三个参数 0.0 是累加初值（必须写，且类型要匹配）
    double sum = accumulate(temp.begin(), temp.end(), 0.0);
    cout << "平均温度: " << sum / temp.size() << endl;
    return 0;
}
```

```text
平均温度: 25
```

| 算法 | 头文件 | 干什么 | 关键参数 |
|---|---|---|---|
| `sort` | `<algorithm>` | 排序 | 可选：比较规则（lambda） |
| `find` | `<algorithm>` | 查找，返回迭代器 | 要找的值 |
| `count_if` | `<algorithm>` | 按条件计数 | 条件（lambda） |
| `accumulate` | `<numeric>` | 求和 | 累加初值 |

---

## 6. 和机器人有什么关系：命令行机器人状态监控器（实战小项目）

前三章的知识（struct、vector、const 引用、类、STL）现在合成一个真实项目。

### 6.1 需求与拆解

**场景**：机器人每秒上报一条传感器记录——时间戳、温度、距离。你要写一个监控器，读入 N 条记录后：

```text
读入 N 条记录 → 按 10 秒分桶 → 每桶算均值 → 找异常距离 → 输出排序报表
```

| 步骤 | 用什么工具 | 输出什么 |
|---|---|---|
| 1. 读入 | `struct Record` + `vector` | 记录列表 |
| 2. 分桶 | `map<int, vector<Record>>` | 桶号 → 记录列表（键自动有序） |
| 3. 统计 | 范围 for + 累加 | 每桶平均温度、平均距离 |
| 4. 找异常 | `fabs(偏离) > 0.5` 判定 | (时间戳, 距离) 列表 |
| 5. 报表 | `sort` + `fixed/setprecision` | 按时间排序的异常清单 |

**分桶规则**：桶号 = 时间戳 ÷ 10（整数除法）。0~9 秒进 0 号桶，10~19 秒进 1 号桶……
**异常规则**：一条记录的距离偏离它所在桶的平均距离超过 0.5 米，记为异常（可能是假回波或障碍突现）。

### 6.2 分块走读（5 块）

**块 1/5：数据结构与读入**

```cpp
struct Record {                  // 一条传感器记录（第 50 章的 struct）
    int time;                    // 时间戳（秒）
    double temp;                 // 温度（摄氏度）
    double dist;                 // 障碍距离（米）
};

int n;
cin >> n;                        // 第一行：记录条数 N
vector<Record> records;          // 全部记录先装进 vector
for (int i = 0; i < n; i++) {
    Record r;
    cin >> r.time >> r.temp >> r.dist;   // 之后每行：时间 温度 距离
    records.push_back(r);
}
```

**块 2/5：按 10 秒分桶**

```cpp
map<int, vector<Record>> buckets;        // 键=桶号，值=该时段的记录列表
for (const Record& r : records) {        // const 引用：不拷贝（第 40 章）
    int id = r.time / 10;                // 整数除法自动完成分桶
    buckets[id].push_back(r);            // 键不存在时 map 自动创建空桶！
}
```

这一块是全项目的题眼：`buckets[id]` 在键不存在时会**自动插入**一个空的 `vector`，所以"建桶 + 放数据"一步完成——第 2 节词频统计的同款技巧，只是值从 `int` 换成了 `vector<Record>`。

**块 3/5：每桶统计均值**

```cpp
map<int, pair<double, double>> mean;     // 桶号 -> (平均温度, 平均距离)
for (const auto& [id, recs] : buckets) { // 结构化绑定（第 50 章）：拆出桶号与记录
    double sumT = 0.0, sumD = 0.0;
    for (const Record& r : recs) {
        sumT += r.temp;
        sumD += r.dist;
    }
    mean[id] = {sumT / recs.size(), sumD / recs.size()};   // pair 直接用花括号拼
}
```

**块 4/5：找异常值**

```cpp
vector<pair<int, double>> anomalies;     // (时间戳, 该记录距离)
for (const auto& [id, recs] : buckets) {
    double meanD = mean[id].second;      // 该桶的平均距离
    for (const Record& r : recs) {
        if (fabs(r.dist - meanD) > 0.5) {        // fabs：浮点绝对值（<cmath>）
            anomalies.push_back({r.time, r.dist});
        }
    }
}
sort(anomalies.begin(), anomalies.end());        // pair 默认按 first 升序=按时间排序
```

**块 5/5：输出报表**

```cpp
cout << fixed << setprecision(2);        // 小数固定 2 位（<iomanip>）
cout << "==== 分桶统计 ====" << endl;
cout << "桶号 条数 平均温度 平均距离" << endl;
for (const auto& [id, recs] : buckets) { // map 按桶号升序 → 报表天然有序
    cout << id << " " << recs.size() << " "
         << mean[id].first << " " << mean[id].second << endl;
}
cout << "==== 异常记录(偏离桶均值>0.5m) ====" << endl;
if (anomalies.empty()) {
    cout << "无" << endl;
} else {
    for (const auto& a : anomalies) {    // 已按时间排好
        cout << "t=" << a.first << "s dist=" << a.second << "m" << endl;
    }
}
```

### 6.3 完整合并版（monitor.cpp，约 120 行）

```cpp
// monitor.cpp —— 命令行机器人状态监控器
// 编译：g++ monitor.cpp -o monitor -std=c++17
// 运行：./monitor，先输入记录条数 N，再逐行输入"时间 温度 距离"，输完自动出报表

#include <iostream>      // cin、cout
#include <vector>        // vector
#include <map>           // map
#include <algorithm>     // sort
#include <iomanip>       // fixed、setprecision
#include <cmath>         // fabs
using namespace std;

// ---------- 数据结构 ----------
// 一条传感器记录：机器人每秒上报一次
struct Record {
    int time;            // 时间戳（秒）
    double temp;         // 温度（摄氏度）
    double dist;         // 障碍距离（米）
};

int main() {
    // ---------- 块 1：读入 ----------
    int n;
    cin >> n;                                // 第一行：记录条数 N
    vector<Record> records;                  // 全部记录先装进 vector
    for (int i = 0; i < n; i++) {
        Record r;
        cin >> r.time >> r.temp >> r.dist;   // 之后每行三个数：时间 温度 距离
        records.push_back(r);
    }

    // ---------- 块 2：按 10 秒分桶 ----------
    map<int, vector<Record>> buckets;        // 键=桶号，值=该时段的记录列表
    for (const Record& r : records) {
        int id = r.time / 10;                // 整数除法：0-9 秒进 0 号桶
        buckets[id].push_back(r);            // 键不存在时 map 自动建空桶
    }

    // ---------- 块 3：每桶统计均值 ----------
    map<int, pair<double, double>> mean;     // 桶号 -> (平均温度, 平均距离)
    for (const auto& [id, recs] : buckets) { // 结构化绑定：拆出桶号与记录列表
        double sumT = 0.0, sumD = 0.0;
        for (const Record& r : recs) {
            sumT += r.temp;                  // 温度累加
            sumD += r.dist;                  // 距离累加
        }
        mean[id] = {sumT / recs.size(), sumD / recs.size()};
    }

    // ---------- 块 4：找异常值 ----------
    vector<pair<int, double>> anomalies;     // (时间戳, 该记录距离)
    for (const auto& [id, recs] : buckets) {
        double meanD = mean[id].second;      // 所在桶的平均距离
        for (const Record& r : recs) {
            if (fabs(r.dist - meanD) > 0.5) {        // 偏离超过 0.5 米
                anomalies.push_back({r.time, r.dist});
            }
        }
    }
    sort(anomalies.begin(), anomalies.end());        // pair 按 first（时间）升序

    // ---------- 块 5：输出报表 ----------
    cout << fixed << setprecision(2);        // 小数固定保留 2 位
    cout << "==== 分桶统计 ====" << endl;
    cout << "桶号 条数 平均温度 平均距离" << endl;
    for (const auto& [id, recs] : buckets) { // map 按桶号升序 → 报表天然有序
        cout << id << " " << recs.size() << " "
             << mean[id].first << " " << mean[id].second << endl;
    }
    cout << "==== 异常记录(偏离桶均值>0.5m) ====" << endl;
    if (anomalies.empty()) {
        cout << "无" << endl;                // 一条异常都没有
    } else {
        for (const auto& a : anomalies) {    // 已按时间排好
            cout << "t=" << a.first << "s dist=" << a.second << "m" << endl;
        }
    }
    return 0;
}
```

### 6.4 两组样例输入输出

**样例 1：有一个障碍突现**（t=13 秒时距离掉到 0.40 米）——输入：

```text
6
3 25.0 2.10
5 26.0 2.05
12 24.5 1.80
13 24.0 0.40
18 25.5 1.75
33 22.0 3.00
```

输出：

```text
==== 分桶统计 ====
桶号 条数 平均温度 平均距离
0 2 25.50 2.07
1 3 24.67 1.32
3 1 22.00 3.00
==== 异常记录(偏离桶均值>0.5m) ====
t=13s dist=0.40m
```

核对一下：1 号桶平均距离 = (1.80+0.40+1.75)/3 ≈ 1.32，t=13 的 0.40 偏离约 0.92 米 > 0.5，被抓出；t=12、t=18 分别偏离约 0.48、0.43 米，未超阈值。0 号桶、3 号桶各点都贴近自家均值，无异常。

**样例 2：一切正常**——输入：

```text
4
1 20.0 2.00
8 22.0 2.20
11 21.0 2.05
19 23.0 2.15
```

输出：

```text
==== 分桶统计 ====
桶号 条数 平均温度 平均距离
0 2 21.00 2.10
1 2 22.00 2.10
==== 异常记录(偏离桶均值>0.5m) ====
无
```

从空文件到这份报表，你用到了 struct、vector、map、pair、结构化绑定、const 引用、迭代器风格的 sort、流格式控制——入门篇的每一章都在这 120 行里。把报表写得这样清楚，紫樱看了也要赞一句"懂得趣味呢"。

---

## 7. 常见错误与自救

| 错误现象 | 原因 | 怎么改 |
|---|---|---|
| 编译报错 `'map' was not declared` | 忘了 `#include <map>`（或 `<set>`、`<numeric>`） | 每用一样工具先补头文件 |
| `m["key"]` 读出一个意外的 0 | `[]` 在键不存在时会**插入**默认值 | 只读查询用 `count()` 或 `find()` 判断存在性 |
| 遍历 map 报错 no match for `[]` | 把 map 元素当成了数组下标访问 | 遍历出来的是 pair：`kv.first` / `kv.second` |
| `sort` 编译报错找不到函数 | 忘了 `#include <algorithm>` | 同上，补头文件 |
| accumulate 结果恒为整数 | 初值写成 `0`（int 求和后截断） | 初值写 `0.0` |
| `end()` 处取值崩溃 | `end()` 不指向元素，解引用即未定义行为 | 先判 `it != v.end()` 再 `*it` |
| lambda 返回值类型纠结 | 比较器写成 `a > b` 却期望升序 | 记住：返回 true = a 排前面 |

---

## 8. 动手练习

**练习 1**：用 `map<char, int>` 统计字符串 `"robotics"` 中每个字符出现的次数，按字典序打印。
**练习 2**：两路传感器各自检测到一串物体 id：A = {1, 2, 3, 4}，B = {3, 4, 5}。用 `set` 求两路**都**检测到的 id。
**练习 3**：`vector<vector<double>> path = {{2,1},{0,0},{1,3}};`，用 sort + lambda 按 x 坐标从小到大排序并打印。
**练习 4**：给监控器加一个功能：在报表最后输出"温度最高的桶号及其平均温度"。

??? details "练习解答"

    **练习 1**：
    ```cpp
    #include <iostream>
    #include <string>
    #include <map>
    using namespace std;

    int main() {
        string s = "robotics";
        map<char, int> count;
        for (char c : s) {
            count[c] += 1;             // 同款技巧：不存在自动创建为 0
        }
        for (const auto& kv : count) { // map 自动按字符字典序输出
            cout << kv.first << ": " << kv.second << endl;
        }
        return 0;
    }
    ```
    ```text
    b: 1
    c: 1
    i: 1
    o: 2
    r: 1
    s: 1
    t: 1
    ```

    **练习 2**：
    ```cpp
    #include <iostream>
    #include <set>
    using namespace std;

    int main() {
        set<int> a = {1, 2, 3, 4};
        set<int> b = {3, 4, 5};
        for (int x : a) {
            if (b.count(x) > 0) {      // count(x)：x 在 set 里几个（0 或 1）
                cout << x << " ";      // 两路都有 = 交集
            }
        }
        cout << endl;
        return 0;
    }
    ```
    ```text
    3 4
    ```

    **练习 3**：
    ```cpp
    #include <iostream>
    #include <vector>
    #include <algorithm>
    using namespace std;

    int main() {
        vector<vector<double>> path = {{2, 1}, {0, 0}, {1, 3}};
        sort(path.begin(), path.end(),
             [](const vector<double>& a, const vector<double>& b) {
                 return a[0] < b[0];   // 按 x 坐标（第 0 个分量）升序
             });
        for (const auto& p : path) {
            cout << "(" << p[0] << ", " << p[1] << ")" << endl;
        }
        return 0;
    }
    ```
    ```text
    (0, 0)
    (1, 3)
    (2, 1)
    ```

    **练习 4**：在块 5 报表输出之后、`return 0;` 之前加：
    ```cpp
        // 找平均温度最高的桶：遍历 mean，维护最大值
        int hottestId = -1;
        double hottestT = -1e9;              // 比任何真实温度都低的初值
        for (const auto& [id, m] : mean) {
            if (m.first > hottestT) {
                hottestT = m.first;
                hottestId = id;
            }
        }
        if (hottestId != -1) {
            cout << "最热桶号: " << hottestId
                 << " 平均温度: " << hottestT << endl;
        }
    ```
    用样例 1 的输入验证，最后多一行 `最热桶号: 0 平均温度: 25.50`。

---

## 综合习题：给状态监控器加"故障统计面板"（全章知识串联）

在 §6 命令行状态监控器的基础上扩展：CPU 负载序列 `{72, 95, 40, 88, 61}`，>80 记一次"过载"故障；另有"低电"故障一次。产出四行统计：故障计数、排序后峰值、均值、去重后的负载数。

**(a) 计数面板**（§2 map）：用 `map<string,int>` 累计故障名 → 次数，并按 `auto& [k,v]` 遍历打印。

**(b) 去重花名册**（§3 set）：把负载序列灌进 `set`，回答"几个不同档位的负载"。

**(c) 四把电动工具**（§5 算法）：用 `sort`、`accumulate`、`count_if`（配合 lambda）、`back()` 完成峰值/均值/超载帧数。

**(d) 迭代器即通用取物夹**（§4）：为什么同一套算法函数能同时作用于 `vector` 和数组？

**(e) 工程复盘**（§6）：这个面板离一个真正的机器人 watchdog 还差什么（提示：谁在刷新数据？超限后做什么）？

??? details "综合习题完整解答（程序已实测编译运行）"

    ```cpp
    #include <algorithm>
    #include <iostream>
    #include <map>
    #include <numeric>
    #include <set>
    #include <vector>
    int main() {
        std::map<std::string, int> faults;                       // (a)
        std::vector<int> loads = {72, 95, 40, 88, 61};
        for (int x : loads) if (x > 80) faults["过载"]++;
        faults["低电"] = 1;
        for (const auto& [k, v] : faults)
            std::cout << k << " x" << v << "  ";
        std::cout << "\n";
        std::sort(loads.begin(), loads.end());                   // (c)
        double mean = std::accumulate(loads.begin(), loads.end(), 0.0) / loads.size();
        auto n_over = std::count_if(loads.begin(), loads.end(),
                                    [](int x){ return x > 60; });
        std::set<int> uniq(loads.begin(), loads.end());          // (b)
        std::cout << "排序后最大=" << loads.back() << " 均值=" << mean
                  << " 超载帧=" << n_over << " 去重后=" << uniq.size() << "\n";
        return 0;
    }
    ```

    实测输出：

    ```text
    低电 x1  过载 x2
    排序后最大=95 均值=71.2 超载帧=4 去重后=5
    ```

    **(b)** `set` 自动排序去重，5 个负载两两不同 → 5。**(d)** 算法函数收的是迭代器区间 `[first, last)`——迭代器是"会走路的指针"，vector、数组、甚至 `set` 都提供同款接口，这就是 STL "容器 × 算法"可自由拼装的秘密（§4 通用取物夹）。**(e)** 还差三块：①数据源接成回调/主循环（§6 的 while 结构）而不是写死的数组；②超限要**触发动作**（降速、告警日志），不是只打印；③阈值与计数需要随时间衰减（滑动窗口），否则一次尖峰永久占着"过载"名额——这三步正是从"练习题"到"工程代码"的距离。

---

## 本章速查卡

| 想做的事 | 写法 | 头文件 |
|---|---|---|
| 键值对容器 | `map<K, V> m;`，`m[k] = v;` | `<map>` |
| 遍历 map | `for (const auto& kv : m)` → `kv.first/second` | `<map>` |
| 去重集合 | `set<T> s; s.insert(x);`，存在性 `s.count(x)` | `<set>` |
| 迭代器循环 | `for (auto it = v.begin(); it != v.end(); ++it)` 用 `*it` | 各容器自带 |
| 推导类型 | `auto x = 表达式;` | 无需头文件 |
| 排序（升/自定义） | `sort(v.begin(), v.end());` / 加 lambda | `<algorithm>` |
| 查找 | `find(v.begin(), v.end(), x)`，判 `!= v.end()` | `<algorithm>` |
| 条件计数 | `count_if(v.begin(), v.end(), 条件lambda)` | `<algorithm>` |
| 求和 | `accumulate(v.begin(), v.end(), 0.0)` | `<numeric>` |
| 输出小数位 | `cout << fixed << setprecision(2);` | `<iomanip>` |
| 绝对值 | `fabs(x)` | `<cmath>` |

**容器选型直觉**：按下标快速访问 → `vector`；按名字查找/计数 → `map`；只要"有没有"→ `set`。拿不准就 `vector`，九成场景它都对。

---

## 从这里去哪里：入门篇毕业典礼

入门五章到此全部完成。你从"什么是变量"走到了"用 STL 写出一个 120 行的状态监控器"——这已经不是玩具，而是一个能读数据、能统计、能发现异常的小型机器人软件。

```text
00_入门（已毕业）
├── 10_环境搭建与第一个程序
├── 20_控制流_函数与程序结构
├── 30_数组_string与vector
├── 40_指针_引用与内存模型
├── 50_类与对象初步
└── 60_STL容器算法与实战小项目  ← 刚刚站在这里
        │
        ├── 第一站：Python 与工具链
        ├── 第二站：机器人学导论
        └── 支线：C++ 进阶篇
```

三个出口，按你的目标选：

1. **下一站：Python 与工具链** —— [15_Python与工具链/10_Python与NumPy入门_面向机器人](../15_Python与工具链/10_Python与NumPy入门_面向机器人.md)。机器人学的"数学练习场"几乎都设在 Python 里（NumPy 矩阵运算、Matplotlib 画图），有了 C++ 底子再学 Python，两天就能上手。
2. **正式进入主题：机器人学导论** —— [07_机器人学导论/00_机器人学导论_学习地图](../../07_机器人学导论/00_机器人学导论_学习地图.md)。坐标变换、正逆运动学、轨迹规划——机器人学的正餐从这张学习地图开始。
3. **C++ 支线升级：进阶篇** —— [10_C++语言核心/README](../10_C++语言核心/README.md)。想读懂真实 ROS 2 工程源码（模板、智能指针、RAII、并发），沿进阶篇逐章推进；第 40 章预告过的智能指针深水区就在那里。

> ◇ 推荐路线：先 1 后 2，C++ 进阶篇作为支线随用随查。写代码的手感不会骗人——把本章的监控器改出你自己的版本（换分桶宽度、加新统计项），比再读三遍更管用。下一站见。

---

> 🔬 **配套实验**：用类与 STL 写一个 2D 位姿小库——打开 [lab12 · C++ 工程实验室](../../08_可视化实验室/lab12_Cpp工程实验室.md)，编译运行并让全部断言通过。
