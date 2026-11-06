# 本轮研究素材接口

只写分配的 JSON / 原创 SVG / 数值实验素材文件；不得修改页面、构建脚本、现有 source JSON、许可证或部署。不要派生子代理。以完整本地正文为成果，不要只给链接。不要提交 git。发现原资料错误应修正且说明依据。

章节 JSON 输出格式：{"chapters": [...], "resources": [...]}。章字段：id,title,summary,goals(字符串列表),prerequisites(字符串列表),version,concepts(字符串列表),sections,workedExample{title,scenario,steps(字符串列表),result},exercises[{question,answer}],steps[{title,body,code,language}],commands[],expected[],pitfalls[],exercise,exerciseAnswer,sourceIds[],validation。

每个 section: {title,paragraphs:[...],bullets:[],codeBlocks:[{label,language,type,code,explanation}],equations:[{tex,label,explanation,symbols:[{symbol,meaning,unit}]}]}。equations 可省略；tex 不含美元分隔符、只用标准 LaTeX 数学语法。每个公式逐项解释符号、单位、前提、推导步骤和局限；重要公式搭配代入数值。code type 只允许 complete/snippet/commands/concept。complete Python 使用标准库、可独立运行断言并打印可解释结果；label 为安全相对 .py 文件名；别把互相依赖片段冒充完整工程。

每章至少五节、至少 1800 中文正文字符（目标 2500–4000，内容优先），至少三道带答案练习、一个 workedExample；新章应讲清所述范围，避免用泛泛口号填篇幅。每组公式至少有一份完整实验作数值验证。不运行用户硬件。

resources 字段为 id,title,url,category,version,description,verification,type，必要时 sourceUrl/versionNote。verification 写清实际读取方式，不能声称运行未执行的 ROS/仿真。使用官方、维护者或原始论文核对技术。社区教程只作为范围导航，不复刻全文和长段落。

查阅 ../scripts/build_content.py 可了解现有整合模式，但不要修改。阅读 Robotics_Tutorial 的 SUMMARY.md 与负责领域的原文，同时核对一手出处。资源 ID 使用 math- 或 applied- 前缀避免冲突。
