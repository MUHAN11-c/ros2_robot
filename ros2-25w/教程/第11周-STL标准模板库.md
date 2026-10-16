# 第11章 STL 标准模板库（容器选型与实践）

> 本章对应课程第 11 周：容器 + 迭代器 + 算法三件套。string/vector 打底，deque/list/stack/queue/set/map 进阶，机器人开发中的消息缓存、路径序列、去重与查询全落在这些容器上。

## 11.1 案例以及案例分析

**需求**：传感器滑动窗口（保留最近 3 帧）、降序分数集合（去重）、按键查询表（map）——三种访问模式对应三种容器。

## 11.2 知识点与实现

### 11.2.1 string 与 vector

- string：`substr/find/append/replace/compare/c_str`；`find` 失败返回 `npos`；
- vector：`size()`（元素数）vs `capacity()`（已分配）；扩容策略是倍增、会使迭代器失效；
- `reserve(n)` 预分配避免反复扩容；`shrink_to_fit` 或 swap 技巧收缩内存；
- 遍历中删除必须 `it = c.erase(it)`。

### 11.2.2 容器选型速查

| 场景 | 容器 | 关键操作 |
| --- | --- | --- |
| 随机访问/与 C 接口互操作 | `vector` | `[]/push_back/reserve` |
| 头尾操作/滑动窗口 | `deque` | `push_front/pop_front` |
| 中间频繁插删 | `list` | 成员函数 `sort/remove_if` |
| 去重有序 | `set/multiset` | `insert` 返回 `pair<it,bool>` |
| 键值有序查询 | `map` | `find/at/[]`（`[]` 会隐式插入！） |
| 高频 O(1) 点查 | `unordered_map` | 哈希实现、无序 |
| LIFO/FIFO/优先级 | `stack/queue/priority_queue` | `top/front/pop` |

- 自定义类型进 set/map 需提供 `operator<` 或比较器；`insert` 去重可用 C++17 结构化绑定接收结果。

## 11.3 运行效果（实测）

```text
2 3 4 
insert dup ok=0 top=90
lidar=1
0
```

编译命令：`g++ -std=c++17 -Wall w11_setmap.cpp -o w11 && ./w11`（滑动窗口淘汰最旧帧；重复插入 `ok=0`；`count("camera")==0`）。

## 11.4 端到端实战（实测）：CSV 点位分组统计

传感器点位按名称分组（`map + stringstream` 解析、结构化绑定遍历）——轨迹/标定数据处理的标准形态：

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

## 11.5 本章小结

- 迭代器失效是头号坑：扩容、erase 之后旧迭代器不可用；
- `map::operator[]` 在键不存在时**插入默认值**——只查不改用 `find/at`；
- nav2 路径就是 `vector<PoseStamped>`；open/closed 列表用 `set/priority_queue`；TF 帧缓存用 `unordered_map`；
- 实时循环里 `reserve` 优先 `vector`：缓存友好且与 DDS 序列化零拷贝兼容。
