# 双层公交与社区接驳车电动化证据审计

审计日期：2026-10-18。研究对象是 TransLink/CMBC 的固定线路双层公交与社区接驳车。本文只使用公开的运营方、制造商、采购文件和 2023 GTFS，不使用 2023 HiMCM 原解。所有金额都是名义值；没有把不同年份的金额直接当成实际价格或折现值。

## 判断先行

1. **双层车 57 辆可以核对到运营规模。** TransLink 2019 年公开订单为 32 辆，另行使 25 辆选择权，合计 57；2023 年 6 月董事会追踪表把 25 辆列为 Q2 2023 已接收。[TransLink 2019-08](https://www.translink.ca/news/2019/august/double-decker%20buses%20rolling%20into%20service%20this%20october)、[TransLink 2019 Buzzer](https://buzzer.translink.ca/2019/08/pne-fair-double-the-delight-with-our-double-decker-bus-onsite/)、[2023 Board package, p. 22](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/board-of-directors/board-minutes-and-reports/2023/june/23-06-22-public-board-meeting-package---for-posting.pdf)。2023 fall GTFS 的 `cap85` 容量 proxy 也恰为 57 个 weekday duty blocks。这个数量重合是有用的交叉检查，**不是车辆 ID/block 的逐一对应证明**。
2. **接驳车只能形成 171–206 辆区间。** 较早的详细 snapshot 为 206 辆（163 辆 CMBC + 43 辆 contracted）；2025-11-18 active snapshot 为 171 辆 gasoline shuttle。[CMBC fleet page](https://www.translink.ca/about%20us/about%20translink/operating%20companies/coast%20mountain%20bus%20company)、[2025 FOI snapshot, p. 1](https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/cmbc-fleet--active--instorage.pdf)。2023 年没有可验证的逐车名册；168 辆是 2023 年采购追踪表中的 replacement order，不是 fleet total，也不是电动车承诺。
3. **57 个双层 duty 不能全部靠单次夜间充电完成。** 2023 年公开的 472 kWh Enviro500EV 在 80% 可规划电量、1.79 kWh/km 的最冷日 proxy 下只有约 211 km；57 个 weekday duties 中 33 个可以确定单充完成、2 个区间不确定、22 个必然需要补充充电。即使换到 827 kWh 的乐观 2033 规格，仍有 8 个 duty 必然超出约 465 km 的单充范围。**因此“57 辆全部夜间充电”不可行；全量 57 辆在 2033 只能有条件依赖终点/中途快充。**
4. **171–206 辆接驳车用 2023 年现成 16–20 座车辆直接一比一替换，不可行。** 118 kWh EV Star 在保守冬季 proxy 下约 118 km，101 个 `cap24` duty proxies 中 53 个必然需要补充充电；150 kWh 车型也还有 49 个必然短差。到 2033，260 kWh/30-ft 方案把单充范围提高到约 246 km，仍有 20 个 duty 必然短差，但配合中途充电具备技术可能性。真正的约束是 20 座容量、窄路转弯半径、全电加热和 depot 供电。TransLink 自己在 2024 年计划中把接驳车大规模转换放在 mid-2030s，并把双层车转换放在 2030 年之后。[2024 Plan summary, p. 20](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf)。

## 数量与班次对应

| 项目 | 结果 | 年份/含义 | 来源与页码 |
|---|---:|---|---|
| 双层物理车队 | 57 辆 | 32 + 25，2019 订单；2023 追踪表 25 辆已接收 | TransLink 2019-08；2023 Board PDF p. 22 |
| 2023 weekday `cap85` blocks | 57 | 2023-11-14，route-capacity proxy | archived 2023 GTFS；`src/analyze_vancouver_blocks.py` 计算 |
| 双层 capacity | 80–86 seats/辆；85-space proxy | TransLink 2017 pilot；2023 load-factor diagnostic | [2017 release](https://www.translink.ca/news/2017/november/translink%20launches%20double%20decker%20bus%20pilot%20project)；`results/vancouver_block_range_audit.json` |
| 双层 annual km estimate | 5.11–5.79 million km | 由 57 个 weekday duties 的双层距离份额推到 2023 年 106.87m km；不是运营商分类公里表 | 2023 GTFS + [2025 Business Plan p. 23](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf) |
| 双层 annual km/物理车 | 89.6–101.6k km | 年化 proxy | 同上 |
| 社区接驳车 physical stock | 171–206 辆 | 171 = 2025 active gas shuttles；206 = 较早 detailed stock | 2025 FOI p. 1；CMBC fleet page |
| 2023 weekday `cap24` blocks | 101 | route-level capacity proxy；不是 171–206 辆车本身 | archived 2023 GTFS；本地 block audit |
| 2023 shuttle service | 13,653,519 km；705,621 h | CMBC 10,920,849 km + contracted 2,732,670 km；hours 为 576,937 + 128,684 | [2025 Business Plan p. 23](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf) |
| shuttle annual km/物理车 | 66.3–79.8k km | 13.653m km 除以 206 或 171；是平均车辆负担，不是逐车里程 | 同上 |
| shuttle capacity | 20 spaces：current operating limit；2018 planning reference mini-bus 24 | 2026 limit 是后续资料，不能倒推为 2023 规则 | [TransLink special events](https://www.translink.ca/about-us/doing-business-with-translink/planned-special-events)；[2018 service guidelines](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/transit-oriented-communities/transit-services-guidelines-public-summary.pdf) |

206 与 171 的差异不能解释成“退役了 35 辆”而不加证据：一个数字来自较早的 detailed snapshot，另一个来自 2025 active/in-storage 文件，时间、在役定义和 contracted 范围不同。168 辆 2023 order 也不是 2023 fleet count。

## 车辆、冬季能耗与充电参数

| 参数 | 量化值 | 年份与状态 | 来源、页码、币种 |
|---|---:|---|---|
| 2023 Enviro500EV battery / DC / capacity | 472 kWh；150 kW；KMB configuration up to 122 passengers | 2023 specification；2024 service | [ADL HK spec, p. 1](https://www.alexander-dennis.com/site-content/uploads/2023/10/Enviro500EV-Hong-Kong-2023-11.pdf)；[KMB launch 2024](https://www.alexander-dennis.com/kmb-launches-alexander-dennis-enviro500ev-into-hong-kong-service-following-completion-of-testing-and-certification/)；不含币种 |
| 2021 NA Enviro500EV CHARGE prototype | 648 kWh；up to 82 seats；45-ft；heat pump | known by 2023；prototype, not fleet availability | [ADL 2021 release](https://www.alexander-dennis.com/alexander-dennis-unveils-its-first-zero-emission-three-axle-double-deck-bus-the-enviro500ev-charge-for-north-america/)，web unpaginated |
| 2024 next-generation NA deck | >700 kWh；up to 300 mi；2 kWh/mi | later evidence, not 2023 known | [Foothill Board, p. 21](https://www.foothilltransit.org/sites/default/files/2024-01/01-26-24_eb_agenda_packet.pdf)；mild-condition claim |
| Current NA deck envelope | 709 or 827 kWh；up to 340 mi；300 kW charge | later evidence; optimistic 2033 screen | [ADL NA product](https://www.alexander-dennis.com/buses/enviro500ev-north-america/)，web unpaginated |
| 40-ft CMBC winter intensity | annual mean 1.60；coldest-day mean 1.79 kWh/km | 2020 modeled CMBC routes | [2020 Fleet Plan, pp. 72–73](https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf)；CAD context |
| 60-ft CMBC winter intensity | annual mean 2.15；coldest-day mean 2.42 kWh/km | 2020 modeled CMBC routes | same, pp. 72–73 |
| 2020 heating anchor | up to 14 kW electric resistance at −18 °C; 2.5 kW cooling at 27 °C | Vancouver planning prior；do not add it twice to all-in kWh/km | same, p. 72 |
| Community shuttle nominal products | EV Star 118 kWh / up to 19+driver / 150 mi / 60 kW DCFC；Endera 150 kWh / 10–80% in 30 min / 12+2 or 16+2 | 2023-known products | [GreenPower EV Star](https://greenpowermotor.com/gp-products/ev-star/)；[Endera 2023](https://www.enderamotors.com/press-releases/endera-unveils-the-2023-all-electric-shuttle-model-with-extended-range-and-fast-charging-speeds)；[CALACT release](https://www.enderamotors.com/blog/press-releases/endera-selected-for-largest-state-ev-bus-contract-in-us-history/) |
| LionM | 160 kWh / 150 mi nominal；commercial production indefinitely delayed in Q4 2023 | known product with a 2023 supply failure signal | [Lion 2023 results](https://www.prnewswire.com/news-releases/lion-electric-announces-fourth-quarter-and-fiscal-2023-results-302075488.html)，web unpaginated |
| Depot / in-route charger technology | depot CCS plug-in；in-route 300–450 kW pantograph typically；5–15 min/event；45–90 min/day | 2020 CMBC engineering case | [2020 Fleet Plan, p. 64](https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf) |
| North America opportunity-charging case | 13 × 300 kW in-ground inductive chargers for 48 electric buses (33 double-deck + 15 articulated) | 2024 order; not delivered/operational in 2023 | [Sound Transit/InductEV release](https://www.prnewswire.com/news-releases/sound-transit-to-go-wireless-in-seattle-with-48-electric-buses-including-33-double-deckers-302066915.html)，web unpaginated |
| New Flyer direct-product check | Xcelsior CHARGE NG 35/40/60 ft；40-ft up to 88 total；450 kW rapid-charge configuration | 2023 brochure; no direct deck or 20-passenger shuttle | [New Flyer 2023 brochure, pp. 1, 5–6](https://www.newflyer.com/site-content/uploads/2023/01/Xcelsior-CHARGE_NG_Brochure.pdf) |

**冬季口径：** 对双层车，`1.79 kWh/km` 是 TransLink 2020 年 40-ft 最冷日模型，不能当作 Enviro500EV 实测；中央值 `1.80` 是对该历史 winter anchor 与 deck 的高速/重量差异的保守 proxy。对接驳车，没有公开的 Vancouver 20-passenger winter test；`0.80–0.90 kWh/km` 是由制造商 nominal range 与本审计的冬季折减假设形成的 screening value，不是实测。任何需要正式校核的表都应将这几项标为 **DERIVED / UNVERIFIED**。

## 成本参数与公开案例

| 项目 | 金额 | 年份/币种/口径 | 来源与页码 |
|---|---:|---|---|
| 2023 TransLink generic BEB screen | 1.2 million / bus | 2023 nominal CAD；非 deck-specific | [June 2023 technology deck, p. 29](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf) |
| 2023 one in-route charger screen | 460–610k | 2023 nominal CAD；equipment-oriented | same, p. 29 |
| 2020 in-route charger all-in engineering | 0.9–1.2 million；average 1.0；p85 1.3 | 2019 CAD；includes site work, excludes some project delivery | [2020 Fleet Plan, pp. 97–98](https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf) |
| Hamilton Route-100 charging envelope | 2.3 million | 2023 CAD screen；depot plug-in chargers + one in-route charger, planned 19 BEBs | June 2023 deck p. 30 |
| Port Coquitlam charging envelope | 46 million / 10 in-route chargers = 4.6 million each | 2023 CAD screen；high site-integration envelope | June 2023 deck p. 30 |
| Marpole depot envelope | 500 million / 340 BEB positions = 1.47 million per position | 2023 CAD screen；includes land/development and is not charger-only | June 2023 deck p. 30 |
| Foothill next-generation deck actual contract | USD 21,096,000 / 12 = USD 1,758,000 per bus | 2024 USD；42-ft；excludes infrastructure and taxes | [Foothill Board, p. 21](https://www.foothilltransit.org/sites/default/files/2024-01/01-26-24_eb_agenda_packet.pdf) |
| BC incentive-list double-deck EV MSRP | USD 870,000 for 313-kWh DD8；USD 1,165,000 for 446-kWh DD10 | 2020 model-year market listing, published 2021；USD；not a TransLink bid | [BC SUVI list, p. 1](https://pluginbc.ca/wp/wp-content/uploads/2020/12/SUVI_MHD_03_09_2021.pdf) |
| Calgary electric shuttle purchase | over CAD 6,000,000 / 14 = CAD 428,571 per vehicle | 2021 CAD；28-ft/22-passenger order；not delivered | [Vicinity 2021 disclosure](https://www.sec.gov/Archives/edgar/data/1834975/000173112222000597/e3635_ex99-1.htm)，web unpaginated |
| BC incentive-list EV Star prices | USD 195,500 with side；USD 239,500 Transit Plus；USD 265,000 Transit Plus with ADA | 2021 model-year MSRP, published 2021；USD；before listed incentive | [BC SUVI list, pp. 1–2](https://pluginbc.ca/wp/wp-content/uploads/2020/12/SUVI_MHD_03_09_2021.pdf) |
| BC incentive-list comparable 25–28-ft vehicles | Vicinity Lightning 168 kWh：USD 400,000；LionM 160 kWh：USD 395,000 | 2021 model-year list prices；USD | [BC SUVI list, p. 3](https://pluginbc.ca/wp/wp-content/uploads/2020/12/SUVI_MHD_03_09_2021.pdf) |
| Calgary pilot close-out | CAD 5 million spent；mostly charging infrastructure | 2024 retrospective CAD；contract cancelled after vendor missed commitments | [Calgary Transit update](https://www.calgarytransit.com/plans---projects/electric-bus-pilot-project.html)，web unpaginated |
| 2020 AVTA EV Star screen | USD 574,683 / 6 = USD 95,781 per vehicle | 2020 USD；Board text says USD 100k/vehicle HVIP credit included | [AVTA agenda, pp. 2, 162](https://www.avta.com/downloads/meetings/bod/2020/022520-agenda.pdf) |
| 2020 AVTA charger equipment | USD 183,948 / 6 = USD 30,658 per charger | 2020 USD；equipment line item，installation/utility not established | [AVTA agenda, pp. 2, 164](https://www.avta.com/downloads/meetings/bod/2020/022520-agenda.pdf) |
| 2023 Redwood Coast EV Star grant | USD 160,000 | 2023 USD；covers most of one EV Star Plus, **less charger** | [RCTA packet, p. 5](https://redwoodcoasttransit.org/wp-content/uploads/2023/04/RCTA-Agenda-Packet-4-24-2023.pdf) |

`CAPITAL` 情景只包括车辆和本审计明确列出的充电/场站 envelope。它不包含电费、运维、司机、税、融资、电池早期更换余值或完整场站扩建。尤其不能把 `57 × 1.47m` 直接加在当前城市模型的 depot 数字上：Marpole ratio 与现有非 deck 车辆的共享 charger 已经可能重叠。

## Low / Central / High 情景

方法：每个 2023 weekday duty 的距离取 GTFS 的上下界；`certain feasible` 要求上界小于规划半径，`interval` 为上下界跨过半径，`certain shortfall` 要求下界已高于半径。情景半径 = battery × usable fraction ÷ winter kWh/km。充电分钟数按 vehicle DC rate × 0.90 efficiency 计算，并只用于 screening。

| 双层情景 | battery；winter intensity；usable | 规划半径 | 57 duties：certain / interval / shortfall | 典型补充充电分钟/短差 duty | 57 辆 capital envelope |
|---|---:|---:|---:|---:|---:|
| Low：2023-known 472-kWh point；150 kW | 472 kWh；1.79 kWh/km；80% | 211 km | 33 / 2 / 22 | 约245 min upper-bound | CAD 100.2m |
| Central：2024 >700-kWh production proxy；300 kW | 700 kWh；1.80 kWh/km；85% | 331 km | 35 / 5 / 17 | 约90 min upper-bound | CAD 154.1m |
| High：827-kWh forward envelope；300 kW | 827 kWh；1.60 kWh/km；90% | 465 km | 43 / 6 / 8 | 约63 min upper-bound | CAD 296.8m |

Low 用 2021 BC 名单的 BYD DD10 446-kWh 双层 coach MSRP US$1.165m × 1.35 = CAD 1.573m/bus；该车型不是 TransLink 三轴公交认证版本，所以结果仍是 **lower market envelope**。Central 用 Foothill 的 2024 合同按 US$1.758m × 1.37 = CAD 2.408m/bus；High 再加 25% supply/engineering premium。充电基础设施的 Low 为 HTC 2.3m 中的 depot share（扣除 610k in-route 后的约 89k/bus）+ 9 个 610k 设备 screen；Central 为同一 depot share + 9 个 1.3m all-in charger；High 为 Marpole 1.47m/position + 9 × 4.6m port envelope。

| 接驳车情景 | battery；winter intensity；usable | 规划半径 | 101 duties：certain / interval / shortfall | 典型补充充电分钟/短差 duty | fleet / capital envelope |
|---|---:|---:|---:|---:|---:|
| Low：118-kWh 2023 small shuttle；60 kW | 118 kWh；0.80 kWh/km；80% | 118 km | 46 / 2 / 53 | 约113 min upper-bound | 171 辆；CAD 64.0m |
| Central：150-kWh Endera-class；70 kW | 150 kWh；0.90 kWh/km；85% | 142 km | 51 / 1 / 49 | 约96 min upper-bound | 189 辆；CAD 90.5m |
| High：260-kWh / 30-ft forward；120 kW | 260 kWh；0.90 kWh/km；85% | 246 km | 74 / 7 / 20 | 约30 min upper-bound | 206 辆；CAD 195.7m |

接驳车 Low 使用 2021 BC 名单的 EV Star Transit Plus with ADA MSRP US$265k ×1.35 = CAD358k；Central 用 Calgary 的 over-CAD 6m/14 = CAD428,571；High 取 2033 30-ft、场站和供应风险的 CAD650k planning value。充电按 Low 1 charger/3 vehicles、Central 1/2、High 1/1，充电位分别为 57、95、206 个；每口为 CAD50k、100k、300k 的 screen。High 的 300k/口以 Calgary 已花 5m、主要是充电基础设施作为高位锚点，不是设备清单。

班次可行性总结：双层 Low 的 22 个必然短差 duty 平均仍需约 245 min 车上/终点补能，远超 2020 CMBC 的 45–90 min/day 规划参考；Central 约 90 min 刚好贴近该范围；High 约 63 min 落在范围内，但仍需多个 terminal stops 和足够的停车/电网能力。接驳车 Low/Central 的短差 duty 分别约 113/96 min；High 约30 min，但 20 个 duty 仍不能单靠夜间充电。

## 2033 可行性

**双层车：** “57 辆全部在 2033 实现全电、且维持 2023 全部 duty”在物理上只能作为带中途/终点快充的条件方案，不能作为夜间充电方案。2023 年可查的 472-kWh 产品在全电冬季假设下只覆盖 33 辆确定 feasible；2024 年 >700-kWh 产品把确定 feasible 提高到 35 辆，并把必然短差降到 17 辆；827-kWh 的乐观 2033 envelope 也只有 43 辆确定 feasible、6 辆区间不确定、8 辆必然短差。另有容量、轴重、坡道和制动认证没有得到公开证据。TransLink 在 2024 年计划中建议双层车 **after 2030** 才开始转换，所以把 2033 当作全量部署年份，是政策加速，不是已证明的采购结论。[2024 Plan, p. 20](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf)。

**社区接驳车：** 2023 年的 16+2 座小巴甚至低于 TransLink 当前的 20 座 operating limit，可能要多发一班或增加约 11% 车辆；118 kWh 车型只覆盖 46 个确定的 `cap24` duty，150 kWh 车型覆盖 51 个。2033 的 260-kWh、约 246-km 的 30-ft 方案可把确定覆盖提高到 74 个，剩下 20 个仍需要中途充电、block 重组或拆分。TransLink 2025 的 Letenda 30-ft trial 给出 22 seats、44 max、约250 km，但它只是 2025 年测试，不是已交付的全量方案。[2025 test](https://buzzer.translink.ca/2025/03/were-testing-a-30-foot-battery-electric-bus/)。因此 171–206 辆的**全量 2033 替换是可以研究的技术 stretch，但没有被现有采购/运营证据支持为 plan-of-record**；更可靠的基准是 mid-2030s 分批转换。

## 不可验证项

- 2023-12-31 的逐车 class/age/depot/propulsion 名册；171 与 206 之间没有共同的 2023 point-in-time count。
- GTFS 中没有 vehicle ID、garage、charger、destination pull-in/pull-out，也没有逐 block 的 deadhead 和停车/换乘时间；57/101 只能称 duty proxy。
- 没有 Vancouver 的纯电 Enviro500EV 全电冬季、满载、坡道、制动和 SOC 实测；`1.79/1.80/1.60` 是模型代理。
- 没有 20-passenger shuttle 的 Vancouver 冬季实测；Endera 的 16+2、LionM 的延期和 Calgary 的取消都说明供应商交付是实质风险。
- 没有双层车和接驳车候选的 GVW/轴重/座椅布局/轮椅位/电池重量公开组合；容量是否守恒不能只按 seat count 假定。
- 没有 depot 的 transformer、firm power、充电位占用、雨雪维护、BC Hydro 接入报价或施工工期；$500m/340 和 $46m/10 是规划 envelope，不是可加总的报价。
- 没有 2023 TransLink 双层或接驳车的 awarded EV tender、税后单价和实际交付/在役记录。Foothill 和 Calgary 是外部案例。

## 机器可读产出

- `data/processed/deck_shuttle_parameter_table.csv`：带 URL、页码/网页位置、来源年份、币种、2023 availability 与 status 的逐参数表。
- `data/processed/deck_shuttle_fleet_mapping.csv`：57 辆与 57 个 `cap85` block、171–206 辆与 101 个 `cap24` block 的对应边界。
- `data/processed/deck_shuttle_duty_screen_2023.csv`：57 + 101 个 duty 在三种半径下的 overnight status、短差能量和充电分钟。
- `data/processed/deck_shuttle_scenarios.csv`：三种情景的能耗、班次可行性、车辆/充电/资本 envelope。
- `results/deck_shuttle_electrification_audit.json`：执行结果、判断和不可验证项。
- 复现：`python src/audit_deck_shuttle_electrification.py`。
