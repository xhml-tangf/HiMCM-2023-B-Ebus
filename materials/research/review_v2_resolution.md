# 新版审稿报告修复记录

日期：2026-10-20。对应 `D:/AI/ebus-peer-review-v2/新版审稿报告.md`。
本记录替代第一轮记录中关于终值和周期验证的关闭结论。

| 编号 | 修复 | 可核查证据 |
|---|---|---|
| V2-01 Major | 主账本先加回已抵扣的新车终值，再统一扣一次全部车辆终值；共同无轨电车抵扣不变。重算表 6、摘要、结论和信。旧重型车和接驳车出售价值改用常规车型价格。 | `src/build_asset_boundary.py`、`results/vancouver_asset_boundary.json:terminal_reconciliation`；`tests/test_asset_boundary.py` 独立逐辆队列核算初始幸存资产，并核对两边抵扣。 |
| V2-02 Major | 撤销临时“仅接受日历日”限制。按 `1440*n+local_time` 建立绝对时轴，保留活动时长；两个周期副本检验周期首尾、车辆、道路、充电位、电网和馈线并发。逐事件传播 SOC/燃料，在同一车辆事件相位比较周期状态；午夜不回库、不补能、不重置地点。 | `src/model.py:check_periodic_schedule`；`tests/test_model.py` 包含报告原反例、单日周期首尾、异车站点冲突、馈线冲突、回库时间不足、缓慢耗电及合法 26 小时班次/跨午夜行程。 |
| V2-03 Moderate | 新购变量改为 `x^p`，总购置为推进类别之和；服务模式用 omega、日期用 n；能耗距离绑定 `sum_i z_iv*l_it`，声明充电二元变量和日周期长度。 | `paper/ebus_transition.tex` 第 3 节公式及符号说明；未执行的完整 master 仍明确标注为概念模型。 |
| V2-04 Moderate | 所有实际用于主财务比较的通用、分类及敏感性价格改为来源标注的叶子项；先按来源币种和明确汇率假设换算，再按源年 CPI 统一到 2023 CAD。2021 Calgary、2021 低价车型、2025 articulated 均修正；混合设施拆为 2019 充电设备和 2023 场站费用。更新采购、补贴、残值、图表和文字，去除旧的“未换算”说明。 | `src/price_catalog.py`、`src/price_index.py`、`results/vancouver_price_ledger.json`、`results/deck_shuttle_price_ledger.json`；新央行 2019—2025 月度数据共 84 条，SHA-256 记入 `results/canada_cpi_audit.json`；`tests/test_price_index.py` 检查不同源年及无二次换算。 |
| V2-05 Moderate | 统一采用 `gap < 5 + 60*distance/50`，含零距离短间隔。代表日 4,588/20,679 个连接不满足这一假设；Route 100 的 200 个连接仍通过。文字明确不是实际运营失败数量。 | `src/analyze_vancouver_blocks.py`、`results/vancouver_block_range_audit.json`；`tests/test_small_duty_plan.py` 的零距离及恰好五分钟反例。 |
| V2-06 Minor | 表 10 列名改为 `On-time new due`，对应“本年新到期且按时更新”，不再称累计购买。 | `src/make_three_city_roadmap.py`、`paper/tables/chicago_age_roadmap.tex`。 |

## 当前数值及边界

- 分类中央 PV：4.434461 / 2.643963 十亿 CAD；经济评分 −67.7202%。对称 0/25/50% 补贴：−67.7/−38.0/−5.0%。
- 资产补充基准 PV：2.531867 十亿 CAD。全部终值 474.902 百万中，364.644 百万已经抵扣；只追加初始幸存资产 110.257 百万和共同既有电动车 1.838 百万。
- 联合价格、出售代理及设施终值修正后，资产评分范围 −75.0733% 至 −20.5604%。
- 通用 high PV：7.996922 十亿 CAD；分类 high PV：4.730526 十亿 CAD。
- 补充充电器维护、电池储备和额外运营劳动后，分类全 TCO 桥接评分为 −68.7% 至 −71.1%。
- 加入设施隐含碳后，四类燃料下的分类环境评分为 −67.0% 至 3.4%。
- USD/CAD 1.35、1.37 仍为固定敏感性假设，不冒充历史实测汇率。双层旧车缺少当地常规购价，终值和出售仍保留同一披露的等效资产代理。

## 验证

`python scripts/reproduce_local.py` 完成全部分析及 432,768 格参数计算；88 项测试通过。
主文数字检查通过。区域影响脚本在通用财务结果之后运行，以避免读入旧金额。
最终 PDF 的编译、页数和检查结果见 `results/editor_pdf_build.json` 与 `results/pdf_layout_checks.json`。

## 保留的证据限制

本次关闭的是报告列出的六项确定错误。完整城市调度、真实 2023 逐车登记、当地充电容量及严格零排放电源采购仍为 UNVERIFIED。周期验证针对给定数据，附件负荷在连续值勤和跨日停留中持续计入；没有自动推断停车停机策略。合成跨午夜测试不是 Route 100 的现实充电方案。

报告 E6/F 中的额外分析建议（405 辆超过经济寿命车辆的真实延寿方案、Route 100 站点实测、伦敦新增释放年约束）仍需要当地数据，不是这六项程序/会计错误的验证证据。司机费用只是增量 FTE 情景，deadhead 是假设加项，期外电池储备不能与十年 PV 直接相加；基础设施终值也不是市场出售价。论文继续保留这些限制。

## 后续补齐

The numbers in the historical section above were superseded after official
fleet, full-city schedule, cost, environmental and three-city execution audits.
See `materials/research/remaining_evidence_closure.md` and the current result JSON files.
