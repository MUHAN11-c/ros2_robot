# 持续内容迭代：第1轮

目标保持“持续迭代完善内容和细节”，状态active。上一目标回合为有证据的实质进展：完成初版正式教材；本轮从当前工作树重新核读，不仅沿用统计数。

## 本轮完成

- 根据三份独立审查，22条发现分为14已修订、2部分完成、6明确计划；完整状态见validation-evidence/iteration-worklist.json，不宣称全部关闭。
- 实际运行QoS7个真实端点场景、异步服务3场景、tf2进程内Buffer8组、软件clock3阶段，均有源码SHA和版本/输入证据；QoS CLI另有6项输入/帮助/断言保护检查。
- 修正Python/C++实体所有权、服务退出码语义、默认ROS timer暂停检查路径、tf2同步timeout时钟条件、clock_probe/view_frames注释和快捷bag主题筛选。
- 章节增加QoS API、默认与租约规则、发现UNKNOWN边界、Context及Future调度细节、非零旋转/动态采样和可运行源码。当前60章、12实现对照、12API表、49公式、251练习、103完整文件、161教材出处。
- 新增sourceFile同源代码装载，append修订可重复构建不累加；Markdown逐章保留验证范围，源码ZIP全部103文件与正文逐字节比较。
- 观察页面后修正长目录当前章不可见问题，只滚章节树自身容器；离线浏览器有对应断言。

## 已执行验收

- build_content.py --require-full、package_offline.py、check_content.py通过；重复构建content/book/Markdown字节一致。
- reader-checks.cjs通过：60章、49MathML、29SVG、断网无外部请求/脚本错误，新增实验可见，长目录定位通过。
- browser-checks.cjs通过：搜索/进度/筛选/下载/原文与390/320px共170路由无整页溢出。
- delivery-checks.cjs对实际解压ZIP通过：便携原文入口、复制回退、无脚本连续版和390/320px。
- 新实验的真实执行范围以四份报告为准，不当成跨机网络、完整仿真、所有执行器/参数阶段或硬件验证。

## 继续方向

慢消费者数据年龄实验、三配置执行器矩阵、参数pre/on/post候选提交、迟到服务响应/Count忙碌和失败路径、组件参数和isolated容器。此为剩余真实需求，持续目标没有被缩小为本轮已完成内容。

预览：ros2-learning-hub/deliverables/iteration-qos-preview.png。最新包和校验：deliverables/ros2-learning-hub-offline.zip、SHA256SUMS。临时本机服务验收后关闭，按CONTINUE/README继续。
