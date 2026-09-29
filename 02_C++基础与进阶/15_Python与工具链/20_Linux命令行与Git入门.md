# Linux 命令行与 Git 入门

> 本章是"Python 与工具链"的第二章。上一章你握住了 Python；本章补上机器人工程师的另外两个生存技能——Linux 命令行和 Git。

## 本章导航

**上一章**：[Python 与 NumPy 入门（面向机器人）](./10_Python与NumPy入门_面向机器人.md)

**本章讲什么？**
Linux 的最小生存集：装好环境、会敲二十来个命令、看懂权限；加上版本控制工具 Git：从 init 到 push 的完整工作流。

**为什么要学它？**
ROS2 的主力支持平台是 Ubuntu，机器人身上的板子（Jetson、树莓派）几乎都跑 Linux，团队代码都靠 Git 管理。这两样不会，到了 ROS2 章你连"把例程跑起来"都做不到。

**学完能做什么？**
在 Windows 上用 WSL2 装好 Ubuntu；用纯命令行完成建目录、装软件、找文件；把上一章写的小项目推上 GitHub；看得懂"连上机器人 → 拉代码 → 编译"这条完整流程。

**本章在路线图中的位置**

```
[00_零基础入门] ──► [02_C++基础与进阶] ──► [15_Python与工具链] ──► [07_机器人学导论]
   已完成              C++/STL 已完成         ★ 你在这里（本章）              下一步
```

| 学习方式 | 时间 | 适合谁 |
|---|---|---|
| 首次学习（边读边敲命令） | 3-4 小时 | 没用过 Linux / Git |
| 快速复习 | 40-60 分钟 | 都用过，来查漏补缺 |

## 1. 为什么机器人开发"住在" Linux 里

三个现实原因，一个都绕不开：

- **ROS2 主力支持 Ubuntu**：官方在 Ubuntu 上开发测试最充分（例如 ROS2 Humble 对应 Ubuntu 22.04），其他系统永远属于"二等公民"，各种奇怪的坑先找上你
- **机器人本体跑 Linux**：Jetson、树莓派这些机器人"大脑"几乎全是 Linux——你写的代码最终要部署到一台没有屏幕的 Linux 机器上
- **实验环境一致性**：论文的开源代码、实验室服务器默认都是 Linux；团队所有人的环境一致，"在我电脑上能跑"这句话才有说服力

> 📖 教材对照：《鸟哥的 Linux 私房菜》基础学习篇——全书都在回答"Linux 是什么、怎么用"，本章只取生存必需的一小角

## 2. 三种获得 Linux 的方式

Windows 用户不用放弃 Windows——先看对比表再决定：

| 方式 | 是什么 | 优点 | 缺点 | 建议 |
|---|---|---|---|---|
| **WSL2** | Windows 内置的 Linux 子系统，一条命令装好 Ubuntu | 安装最快、和 Windows 共享文件与剪贴板、随开随关 | USB/串口等硬件直通要额外配置 | ★ Windows 用户首选，本站默认 |
| **虚拟机** | 用 VMware/VirtualBox 在 Windows 里"套"一台 Ubuntu | 完整 Ubuntu、坏了快照还原、隔离彻底 | 吃内存（建议 16G 以上）、性能有损耗 | WSL2 装不顺时的备选 |
| **双系统 / 原生** | 硬盘分一个区，装"真" Ubuntu | 性能满血、硬件直通，最接近机器人真实环境 | 要动磁盘分区，装错有风险，切系统要重启 | 有备用电脑或要做实物机器人时再上 |

### 2.1 安装 WSL2（Windows 推荐，三步）

以**管理员身份**打开 PowerShell（开始菜单搜 PowerShell → 右键 → 以管理员身份运行）：

```powershell
wsl --install -d Ubuntu-22.04    # 安装 WSL2 并装 Ubuntu 22.04（ROS2 Humble 对应的版本）
```

1. 执行后可能要求**重启电脑**
2. 重启后会自动弹出一个终端窗口，让你设置用户名和密码
3. 以后从开始菜单搜 "Ubuntu 22.04" 就能进入 Linux 终端

!!! warning "输密码时屏幕没反应是正常的"
    Linux 的密码输入**不回显**——你敲的任何字符都不会显示，连星号都没有。盲打完直接回车即可。

!!! tip
    Windows 10 用户：需要系统版本 1903 以上，且 BIOS 里开启了虚拟化（Intel VT-x / AMD-V）。`wsl --install` 报错时优先排查这两项。装好后记得在 Ubuntu 终端里跑一次 `sudo apt update && sudo apt upgrade` 更新系统。

## 3. 终端与 Shell：机器人工程师的驾驶舱

**终端（Terminal）** 是那个黑底白字的窗口；窗口里真正解释你输入命令的程序叫 **Shell**（Ubuntu 默认是 **bash**）。图形界面靠鼠标点，命令行靠敲字：

| 对比 | 图形界面（鼠标点） | 命令行（敲字） |
|---|---|---|
| 速度 | 翻菜单、找按钮 | 一个词直达 |
| 批量操作 | 一次次重复点 | 一行循环搞定 |
| 远程控制 | 很难 | `ssh` 一条命令连上机器人 |
| 自动化 | 几乎不行 | 存成脚本天天复用 |
| 机器人本体 / 服务器 | 通常根本没有图形界面 | **唯一入口** |

玩过《原神》的话这么记：图形界面像徒步翻山，一路点一路绕；命令行像已激活的传送锚点——敲个名字，瞬间抵达。

打开终端后你会看到一行**提示符（prompt）**，它会"拆解"成这样：

```
yourname@ubuntu:~$ 
   │       │  │ └─ $ 表示普通用户（root 管理员是 #）
   │       │  └─── 当前所在目录：~ 代表家目录
   │       └────── 主机名
   └────────────── 你的用户名
```

提示符是永远亮着的"你在哪、你是谁"状态栏。后面所有命令都在提示符后输入，按回车执行。

## 4. 必会命令：一个一个来

以下命令在 Ubuntu / WSL2 的终端里逐个跟敲。我们围绕一个练习场目录 `~/robot_ws` 展开，前后的命令是连贯的一套。

### 4.1 pwd：我现在在哪

```bash
pwd                     # print working directory：打印当前所在目录的绝对路径
# 输出：/home/yourname
```

迷路时第一反应永远是敲 `pwd`。

### 4.2 ls：这里有什么

```bash
ls                      # list：列出当前目录的文件和文件夹
ls -l                   # long：长格式，能看到权限、大小、修改时间
ls -a                   # all：连隐藏文件一起列（以 . 开头的，如 .git）
ls -la                  # 参数可合写：长格式 + 隐藏文件，最常用
```

### 4.3 先看地图：Linux 的目录是一棵树

Windows 有 C 盘 D 盘好几个盘符；Linux **只有一个根 `/`**，所有东西都挂在这棵树上：

```
/                        ← 根目录，一切的起点
├── home/
│   └── yourname/        ← 你的家目录，简写 ~（你的地盘随便动）
│       ├── robot_ws/    ← 以后放机器人工作空间
│       └── notes.md
├── etc/                 ← 系统配置文件（改系统设置都在这）
├── usr/                 ← 安装的软件
├── var/                 ← 日志等经常变化的数据
└── bin/                 ← 基本命令的程序本体
```

**绝对路径（absolute path）** 从根 `/` 写起（如 `/home/yourname/robot_ws`），**相对路径（relative path）** 从当前目录写起（如 `robot_ws/src`）。

### 4.4 cd：去哪里

```bash
cd /home/yourname/robot_ws   # 绝对路径：从根写起，在哪都能去
cd robot_ws                  # 相对路径：从当前目录写起
cd ..                        # 回上一级（.. 就是"上级目录"）
cd ~                         # 回家目录；直接敲 cd 不带参数也一样
cd -                         # 回到"你刚才待过的那个目录"，来回横跳神器
```

### 4.5 mkdir / touch：建目录和空文件

```bash
mkdir robot_ws               # make directory：新建目录
mkdir -p robot_ws/src/filter # -p：一次建一整条路径，中间缺的目录全补上
touch main.py                # 新建一个空文件（文件已存在则只更新时间戳）
```

### 4.6 cp：复制

```bash
cp main.py main_backup.py    # copy：复制文件，两个参数 = 从哪 到哪
cp -r src/ src_backup/       # -r（recursive）：复制整个目录必须加 -r
```

### 4.7 mv：移动与改名是同一个命令

```bash
mv main.py src/              # move：把文件移进 src/ 目录
mv main.py robot_main.py     # 目标是个新名字 → 就是"改名"
```

### 4.8 rm：删除（本章最危险的命令）

```bash
rm main_backup.py            # remove：删除文件，没有确认提示！
rm -r src_backup/            # -r：删除整个目录
```

!!! warning "rm 没有回收站"
    `rm` 删掉的东西**找不回来**——没有回收站、没有二次确认。三条保命习惯：
    1. 删之前先 `pwd` 确认自己在哪
    2. `rm -rf` 组合（强制 + 递归）威力巨大，**永远不要**对 `/`、`~` 或任何你想不起来的路径使用
    3. 重要目录尽早用 Git 管起来（本章第 6 节就是干这个的）

### 4.9 cat / less：看文件内容

```bash
cat main.py              # 短文件：一次性全部打印出来
less install_log.txt     # 长文件：进入翻页模式
# less 里的操作：空格 下一页，b 上一页，/关键词 搜索，q 退出
```

### 4.10 man：命令的说明书

```bash
man ls                   # manual：ls 的完整说明书（按 q 退出）
ls --help                # 快速版：大多数命令支持 --help，比 man 短
```

`man` 是你自学新命令的入口——忘了参数不用搜网页，先 man 一下。

> 📖 教材对照：《鸟哥的 Linux 私房菜》基础学习篇 第 5 章（在线求助 man page）、第 6 章（文件权限与目录配置）、第 7 章（文件与目录管理）

### 4.11 权限初见：rwx 是什么

再回头看 `ls -l` 输出的开头一串：

```bash
ls -l main.py
# -rw-r--r-- 1 yourname yourname 220 Sep 29 10:00 main.py
```

最前面 10 个字符就是权限，拆开看：

```
-  rw-  r--  r--
│  │    │    └── 其他人（others）的权限：r-- 只能读
│  │    └─────── 同组用户（group）的权限：r-- 只能读
│  └──────────── 文件属主（owner）的权限：rw- 可读可写
└─────────────── 类型：- 是普通文件，d 是目录
```

| 字母 | 含义 | 数字 | 对普通文件 | 对目录 |
|---|---|---|---|---|
| r | read 读 | 4 | 查看内容 | 列出里面的文件 |
| w | write 写 | 2 | 修改内容 | 在里面建/删文件 |
| x | execute 执行 | 1 | 当程序运行 | 进入这个目录 |

**chmod** 用数字法改权限：三位数字依次对应"属主 / 组 / 其他人"，每位是 r+w+x 相加：

```bash
chmod 755 run.sh      # 7=rwx，5=r-x，5=r-x：自己全能，别人可看可执行
chmod 700 secret.txt  # 只有自己能读写，同组和其他人全部拒绝
chmod +x run.sh       # 简写：不动其他权限，只加上"可执行"
```

为什么要学这个？机器人上跑的启动脚本 `run.sh` 忘了加可执行权限，敲 `./run.sh` 就会报 `Permission denied`——新手必踩的坑，你现在已经在起跑线上绕开了它。

### 4.12 apt：一条命令装软件

**apt** 是 Ubuntu 的软件包管理器——"应用商店"的命令行版：

```bash
sudo apt update           # 刷新软件目录：问服务器"今天有哪些软件、什么版本"（不安装）
sudo apt install htop     # 安装 htop：终端里的"任务管理器"，比图形版还炫
htop                      # 运行看看：CPU/内存一目了然，按 q 退出
```

`update` 只刷新"有什么可装"的清单，真正升级软件是另一条命令 `sudo apt upgrade`——两件事、两条命令，别混。

**sudo（superuser do）** 表示"以管理员身份执行"，系统会要求输密码（不回显）。装软件、改系统配置都要 sudo；普通文件操作不要乱用——管理员权限下 `rm` 没有任何拦截。

### 4.13 SSH 初见：一句话版

**SSH（Secure Shell）**：在你自己的电脑上敲命令，命令实际运行在**另一台机器**上——就像把键盘隔空接到了那台机器上。

```bash
ssh ros@192.168.1.50      # 以用户名 ros 登录 IP 为 192.168.1.50 的机器（输对方的密码）
exit                      # 断开连接，回到自己电脑
```

一句话记住它的价值：机器人头上没有屏幕，SSH 就是你和它对话的唯一窗口。第 8 节马上用到。

## 5. 文本三剑客一句话版：grep 与管道

Linux 老兵口中的"文本三剑客"一句话版：

| 工具 | 一句话 | 本站进度 |
|---|---|---|
| grep | 找行：把含关键词的行捞出来 | ✔ 本节学 |
| sed | 改行：批量替换文本 | 用到再学 |
| awk | 取列：按列提取数据 | 用到再学 |

### 5.1 grep：在代码里找东西

```bash
grep -rn "TODO" src/     # -r 连子目录一起搜，-n 顺便报行号
# 输出示例：
# src/filter.cpp:88:  // TODO: 换成卡尔曼滤波
# src/main.py:12:     # TODO: 阈值先写死，回头改成参数
```

团队项目里"这功能写到哪了？"——一条 grep 全找到。

### 5.2 管道 |：把两个命令串起来

**管道（pipe）** 用竖线 `|` 把左命令的输出直接喂给右命令当输入：

```bash
ls -l | grep ".md"       # 先列出长格式，再从中筛出含 .md 的行
```

数据流向：

```
ls -l ──全部输出──► [ | ] ──筛过的──► grep ──► 屏幕
```

这是 Linux 的核心哲学：每个命令只做一件事，管道组合起来威力无穷。比如 `history | grep git` 能从你敲过的所有命令里翻出 git 相关的那几条。

## 6. Git：代码的时光机

### 6.1 痛点故事：改崩了回不去

熟悉的一幕：你给小车写避障逻辑，灵感来了大改三小时——结果越改越糟，想回到昨天那个能跑的版本。可昨天没备份，Ctrl+Z 只能撤最近几步，桌面上的文件叫 `main_最终版.py`、`main_最终版2.py`、`main_真的最终版.py`……

就像打 Boss 前要在七天神像旁存个档——**版本控制（Version Control）** 就是给代码的每个阶段存档：**Git** 记录每次改动做成快照，你随时能回到任意一个历史时刻，还附带"谁在什么时候改了什么"的完整案底。

被 Git 管理的项目文件夹叫**仓库（repository，简称 repo）**。

### 6.2 心智模型：三个区域

Git 内部有三个"区域"，所有命令都是在它们之间搬运东西：

```
┌──────────────────┐  git add   ┌──────────────────┐ git commit ┌──────────────────┐
│     工作区        │ ─────────► │     暂存区        │ ─────────► │    本地仓库       │
│  你正在改的文件    │            │  下次要提交的改动  │            │   永久历史快照     │
└──────────────────┘ ◄───────── └──────────────────┘ ◄───────── └──────────────────┘
   git restore（把误改的文件还原）          git restore --staged（把文件退出暂存区）
```

类比：工作区是餐桌上正在做的菜，暂存区是打包好的外卖盒，仓库是已入库的订单。类比失效的地方要说清：暂存区存的不是"文件列表"，而是**文件内容快照**——同一文件可以改一半、只提交另一半。

### 6.3 第一次提交：init → add → commit

先装 Git 并报上名号（每台机器只需一次）：

```bash
sudo apt install git                          # Ubuntu/WSL2 一行装好
git config --global user.name "Zhang San"     # 全局署名：每次提交都会记录作者
git config --global user.email "zs@example.com"
```

然后走完整流程（在 `~/robot_ws` 里，`main.py` 已用编辑器创建，内容随意，比如一行 `print("v1")`）：

```bash
cd ~/robot_ws
git init             # 初始化：生成隐藏的 .git 文件夹，此目录从此归 Git 管
# 输出：Initialized empty Git repository in /home/yourname/robot_ws/.git/

git status           # 查看状态：红色 main.py = untracked（未跟踪），Git 还没管它
git add main.py      # 放进暂存区：把这个文件"当前的样子"装进购物车
git status           # 变绿色 new file：已暂存（staged）
git commit -m "add main.py: print version info"   # 正式入库；-m 后面必须写提交信息
# 输出：[main (root-commit) a1b2c3d] add main.py: print version info

git log --oneline    # 一行一条看历史：a1b2c3d add main.py: print version info
```

每次 commit 生成一个形如 `a1b2c3d` 的哈希号——快照的"身份证"，回溯时光全靠指认它。

改了文件还没暂存时，用 `git diff` 看改了什么：

```bash
# 用编辑器把 main.py 改成 print("v2")，然后：
git diff             # 对比工作区与暂存区：- 开头是旧行，+ 开头是新行
git add main.py
git commit -m "print robot name instead of version"
git log --oneline    # 两条历史，随时能"读档"
```

> 📖 教材对照：《Pro Git》第 1 章（起步）、第 2 章（Git 基础）——中文版官方免费在线：git-scm.com/book/zh/v2

### 6.4 推到 GitHub：远程仓库

**GitHub** 是全球最大的代码托管网站，给你的仓库提供云端副本（**远程仓库，remote**）——既是备份，也是团队协作的中转站。

**第一步：注册。** 打开 `github.com` 注册账号。用户名是要挂在网上示人多年的，起个正经的。

**第二步：配置 SSH 密钥。** 让 GitHub 认出"这台电脑有权推代码"。原理：一对钥匙——**私钥（private key）** 留在自己电脑绝不外传，**公钥（public key）** 贴到 GitHub，两边对上暗号即可免密传输。

```bash
ssh-keygen -t ed25519 -C "zs@example.com"
# 一路回车即可：密钥存到默认位置 ~/.ssh/，密码短语留空
# 生成两个文件：id_ed25519（私钥，绝不外传！）和 id_ed25519.pub（公钥，随便贴）

cat ~/.ssh/id_ed25519.pub    # 打印公钥：整行复制（以 ssh-ed25519 开头，你的邮箱结尾）
```

然后去 GitHub 网页：右上角头像 → **Settings** → **SSH and GPG keys** → **New SSH key** → Title 随意填 → 把公钥整行粘贴进 Key 框 → **Add SSH key**。

验证连通：

```bash
ssh -T git@github.com
# 首次会问 Are you sure you want to continue connecting? → 输 yes
# 看到 Hi ZhangSan! You've successfully authenticated... 就成功了
```

> 📖 教材对照：《Pro Git》第 4.3 节（生成 SSH 公钥）、第 6 章（GitHub）

**第三步：clone（下载现成项目）与 remote + push（上传自己的项目）。**

```bash
git clone git@github.com:lab/hexapod_ws.git   # 把别人的现成项目整个下载到本地
cd hexapod_ws

# 反过来，把本地的 robot_ws 推上去：
# 先在 GitHub 网页：New repository → 名字 robot_ws → 保持全空 → Create
cd ~/robot_ws
git remote add origin git@github.com:ZhangSan/robot_ws.git  # 登记远程地址，代号 origin
git push -u origin main    # 首次推送：-u 让本地记住对应关系，以后只敲 git push
git pull                   # 以后在别的电脑改过代码，先 pull 拉最新，再干活
```

日常节奏就三拍：**改代码 → `git add` + `git commit` → `git push`**。每完成一个小功能就提交一次，别攒一个月。

### 6.5 .gitignore：有些文件不配进历史

编译产物、缓存、大数据文件——它们能随时重新生成，却动辄几百 MB，不该进 Git 历史。在仓库根目录放一个 `.gitignore` 文件，一行一条规则：

```bash
# 文件 .gitignore（放在仓库根目录）
build/          # 忽略 build 目录：编译产物，随时能重新生成
install/
log/
__pycache__/    # Python 的缓存目录
*.csv           # 忽略所有 csv 数据文件
```

`.gitignore` 本身要提交进仓库，这样全队共享同一套忽略规则。注意：已经被 Git 跟踪的文件不会因为写了 ignore 就被忽略，要先 `git rm --cached 文件名` 把它移出跟踪再提交。

### 6.6 提交信息怎么写：给三个月后的自己留话

提交信息是仓库的"案卷目录"，写得好不好，三个月后翻历史时一见分晓：

| ❌ 坏提交信息 | ✔ 好提交信息 | 好在哪 |
|---|---|---|
| update | fix: 修复激光雷达重复订阅导致数据翻倍 | 说清改了什么、为什么 |
| asdf | feat: 增加底盘速度上限保护（0.5 m/s） | 一眼看出新功能 |
| 最终版2 | refactor: 把 PID 参数抽到 yaml 配置文件 | 说明性质，便于日后检索 |
| bug fix | docs: 补充 README 的编译步骤 | 类型清晰，团队看得懂 |

三条原则：**动词或类型词开头**（fix/feat/docs/refactor）、**一行说清一件事**、**50 字以内**写明"改了什么、为什么改"。

## 7. 综合演练：把上一章的小项目推上 GitHub

把本章所有知识串成一次完整实战。目标：把上一章的 `lidar_sim.py`、`plot_demo.py` 组成一个项目上传。最终目录长这样：

```
~/my-robot-project/
├── lidar_sim.py      ← 上一章的综合例程
├── plot_demo.py      ← 画正弦曲线的例程
└── .gitignore        ← 告诉 Git 哪些文件不要管
```

逐步执行（`①②③` 对应你要做的动作）：

```bash
# ① GitHub 网页：New repository → 名字 my-robot-project → 保持全空 → Create
# ② 本地：把 lidar_sim.py、plot_demo.py 挪进 ~/my-robot-project，并写好 .gitignore
cd ~/my-robot-project
git init                          # ③ 变成 Git 仓库
git branch -M main                # ④ 把默认分支命名为 main（与 GitHub 习惯一致）
git add .                         # ⑤ 暂存全部文件（.gitignore 会自动排除 build/ 等）
git status                        # ⑥ 提交前检查一眼：不该传的文件在不在列表里？
git commit -m "feat: 激光测距仿真与正弦曲线示例"      # ⑦ 第一次正式提交
git remote add origin git@github.com:ZhangSan/my-robot-project.git   # ⑧ 登记远程
git push -u origin main           # ⑨ 推上云端
# ⑩ 刷新 GitHub 网页：代码已经在上面了
```

之后每天的循环只有三拍：

```bash
git add .                         # 改完代码，暂存
git commit -m "fix: ..."          # 提交，写清改了什么
git push                          # 推上云端备份
```

对照检查：第 4 节的 `cd`、第 6.3 节的 init/add/commit、6.4 节的 remote/push、6.5 节的 .gitignore——一条龙里全是刚学的命令。

## 8. 和机器人有什么关系：拿到一台机器人上的代码

把镜头拉到 ROS2 时代的一个平常下午——实验室新到一台六足机器人，Jetson 开发板已开机、和你的电脑连同一个 WiFi。你从"什么都没有"到"机器人动起来"，只要五步：

```bash
# 场景：在 Windows 上，目标：把团队代码跑在机器人上
ssh ros@192.168.1.50                          # ① 远程登录机器人的开发板
git clone git@github.com:lab/hexapod_ws.git   # ② 把团队代码拉到机器人上
cd hexapod_ws
colcon build                                  # ③ 编译整个工作空间（ROS2 的标准构建工具）
source install/setup.bash                     # ④ 让当前终端"认识"刚编译好的包
ros2 launch hexapod_bringup hexapod.launch.py # ⑤ 一键启动机器人
```

| 步骤 | 用到的本章知识 | 一句话解释 |
|---|---|---|
| ① `ssh` | 4.13 节 | 键盘隔空接到机器人上 |
| ② `git clone` | 6.4 节 | 从 GitHub 整体下载项目 |
| ③ `cd` | 4.4 节 | 进入项目目录 |
| ④ `colcon build` | （ROS2 章正式学） | 相当于"整个项目的 C++ 大编译" |
| ⑤ `source` | （同上） | 加载环境变量，让终端找到新编好的程序 |

这五条命令就是未来 ROS2 时代你每天的开场白——今天学的每一步都在里面，到时候你只是换了个更大的"仓库"而已。

## 9. 常见错误与自救

| 错误现象 | 原因 | 怎么改 |
|---|---|---|
| `command not found` | 命令拼错了，或软件没装 | 检查拼写；`sudo apt install 命令名` |
| `Permission denied` | 权限不够 | 需要系统权限加 `sudo`；脚本不可执行用 `chmod +x` |
| 输密码时"卡住" | Linux 密码不回显 | 正常现象，盲打后回车 |
| `fatal: not a git repository` | 当前目录不是 Git 仓库 | `cd` 到项目根目录（有 .git 的那层）再操作 |
| commit 报 "Please tell me who you are" | 没配置署名 | 补 `git config --global user.name / user.email` |
| push 报 `Permission denied (publickey)` | SSH 公钥没配对 | 重新核对 GitHub 设置页里的公钥，重跑 `ssh -T git@github.com` |
| rm 删错了想找回 | rm 没有回收站 | 救不回来；以后删前 `pwd`，重要目录尽早 Git 化 |
| WSL 里 matplotlib 图弹不出 | Windows 10 无 WSLg | 用 `plt.savefig("x.png")` 存图再看 |
| ssh 连不上机器人 | IP 错 / 不在同一网络 / 对方没开 SSH 服务 | 先 `ping` 一下 IP；服务器端需 `sudo apt install openssh-server` |

## 10. 动手练习

练习 1（纯键盘搭目录）：不许碰鼠标，在家目录下建出 `robot_ws/src`、`robot_ws/build`、`robot_ws/log` 三个目录，并用命令验证结构。

??? details "练习 1 解答"

    ```bash
    mkdir -p robot_ws/{src,build,log}   # -p 建整条路径；{a,b,c} 是花括号展开，一次建三个
    ls -R robot_ws                       # -R 递归列出所有子目录，验证结构
    # 输出：
    # robot_ws:
    # build  log  src
    #
    # robot_ws/build:
    #
    # robot_ws/log:
    #
    # robot_ws/src:
    ```

练习 2（备份与清理）：把 `robot_ws/src` 复制一份为备份，改名为 `src_old`，确认无误后删除备份。

??? details "练习 2 解答"

    ```bash
    cd ~/robot_ws
    cp -r src/ src_backup/      # 复制目录必须 -r
    mv src_backup/ src_old/     # mv 改名
    ls                           # 确认 src_old 存在
    rm -r src_old/              # 删除备份（先 pwd 确认自己在 robot_ws！）
    ```

练习 3（grep 与管道）：在 `robot_ws` 里建两个带 `# TODO` 注释的 Python 文件，用一条命令找出全部 TODO 及所在行号；再用管道统计家目录下有多少含 `robot` 的条目。

??? details "练习 3 解答"

    ```bash
    echo '# TODO: 补滤波' > robot_ws/src/a.py    # echo 把文字写进文件（> 是重定向）
    echo '# TODO: 补测试' > robot_ws/src/b.py
    grep -rn "TODO" robot_ws/                   # 带行号全找出
    # robot_ws/src/a.py:1:# TODO: 补滤波
    # robot_ws/src/b.py:1:# TODO: 补测试
    ls ~ | grep robot | wc -l                   # 管道三连：列出家目录 → 筛 robot → 数行数
    ```

练习 4（Git 本地全流程）：把练习 1 的 `robot_ws` 变成 Git 仓库，提交 `src` 里的文件；修改一个文件后用 `git diff` 看差异，再次提交；用一行式查看历史。

??? details "练习 4 解答"

    ```bash
    cd ~/robot_ws
    git init
    git add src/
    git commit -m "feat: 初始传感器脚本"
    echo '# TODO: 补滤波' >> src/a.py   # >> 追加一行（前面练习 3 已建过同名文件则直接改）
    git diff                            # 看到绿色 + 行就是新改动
    git add src/ && git commit -m "docs: 补充滤波 TODO"
    git log --oneline                   # 两行历史，各带哈希号
    ```

练习 5（挑战：上云端）：把练习 4 的仓库推上 GitHub（注册 → 配 SSH → 建空仓库 → push）。

??? details "练习 5 解答"

    按顺序自查这 6 个检查点：
    1. github.com 注册成功，用户名已定
    2. `ssh-keygen -t ed25519 -C "邮箱"` 已执行，`cat ~/.ssh/id_ed25519.pub` 复制了公钥
    3. GitHub → Settings → SSH and GPG keys → New SSH key → 粘贴保存
    4. `ssh -T git@github.com` 显示 `Hi xxx! You've successfully authenticated`
    5. GitHub 上 New repository 建了**空**仓库（不勾 README）
    6. 在 robot_ws 里 `git remote add origin git@github.com:你的用户名/robot_ws.git` → `git push -u origin main`，刷新网页看到代码即通关

## 本章速查卡

**Linux 命令**

| 命令 | 作用 | 记忆点 |
|---|---|---|
| `pwd` | 我在哪 | 迷路先敲它 |
| `ls -la` | 这里有什么 | 长格式+隐藏文件 |
| `cd` / `cd ..` / `cd ~` | 去哪 / 上一级 / 回家 | 绝对路径从 `/` 起 |
| `mkdir -p` / `touch` | 建目录 / 建空文件 | -p 一次建一串 |
| `cp -r` / `mv` | 复制 / 移动即改名 | 目录操作带 -r |
| `rm -r` | 删除 | 没有回收站！ |
| `cat` / `less` / `man` | 看短文件 / 翻长文件 / 说明书 | less 里 q 退出 |
| `grep -rn` / `\|` | 找关键词 / 串联命令 | 找行号靠 -n |
| `chmod 755` | 改权限 | r4 w2 x1 相加 |
| `sudo apt update` / `install` | 刷新软件目录 / 装软件 | update 不等于 upgrade |
| `ssh user@ip` | 远程登录 | 机器人的唯一入口 |

**Git 工作流**

| 场景 | 命令 |
|---|---|
| 首次配置 | `git config --global user.name / user.email` |
| 新仓库 | `git init`（推 GitHub 前 `git branch -M main`） |
| 日常三拍 | `git add .` → `git commit -m "..."` → `git push` |
| 查看状态 / 历史 / 差异 | `git status` / `git log --oneline` / `git diff` |
| 登记远程 | `git remote add origin git@github.com:用户/仓库.git` |
| 首次推送 / 日常拉取 | `git push -u origin main` / `git pull` |
| 下载现成项目 | `git clone git@github.com:...` |
| 忽略文件 | 根目录写 `.gitignore`（一行一条） |

## 下一站预告

工具链至此集齐：C++ 写实时、Python 做分析、Linux 是主场、Git 管历史——四件武器全部入袋。下一站我们正式推开机器人大门：**机器人学导论**，从"机器人是什么"出发，建立整门课程的学习地图。出发：[机器人学导论 · 学习地图](../../07_机器人学导论/00_机器人学导论_学习地图.md)。
