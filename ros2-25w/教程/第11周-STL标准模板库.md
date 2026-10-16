# 第11章 STL 标准模板库（容器选型与实践）

> 本章对应课程第 11 周：容器 + 迭代器 + 算法三件套。string/vector 打底，deque/list/stack/queue/set/map 进阶，机器人开发中的消息缓存、路径序列、去重与查询全落在这些容器上。

## 11.1 本周概览与课时结构

STL（Standard Template Library，标准模板库）是 C++ 的「数据结构与算法军火库」：容器（container）、迭代器（iterator）、算法（algorithm）三件套。本周从 string 与 vector 打基础，到 deque/list/stack/queue，再到关联容器 set/map，完整走一遍容器的增删查改与选型逻辑。机器人开发中，消息缓存、路径点序列、传感器去重、坐标查询——全落在这些容器上；选错容器，实时性直接掉一个数量级。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 STL 容器基础语法与操作 | 20 节 | 约 2h18m | STL 三大件、遍历、string 全操作、vector 构造与容量 |
| 第2课 STL 容器的进阶应用与实践 | 27 节 | 约 3h27m | deque/list/stack/queue/set/map 实操与容器选型 |

## 11.2 知识点梳理

### 11.2.1 第1课：STL 容器基础语法与操作

- **核心概念**：STL = 容器（存数据）+ 迭代器（遍历的统一指针抽象）+ 算法（`<algorithm>` 里的 sort/find/transform 等）+ 仿函数/适配器。三者通过迭代器解耦：算法不关心容器类型，只认迭代器区间 `[begin, end)`。
- **STL 基础语法**：`#include <vector>` 等头文件、`std::` 命名空间、模板参数 `std::vector<int>`；所有容器提供统一接口：`begin/end/size/empty/clear/push_back` 等。
- **遍历容器**：三种方式——下标（随机访问容器）、迭代器（`for (auto it = v.begin(); it != v.end(); ++it)`）、范围 for（`for (auto& x : v)`）。范围 for 最简洁，需要修改元素用 `auto&`。
- **遍历自定义数据类型**：容器存对象或对象指针；遍历时注意拷贝开销（大对象用 `const auto&`）。配合重载 `operator<<` 打印。
- **容器嵌套容器的遍历**：`std::vector<std::vector<int>>`（如栅格地图）、`std::map<std::string, std::vector<double>>`（如关节轨迹）；用范围 for 或迭代器逐层遍历。
- **string 构造与赋值**：`std::string s1("lidar"), s2 = s1, s3(10, 'x'), s4 = "scan";`；`assign()` 可一次性替换。
- **string 存取字符**：`s[i]`（越界未定义）、`s.at(i)`（越界抛 `std::out_of_range`）、`s.front()/s.back()`、`s.push_back('c')`。
- **string 拼接**：`operator+`、`append()`、`+=`；`reserve()` 预留避免多次扩容。
- **string 查找**：`find()` 返回 `size_t`（`std::string::npos` 表示失败）、`rfind()` 反向、`find_first_of()` 字符集合查找。
- **string 插入和删除**：`insert(pos, str)`、`erase(pos, len)`；频繁中间插入应改用 `std::list` 或先拼接。
- **string 替换**：`replace(pos, len, str)`。
- **string 比较**：`compare()` 返回负/零/正，或直接用 `==/!=/</>`；大小写敏感，比较的是字典序。
- **string 转 C 字符串**：`s.c_str()` 返回 `const char*`（含 `\0`），用于调 C 接口；`s.data()`（C++11 起保证 null 结尾）。
- **string 子串**：`s.substr(pos, len)` 截取，用于解析 "frame_id:xxx" 这类键值串。
- **大小写转换**：`std::transform(s.begin(), s.end(), s.begin(), ::toupper)`（注意 `::toupper` 要包 `<cctype>`，且要用 `unsigned char` 规避 UB）。
- **容器动态容量空间**：`capacity()`（已分配）vs `size()`（元素个数）；vector 扩容策略是「倍增」，扩容会拷贝全部元素、迭代器失效。
- **vector 构造函数**：`std::vector<int> v1(10);`（10 个 0）、`v2(10, 5)`（10 个 5）、`v3{1,2,3}`（初始化列表）、`v4(v3.begin(), v3.end())`（区间拷贝）。
- **vector 常用赋值**：`assign(n, value)`、`assign(iter1, iter2)`、`swap(v2)`（交换内容与容量）。
- **容器大小**：`size()/empty()/resize()/max_size()`；`resize(n)` 缩小会析构多余元素，`resize(n, val)` 扩大补默认值。

```cpp
std::vector<int> v{1, 2, 3};
for (const auto& x : v) std::cout << x << " ";
std::cout << "size=" << v.size() << " cap=" << v.capacity() << "\n";
```

### 11.2.2 第2课：STL 容器的进阶应用与实践

- **容器数据的存取**：`front()/back()/at(i)/[]`；deque/list 不支持 `[]` 随机访问（list 只有迭代器），这是容器选型的第一约束。
- **容器插入和删除**：`push_back/pop_back/insert(pos, val)/erase(pos)/erase(iter1, iter2)/clear`；`erase` 返回下一个有效迭代器（遍历中删除必须用 `it = v.erase(it)`）。
- **巧用 swap 收缩内存**：`std::vector<T>(v).swap(v);` 或 C++11 `v.shrink_to_fit()` 释放多余容量——处理完大批量轨迹后省内存。
- **reserve 预留空间**：`v.reserve(1000)` 预分配容量，避免循环 push_back 反复扩容；已知点云帧大小时必用。
- **deque 概念与容器**：双端队列，头尾插入 O(1)，分段连续内存（迭代器可 `+n` 但不如 vector 缓存友好）；适合「滑动窗口」场景（`push_front/pop_front`）。
- **stack 栈容器**：LIFO，`push/pop/top/empty/size`，底层默认 deque；不能遍历。用于撤销栈、括号匹配、DFS。
- **队列容器（queue）**：FIFO，`push/pop/front/back`；`priority_queue`（默认大顶堆）按优先级出队——机器人任务调度、A* 开放列表常用。
- **list 简介与容器**：双向链表，任意位置插入/删除 O(1)（迭代器指向元素时），不支持随机访问；`sort/remove/unique/reverse/merge` 是成员函数（因为 `std::sort` 需要随机访问迭代器）。
- **list 排序与删除自定义类型**：`l.sort(cmp)` 传自定义比较器；`l.remove(value)`/`l.remove_if(pred)` 删除满足条件的元素（自定义类型需重载 `==` 或传谓词）。
- **set 基本概念**：关联容器，元素唯一且自动按升序排序（红黑树，O(log n) 插入查找）；`insert` 返回 `pair<iterator, bool>` 判断是否重复。
- **set 容器操作**：`insert/erase/find/count/lower_bound/upper_bound/equal_range`；`find` 找不到返回 `end()`。
- **pair 对组**：`std::pair<K, V>`（`make_pair`），map 的元素类型就是 `pair<const K, V>`；`first/second` 访问。
- **set 插入验证**：`auto [it, ok] = s.insert(v);`（C++17 结构化绑定）判断插入成功。
- **multiset**：允许重复元素的有序集合；`count(v)` 返回重复个数，`equal_range` 一次取走所有相等元素。
- **set 设置降序**：`std::set<int, std::greater<int>> s;`，传入函数对象改变排序准则。
- **自定义数据类型 set 排序**：自定义类型需要提供 `operator<` 或传入比较器仿函数（`set<Person, CmpByName>`）。
- **map 容器**：键唯一、按键有序的键值对（`std::map<K, V>`）；`m[k]` 不存在会**自动插入默认值**（副作用），只读查找用 `m.find(k)` 或 `m.at(k)`（越界抛异常）。
- **map 进阶**：`insert({k,v})` 不覆盖已有值、`m.count(k)`/`m.contains(k)`（C++20）判断存在、`erase(k)`、遍历 `for (const auto& [k, v] : m)`。
- **unordered_map**：哈希表实现，平均 O(1) 查找，无序；适合「ID → 数据」高频查询（如 TF 帧缓存）。
- **容器使用时机**：快速随机访问→vector；头尾操作→deque；中间频繁插入删除→list；去重有序→set；键值查询→map；高频 O(1) 查询→unordered_map；LIFO→stack；FIFO→queue。

```cpp
std::map<std::string, std::vector<double>> traj;
traj["joint1"] = {0.1, 0.2, 0.3};
for (const auto& [name, points] : traj)        // C++17 结构化绑定
    std::cout << name << " has " << points.size() << " points\n";
```

#### 容器选型速查表

| 场景 | 容器 | 关键操作 |
| --- | --- | --- |
| 随机访问/与 C 接口互操作 | `vector` | `[]/push_back/reserve` |
| 头尾操作/滑动窗口 | `deque` | `push_front/pop_front` |
| 中间频繁插删 | `list` | 成员函数 `sort/remove_if` |
| 去重有序 | `set/multiset` | `insert` 返回 `pair<it,bool>` |
| 键值有序查询 | `map` | `find/at/[]`（`[]` 会隐式插入！） |
| 高频 O(1) 点查 | `unordered_map` | 哈希实现、无序 |
| LIFO/FIFO/优先级 | `stack/queue/priority_queue` | `top/front/pop` |

> **注意：** `std::map::operator[]` 在键不存在时插入默认值——在 const 场景或「只查不改」场景用 `find()`/`at()`，否则会悄悄把 map 撑大、改变排序结果。

## 11.3 重点与难点

1. **迭代器失效**：vector 扩容使所有迭代器失效；`erase` 使被删位置之后迭代器失效；`insert` 可能触发扩容。循环删除用 `it = c.erase(it)`，插入前若要保迭代器需预留容量。
2. **容量 vs 大小**：`capacity()` 与 `size()` 的区别、`reserve` 与 `resize` 的区别——面试与性能优化双高频。
3. **关联容器排序**：set/map 依据「严格弱序」（`operator<`）排序，自定义类型必须提供比较方式，否则编译失败。
4. **`map::[]` 的副作用**：查询用 `find`，插入用 `insert`/`emplace`，别在只读路径上用 `[]`。
5. **容器选型表**：先问「访问模式」（随机/头尾/中间）再问「是否去重/有序/键值」，最后问「内存连续性要求」（缓存/与 C 接口互操作优先 vector）。

## 11.4 代码与命令实战

**场景 1：string 全套操作（对应第1课）**

```cpp
// string_demo.cpp
#include <algorithm>
#include <cctype>
#include <iostream>
#include <string>

int main() {
    std::string topic = "robot/cmd_vel";
    std::cout << topic.substr(0, 5) << "\n";                    // robot
    std::size_t pos = topic.find('/');
    std::cout << topic.substr(pos + 1) << "\n";                 // cmd_vel
    topic.append("_x");
    topic.replace(topic.find("_x"), 2, "");
    std::string up = topic;
    std::transform(up.begin(), up.end(), up.begin(),
                   [](unsigned char c) { return std::toupper(c); });
    std::cout << topic << " -> " << up << "\n";
    std::cout << topic.compare("robot/cmd_vel") << "\n";        // 0 相等
}
```

```bash
g++ -std=c++17 -Wall -o string_demo string_demo.cpp && ./string_demo
```

**场景 2：vector 容量管理与安全遍历删除（对应第1、2课）**

```cpp
// vector_demo.cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> pts;
    pts.reserve(1000);                       // 预留：避免反复扩容
    for (int i = 0; i < 1000; ++i) pts.push_back(i);
    std::cout << "size=" << pts.size() << " cap=" << pts.capacity() << "\n";

    for (auto it = pts.begin(); it != pts.end();) {          // 删除偶数
        if (*it % 2 == 0) it = pts.erase(it);                // 返回下一迭代器
        else ++it;
    }
    std::vector<int>(pts).swap(pts);         // swap 收缩容量
    std::cout << "after size=" << pts.size() << " cap=" << pts.capacity() << "\n";
}
```

```bash
g++ -std=c++17 -Wall -o vector_demo vector_demo.cpp && ./vector_demo
```

**场景 3：deque 滑动窗口 + stack/queue（对应第2课）**

```cpp
// dq_sq.cpp
#include <deque>
#include <iostream>
#include <queue>
#include <stack>

int main() {
    std::deque<double> window;               // 传感器滑动窗口：保留最近 3 帧
    for (double v : {1.0, 2.0, 3.0, 4.0}) {
        window.push_back(v);
        if (window.size() > 3) window.pop_front();
    }
    for (double v : window) std::cout << v << " ";           // 2 3 4
    std::cout << "\n";

    std::stack<int> st;                      // 撤销栈
    st.push(1); st.push(2);
    std::cout << st.top() << " "; st.pop();                  // 2

    std::queue<int> q;                       // 任务队列 FIFO
    q.push(10); q.push(20);
    std::cout << q.front() << " " << q.back() << "\n";       // 10 20
}
```

```bash
g++ -std=c++17 -Wall -o dq_sq dq_sq.cpp && ./dq_sq
```

**场景 4：set/map 与自定义排序（对应第2课）**

```cpp
// set_map.cpp
#include <iostream>
#include <map>
#include <set>
#include <string>

struct Pose { double x, y; };

struct PoseLess {
    bool operator()(const Pose& a, const Pose& b) const {
        return a.x < b.x || (a.x == b.x && a.y < b.y);
    }
};

int main() {
    std::set<int, std::greater<int>> scores{70, 90, 80};     // 降序
    auto [it, ok] = scores.insert(90);                       // C++17 结构化绑定
    std::cout << "insert dup: " << ok << "\n";               // 0

    std::set<Pose, PoseLess> path{ {1, 2}, {0, 3}, {1, 1} };   // 自定义类型排序
    for (const auto& p : path) std::cout << "(" << p.x << "," << p.y << ") ";

    std::map<std::string, int> ids{ {"lidar", 1}, {"imu", 2} };
    if (auto f = ids.find("lidar"); f != ids.end()) std::cout << "\n" << f->second;
    std::cout << " count=" << ids.count("camera") << "\n";   // 0
}
```

```bash
g++ -std=c++17 -Wall -o set_map set_map.cpp && ./set_map
```

**场景 5：容器嵌套——轨迹缓存（对应第1课嵌套遍历）**

```cpp
// nested.cpp
#include <iostream>
#include <map>
#include <vector>

int main() {
    std::map<std::string, std::vector<double>> traj;          // 关节 → 角度序列
    traj["shoulder"] = {0.1, 0.2};
    traj["elbow"]    = {0.5, 0.6, 0.7};
    for (const auto& [joint, angles] : traj) {
        std::cout << joint << ": ";
        for (double a : angles) std::cout << a << " ";
        std::cout << "\n";
    }
}
```

```bash
g++ -std=c++17 -Wall -o nested nested.cpp && ./nested
```

## 11.5 运行效果（实测）

以下为滑动窗口（deque 保留最近 3 帧）、set 降序去重插入与 map 查找（`find` 命中 + `count` 未命中）的综合实测输出：

```text
2 3 4 
insert dup ok=0 top=90
lidar=1
0
```

编译命令：`g++ -std=c++17 -Wall w11_setmap.cpp -o w11 && ./w11`（滑动窗口淘汰最旧帧；重复插入 `ok=0`；`count("camera")==0`）。

## 端到端实战（实测）：CSV 点位分组统计

**需求**：传感器点位按名称分组（`map + stringstream` 解析、结构化绑定遍历）——轨迹/标定数据处理的标准形态：

```cpp
// csv_group.cpp
std::map<std::string, std::vector<double>> groups;      // name -> 坐标序列
std::istringstream in(csv);
std::string line;
while (std::getline(in, line)) {                        // 逐行
    std::stringstream ss(line);
    std::string name, xs, ys;
    std::getline(ss, name, ',');                        // 按逗号分列
    std::getline(ss, xs, ',');
    std::getline(ss, ys, ',');
    groups[name].push_back(std::stod(xs));
    groups[name].push_back(std::stod(ys));
}
for (const auto& [name, coords] : groups) {             // 结构化绑定，按 name 升序
    std::cout << name << ": " << coords.size() / 2 << " 点 -> ";
    for (double v : coords) std::cout << v << " ";
}
```

实测（输入 CSV 含 lidar/imu/camera 共 5 行）：

```text
camera: 1 点 -> 100 200 
imu: 2 点 -> 1 2 3 4 
lidar: 2 点 -> 10 20 30 40 
```

要点解析：

- `map` 天然按 key 升序遍历，所以输出顺序是 camera → imu → lidar，无需额外排序；
- `groups[name]` 首次访问自动创建空 vector——`operator[]` 的「隐式插入」副作用在这里是正向利用（分组写入）；
- `coords.size()/2` 是因为每个点占 x、y 两列，打印点数需除以 2；
- 逐行 `getline` + 逐列 `getline(ss, cell, ',')` 是 CSV 解析的最小可靠套路，可直接迁移到轨迹/标定文件处理。

## 11.6 与 ROS2 / 机器人开发的关联

1. **消息缓存队列**：订阅回调里把 `msg` 推入 `std::deque`（滑动窗口）或 `std::queue`（FIFO 任务队列），控制保留帧数、`pop_front` 淘汰旧帧——雷达/图像帧缓冲的标准做法。
2. **路径规划**：nav2 路径是 `nav_msgs::msg::Path`（`std::vector<geometry_msgs::msg::PoseStamped>`）；open/closed 列表用 `std::set`/`std::priority_queue`，坐标查询用 `unordered_map` 做 O(1) 查重。
3. **TF 与参数表**：`std::map<std::string, rclcpp::Time>` 管理各帧最新时间戳；`unordered_map` 做 frame_id → 位姿的快速查询。
4. **去重与排序**：传感器 ID 去重用 `std::set`；多传感器数据按时间戳合并用 `std::multiset` + 时间比较器。
5. **性能细节**：实时循环里 `reserve` 避免扩容、`shrink_to_fit` 释放内存、优先 `vector`（缓存友好、与 C 接口/DDS 序列化零拷贝兼容）。

## 11.7 自测与练习（含参考答案要点）

1. **概念题**：`vector` 的 `capacity()` 与 `size()`、`reserve()` 与 `resize()` 分别是什么关系？
2. **概念题**：为什么 `std::map` 的 `operator[]` 不能用在 const 对象上？它有什么副作用？
3. **动手任务**：实现一个「最近 N 帧点云数」滑动窗口统计器：底层 `std::deque`，提供 `add(count)`、`average()`、`size()`。验收：超过 N 自动淘汰最旧帧。
4. **动手任务**：读取一段 CSV（每行 "name,x,y"），用 `std::map<std::string, std::vector<double>>` 分组统计各 name 的点数并输出。验收：输出按 name 升序。

> 参考答案要点：题 1——size 是元素个数，capacity 是已分配容量；reserve 只扩容量不增元素，resize 改变元素个数（多退少补）。题 2——`[]` 可能在键不存在时插入默认值，改变 map 内容，故 const 版本禁用；副作用是隐式插入。题 3——`if (dq.size() > N) dq.pop_front();` 平均值遍历求和。题 4——`std::map` 天然按 key 升序；`getline` + `find(',')` 或 `std::stringstream` 分列。

## 11.8 常见问题（FAQ）

- **Q：`std::vector<bool>` 为什么是坑？** A：它是按位存储的特化，`operator[]` 返回代理对象而非 `bool&`，取地址/引用会出错；需要位集合用 `std::vector<char>` 或 `std::bitset`。
- **Q：`map` 和 `unordered_map` 怎么选？** A：需要有序遍历/范围查询用 `map`（O(log n)）；只要快速点查用 `unordered_map`（平均 O(1)，最坏 O(n)，需要哈希函数）。
- **Q：遍历时删除元素为什么会崩溃？** A：`erase` 使被删位置及其后的迭代器失效，继续用旧迭代器是 UB；正确写法 `it = c.erase(it)`。
- **Q：`list` 为什么不用 `std::sort`？** A：`std::sort` 需要随机访问迭代器，list 是双向链表；用成员函数 `l.sort(cmp)`（归并排序，O(n log n)）。
- **Q：什么时候用 `emplace_back` 代替 `push_back`？** A：构造复杂对象时可原地构造、省一次拷贝；C++11 起推荐，但简单类型两者差异不大。

## 11.9 本章小结

- 迭代器失效是头号坑：扩容、erase 之后旧迭代器不可用；
- `map::operator[]` 在键不存在时**插入默认值**——只查不改用 `find/at`；
- nav2 路径就是 `vector<PoseStamped>`；open/closed 列表用 `set/priority_queue`；TF 帧缓存用 `unordered_map`；
- 实时循环里 `reserve` 优先 `vector`：缓存友好且与 DDS 序列化零拷贝兼容；
- 先按「访问模式 → 去重/有序/键值 → 内存连续性」三问选容器，选错容器实时性掉一个数量级；
- 自定义类型进 set/map 必须提供 `operator<` 或比较器，插入验证用结构化绑定接 `pair<it, bool>`。
