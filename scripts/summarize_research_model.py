"""Publish the computed outputs without manually transcribing scores."""
from pathlib import Path
import json
import sys
import hashlib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/research_model'
LABELS={'central':'全新设施／中央冬季','slow_charge':'半功率慢充','winter_stress':'恶劣冬季',
        'capacity_stress':'未知容量按85人','central_retrofit':'混合改造／年电量80%',
        'central_high_cost':'较高设施、司机及维修成本'}


def common_trolley(driver_rate=60.):
    """Common-activity denominator bridge; leaves fleet rankings unchanged."""
    sys.path.insert(0,str(ROOT/'src'))
    from price_index import to_2023
    mf=pd.read_csv(ROOT/'data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv',
                   dtype={'trip_id':str,'service_id':str,'block_id':str},low_memory=False)
    mf=mf[mf.proxy_class.isin(['cap47','cap70'])]
    daily=pd.read_csv(ROOT/'data/processed/vancouver_gtfs_daily_service_2023.csv')
    counts=daily.pattern_id.value_counts()
    patterns=json.loads((ROOT/'results/vancouver_gtfs_baseline_audit.json').read_text())['unique_service_patterns']
    km=hours=0.
    for p in patterns:
        g=mf[mf.service_id.isin(p['active_service_ids'])]
        span=g.groupby('block_id').agg(start=('start_seconds','min'),end=('end_seconds','max'))
        km+=g.distance_km_upper.sum()*counts[p['pattern_id']]
        hours+=(span.end-span.start).sum()/3600*counts[p['pattern_id']]
    km*=365/len(daily)*1.10  # explicit common deadhead allowance
    hours*=365/len(daily)*1.05
    comp=json.loads((ROOT/'results/vancouver_full_fleet_bound.json').read_text())['central_result']['components_pv_cad']
    capital=comp['common_trolley_replacement_capex']+comp['common_trolley_replacement_residual']
    annuity=sum(1/1.03**i for i in range(1,11))
    cost=capital+(km*to_2023(4.12,2024)+hours*driver_rate)*annuity
    # 189 standard + 73 articulated common trolley acquisitions; proxy masses.
    production=(189*12000+73*18000)*6.6/1000
    ghg=production+10*km*(2.0*.0113+.0675)/1000
    return dict(common_pv_cad=cost,common_ghg_t=ghg,common_net_capital_pv_cad=capital,
                annual_km=km,annual_driver_hours=hours,
                assumptions='Existing timetable normal; 10% extra km, 5% extra block-span hours; 2 kWh/km; 12/18t glider proxies. These are common to both fleets.',
                sources='2023 GTFS; 2024 ZEFTP trolley O&M 4.12 CAD/km rebased; existing 262-trolley renewal and terminal-value ledger.')


def main():
    comparisons=[]
    frames=[]
    trolley_bridges={}
    for name,label in LABELS.items():
        t=json.loads((OUT/f'{name}_transition.json').read_text())
        schedule=json.loads((OUT/t['source_schedule']).read_text())
        e=schedule['outputs']['electric']
        ps=e['packages']
        common=common_trolley(t['parameter_overrides'].get('driver_rate',60.))
        trolley_bridges[name]=common
        for r in t['results']:
            points=[s for s in r['solutions'] if 'plan_pv_cad' in s]
            if not points:
                raise ValueError(f'{name}: no feasible master solution')
            cheapest=min(points,key=lambda x:x['plan_pv_cad'])
            lowest_carbon=min(points,key=lambda x:x['plan_ghg_t'])
            comparisons.append(dict(scenario=name,label=label,fuel_case=r['fuel_case'],
                beb_fleet=e['fleet_with_spares'],with_retained_trolleys=e['fleet_with_spares']+275,
                baseline_non_trolley_fleet=schedule['outputs']['baseline']['fleet_with_spares'],
                active_buses=e['active_buses'],required_firm_power_mw=sum(p['required_power_kw'] for p in ps)/1000,
                annual_grid_gwh=sum(p['annual_grid_kwh'] for p in ps)/1e6*t['parameter_overrides'].get('annual_energy_multiplier',1),
                annual_revenue_km=sum(p['annual_revenue_km'] for p in ps),
                annual_deadhead_km=sum(p['annual_deadhead_km'] for p in ps),
                minimum_plan_pv_billion=cheapest['plan_pv_cad']/1e9,
                baseline_pv_billion=cheapest['baseline_pv_cad']/1e9,
                min_cost_economic_pct=cheapest['economic_score_pct'],
                whole_fleet_baseline_pv_billion=(cheapest['baseline_pv_cad']+common['common_pv_cad'])/1e9,
                whole_fleet_plan_pv_billion=(cheapest['plan_pv_cad']+common['common_pv_cad'])/1e9,
                whole_fleet_economic_pct=100*(cheapest['baseline_pv_cad']-cheapest['plan_pv_cad'])/(cheapest['baseline_pv_cad']+common['common_pv_cad']),
                whole_fleet_environmental_pct=100*(cheapest['baseline_ghg_t']-cheapest['plan_ghg_t'])/(cheapest['baseline_ghg_t']+common['common_ghg_t']),
                min_cost_environmental_pct=cheapest['environmental_score_pct'],
                best_environmental_pct=lowest_carbon['environmental_score_pct'],
                min_cost_grant_50_economic_pct=cheapest['grants'][-1]['economic_score_pct'],
                sampled_points=len(points),max_mip_gap=max(s['mip_gap'] for s in points)))
            for s in points:
                frames.append(dict(scenario=name,fuel_case=r['fuel_case'],pv_billion=s['plan_pv_cad']/1e9,
                                   ghg_million_t=s['plan_ghg_t']/1e6,weight=s['weight']))
    table=pd.DataFrame(comparisons)
    (OUT/'common_trolley_denominator_bridge.json').write_text(json.dumps(trolley_bridges,indent=2)+'\n',encoding='utf-8')
    table.to_csv(OUT/'comparison.csv',index=False,encoding='utf-8-sig')
    point_table=pd.DataFrame(frames)
    point_table.to_csv(OUT/'tradeoff_points.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4.4))
    for ax,fuel in zip(axes,['renewable_mix','fossil_diesel']):
        for name in ['central','slow_charge','winter_stress','central_retrofit']:
            g=point_table[(point_table.scenario==name)&(point_table.fuel_case==fuel)].sort_values('pv_billion')
            ax.plot(g.pv_billion,g.ghg_million_t,'o-',label=name,markersize=3)
        ax.set(xlabel='2023 CAD billion (discounted)',ylabel='2024-2033 emissions (million t CO2e)',
               title=fuel.replace('_',' '))
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.suptitle('Conditional schedules: sampled cost-carbon trade-offs',fontsize=12)
    fig.tight_layout();fig.savefig(OUT/'cost_carbon_tradeoffs.png',dpi=180);plt.close(fig)
    text=['# 全城条件研究模型：计算结果（2026-10-21）','',
          '**本次已经执行排班、充电、年度采购和双评分计算。数值是程序实际运行输出，适用范围为列明假设下的研究方案。**','',
          '相比旧稿，新增了全部非无轨班次的车辆分配、回库及充电、119日周期边界检查，以及与这些车辆数量相连的年度整数优化。',
          '排班给出可行构造上界；年度优化只在固定场站和车型包内求解至所记录的求解器容差。','',
          '## 主要计算结果','',
          '下表经济分母含司机、维修、能源、更新和对称期末资产价值；不变的无轨公共项剔除。环境主表使用低碳燃料基准0.302 kgCO2e/km，计车辆与设施制造。','',
          '| 情景 | BEB含备用 | 加275无轨后 | 所需供电MW | 最低成本十亿CAD | 经济分% | 该方案环境分% | 抽样最佳环境分% |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:
        if r['fuel_case']=='renewable_mix':
            text.append(f"| {r['label']} | {r['beb_fleet']} | {r['with_retained_trolleys']} | {r['required_firm_power_mw']:.2f} | {r['minimum_plan_pv_billion']:.3f} | {r['min_cost_economic_pct']:.2f} | {r['min_cost_environmental_pct']:.2f} | {r['best_environmental_pct']:.2f} |")
    text += ['', '负分表示相对于同一服务需求的基准，成本或十年期累计排放更高。650辆/年的采购能力、2030—2033投运是研究设定。',
             '设施供电列是各车型充电峰值之和，构成足够供电的保守要求；不是同时全系统实测峰值，也不是电网已批准容量。',
             '全新设施情景按Marpole单位包价全部重建。改造情景用50%设施成本、30%建筑隐含碳、80%年度电量，均为待检验假设，不能当作已证实的节约。','',
             '### 补回无轨公共项后的全车队分数','',
             '另用原无轨班次、262辆共同更新、公开4.12 CAD/km运维费，并假设10%额外里程、5%出入场工时、2 kWh/km与12/18吨车体，补回两边的相同分母。这些共同项不改变方案的成本差和排放差。',
             '全车队分数仍是条件结果，避免把剔除公共项的百分数冒充全车队百分数。','',
             '| 情景 | 全车队基准十亿CAD | 全车队方案十亿CAD | 经济分% | 环境分% |',
             '|---|---:|---:|---:|---:|']
    for r in comparisons:
        if r['fuel_case']=='renewable_mix':
            text.append(f"| {r['label']} | {r['whole_fleet_baseline_pv_billion']:.3f} | {r['whole_fleet_plan_pv_billion']:.3f} | {r['whole_fleet_economic_pct']:.2f} | {r['whole_fleet_environmental_pct']:.2f} |")
    text += ['',
             '## 为什么与旧分数不同','',
             '- 购车数由逐班排班及完整充电后再利用导出，未继续使用旧的固定替换比例。',
             '- 两边使用同一套公开班次、路线容量代理和场站模型；新增空驶及完整任务司机工时进入成本。',
             '- 接驳车五年寿命会产生电动化投运前的常规更新；年份上先退役、全年服务、再增加车龄。',
             '- 保留无轨运营，先假设既有架空线可以正常执行原服务；不把内部馈线资料缺失视为禁止研究的条件。',
             '- 建设及制造碳在2024—2033发生，但晚投运只获得少数年份的运营减排，因此十年环境分可能为负。','',
             '## 可再现与验收','',
             '入口：`python scripts/run_research_model.py`；结果汇总：`python scripts/summarize_research_model.py`。',
             '每个模式、每个非无轨班次恰好一次；车辆容量代理、路程时间、回库能耗、SOC储备、补足电量、专用充电口、周期首尾冲突均检查。',
             '年度检查包括库存守恒、备用车、六年建设先行、年度交付限额，以及2033常规库存为零。',
             f"保留全部实际最优间隙，最大为 {max(r['max_mip_gap'] for r in comparisons):.9f}（相对值）；不能称全部零间隙。",
             '各模式保留原始班次ID，119日运行台账保存了每个任务的车辆、出库、回库和完成充电时刻。','',
             '## 还不能声称什么','',
             '道路路径用球面距离乘路程系数；区域场站坐标是规划锚点，24人电接驳等配置是采购要求。缺少实际地块、电网许可及载荷认证不会阻塞本研究运算，但会影响现实落地。',
             '119日服务周期不等于全年历史时刻表。未分类容量另用85人压力情景检验；主情景标准车假设仍须披露。',
             '环境边界尚无本地车辆拆解清单；设施和部分车体生产用外部代理，故称十年期环境情景，不称完整本地生命周期实测结果。',
             '当前没有求解充电延迟控制、场站选址或车型任意混搭的全局最优；后续可降低这里给出的保守可行上界。','',
             '详细来源与假设：[研究假设说明](research_assumptions_2026_10_21.md)。机器可读参数、每个解的逐年账本和图表见 `results/research_model/`。']
    (ROOT/'materials/research/research_model_results_2026_10_21.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(table[table.fuel_case=='renewable_mix'].to_json(orient='records',force_ascii=False,indent=2))


if __name__=='__main__':
    main()
