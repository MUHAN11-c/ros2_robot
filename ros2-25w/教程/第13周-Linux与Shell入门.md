# 第13章 Linux 与 Shell 入门（操作系统地基）

> 本章对应课程第 13 周：Linux 常用命令、权限模型、进程与端口管理、SSH 远程，以及带判断/循环/函数的 Shell 脚本。ROS2 的编译、环境加载（`source setup.bash`）、远程调试全部发生在 bash 里——这是 ROS2 核心架构之前的最后一章。

## 13.1 案例以及案例分析

**需求**：写一个自检脚本——变量与命令替换、函数 + if 多分支判断文件/目录、case 分支、数组统计；运行方式与传参遵循 `$0/$1/$#/$?` 约定。

## 13.2 知识点与实现

### 13.2.1 Linux 常用命令

- 目录导航：`cd/pwd/ls -lah`；增删移：`mkdir -p/touch/rm -r/cp -r/mv`；
- 查看与搜索：`cat/head/tail -f（实时日志）/less`；`grep -rn` 内容搜索、`find -name "*.py"` 文件查找；
- 重定向与管道：`>` 覆盖、`>>` 追加、`2>` 错误、`2>&1` 合并；`|` 管道（`ps aux | grep ros | grep -v grep`）；
- 权限：`ls -l` 首列三组 rwx（421）；`chmod 755 脚本`、`chmod 644 普通文件`；`sudo/su/exit`；
- 进程与端口：`ps aux`、`top`、`kill -9`；`ss -tlnp | grep 端口` / `lsof -i:端口` 排查占用；
- 远程：`ssh 用户@IP`、`scp -r`、`rsync -av`——机器人无显示器时的标准运维组合。

### 13.2.2 Shell 脚本

- 首行 `#!/bin/bash`；三种运行方式：`bash s.sh` / `./s.sh`（需 +x）/ `source s.sh`（当前会话生效——`setup.bash` 必须用 source 的原因）；
- 变量 `name=value`（等号两侧**不能有空格**）、`${name}` 引用、`$(命令替换)`；
- 传参：`$0/$1/$#/$@/$?/$$`；`read -p "提示" 变量` 读取输入；
- 判断：数值 `-eq/-gt/-lt`、字符串 `=/-z`、文件 `-f/-d/-x`；`[ ]` 内侧必须留空格、变量加双引号；
- 流程：`if/elif/else/fi`、`case ... esac`（`;;` 结尾）、`for/while ... do/done`、数组 `arr=(a b c)`、`${#arr[@]}`；
- 调试：`bash -x` 逐行跟踪、`set -e` 出错即停、`shellcheck` 静态检查。

## 13.3 运行效果（实测）

```text
你好, zcode！现在是 2026-10-15 15:46:27
/etc/hosts 是普通文件
/no/such/path 不存在
查询状态
主机数: 2
```

运行命令：`bash w13.sh zcode`（Ubuntu 24.04 / bash 实测）。

## 13.4 本章小结

- `source` 与 `bash` 执行的区别决定了 ROS2 环境为什么必须 `source setup.bash`；
- 把「进入工作空间 → colcon build → source 产物」固化成脚本，用 `$?` 判失败、`set -e` 出错即停，是本周技能的直接落地；
- SSH + `scp` + `tail -f` + `top` + `ss -tlnp` 是远程调试无显示器机器人的标准工具链；
- 三大经典坑：`[ ]` 内侧空格、赋值两侧不能有空格、`$?` 只反映上一条命令。

## 13.5 基础篇总结（第 1~13 周）

| 篇 | 周 | 内容 | 与 ROS2 的关系 |
| --- | --- | --- | --- |
| 第一篇 Python | 1-3 | 容器/函数/类/异常/NumPy/OpenCV | rclpy 节点与感知处理 |
| 第二篇 C 语言 | 4-7 | 编译/类型/指针/结构体/文件 | rclcpp 内存模型与消息原型 |
| 第三篇 C++ | 8-12 | 类/多态/模板/STL/算法/chrono | rclcpp API 的语言基础 |
| 第四篇 Linux | 13 | 命令/权限/Shell 脚本 | 构建与运维环境 |

从下一章（第 14 章）起进入 ROS2 实战：所有概念将在 turtlesim 与真实代码中落地。
