# 第13章 Linux 与 Shell 入门（操作系统地基）

> 本章对应课程第 13 周：Linux 常用命令、权限模型、进程与端口管理、SSH 远程，以及带判断/循环/函数的 Shell 脚本。ROS2 的编译、环境加载（`source setup.bash`）、远程调试全部发生在 bash 里——这是 ROS2 核心架构之前的最后一章。

## 13.1 本周概览与课时结构

本周是 ROS2 开发的"操作系统地基"：先用第 1 课（2h51m）把 Linux 装起来、把常用命令练成肌肉记忆，再用第 2 课（2h55m）学会用 Shell 脚本把重复劳动自动化。它位于语言阶段（Python/C/C++）之后、ROS2 核心架构之前，因为 ROS2 的编译、环境加载、远程调试全部发生在 bash 里。学完本周，你应当能自如地在 Ubuntu 终端中管理文件与权限、SSH 连接远程机器人，并独立写出带判断、循环、函数的可调试 Shell 脚本。

| 课 | 小节 | 时长 | 一句话导览 |
|---|---|---|---|
| 第1课 Linux 操作系统操作入门 | 4 组 33 节 | 2h51m | 从安装与操作系统概念，到目录/文件/打包压缩命令，再到权限、用户、进程管理与 SSH 远程连接 |
| 第2课 Shell 编程实践基础 | 3 组 32 节 | 2h55m | 从第一个脚本与变量、传参、输入，到运算符与判断，再到函数、if/case/for/while、重定向与数组 |

第 1 课细分：

| 分组 | 小节数 | 时长 | 覆盖内容 |
|---|---|---|---|
| Linux操作系统安装与概述 | 2 | 约 14m | 安装 Linux、操作系统简介 |
| Linux常用命令 | 19 | 约 1h34m | 复制粘贴、cd/ls、增删移、查看内容、分屏、grep、重定向、管道、find、软硬链接、打包压缩、"一句搞定"综合案例 |
| Linux用户权限 | 11 | 约 54m | 权限基础、chmod 字母法/数字法、which、exit、sudo/su、关机重启、杀进程、端口占用、top 监控、系统信息 |
| Linux远程连接 | 2 | 约 8m | PuTTY（SSH）远程连接、WinSCP（SFTP）文件传输 |

第 2 课细分：

| 分组 | 小节数 | 时长 | 覆盖内容 |
|---|---|---|---|
| Shell 编程基础入门 | 8 | 约 42m | shell 简介、第一个程序、注释、变量基础与细节、传参、读取用户输入 |
| Shell 编程进阶操作 | 8 | 约 40m | 命令变量（命令替换）、案例、算术/比较/逻辑运算符、字符串判断、文件判断 |
| Shell 编程流程控制与函数 | 16 | 约 1h33m | 函数及传参/返回值、面积周长案例、if 单双分支与多分支、账号密码判断、文件目录判断、case、for、while、重定向、数组 |

## 13.2 知识点梳理

### 13.2.1 第1课 Linux 操作系统操作入门

- **核心概念**：操作系统（Operating System）是管理硬件（CPU、内存、磁盘、网卡）与软件资源的系统软件；Linux 内核（Kernel）由 Linus Torvalds 于 1991 年发起，常说的"Linux 系统"准确说是"Linux 内核 + GNU 工具 + 发行版（Distribution）"，如 Ubuntu、Debian、CentOS；Shell 是用户与内核之间的命令解释器，Ubuntu 默认 bash（Bourne Again Shell）。

- **要点 1（安装 Linux）**：三条主流路线——实体机安装、虚拟机（VMware/VirtualBox）安装、Windows 下的 WSL2。ROS2 开发推荐 Ubuntu 22.04（配 Humble）或 24.04（配 Jazzy）；虚拟机安装时内存建议 8 GB+、磁盘 60 GB+，安装完成后先换国内源并 `sudo apt update`。

- **要点 2（目录结构与路径）**：Linux 一切皆文件，根目录 `/` 是树根；常见目录：`/home/用户`（家目录，`~`）、`/etc`（配置）、`/usr`（用户程序）、`/var`（日志）、`/tmp`（临时）。路径分绝对路径（以 `/` 开头）与相对路径（相对当前目录）。

- **要点 3（cd / ls 与目录导航）**：`cd` 切换目录，`pwd` 显示当前路径，`ls` 列出内容。`cd -` 回到上一次目录，`cd ~` 回家目录；`ls -l` 长格式（含权限与时间）、`-a` 显示隐藏文件（`.` 开头）、`-h` 人类可读大小、`-R` 递归。

- **要点 4（新建、删除、复制、移动）**：`mkdir`/`rmdir` 管目录，`touch` 建空文件，`rm` 删文件（`-r` 递归目录、`-f` 强制），`cp` 复制（`-r` 复制目录、`-i` 覆盖前确认、`-v` 显示过程），`mv` 移动/重命名（同目录下 `mv a.txt b.txt` 即改名）。

- **要点 5（查看文件内容与分屏）**：`cat`（小文件全显、`-n` 带行号）、`tac`（倒序）、`head`/`tail`（默认前后 10 行，`-n 20` 指定行数，`tail -f` 实时跟踪日志）、`more`/`less`（分屏翻页，`less` 支持 `/关键字` 搜索、`q` 退出）、`nl` 带行号查看。

- **要点 6（查找内容、查找文件）**：`grep` 在文件内容里搜索（`-n` 行号、`-i` 忽略大小写、`-r` 递归目录、`-v` 反选）；`find` 按文件名/类型/时间查找（`find /path -name "*.py"`、`-type f|d`、`-size +10M`）；`which`/`whereis` 查命令位置（见权限一节）。

- **要点 7（重定向与管道）**：`>` 覆盖写、`>>` 追加写、`<` 输入重定向、`2>` 错误重定向、`&>` 一起重定向；管道 `|` 把前一条命令的输出当下一条的输入，如 `ps aux | grep ros | grep -v grep`、`ls -l | wc -l`、`dmesg | tail`。

- **要点 8（软链接与硬链接）**：软链接（符号链接，Symbolic Link）像 Windows 快捷方式，`ln -s 目标 链接名`，目标删除后链接失效；硬链接（Hard Link）是同一个 inode（索引节点）的另一个文件名，`ln 目标 链接名`，删除任一名字文件内容仍在。`ls -i` 可查看 inode。

- **要点 9（打包压缩）**：`tar` 负责打包（归档），`gzip/bzip2/xz` 负责压缩。`tar -cvf a.tar 目录/` 打包、`-xvf` 解包、`-tvf` 查看包内容；一步到位：`tar -czvf a.tar.gz 目录/`（z 用 gzip）、`tar -xzvf a.tar.gz` 解压。zip 对应 `zip -r a.zip 目录/`、`unzip a.zip`。

- **要点 10（"一句搞定"综合案例）**：用管道与重定向把多步操作合成一条命令——统计代码行数、批量改名前先备份、把构建日志同时显示并落盘等，这是把命令行用出效率的关键。

- **要点 11（权限基础与 chmod）**：`ls -l` 首列如 `-rwxr-xr--`：第 1 位文件类型（`-` 文件、`d` 目录、`l` 链接），后 9 位分三组（所有者 owner / 所属组 group / 其他人 others），每组 r（读 4）w（写 2）x（执行 1）。字母法：`chmod u+x,g-w,o=r file`；数字法：`chmod 755 file`（rwxr-xr-x）、`chmod 644 file`（rw-r--r--）。目录的 x 表示"可进入"。

- **要点 12（用户与身份切换）**：`whoami` 看当前用户，`exit` 退出当前 shell/登录/远程会话，`su 用户名` 切换用户（`su -` 连环境一起切），`sudo 命令` 以 root 权限执行单条命令，`useradd`/`passwd` 建用户改密码。普通用户在 sudo 组才有 sudo 权限。

- **要点 13（进程、端口与监控）**：`ps aux` 查进程、`top`/`htop` 实时监控（CPU/内存，`q` 退出）、`kill PID`（默认 SIGTERM，`kill -9` 强杀）、`killall/pkill 进程名` 批量结束；端口占用用 `ss -tlnp | grep 端口` 或 `lsof -i:端口`、`fuser -k 端口/tcp` 释放端口。关机重启：`shutdown -h now`、`reboot`（或 `shutdown -r now`）。

- **要点 14（系统信息）**：`uname -a` 内核信息、`lsb_release -a` 发行版、`free -h` 内存、`df -h` 磁盘分区、`du -sh 目录` 目录占用、`hostname` 主机名、`top` 综合监控。

- **要点 15（远程连接）**：SSH（Secure Shell）加密远程登录：Windows 用 PuTTY（或 PowerShell 自带 `ssh 用户名@IP -p 22`）连接机器人/工控机；WinSCP 用 SFTP 协议图形化拖拽上传下载文件；Linux/macOS 间直接 `scp -r 本地 目标机:/路径` 传目录、`rsync -av` 增量同步。

> **注意：** `rm -rf` 是不可逆操作，尤其 `rm -rf /` 或 `rm -rf *` 在错误目录下会毁掉系统。建议养成习惯：先 `pwd` 确认当前位置，再 `ls` 看清目标，最后才执行删除；或给 `rm` 加 `-i` 别名。

### 13.2.2 第2课 Shell 编程实践基础

- **核心概念**：Shell 既是命令解释器（交互式执行命令），也是脚本编程语言（批量执行命令 + 逻辑控制）。脚本首行 `#!/bin/bash`（Shebang）指定解释器；运行方式有三种：`bash script.sh`（子 shell 执行）、`./script.sh`（需先 `chmod +x`）、`source script.sh`（在当前 shell 执行，环境变量留在当前会话）。

- **要点 1（第一个程序与注释）**：脚本第一行写 Shebang，`#` 后是单行注释，多行注释可用多个 `#` 或 `: <<'EOF' ... EOF`；`echo` 输出内容（`-e` 开启转义，如 `\n` 换行；`-n` 不换行）。

- **要点 2（变量）**：定义 `name=value`（等号两边**不能有空格**），使用 `$name` 或 `${name}`；只读 `readonly name`，删除 `unset name`；变量默认是字符串，`local` 用于函数内局部变量；双引号内 `$` 会被求值，单引号原样输出（`echo '结果: $name'` 输出字面量）。

- **要点 3（变量细节）**：`""` 双引号保留变量含义、`''` 单引号原样、反引号/`$()` 执行命令（推荐 `$()`）；`\` 转义特殊字符；`${#name}` 取字符串长度、`${name:起始:长度}` 截取。

- **要点 4（传参与用户输入）**：脚本参数：`$0` 脚本名、`$1..$9` 第 n 个参数、`$#` 参数个数、`$@`/`$*` 全部参数（`"$@"` 加引号更安全）、`$?` 上条命令退出码、`$$` 当前进程 PID；`read 变量名` 读键盘输入，`-p "提示"` 显示提示，`-s` 静默（适合密码），`-t 5` 超时 5 秒。

- **要点 5（命令变量/命令替换）**：`result=$(命令)` 把命令输出存入变量，反引号 `` `命令` `` 是旧写法、内部不能再嵌套反引号；常与 `date +%F`、`whoami`、`pwd`、`find` 等组合，这是自动化脚本的核心技巧。

- **要点 6（运算符）**：算术用 `$(( ))`（`+ - * / %`，`**` 乘方）或 `expr`（运算符两侧要空格、`*` 需转义 `\*`）；数值比较：`test $a -eq $b` 或 `[ $a -eq $b ]`，运算符 `-eq -ne -gt -lt -ge -le`；逻辑运算符 `-a`（与）、`-o`（或）、`!`（非），也可用 `&&`、`||`、`!` 组合命令；字符串判断：`-z` 空串、`-n` 非空、`=`/`==` 相等、`!=` 不等（比较符两侧留空格）。

- **要点 7（文件判断）**：`[ -e 文件 ]` 存在、`-f` 是普通文件、`-d` 是目录、`-r/-w/-x` 可读/写/执行、`-s` 文件非空、`-L` 是软链接；两个文件比较用 `-nt`（更新）/`-ot`（更旧）/`-ef`（同一文件）。

- **要点 8（函数）**：`function 名字 { ... }` 或 `名字() { ... }` 定义；函数内用 `$1`、`$2` 接收**函数参数**（不是脚本参数）；返回值用 `return 数字`（0-255，表示状态），取值 `$?`，返回数据用 `echo` 输出再由调用方 `$(...)` 捕获。

- **要点 9（流程控制）**：`if [ 条件 ]; then ... elif [ 条件 ]; then ... else ... fi`（条件两侧留空格、结尾 `fi`）；`case 变量 in 模式1) ...;; 模式2) ...;; *) 默认;; esac`，模式可用 `|` 并列、`*` 通配；`for 变量 in 列表; do ... done`（列表可为 `1 2 3`、`$(seq 1 5)`、`{1..5}`、通配符 `*.txt`）；`while [ 条件 ]; do ... done`，常与 `read` 配合逐行读文件，`break`/`continue` 控制循环。

- **要点 10（重定向与数组）**：`>` `>>` 输出、`<` 输入、`2>` 错误、`&>` 全部、`<<EOF` Here Document（脚本内嵌多行输入）；数组：`arr=(a b c)`、`arr[0]=x`、`${arr[0]}` 取元素、`${arr[@]}` 全部元素、`${#arr[@]}` 个数、`unset arr[1]` 删除元素。

- **要点 11（脚本调试）**：`bash -n script.sh` 只查语法、`bash -x script.sh` 逐行打印执行过程、脚本内 `set -e`（出错即停）、`set -u`（未定义变量报错）、`set -x`（开启跟踪）；`shellcheck script.sh` 静态检查脚本质量问题。

> **注意：** Shell 脚本三大经典坑：① `[ $a = $b ]` 中 `[`、变量、`]` 之间**必须有空格**；② 变量赋值 `a=1` 不能写成 `a = 1`；③ `$?` 只反映上一条命令，中间夹了别的命令就取不到了——要用临时变量接住。

## 13.3 重点与难点

1. **权限模型与 chmod 数字法**：把 rwx 与 421 对应起来是重点；难点是理解"目录必须有 x 才能 cd 进去、有 w 才能在其中新建文件"，以及 `755`（脚本常用）与 `644`（普通文件常用）的典型取值。
2. **重定向与管道的组合**：理解"每个进程有 stdin/stdout/stderr 三个流"，才能看懂 `2>&1`、`> log 2>&1`、`ps aux | grep ros | grep -v grep` 这类组合；这是从"会用命令"到"会写自动化"的分水岭。
3. **变量引用与引号规则**：单引号不求值、双引号求值、`$()` 执行命令替换，三者嵌套时容易混乱；建议用 `echo "$var"` 养成"引用变量必加双引号"的习惯（防含空格的路径出错）。
4. **test/[] 条件表达式**：数值比较用 `-eq` 而不是 `==`，字符串用 `=`，文件用 `-f/-d`；`[[ ]]`（bash 增强）支持 `&&`、`||` 与模式匹配，比 `[ ]` 更不容易踩空格坑。
5. **流程控制语法细节**：`then`/`do` 与 `fi`/`esac`/`done` 的配对、`;;` 结尾、`for` 遍历带空格文件名要 `"$@"` 或 `while read`，这些是初学写脚本最常见的语法错误来源。
6. **调试能力**：`bash -x` 看清每步实际执行的命令，`set -e` 防止错误被吞掉，是脚本可维护性的关键，也直接对应将来 launch/构建脚本的排错。

## 13.4 代码与命令实战

**场景 1：日常目录与文件管理（第 1 课命令综合）**

```bash
# 创建练习目录并进入（-p 递归创建，目录已存在不报错）
mkdir -p ~/ros2_ws/notes_playground && cd ~/ros2_ws/notes_playground

# 建文件、复制、改名、查看
touch hello.txt                     # 新建空文件
echo "ROS2 humble" > hello.txt      # 覆盖写入内容
cp hello.txt hello_bak.txt          # 复制为备份
mv hello_bak.txt backup/            # 移动到 backup 目录（不存在则先 mkdir backup）
ls -lh                              # 长格式 + 人类可读大小查看
```

**场景 2：管道 + 重定向 + grep："一句话搞定"**

```bash
# 从进程表里找 ROS 相关进程，并把结果同时写入日志文件
ps aux | grep ros | grep -v grep | tee ros_procs.log   # tee：边显示边存盘

# 统计当前目录下 python 文件的总行数（-r 递归、-n 行号、wc -l 计行）
grep -rn "" --include="*.py" . | wc -l

# 追加错误与标准输出都进 build.log（2>&1 表示把 stderr 并到 stdout）
./build.sh > build.log 2>&1
```

**场景 3：权限设置与脚本赋执行权**

```bash
# 字母法：给所有者加执行权、去掉组写权、其他人只读
chmod u+x,g-w,o=r my_script.sh

# 数字法：755 = rwxr-xr-x，脚本常用；644 = rw-r--r--，普通文件常用
chmod 755 deploy_robot.sh
chmod 644 config.yaml

# 查看命令位置（区分 which 查 PATH、whereis 还查 man 源码路径）
which colcon
whereis bash
```

**场景 4：第一个 Shell 脚本 —— 传参、变量、命令替换**

```bash
#!/bin/bash
# 文件: hello_shell.sh —— 演示 Shebang、变量、命令替换、传参
name="${1:-world}"                  # 取第 1 个参数，缺省用 world
now=$(date +%F\ %T)                 # $(命令替换) 把命令输出存入变量
echo "你好, ${name}！现在是 ${now}"  # 引用变量加 ${} 更清晰
echo "脚本名: $0, 参数个数: $#"
exit 0                              # 返回退出码 0 表示成功
```

**场景 5：函数 + if 多分支 —— 判断文件/目录（含返回值）**

```bash
#!/bin/bash
# 文件: check_path.sh —— 函数传参、return 返回状态、if 多分支
check() {                            # $1 是函数参数，不是脚本参数
    if [ -d "$1" ]; then
        echo "$1 是目录"
        return 0                     # 0 表示成功/成立
    elif [ -f "$1" ]; then
        echo "$1 是普通文件"
        return 0
    else
        echo "$1 不存在"
        return 1                     # 非 0 表示不成立
    fi
}

check /etc/hosts                     # 调用函数
if [ $? -eq 0 ]; then                # $? 取函数返回值
    echo "检查通过"
fi
```

**场景 6：case + for + while + 数组 —— 批量操作与统计**

```bash
#!/bin/bash
# 文件: batch_ops.sh —— case 分支、for/while 循环、数组、Here Document
hosts=(192.168.1.10 192.168.1.11)    # 数组定义
for ip in "${hosts[@]}"; do          # 遍历数组全部元素
    ping -c 1 -W 1 "$ip" >/dev/null 2>&1 && echo "$ip 在线" || echo "$ip 不可达"
done

action="${1:-status}"                # 脚本第 1 个参数决定行为
case "$action" in                    # case 匹配分支
    start)   echo "启动机器人节点..." ;;
    stop)    echo "停止机器人节点..." ;;
    status|info) echo "查询状态" ;;  # | 表示或
    *)       echo "用法: $0 {start|stop|status}" ;;
esac

i=0
while read -r line; do               # while + read 逐行读文件
    i=$((i+1))                       # $(( )) 算术运算
done < /etc/hosts                    # < 输入重定向
echo "共读取 $i 行"
```

**场景 7：本章综合自检脚本 w13.sh**（融合场景 4~6 的全部要素：变量与命令替换、函数 + if 多分支、case 分支、数组统计；运行方式与传参遵循 `$0/$1/$#/$?` 约定）

```bash
#!/bin/bash
# 文件: w13.sh —— 第13章综合自检脚本
name="${1:-world}"                       # 传参 + 缺省值
now=$(date +%F\ %T)                      # 命令替换
echo "你好, ${name}！现在是 ${now}"

check() {                                # 函数 + if 多分支
    if [ -d "$1" ]; then
        echo "$1 是目录"
    elif [ -f "$1" ]; then
        echo "$1 是普通文件"
    else
        echo "$1 不存在"
    fi
}
check /etc/hosts
check /no/such/path

action="${2:-status}"                    # case 分支（缺省 status）
case "$action" in
    start)   echo "启动机器人节点..." ;;
    stop)    echo "停止机器人节点..." ;;
    status|info) echo "查询状态" ;;
    *)       echo "用法: $0 [名字] {start|stop|status}" ;;
esac

hosts=(192.168.1.10 192.168.1.11)        # 数组统计
echo "主机数: ${#hosts[@]}"
```

## 13.5 运行效果（实测）

### 13.5.1 综合自检脚本（实测）

```text
你好, zcode！现在是 2026-10-15 15:46:27
/etc/hosts 是普通文件
/no/such/path 不存在
查询状态
主机数: 2
```

运行命令：`bash w13.sh zcode`（Ubuntu 24.04 / bash 实测）。

### 13.5.2 端到端实战（实测）：日志清理脚本 clean_log.sh

课程动手任务的实现：删除指定目录下 7 天前的 `.log` 文件，执行前列出待删文件并确认，参数缺失时给出用法并以非 0 码退出。

```bash
# clean_log.sh
DIR="${1:-}"
if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
    echo "用法: $0 <日志目录>"
    exit 1
fi
echo "将删除以下 7 天前的 .log 文件："
find "$DIR" -mtime +7 -name "*.log" -type f
read -r -p "确认删除? (y/N): " ans
if [ "$ans" = "y" ]; then
    find "$DIR" -mtime +7 -name "*.log" -type f -delete
    echo "已删除"
else
    echo "已取消"
fi
```

实测（构造新/旧两个日志文件后运行）：

```text
$ mkdir -p logs && touch -d "10 days ago" logs/old.log && echo x > logs/new.log
$ printf "y\n" | bash clean_log.sh logs
将删除以下 7 天前的 .log 文件：
logs/old.log
已删除
$ ls logs/
new.log
```

旧日志被清理、新日志保留，确认机制生效。

## 13.6 与 ROS2 / 机器人开发的关联

1. **bashrc 与 ROS2 环境变量**：ROS2 安装后必须 `source /opt/ros/humble/setup.bash`，工作空间还需 `source install/setup.bash`；把它们写进 `~/.bashrc`，每次开终端自动生效。变量、别名、PATH 修改同理，本周的"变量 + 脚本"技能直接用于配置开发环境：

```bash
# 追加到 ~/.bashrc：ROS2 环境与常用别名（写完 source ~/.bashrc 生效）
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo 'alias cb="colcon build --symlink-install"' >> ~/.bashrc
```

2. **colcon 构建脚本**：把"进入工作空间 → source 环境 → colcon build → source 新产物 → 运行测试"固化成 `build_ros2_ws.sh`，配合 `$1` 传参（如 `--packages-select`）、`$?` 判断构建是否失败、`set -e` 出错即停，就是本周脚本技能的直接落地。
3. **systemd / launch 启动脚本**：机器人开机自启节点，需要写 systemd service 文件（本质是带 `ExecStart=bash -c 'source ...; ros2 run ...'` 的文本配置）或 ROS2 launch 启动脚本，其中的路径拼接、条件判断、循环启动多节点，用的全是 if/for/函数。
4. **SSH 远程调试机器人**：机器人（树莓派/Jetson/工控机）通常无显示器，用 PuTTY/`ssh` 登录、WinSCP/`scp` 拷代码与日志、`tail -f log.txt` 看节点输出、`top` 看 CPU、`kill` 停失控节点、`ss -tlnp` 排查 DDS/话题端口占用——本周第 1 课后半部分几乎就是"机器人运维手册"。
5. **日志与排错方法论**：ROS2 的 `~/.ros/log`、`colcon` 构建日志都要靠 `grep`/`tail`/重定向分析；`bash -x`、`set -e` 的调试思路同样适用于定位 launch 文件与参数配置错误。

## 13.7 自测与练习（含参考答案要点）

1. **概念题**：解释软链接与硬链接的区别；`chmod 755` 给三类用户分别赋予了什么权限；`$?`、`$#`、`$@` 分别表示什么？
2. **动手任务**：写一个 `clean_log.sh`，功能：删除指定目录下 7 天前的 `.log` 文件（`find ... -mtime +7 -name "*.log" -delete`），执行前显示将删除的文件列表并让用户 `read` 确认（输入 `y` 才执行）。验收标准：传入目录参数时行为正确，不传参数时给出用法提示并以非 0 码退出。
3. **动手任务**：写一个 `robot_check.sh`，用函数封装"检查 IP 是否在线、检查端口是否监听、检查磁盘剩余空间是否大于 20%"，用 `if` 多分支输出 ✅/❌，全部通过则 `return 0`。验收标准：用 `bash -x` 运行能看到每一步判断过程。

> 参考答案要点：1）软链接是独立的路径指向（可跨分区、目标删除即失效），硬链接是同一 inode 的别名（不能跨分区、链接数 +1）；`755` = 所有者 rwx、组 r-x、其他人 r-x；`$?` 上条命令退出码、`$#` 参数个数、`$@` 全部参数。2）注意 `read -p` 确认、`"$1"` 加引号防空格路径、`exit 1` 表示用法错误。3）`ping -c 1`、`ss -tln | grep`、`df -h` 配合 `awk` 取百分比，函数用 `return` 汇总状态。

## 13.8 常见问题（FAQ）

- **Q：`source script.sh`、`bash script.sh`、`./script.sh` 有什么区别？** A：`bash`/`./script.sh` 都在**子 shell** 中执行，脚本里的 `cd`、变量不影响当前终端；`source` 在**当前 shell** 执行，`export` 的变量、`cd` 的结果会留在当前会话——所以 ROS2 的 `setup.bash` 必须用 `source`。`./script.sh` 额外要求文件有 `x` 执行权限和正确的 Shebang。
- **Q：为什么 `[ -d $dir ]` 报错 "unary operator expected"？** A：变量为空或含空格导致条件表达式结构被破坏，应写成 `[ -d "$dir" ]`（变量加引号），或改用 bash 的 `[[ -d $dir ]]`。
- **Q：`kill PID` 杀不掉进程怎么办？** A：先 `ps aux | grep 进程名` 确认 PID；`kill`（SIGTERM）可被捕获，顽固进程用 `kill -9 PID`（SIGKILL，强制但可能丢数据）；批量结束用 `killall 进程名`。机器人上杀 ROS 节点前先确认没有正在进行的电机控制。
- **Q：端口被占用（如 ROS2 调试端口、Web 端口）怎么排查？** A：`ss -tlnp | grep 端口号` 或 `lsof -i:端口号` 找到占用进程的 PID，再 `kill` 它；`fuser -k 端口/tcp` 可直接释放端口。
- **Q：脚本在 Windows 上写好，Linux 上运行报 `bad interpreter: /bin/bash^M`？** A：Windows 换行符 `\r\n` 里的 `\r` 被当成文件名的一部分。用 `sed -i 's/\r$//' script.sh` 转换，或在 Windows 编辑器里把换行格式改为 LF。
- **Q：`>` 和 `>>`、`2>&1` 分别什么时候用？** A：`>` 覆盖写、`>>` 追加写；`2>&1` 把标准错误并到标准输出（配合 `>` 一起落盘），`&> file` 是两者的快捷写法。写构建日志建议 `colcon build 2>&1 | tee build.log`。

## 13.9 本章小结

- `source` 与 `bash` 执行的区别决定了 ROS2 环境为什么必须 `source setup.bash`；
- 把「进入工作空间 → colcon build → source 产物」固化成脚本，用 `$?` 判失败、`set -e` 出错即停，是本周技能的直接落地；
- SSH + `scp` + `tail -f` + `top` + `ss -tlnp` 是远程调试无显示器机器人的标准工具链；
- 三大经典坑：`[ ]` 内侧空格、赋值两侧不能有空格、`$?` 只反映上一条命令。

## 13.10 基础篇总结（第 1~13 周）

| 篇 | 周 | 内容 | 与 ROS2 的关系 |
| --- | --- | --- | --- |
| 第一篇 Python | 1-3 | 容器/函数/类/异常/NumPy/OpenCV | rclpy 节点与感知处理 |
| 第二篇 C 语言 | 4-7 | 编译/类型/指针/结构体/文件 | rclcpp 内存模型与消息原型 |
| 第三篇 C++ | 8-12 | 类/多态/模板/STL/算法/chrono | rclcpp API 的语言基础 |
| 第四篇 Linux | 13 | 命令/权限/Shell 脚本 | 构建与运维环境 |

从下一章（第 14 章）起进入 ROS2 实战：所有概念将在 turtlesim 与真实代码中落地。
