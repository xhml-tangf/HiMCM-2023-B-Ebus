# Charging Ahead — LaTeX manuscript

这是现有 Claude 规划稿的 LaTeX 重构版，对应 2023 HiMCM B 题的回顾性建模研究。
入口是 `main.tex`；正文拆分在 `sections/`，六张原始结果图在 `images/`。
无需访问项目外的数据文件即可编译。建模数字沿用已有运行结果。

## 打开与编译

在 Codex 中打开本文件夹，可以编辑源文件并查看 PDF 预览。
也可以将源码压缩包整体上传到 Overleaf，主文件选 `main.tex`，编译器选 XeLaTeX。
本地使用 XeLaTeX 时运行两遍以更新目录、参考文献和页码：

```text
xelatex main.tex
xelatex main.tex
```

Tectonic 会自动完成所需的重复编译：

```text
tectonic main.tex
```

最终 PDF 为 `main.pdf`。`team.tex` 只负责团队控制号，填写真实编号后重新编译即可。
不要使用获奖样本的控制号或自行编造编号。

## 版式依据与实际取舍

- [COMAP 官方规则](https://www.contest.comap.com/highschool/contests/himcm/instructions.html)：英文、可读的至少 12 pt 字号，首页摘要、每页控制号和页码，解答最多 25 页；AI 报告另附。现行网页为 2026 规则，稿件研究的是 2023 旧题，并不宣称是参赛期间的原始提交稿。
- [2023 Outstanding Team 13904](https://reformship.github.io/pages/3competition/2himcm/HiMCM%20Outstanding/2023/B/13904.pdf) 与 [Team 14087](https://reformship.github.io/pages/3competition/2himcm/HiMCM%20Outstanding/2023/B/14087.pdf)：参考摘要首页信息排列、目录、页眉、章节层级及独立信件的惯例。官方获奖身份见 [2023 结果](https://www.contest.comap.com/highschool/contests/himcm/2023results.html)。
- A4、19 mm 页边距、Latin Modern 衬线字体、罗马数字主章节、三线表属于本稿的版式选择；官方并没有指定这套唯一模板。
- 正文、表格、参考文献与图题均使用 12 pt 基础字号，没有通过缩小字体挤入页数。
- 公式使用原生数学环境；表格和参考文献编号、目录及正文总页数自动更新。长表允许跨页并重复表头，信件独立起页，AI 报告在解答之后。

## 编辑说明

直接编辑 `sections/*.tex` 即可修改本版本。
`scripts/build_claude_latex.py` 是从旧 Markdown 内容快照重新导出的工具，运行会覆盖 `sections/` 和 `main.tex`；已手改 LaTeX 后不要盲目运行。它保留现有 `team.tex`。

此次保留 17 张原稿表格、6 张原始图和 25 条参考文献；另外增加符号表。
修正了 AI 附录中“未用过外部论文”的过宽说法：获奖论文实际用于版式参考，模型与数据未从样本迁入。
完整 Claude 原始问答仍未提供，团队控制号仍待填写；排版完成不代表这些材料已补齐。

质量检查记录见 `quality_report.json`。本次排版不重新运行大规模模型，也不将其条件性结果升级为工程承诺。
