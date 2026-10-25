# Claude 规划实现：交付导航

本目录保存用户提供的规划与参考代码原件。实际实现、实验结果及英文论文分别位于 `src/claude_*.py`、`results/claude_plan/` 和 `paper/claude_plan/`。原有论文、模型和用户此前的路线试验保持独立。

## 打开什么

- 最新 LaTeX 版英文论文：`paper/claude_plan/latex/main.pdf`；入口 `main.tex`，可直接在 Codex 编辑或将 `release/charging_ahead_latex_source.zip` 上传至 Overleaf（XeLaTeX）。当前为 21 页解答加 1 页 AI 报告，检查记录在 `paper/claude_plan/latex/quality_report.json`。
- 中文逐章说明与术语表：`paper/claude_plan/中文思路与术语导读.md`。
- 先前的 ReportLab 版本：`paper/claude_plan/charging_ahead_claude_plan.pdf`；同名 Markdown 是 LaTeX 重构使用的内容快照。直接编辑 LaTeX 的 `sections/` 后，不要重新导出覆盖手工修改。
- 顶级论文版式调研与来源：[format_notes.md](../himcm_exemplars/format_notes.md)。最终 PDF 使用 A4、12 pt 正文、集中式摘要首页、页眉控制号/页码和点线目录。
- 先前 ReportLab PDF 共 25 页，其中 24 页属于正文/摘要/目录/信件/参考文献，AI 附录单独 1 页；旧版布局检查结果在 `results/claude_plan/pdf_quality.json`。
- 温哥华主要结果：`results/claude_plan/vancouver_main.json`、`patterns.json`、`impacts.json`、`roadmap_budget.csv`。
- 芝加哥、伦敦：各自 `results/claude_plan/chicago/`、`london/` 下的 `main.json`、`days.json`、`roadmap_budget.csv`、`impacts.json`、`verification.json`。
- 校验总表：`results/claude_plan/verification.json`；小规模最优解对照：`benchmark.json`。
- 站点成本筛选：`results/claude_plan/site_cost_screen.json`；逐条引用台账：`references_audit.json`。
- 新增两城的数据说明：[timetable_acquisition.md](timetable_acquisition.md)。输入清单及逐班时间位于 `data/processed/{city}_claude_gtfs/`。
- AI 披露缺口说明：[AI_DISCLOSURE_CHECKLIST.md](AI_DISCLOSURE_CHECKLIST.md)。
- 原始规划：[spec_original.md](spec_original.md)；原始参考程序：[solver_reference_original.py](solver_reference_original.py)。两者按收到的字节保存，不代表其中所有命题均已成立。

## 实现及纠错

调度同时计入前一班至充电点、充电点至下一班的转场距离和时间，并独立重放每辆车的完整序列。参考程序的两块兼容性不能保证三块串联后的续航可行；回归测试保留了一个三块反例。新实现使用真实入块电耗传播和保守删边修复，结果是**可行上界，不是全局最优解**。

柴油基准先用短连接图求匹配，再在完整可行图中寻找增广路直到不存在，不能把10分钟候选窗口当成最优性证明。充电功率按分钟到小时的60倍系数换算。每次补入的能量等于实际消耗，白天补电与夜间恢复电量合计与总行驶能耗闭合。

固定站点与最多K个站点均可求解；另有小实例MILP、LP下界、独立穷举及随机对照。范围/充电时间的敏感性保留在放宽参数后仍可行的既有方案，防止将启发式搜索噪声误解释成物理规律。

伦敦大实例在分块数超过3,000时采用稀疏充电连接：每个出发块/充电点只保留按可用时间排序的256个后继候选，再做续航筛选。它可能漏掉更优连接，故只提供可行上界；柴油基准仍进行完整图的增广路终止检查。回归测试验证了候选覆盖完整小图时与原连接过程一致，并检验稀疏删边后的可行性。

## 运行

项目使用 Python 3.12；本次运行环境的主要库为 NumPy 2.4.4、SciPy 1.18.0、pandas 3.0.2、Matplotlib 3.11.0。PDF 生成额外需要 ReportLab、Pillow；若系统 Python 缺少它们，使用 `load_workspace_dependencies` 返回的 bundled Python 执行生成器。PDF检查使用 PyMuPDF，并通过 Poppler `pdftoppm` 渲染逐页图片。命令需要在项目根目录运行。

```powershell
python -m pytest tests/test_claude_evsp.py tests/test_claude_impacts.py -q
python scripts/benchmark_claude_plan.py
python scripts/run_claude_plan.py --stage all
python scripts/prepare_comparator_gtfs.py chicago --source materials/sources/raw/comparator_timetables/chicago_2023.zip --start 2023-06-12
python scripts/prepare_comparator_gtfs.py london --source materials/sources/raw/comparator_timetables/london_2023.zip --start 2023-06-12
python scripts/run_comparator_plan.py chicago
python scripts/run_comparator_plan.py london
python scripts/analyze_claude_plan.py
python scripts/verify_comparator_plan.py
python scripts/verify_claude_plan.py
python scripts/build_claude_paper.py
```

生成最终 PDF 前，如有团队控制号，可先设置 `$env:HIMCM_TEAM_NUMBER='1234'`；否则页眉和摘要页会保留 `__________` 占位符。

当前完成的代表日结果：温哥华 19,967 班次，`N_d=1,043`、`N_e=1,247`、2 个成本筛选站点；芝加哥 16,314 班次，`N_d=1,151`、`N_e=1,434`、2 个候选节点；伦敦 105,882 班次，`N_d=6,755`、`N_e=7,383`、4 个候选节点。伦敦四节点均位于 Trafalgar Square/Charing Cross 的 169m 内，不能当成四个独立工程选址。

城市运行器在 `main.json`、各日期和年度结果存在时跳过已完成阶段。要做参数变化，请使用新输出目录或明确归档旧结果；不要混合旧参数和新输出。原始时刻表下载耗时，正常复现直接使用已保存且校验过的快照。

在全新数据目录重建新增原始输入时，先运行 `python scripts/fetch_comparator_timetables.py` 下载CTA历史文件和Zenodo元数据，再运行 `python scripts/extract_london_archive.py --member OBDS_archive_Jun2023/OBDS_archive/bod_2023-06-10_21.00.02_gtfs.zip` 提取英国快照。后者实际传输约489MB并产出581MB成员，完整19.5GB档案不下载。

## 必须保留的解释

1. 这是给定 R、T、同等容量、近似转场和不限充电容量条件下的调度研究。未证明真实站点、电网、司机、车场、重复运营日或备用车辆可行。
2. 温哥华覆盖25种秋季服务模式；新增两城使用2023年6月12日至18日一周。年度里程是外推，不能写成全年观测。
3. 芝加哥和伦敦的统一货币成本、电耗和网碳参数是温哥华基准的迁移试验，不是本地采购建议或本地减排预测。不能把伦敦地理服务范围与TfL合同车队库存直接相加。
4. 十年计划输出“所需预算”，没有凭空设定用户未提供的年度预算上限，也没有证明车龄优先退役与各路线分配一致。它不是已获资助的施工计划。
5. 正文提供0%、25%、50%补助的现金流和NPV，并区分财务补助与社会资源成本。柴油匹配最小化车辆数，不最小化空驶成本；保留零柴油空驶费用的乐观下界检验。
6. Claude完整对话是AI披露的来源凭据。没有它仍可运行模型；正式提交前需补齐原始提问和完整回答。不得将概述冒充逐字记录，也不能据用户文件中的标签擅自认证Claude版本。

## 尚需用户或外部事实才能完成

- 原Claude对话及其他相关AI原始问答；团队控制编号（PDF 中暂留 `__________`）。
- 实际年度预算、车型载客量与路线/车龄/车场映射。
- 可建设站点、实际电网接入容量、零排放电力来源、当地报价与运营电价。

这些缺口不通过编造数据填补，正文和机器可读结果均保留相应范围限制。
