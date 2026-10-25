# HiMCM 顶级论文格式调研

调研日期：2026-10-22。用途仅为版式、章节组织和论证呈现，**没有复制**获奖论文的文字、模型、图表、代码或引用。

## 已核对样本

1. [COMAP 2023 HiMCM Results](https://www.contest.comap.com/highschool/contests/himcm/2023results.html)：官方列出 9 个 Outstanding；B 题获奖队伍为 13694、13904、14087、14323。
2. [COMAP 2024 HiMCM Results](https://www.contest.comap.com/highschool/contests/himcm/2024results.html) 与 [2025 HiMCM Results](https://www.contest.comap.com/highschool/contests/himcm/2025results.html)：用于确认近年 Outstanding 的规模、编号和奖项层级。
3. [COMAP HiMCM Instructions](https://contest.comap.org/highschool/contests/himcm/instructions.html)：确认摘要首页、25 页上限、匿名要求和至少 12 pt 可读字体。
4. [2023 Problem B, Team 13904](https://reformship.github.io/pages/3competition/2himcm/HiMCM%20Outstanding/2023/B/13904.pdf)：25 页 A4。首页为 Team Control Number / Problem Chosen / 2023 HiMCM / Summary Sheet，随后是 Contents；正文主章节用罗马数字，最后为 one-page letter 和 references。
5. [2023 Problem B, Team 14087](https://reformship.github.io/pages/3competition/2himcm/HiMCM%20Outstanding/2023/B/14087.pdf)：24 页 A4。首页是集中式队伍信息块和摘要，随后 Contents；方法、结果、敏感性、强弱项和结论连续展开。
6. [2021 Problem B, Team 11552 摘要与公开节选](https://www.scribd.com/document/903284725/11552)：23 页，首页使用 Team Control Number / Problem Chosen / 2021 HiMCM Summary Sheet，内容按问题、模型、结果、敏感性、强弱项、结论组织。
7. [2022 Problem B, Team 12911 摘要与公开节选](https://www.scribd.com/document/949000702/12911)：首页使用集中式队伍信息块和 Summary Sheet，正文强调建模结果与预测。
8. [2023 Problem A, Team 14632](https://charlestang.dev/HiMCM2023.pdf)：25 页，首页为 Summary Sheet，正文以连贯的建模过程呈现。

## 共同版式规律

- **第一页信息固定**：Team Control Number、Problem Chosen、年份、HiMCM、Summary Sheet。即使摘要正文很长，队伍信息仍独立成块。
- **摘要是页面级交付物**：第一页用一页摘要说明问题、方法、关键数值、验证和结论，不在摘要中堆叠公式或参考文献。
- **目录后进入建模**：第二章通常是 Contents；正文按问题、假设、变量、模型、结果、敏感性、局限、结论推进。
- **层级清晰**：主章节用罗马数字或阿拉伯数字，子章节缩写模型/数据/结果之间的逻辑关系。
- **图表跟随论证**：热图、流程图、路线图紧邻解释；图号、图题和正文引用形成闭环，避免孤立大图。
- **12 pt 正文与克制的排版**：官方规则要求可读字体至少 12 pt。获奖样本以衬线正文、黑色或深蓝标题为主，表格可用较小字号但保持可读。
- **页眉和页码**：多数公开样本在正文页显示 Team # 和 Page x of N；第一页可以额外显示控制号块。
- **结果先于细节**：评委能快速看到模型选择、关键输出和限制；长推导和数据放入结果之后的附录或补充文件。
- **信件独立成页**：写给交通官员的信不是摘要复述，而是面向非技术读者的具体建议和数字。
- **AI 报告在 25 页之后**：AI use report 独立于正文页数，且必须保留原始查询和输出，不能只写概括。

## 本稿采用的格式改动

- 改为 A4；正文 12 pt、两端对齐；统一 `Team # __________` 与 `Page x of 25` 页眉。
- 首页重建为集中式队伍信息块、Summary Sheet 和完整摘要。
- 目录增加点线引导，并把章节改成罗马数字主章节及 `.A/.B` 子章节。
- 图表采用统一宽高、居中图题和编号；结果、敏感性、局限和参考文献保持独立边界。
- 原稿保留为 `tmp/legacy_format/charging_ahead_claude_plan_before_reformat.pdf`，便于比较，但不作为最终版本。

## 来源使用边界

上述样本只用于识别公开的版式惯例。团队控制号当前未提供，因此最终 PDF 中保留空格位；提交前必须由用户填写。样本中的具体措辞、方法、数据和结论没有迁移到本稿。
