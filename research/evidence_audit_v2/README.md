# 证据与数据资产盘点 v2

本目录是一次独立于现有模型和论文的重建前审计。它不评价当前模型好坏，也不推荐新模型；目的是回答“项目实际掌握了哪些事实、这些事实来自哪里、能支持什么”。

## 交付文件

| 文件 | 内容 |
|---|---|
| `evidence_master_register.csv` | 统一主表，88 条记录；当前证据资产、历史恢复项和明确排除的模型产物均有类别 |
| `data_asset_inventory.csv` | 84 条当前数据资产，记录内容、数值、年份、口径、来源、可靠性、用途和限制 |
| `data_gap_register.csv` | 26 条已知数据缺口及闭合所需材料 |
| `source_index.csv` | 86 份资料的可追溯索引，含 43 个本地文件 SHA-256 |
| `historical_recovery.csv` | 从四个论文历史版本恢复的 58 条事实/数字及当前保留状态 |
| `research_question_support_matrix.csv` | 14 类研究问题的证据支持等级与缺口 |
| `data_inventory_report.md` | 数据事实、可靠性等级和主要缺口的分析报告 |
| `source_index_report.md` | 官方资料、厂商规格、学术研究和数据平台的索引说明 |
| `historical_version_diff.md` | 上一版与更早版本删去/保留的事实清单及可靠性判断 |
| `research_capability_assessment.md` | 不依赖现有模型的证据能力总结 |
| `evidence_decision_brief.md` | 给决策讨论使用的浓缩结论 |
| `previous_version_cc7deab/` | 上一版 TeX 与 PDF 快照，便于直接比对，不影响当前论文 |

## 口径

- `EVIDENCE_ASSET`：当前可追溯的事实、官方统计、厂商规格、规划文件或文献估计。
- `DERIVED_SCREEN_NOT_EVIDENCE`：由已知数据计算出的筛查量，可用于探索，但不能替代观测。
- `MODEL_ARTIFACT_NOT_EVIDENCE`：当前或历史模型输出、模型假设、旧库存算术和敏感性结果。
- `HISTORICAL_RECOVERY_ONLY`：旧论文中出现、当前仍需保留的独立事实。

数据性质保留细粒度标签，例如 `OFFICIAL_STATISTIC`、`OFFICIAL_PLANNING_ESTIMATE`、`MANUFACTURER_SPEC`、`PROTOTYPE_TEST`、`PEER_REVIEWED_ESTIMATE`、`DERIVED`、`MODEL_ASSUMPTION` 和 `MODEL_OUTPUT`。

可靠性 A 表示原始文件中的精确计数/字段；B 表示官方但聚合、快照、近似或日期不完全匹配；C 表示外部规格、工程包或跨地区参数；D 表示派生、情景或模型产物。

## 盘点结果摘要

- 当前 84 项数据资产中，38 项可直接使用，37 项只能在限定条件下使用，2 项只能作压力筛查，7 项不是证据。
- 23 项属于“高可靠 A + 可直接使用”。
- 可靠性分布为 A 23 项、B 33 项、C 17 项、D 11 项；A 不代表无条件适用于所有年份或城市。
- 数据主线集中在 2023 服务/时刻表、车队快照、场站名义容量、采购/预算包、车辆规格、费率和排放因子。
- 当前最关键的数据缺口是逐车名册、车辆—班次—车库映射、实际场站占用、逐站 firm power、路线冬季能耗/载荷和严格小时级清洁电源证明。
- 上一版确实删去了一批有价值的官方事实，尤其是采购队列、场站容量、运营测试、电价/需量、空气质量和 CTA/TfL 细表；这些已恢复到 `historical_recovery.csv`。
- 不能恢复为事实的包括跨日期相减得到的 18 辆 BEB、旧库存算术、旧模型分数、432,768 格情景网格和当前模型的 2,100 辆/27.53%/−10.63% 输出。

## 追溯边界

当前规范论文、模型代码和结果没有被本轮盘点改写。`canonical_v4.json`、当前 TeX 和旧版 PDF 仍作为历史工作存在，但它们不能自动升级为原始证据。

本次没有检索或使用 2023 HiMCM 原版解答。所有外部陈述均以 `source_index.csv` 中记录的来源、页码/表名或本地文件为准；没有来源的模型数值被明确放入非证据类别。
