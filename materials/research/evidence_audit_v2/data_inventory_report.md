# 数据与证据资产盘点（独立于模型）

生成日期：2026-10-21。本盘点不修改论文或模型，也不把当前模型输出当成事实。

## 盘点规模

- 资产条目：84
- 缺口条目：26
- 数据性质分布：{'OFFICIAL_STATISTIC': 26, 'DERIVED': 15, 'OFFICIAL_STATISTIC + DERIVED': 2, 'OFFICIAL_APPROXIMATE': 1, 'OBSERVED_SNAPSHOT': 5, 'MODEL_ASSUMPTION': 3, 'DERIVED/OBSERVED': 1, 'OBSERVED_SNAPSHOTS/PROCUREMENT': 1, 'OBSERVED_PUBLISHED_TABLE': 1, 'CAPITAL_PLANNING_ESTIMATE': 1, 'OFFICIAL_PLANNING_ESTIMATE': 6, 'OFFICIAL_PLANNING_CONSTRAINT': 1, 'MANUFACTURER_SPEC': 6, 'PROTOTYPE_TEST': 1, 'PLANNING_ENVELOPE': 1, 'PUBLISHED_PLANNING_PARAMETER': 1, 'OFFICIAL_PLANNING_PARAMETER': 1, 'OFFICIAL_BUDGET': 4, 'PUBLISHED_TARIFF': 1, 'PEER_REVIEWED_ESTIMATE': 1, 'DERIVED / PEER_REVIEWED_ESTIMATE': 1, 'DERIVED / OFFICIAL_STATISTIC': 1, 'MODEL_OUTPUT': 3}
- 类目分布：{'context': 1, 'service': 25, 'fleet': 16, 'depot': 4, 'charging': 3, 'vehicle': 8, 'cost': 13, 'environment': 6, 'derived_screen': 3, 'model_output': 3, 'model_assumption': 2}
- 可靠性等级分布：{'A': 23, 'B': 33, 'D': 11, 'C': 17}

可靠性等级：A 为原始文件中的精确计数/字段；B 为官方但聚合、近似、快照或日期不匹配的数据；C 为外部厂商规格、工程规划包或跨地区转移参数；D 为由清单计算、情景假设或模型输出得到的结果。

使用状态：`DIRECT` 可直接进入描述统计或硬边界；`CONDITIONAL` 只能在列明适用范围时进入情景；`NOT_DIRECT` 只能作压力筛查；`NOT_EVIDENCE` 不是证据，包括当前模型假设和输出。

## 真正可直接支撑研究的原始事实

1. **服务规模**：2023 年实际固定线路公交（除 SeaBus）为 5,575,772 小时、106,868,324 服务公里、5,715,791,401 容量公里；TSPR 有 191 条路线记录。
2. **时刻表**：秋季 GTFS 23SEP_20231020 有 54,497 个不同班次、25 种服务日；展开到 119 天后为 495,198 个班次实例。
3. **负荷代理**：TSPR 频率记录 6,261 条，负荷记录 11,659 条；9,049/9,371 个正负荷单元匹配六种容量签名，但这是路线/时间带代理，不是车辆分配。
4. **车队快照**：2023 年官方电动车合计 280 辆；同日官方文章约 275 辆无轨加 5 辆 BEB；CNG 299 辆。2022 年详细快照 1,711 辆；2025 年活跃 1,733 辆、库存 63 辆。日期、类别和状态不同，不能拼成 2023 逐车名册。
5. **场站与电力**：2020 年六个运营中心名义容量 1,991 个 40-ft 等价位，Marpole 规划 300；2023 年官方称所有场站已满；2024 年全转型 2040 规划约 78 MW 增量，既有场站充电交付 6-8 年。尚无逐站 firm power。
6. **成本与采购**：2023 年有 BEB、充电站和场站的规划包；2025/2026 年有命名车队项目、预算和退役队列。它们是预算/项目包，不是统一口径的交付合同，且存在重叠。
7. **三城车队**：Chicago 2023 年 1,875 辆（1,576 标准+299 铰接，25 辆推断 BEB）；London 2023-03-31 有 8,643 个车体位、950 电动和 20 辆氢燃料。两城均无逐班/车库/充电执行证书。
8. **环境背景**：BC 2023 电网平均因子 11.3 tCO2e/GWh；TransLink 全收入车队运营排放 112,591 tCO2e（全模式）；ICCT 提供外部生命周期转移因子。

## 当前模型参数必须单列

2,100 辆 BEB、101.67 MW、27.53% 完整寿命环境分和 −10.63% 十年经济分均来自 `canonical_v4.json` 的情景计算，依赖 15% 备用、80% 可用电池、80% 季节电量、1.35 道路因子、30 km/h、8 个场站锚点及候选车辆参数。它们不是观测结果。

其他常见混淆：

- 1,725 辆是 2023 库存情景，不是逐车清点结果；
- 85 人容量签名是推断，不等于每辆双层车身份；
- GTFS block 是计划分组，不等于车辆或车库；
- 2022/2025 车队快照不能替代 2023 名册；
- 厂商额定电池和充电功率不等于 Vancouver 冬季/满载实测；
- ICCT/外部 LCA 因子的结果不是本地 EPD。

## 目前能支持的研究问题

**较强支持：**

- 2023 年固定线路公交的路线、服务量、时段频率和容量代理统计；
- 按车辆类别做库存、采购队列、年限和充电规模的描述/情景分析；
- 在明确外部参数边界下做财务和环境敏感性比较；
- 三城车队规模与更换压力的横向比较。

**条件支持：**

- 2033 年全电动的具体车队数、每日排班、充电功率和车库扩建；
- 某辆候选 BEB 是否能完成某条真实班次；
- 特定场站是否可接入足够的电力。

**目前不足：**

- 认证一个真实的 TransLink 2033 全电动最优方案；
- 把模型输出的成本或 LCA 分数当作观测事实；
- 把 Chicago/London 的车队位模型称为完整调度证书。

## 重建顺序

1. 以服务量、路线/时段和容量代理做描述性分析；
2. 以车队类别、燃料、年份、采购队列做库存/财务分析；
3. 只有在逐车、逐班、逐站资料补齐后，才考虑详细调度或基建优化；
4. 现有 `canonical_v4.json` 只保留为待审查的情景，不作为证据基础。

详细逐项资产见 `data_asset_inventory.csv`；缺失项见 `data_gap_register.csv`。
