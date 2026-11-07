# 持续内容迭代：第2轮

持续目标保持active。本轮补齐第1轮明确留下的五项审查需求，并把实测结果接入正式教材；没有把目录下载数或正文统计当作逐段穷尽证明。

## 正文与实测

- 慢消费者：独立发布/接收进程，正常、depth1/depth10慢处理及双时刻门控四组。记录实际频率、来源、序号、采样/回调/处理结束年龄；49运行断言和23边界断言通过，8个PID自然退出。p95包含排空尾部，处理后拒绝在自然负载中未触发。
- 执行器：三配置最大并发1/1/2；负例确认timer已ready及释放后可执行。第四例实际服务Future在响应handler释放client组后，generic done与同组timer重叠。Event.wait释放GIL，不推断CPU计算加速；四例线程/Context已清理。
- 参数：Python pre/on/post十一组，19节点销毁。分别验收候选合并、原子/逐项、on副作用污染、post错误返回与异常、类型/有限性和回调生命周期。存储与应用快照分别检查；C++三阶段仅源码核对，未运行。
- 服务：默认四探针和原C++/Python客户端各迟到/缺服务两项，共八项。服务在本地首次等待收尾或原进程退出后仍完成一次；保留/移除pending分开观察。IPC只是独立服务端观察，不是ROS服务取消。原客户端两类失败均退出1，靠日志和阶段区分。

四份报告保存源码SHA及版本/输入/清理结果。`scripts/build_iteration2_material.py`核对通过状态、源文件和控制变量，再生成`source/iteration-2-revisions.json`；构建器核对五张表的证据SHA。源码、正文、章节ZIP和原创工程ZIP同源，保留完整中文注释。

当前正文60章、12组实现对照、13组API表、49公式、261练习、107条完整文件导出、161教材出处。五张实测表与十道新增练习进入对应章节，不把完整文件条目数解释为独立项目数。

## 导出与验收

发现并修复全文和单章Markdown表格行间空行的问题；表头、分隔行、数据行连续生成，管道与单元格换行转义。Python两项与JavaScript一项格式检查通过，真实浏览器下载参数章节并读取文件确认表格连续。正式阅读器和无脚本连续版都显示五张实测表。

- `build_content.py --require-full`、`package_offline.py`、`check_content.py`通过；107条完整文件逐字节核对，sourceFile另与原创工程ZIP比较。
- HTTP浏览器交互、单章导出、来源与下载通过；390/320px共170路由没有整页溢出。
- file协议断网60章、49 MathML、29 SVG、五张实测表，无远程请求或脚本错误。
- 对实际解压的本轮ZIP执行`delivery-checks.cjs`通过，便携原文缺失提示、复制/回退、无脚本及390/320px连续版通过。被测核心指纹见`delivery-current-validation.json`，最终包再次核对这些指纹。

当前预览为`ros2-learning-hub/deliverables/iteration2-parameters-preview.png`，交付仍为`deliverables/ros2-learning-hub-offline.zip`与`SHA256SUMS`。本机验收服务结束后关闭；日常打开方式见根README和CONTINUE。没有发布、托管登记、推送或改动第三方参考源码/许可证。

## 继续工作

22项独立审查中19项按各自范围修订，3项仍明确计划：Count忙碌拒绝/ABORTED、原创组件NodeOptions参数边界、isolated容器与thread_num。完整Nav2/Gazebo/MoveIt、真实相机、MCU/飞控或电机仍未运行。目标没有缩小为只完成本轮已验证内容。
