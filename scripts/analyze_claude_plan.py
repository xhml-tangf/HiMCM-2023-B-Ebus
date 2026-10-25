"""Build downstream ledgers, evidence-bounded three-city transfer, and figures."""
from pathlib import Path
import sys,json,math
from dataclasses import replace
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.claude_impacts import Parameters,evaluate_impacts,parameter_ledger
from src.optimize_london_cohorts import solve as solve_london
from src.build_threecity_execution_v3 import solve_cta_conversion_schedule,load_cta_age_cohorts
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/claude_plan'


def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def main():
    p=Parameters();main=read('vancouver_main.json');pat=read('patterns.json')['patterns']
    for city in ['chicago','london']:
        path=OUT/city/'main.json'
        if path.exists():
            mcity=read(f'{city}/main.json');dcity=read(f'{city}/days.json')['days']
            for row in [mcity,*dcity]:
                row.setdefault('method','bounded successor graph; resource-correct feasible upper bound')
                row['gap_vs_diesel_pct']=100*(row['vehicles']-row['N_d'])/row['N_d']
                row.setdefault('daytime_grid_kwh',row['daytime_replenished_range_km']*p.epsilon/p.efficiency)
                row.setdefault('overnight_grid_kwh',row['overnight_replenished_range_km']*p.epsilon/p.efficiency)
            save(f'{city}/main.json',mcity);save(f'{city}/days.json',dict(days=dcity))
            if (OUT/city/'roadmap.json').exists():
                road_city=read(f'{city}/roadmap.json')
                for row in road_city['annual']:
                    row.setdefault('method','bounded successor graph; resource-correct feasible upper bound')
                    row.setdefault('daytime_grid_kwh',row['daytime_replenished_range_km']*p.epsilon/p.efficiency)
                    row.setdefault('overnight_grid_kwh',row['overnight_replenished_range_km']*p.epsilon/p.efficiency)
                save(f'{city}/roadmap.json',road_city)
    days=sum(r['occurrence_days'] for r in pat)
    annual=lambda key:sum(r[key]*r['occurrence_days'] for r in pat)*365/days
    Dd=annual('service_km')+annual('diesel_deadhead_km')
    De=annual('service_km')+annual('deadhead_km')
    Nd=max(r['N_d'] for r in pat);Ne=max(r['vehicles'] for r in pat)
    all_nodes=set().union(*(r['charger_peak_by_node'].keys() for r in pat))
    peaks={c:max(r['charger_peak_by_node'].get(c,0) for r in pat) for c in all_nodes}
    args=dict(Nd=Nd,Ne=Ne,Dd=Dd,De=De,stations=len(main['stations']),plugs=sum(peaks.values()))
    central=evaluate_impacts(**args,p=p)
    sensitivity=[]
    changes={'grid':[0.,.2,.5],'epsilon':[1.37,2.0],'electricity':[.06,.20],
             'diesel_price':[1.2,2.2],'battery_price':[100.,300.],
             'battery_decline':[0.,.06],'discount':[0.,.07],'vehicle_life':[15,17],
             'battery_life':[6,12],'diesel_ghg':[.302,.53],
             'overnight_per_bus':[50000.,300000.],'site_fixed':[300000.,1200000.]}
    for key,values in changes.items():
        for v in values:
            result=evaluate_impacts(**args,p=replace(p,**{key:v}))
            sensitivity.append(dict(parameter=key,value=v,NPV25=result['grants'][1]['NPV'],
                                    avoided_t=result['ten_year_avoided_t'],phi_star=result['phi_star']))
    # Range/time sensitivities use newly solved schedules, not frozen fleet counts.
    for r in read('sensitivity.json')['range_time']:
        factor=365
        result=evaluate_impacts(main['N_d'],r['vehicles'],
                   (main['service_km']+main['diesel_deadhead_km'])*factor,
                   (r['service_km']+r['deadhead_km'])*factor,len(main['stations']),
                   sum(r['charger_peak_by_node'].values()),replace(p,R=r['R'],T=r['T']))
        sensitivity.append(dict(parameter='schedule_R_T',R=r['R'],T=r['T'],
                                 NPV25=result['grants'][1]['NPV'],avoided_t=result['ten_year_avoided_t'],
                                 scope='representative day x365, not pattern-weighted central case'))
    air=pd.read_csv(ROOT/'data/processed/transit_air_quality_factors_2023.csv')
    pollution=[]
    for pollutant in ['NOx','PM2.5']:
        factors=air[(air.fuel=='diesel')&(air.pollutant==pollutant)].g_per_km
        pollution.append(dict(pollutant=pollutant,annual_avoided_t_low=Dd*factors.min()/1e6,
                              annual_avoided_t_high=Dd*factors.max()/1e6,
                              ten_year_avoided_t_low=Dd*factors.min()*10/1e6,
                              ten_year_avoided_t_high=Dd*factors.max()*10/1e6,
                              note='Transferred tailpipe factors; no non-exhaust benefit claimed.'))
    annual_charge=annual('daytime_replenished_range_km')*p.epsilon/p.efficiency
    annual_night=annual('overnight_replenished_range_km')*p.epsilon/p.efficiency
    assert abs(annual_charge+annual_night-central['annual_grid_kwh'])<1e-5
    strict=evaluate_impacts(**args,p=replace(p,grid=0.))
    conservative=evaluate_impacts(**{**args,'Dd':annual('service_km')},p=p)
    negative=evaluate_impacts(**args,p=replace(p,grid=.8,diesel_ghg=.302))
    grid_cases=[dict(rate=r,result=evaluate_impacts(**args,p=p,grid_decline=r)) for r in (0.,.03,.05)]
    save('impacts.json',dict(parameters=parameter_ledger(p),central=central,strict_zero_source_scenario=strict,
         zero_diesel_deadhead_cost_lower_bound=conservative,
         joint_grid_and_lowcarbon_fuel_stress=negative,grid_decline_cases=grid_cases,sensitivity=sensitivity,pollution=pollution,
         annualization='Observed 119-day fall pattern frequencies multiplied by 365/119; extrapolation, not annual observed mileage.',
         annual_service_km=annual('service_km'),daytime_grid_kwh=annual_charge,overnight_grid_kwh=annual_night,
         peaks=peaks,night_power_lower_bound_kw=annual_night/365/8,
         night_boundary='8-hour aggregate energy screen only; individual next-day turnaround is not certified.'))
    site_costs={}
    for city,path in [('vancouver','vancouver_main.json'),('chicago','chicago/main.json'),('london','london/main.json')]:
        if not (OUT/path).exists():continue
        mm=read(path)
        points=[dict(K=r['K'],trace_buses=r['N'],bus_cost=r['N']*p.bus_price,
            fixed_site_cost=r['K']*p.site_fixed,total=r['N']*p.bus_price+r['K']*p.site_fixed) for r in mm['trace']]
        site_costs[city]=dict(points=points,recommended=min(points,key=lambda x:(x['total'],x['K'])))
    save('site_cost_screen.json',dict(cases=site_costs,
         boundary='Bus list price plus fixed site allowance only; charger power, grid connection, land, maintenance and overnight depot are excluded. Uses the heuristic trace, so this is not a globally optimal cost solution.'))
    road=read('roadmap_schedule.json')
    budget=[];cum_ghg=0.;cum_capex=0.;previous_d=main['N_d'];cum_cash={0.:0.,.25:0.,.5:0.}
    for r in road['annual']:
        y=r['year'];t=y-2024
        battery_price=p.battery_price*(1-p.battery_decline)**t
        buses=r['new_buses']*(p.body_price+p.B*battery_price)
        infra=(central['infrastructure'] if t==0 else 0.)
        prior=next((x for x in budget if x['year']==y-p.battery_life),None)
        replacements=(prior['new_buses']*p.B*battery_price if prior else 0.)
        replacement_ghg=(prior['new_buses']*p.B*p.battery_ghg/1000 if prior else 0.)
        cap=buses+infra+replacements
        replaced=max(0,previous_d-r['remaining_diesel']);previous_d=r['remaining_diesel']
        eligible=max(0,cap-replaced*p.diesel_bus_price)
        # Same service fraction, with separately computed electric detours.
        electric_km=(r['service_km']+r['deadhead_km'])*365
        displaced_diesel_km=r['service_km']*365 # excludes unknown retired-route diesel detours
        operating_avoided=(displaced_diesel_km*p.diesel_ghg-electric_km*p.epsilon/p.efficiency*p.grid)/1000
        embodied=r['new_buses']*(p.body_ghg_t+p.B*p.battery_ghg/1000)
        cum_ghg+=operating_avoided-embodied-replacement_ghg;cum_capex+=cap
        grid_kwh=electric_km*p.epsilon/p.efficiency
        diesel_op_avoided=displaced_diesel_km*(p.litres_km*p.diesel_price+p.diesel_maintenance)
        electric_op=grid_kwh*p.electricity+electric_km*p.electric_maintenance+infra*p.station_maintenance_fraction
        op_saving=diesel_op_avoided-electric_op
        diesel_purchase_avoided=replaced*p.diesel_bus_price
        cash={phi:op_saving+diesel_purchase_avoided-cap+phi*eligible for phi in (0.,.25,.5)}
        for phi in cum_cash:cum_cash[phi]+=cash[phi]
        budget.append(dict(year=y,route_count=len(r['routes']),new_buses=r['new_buses'],
                           electric_stock=r['purchased_stock'],active_electric=r['vehicles'],
                           diesel=r['remaining_diesel'],stations=len(main['stations']),
                           gross_investment=cap,battery_replacement=replacements,grant_eligible_increment=eligible,
                           grant25=.25*eligible,grant50=.5*eligible,
                           self_funded50=cap-.5*eligible,cumulative_investment=cum_capex,
                           grid_kwh=grid_kwh,diesel_operating_avoided=diesel_op_avoided,electric_operating_cost=electric_op,
                           operating_saving=op_saving,diesel_purchase_avoided=diesel_purchase_avoided,
                           net_cash_grant0=cash[0.],net_cash_grant25=cash[.25],net_cash_grant50=cash[.5],
                           cumulative_cash_grant0=cum_cash[0.],cumulative_cash_grant25=cum_cash[.25],cumulative_cash_grant50=cum_cash[.5],
                           cumulative_partial_avoided_t=cum_ghg))
    # The endpoint stock is increased if another pattern needs more than the roadmap's representative day.
    extra=max(0,Ne-budget[-1]['electric_stock'])
    if extra:
        increment=extra*(p.body_price+p.B*p.battery_price*(1-p.battery_decline)**9)
        last=budget[-1]
        last['new_buses']+=extra;last['electric_stock']+=extra
        for key in ['gross_investment','grant_eligible_increment','cumulative_investment']:last[key]+=increment
        last['grant25']+=.25*increment;last['grant50']+=.5*increment;last['self_funded50']+=.5*increment
        for phi in cum_cash:
            adjustment=-increment+phi*increment
            cum_cash[phi]+=adjustment
            last[f'net_cash_grant{int(phi*100)}']+=adjustment
            last[f'cumulative_cash_grant{int(phi*100)}']=cum_cash[phi]
        last['cumulative_partial_avoided_t']-=extra*(p.body_ghg_t+p.B*p.battery_ghg/1000)
    save('roadmap_budget.json',dict(annual=budget,endpoint_extra_buses=extra,
         scope='Required-budget illustration; no hard budget or construction commissioning certificate. Infrastructure funded at start. Intermediate years validated on representative day.',
         ghg_boundary='Partial staged operating-minus-new-production ledger, not the full replacement LCA; no old-fleet manufacture credit or unknown diesel detours.'))
    cta=solve_cta_conversion_schedule(load_cta_age_cohorts(),17)
    london=[solve_london(life) for life in (12,14,17)]
    comparators=dict(chicago=dict(fleet=1875,initial_electric=25,initial_electric_status='June2023 inferred, not Dec31 propulsion register',
          schedule_status='MISSING_TRIP_TIMETABLE',Nd=None,Ne=None,stations=None,cohort=cta),
          london=dict(fleet=8643,initial_electric=950,schedule_status='MISSING_TRIP_TIMETABLE',
          Nd=None,Ne=None,stations=None,cohort_scenarios=london),
          transfer_boundary='Cohort stock renewal and trip scheduling are separate boundaries; common-CAD transferred impacts are not local forecasts.')
    for city in ['chicago','london']:
        if (OUT/city/'main.json').exists():
            m=read(f'{city}/main.json')
            comparators[city].update(schedule_status='REAL_GTFS_CONDITIONAL_SCHEDULE',Nd=m['N_d'],Ne=m['vehicles'],stations=m['stations'],date=m['date'],
                                      operational_result=f'{city}/main.json',scope=m['source_manifest']['scope'])
    save('comparators.json',comparators)
    pd.DataFrame(budget).to_csv(OUT/'roadmap_budget.csv',index=False)
    pd.DataFrame(pat).drop(columns=['charger_peak_by_node']).to_csv(OUT/'service_patterns.csv',index=False)
    figures(main,pat,central,sensitivity,budget)
    if all((OUT/city/'sensitivity.json').exists() for city in ['chicago','london']):
        fig,axs=plt.subplots(2,2,figsize=(10,5.0),layout='constrained')
        for ax,city in zip(axs[0],['chicago','london']):
            heat=pd.DataFrame(read(f'{city}/sensitivity.json')['cases']).pivot(index='R',columns='T',values='vehicles')
            ax.imshow(heat,aspect='auto',cmap='YlGnBu')
            ax.set_xticks(range(len(heat.columns)),[int(v) for v in heat.columns]);ax.set_yticks(range(len(heat.index)),[int(v) for v in heat.index])
            ax.set(xlabel='Full-charge time (min)',ylabel='Usable range (km)',title=city.title()+' fixed-site fleet')
            threshold=heat.values.min()+.55*(heat.values.max()-heat.values.min())
            for i in range(len(heat.index)):
                for j in range(len(heat.columns)):ax.text(j,i,str(heat.iloc[i,j]),ha='center',va='center',color='white' if heat.iloc[i,j]>threshold else 'black')
        for ax,city in zip(axs[1],['chicago','london']):
            m=read(f'{city}/main.json');tr=m['trace']
            ax.plot([r['K'] for r in tr],[r['N'] for r in tr],'o-',color='#267c99',label='Greedy additions')
            ax.scatter([len(m['stations'])],[m['vehicles']],color='#b84c40',zorder=3,label='Final charging-aware')
            ax.axhline(m['N_d'],ls='--',color='gray',label='Exact diesel')
            ax.set(xlabel='Daytime candidate nodes K',ylabel='Buses',title=city.title()+' station search')
            ax.legend(fontsize=7)
        fig.savefig(OUT/'comparator_sensitivity.png');plt.close(fig)
    if all((OUT/city/'impacts.json').exists() for city in ['chicago','london']):
        rows=[dict(city='Vancouver',date=main['date'],trips=main['trips'],PVR=main['PVR'],Nd=Nd,Ne=Ne,
                   gap_pct=100*(Ne-Nd)/Nd,stations=len(main['stations']),service_km=main['service_km'],
                   daytime_charges=main['daytime_charge_count'],npv0=central['grants'][0]['NPV'],
                   npv25=central['grants'][1]['NPV'],npv50=central['grants'][2]['NPV'])]
        for city in ['chicago','london']:
            m=read(f'{city}/main.json');im=read(f'{city}/impacts.json')['standardized_transfer']
            rows.append(dict(city=city.title(),date=m['date'],trips=m['trips'],PVR=m['PVR'],Nd=m['N_d'],Ne=m['vehicles'],
                gap_pct=100*(m['vehicles']-m['N_d'])/m['N_d'],stations=len(m['stations']),service_km=m['service_km'],
                daytime_charges=m['daytime_charge_count'],npv0=im['grants'][0]['NPV'],npv25=im['grants'][1]['NPV'],npv50=im['grants'][2]['NPV']))
        save('threecity_summary.json',dict(cases=rows,boundary='Representative days; comparator financial and energy values use the common Vancouver screening parameters, not local forecasts.'))
        fig,axs=plt.subplots(1,2,figsize=(10,3.2),layout='constrained')
        names=[r['city'] for r in rows];xx=np.arange(len(rows));width=.36
        axs[0].bar(xx-width/2,[r['Nd'] for r in rows],width,label='Diesel lower bound')
        axs[0].bar(xx+width/2,[r['Ne'] for r in rows],width,label='Feasible electric')
        axs[0].set_xticks(xx,names);axs[0].set(ylabel='Active buses',title='Representative-day fleet');axs[0].legend(fontsize=8)
        axs[1].bar(xx,[r['npv25']/1e6 for r in rows],color=['#267c99','#8a6a3e','#537a45'])
        axs[1].axhline(0,color='black',lw=.7);axs[1].set_xticks(xx,names);axs[1].set(ylabel='CAD million',title='Common-parameter 25% grant NPV')
        fig.savefig(OUT/'threecity_comparison.png');plt.close(fig)
    print(json.dumps(dict(Nd=Nd,Ne=Ne,NPV=[g['NPV'] for g in central['grants']],
                          phi_star=central['phi_star'],avoided_t=central['ten_year_avoided_t']),indent=2))


def figures(main,pat,central,sensitivity,budget):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    fig,axs=plt.subplots(1,2,figsize=(10,3.3),layout='constrained')
    data=pd.DataFrame(read('sensitivity.json')['range_time'])
    heat=data.pivot(index='R',columns='T',values='vehicles')
    im=axs[0].imshow(heat,aspect='auto',cmap='YlGnBu')
    axs[0].set_xticks(range(len(heat.columns)),[int(x) for x in heat.columns]);axs[0].set_yticks(range(len(heat.index)),[int(x) for x in heat.index])
    axs[0].set(xlabel='Full-charge time (min)',ylabel='Usable range (km)',title='Feasible electric fleet, fixed selected sites')
    threshold=float(heat.values.min()+.55*(heat.values.max()-heat.values.min()))
    for i in range(len(heat.index)):
        for j in range(len(heat.columns)):
            axs[0].text(j,i,str(heat.iloc[i,j]),ha='center',va='center',
                        color='white' if heat.iloc[i,j]>threshold else 'black')
    tr=main['trace'];axs[1].plot([r['K'] for r in tr],[r['N'] for r in tr],'o-',label='Greedy additions')
    axs[1].axhline(main['N_d'],ls='--',color='gray',label='Exact diesel lower bound')
    axs[1].set(xlabel='Daytime sites K',ylabel='Buses',title='Station search trace');axs[1].legend(fontsize=8)
    fig.savefig(OUT/'fleet_sensitivity.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
    for g in central['grants']:
        axs[0].plot([r['t'] for r in g['cashflow']],[r['cumulative']/1e6 for r in g['cashflow']],label=f"{g['phi']:.0%} grant")
    axs[0].axhline(0,color='gray',lw=.8);axs[0].set(xlabel='Years since replacement',ylabel='Cumulative savings (CAD million)',title='Cash flow, including terminal assets');axs[0].legend()
    axs[1].plot([r['year'] for r in central['annual']],[r['cumulative_avoided_t']/1000 for r in central['annual']],'o-',label='Fossil-diesel counterfactual')
    axs[1].set(xlabel='Year',ylabel='Cumulative avoided kt CO2e',title='Operating + vehicle production boundary');axs[1].legend(fontsize=8)
    fig.savefig(OUT/'environment_finance.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
    axs[0].plot([r['year'] for r in budget],[r['electric_stock'] for r in budget],'o-',label='Purchased electric stock')
    axs[0].plot([r['year'] for r in budget],[r['diesel'] for r in budget],'o-',label='Representative-day diesel requirement')
    axs[0].set(xlabel='Year',ylabel='Buses',title='Nested-route transition');axs[0].legend(fontsize=8)
    axs[1].bar([r['year'] for r in budget],[r['self_funded50']/1e6 for r in budget],label='Agency funding')
    axs[1].bar([r['year'] for r in budget],[r['grant50']/1e6 for r in budget],bottom=[r['self_funded50']/1e6 for r in budget],label='50% eligible-increment grant')
    axs[1].set(xlabel='Year',ylabel='CAD million',title='Required annual investment');axs[1].legend(fontsize=8)
    fig.savefig(OUT/'roadmap.png');plt.close(fig)
    cases=[r for r in sensitivity if r['parameter']!='schedule_R_T']
    df=pd.DataFrame(cases);base=central['grants'][1]['NPV']/1e6
    fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
    groups=list(df.groupby('parameter'))
    for i,(name,g) in enumerate(groups):
        ax.plot([g.NPV25.min()/1e6,g.NPV25.max()/1e6],[i,i],lw=7,color='#267c99')
    ax.set_yticks(range(len(groups)),[x[0].replace('_',' ') for x in groups]);ax.axvline(base,ls='--',color='black')
    ax.set(xlabel='25%-grant NPV (CAD million)',title='One-at-a-time financial sensitivity')
    fig.savefig(OUT/'tornado.png');plt.close(fig)


if __name__=='__main__':main()
