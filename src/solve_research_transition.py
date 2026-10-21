"""Annual procurement MILP fed by the executed conditional dispatch schedules.

Each depot/body package changes propulsion in one selected year, 2030--33.
The MIP searches only these fixed scheduling packages and commissioning
choices, to the reported floating-point solver tolerance. No claim of global
routing/infrastructure optimality is made.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
try:
    from .price_catalog import price
    from .price_index import to_2023
    from .solve_research_schedule import TECH, OUT, ROOT
except ImportError:
    from price_catalog import price
    from price_index import to_2023
    from solve_research_schedule import TECH, OUT, ROOT

YEARS = list(range(2024,2034))
SCALE = {'standard':1.,'articulated':1.5,'deck':1.,'shuttle':.55}
GLIDER = {'standard':14880.,'articulated':20000.,'deck':18000.,'shuttle':4500.}
CONVENTIONAL_GLIDER = {'standard':11429.,'articulated':16000.,'deck':14000.,'shuttle':4000.}
FUEL = {'renewable_mix':.302,'weighted_mix':1.233,'fossil_diesel':1.58}


def pv(annual):
    return sum(r['cost_cad'] / 1.03**(r['year']-2023) for r in annual)


def allocate(n, weights):
    w=np.array(weights,float)
    target=n*w/w.sum()
    counts=np.floor(target).astype(int)
    for i in np.argsort(-(target-counts),kind='stable')[:n-int(counts.sum())]:
        counts[i]+=1
    assert counts.sum()==n
    return counts.tolist()


def prepare(schedule):
    base={(p['site'],p['vehicle_class']):p for p in schedule['outputs']['baseline']['packages']}
    packages=[]
    for p in schedule['outputs']['electric']['packages']:
        packages.append({'site':p['site'],'cls':p['vehicle_class'],'ev':p,'base':base[(p['site'],p['vehicle_class'])]})
    heavy=[p for p in packages if p['cls'] in ('standard','articulated')]
    heavy_counts=allocate(1204,[p['base']['fleet_with_spares'] for p in heavy])
    for p,n in zip(heavy,heavy_counts):
        p['initial']=n
    for cls,total in (('deck',57),('shuttle',189)):
        group=[p for p in packages if p['cls']==cls]
        for p,n in zip(group,allocate(total,[p['base']['fleet_with_spares'] for p in group])):
            p['initial']=n
    assert sum(p['initial'] for p in packages)==1450
    for p in packages:
        p['baseline_fleet']=max(p['initial'],p['base']['fleet_with_spares'])
        p['existing_beb']=5 if (p['site'],p['cls'])==('Vancouver','standard') else 0
    assert sum(p['existing_beb'] for p in packages)==5
    return packages


def prices(cls):
    # Hardware and class transfer assumptions; source years already rebased.
    ds=pd.read_csv(ROOT/'data/processed/deck_shuttle_scenarios.csv')
    def dsprice(name):
        return float(ds[(ds.asset_class==name)&(ds.scenario=='central')].iloc[0].vehicle_unit_cost_cad_low)
    ev={'standard':price('hardware'),'articulated':1.5*price('hardware'),
        'deck':dsprice('double_deck'),'shuttle':dsprice('community_shuttle')}
    conv={'standard':price('baseline_cng'),'articulated':1.5*price('baseline_cng'),
          'deck':1_000_000.,'shuttle':price('baseline_shuttle')}
    return ev[cls],conv[cls]


def stock_for(p):
    cls=p['cls']
    unit,conv=prices(cls)
    life=5 if cls=='shuttle' else 17
    n=p['initial']-p['existing_beb']
    # Deck acquisitions 2019--2023; other ages uniform synthetic cohorts.
    age_span=5 if cls=='deck' else life
    stock=[dict(age=1+int(i*age_span/max(1,n)),life=life,value=conv,electric=False,
                purchased_in_horizon=False) for i in range(n)]
    stock += [dict(age=1,life=17,value=unit,electric=True,purchased_in_horizon=False)
              for _ in range(p['existing_beb'])]
    return stock


def manufacture(cls,electric):
    mass=GLIDER[cls] if electric else CONVENTIONAL_GLIDER[cls]
    # GLIDER explicitly excludes battery; battery production is counted once.
    return (6.6*mass+(58*TECH[cls][1] if electric else 0))/1000


def ledger(p, conversion, fuel, infra_multiplier=1., infra_carbon_multiplier=1.,
           grid=.0113, driver_rate=60., baseline_om=None,
           electric_maintenance=None, resale=.25, annual_energy_multiplier=1.):
    """Matched baseline and electric cash/GHG, including bridge renewals.

    Infrastructure uses ONE all-in Marpole-style per-position envelope. There
    is no separate charger/connection capex added to that financial envelope.
    """
    cls=p['cls']
    unit,conv=prices(cls)
    life=5 if cls=='shuttle' else 17
    evlife=8 if cls=='shuttle' else 17
    stock=stock_for(p)
    ev=p['ev']; base=p['base']
    base_km=base['annual_revenue_km']+base['annual_deadhead_km']
    ev_km=ev['annual_revenue_km']+ev['annual_deadhead_km']
    om=price('om_cng') if baseline_om is None else baseline_om
    maintenance=to_2023(.8,2019) if electric_maintenance is None else electric_maintenance
    # Existing public fleet tariff snapshot, constant real rates through 2033.
    tariff=json.loads((ROOT/'data/processed/bchydro_2023_charging_tariffs.json').read_text())
    annual_energy=ev['annual_grid_kwh']*annual_energy_multiplier
    electricity=(annual_energy*.0614+12*ev['required_power_kw']*12.5+365*.2708)*.99
    site_cost=ev['fleet_with_spares']*SCALE[cls]*price('depot_per_bus')*infra_multiplier
    infra_t=ev['fleet_with_spares']*SCALE[cls]*(800000*.09290304/340)*.650*infra_carbon_multiplier
    infra_t+=ev['dedicated_ports']*6.40395
    rows=[]
    for y in YEARS:
        r=dict(year=y,site=p['site'],vehicle_class=cls,conversion_year=conversion,
               vehicle_capex_cad=0.,infrastructure_capex_cad=0.,sale_credit_cad=0.,
               terminal_credit_cad=0.,grant_eligible_net_cad=0.,
               acquired_conventional=0,acquired_electric=0,retired=0,
               vehicle_production_t=0.,infrastructure_t=0.)
        if conversion==y:
            r['retired']=len(stock)
            r['sale_credit_cad']=-resale*sum(a['value']*max(0,1-a['age']/a['life']) for a in stock)
            # Proportional recapture of grants on assets acquired in-horizon.
            funded_sale=-resale*sum(a['value']*max(0,1-a['age']/a['life']) for a in stock if a['purchased_in_horizon'])
            n=ev['fleet_with_spares']
            r['acquired_electric']=n
            r['vehicle_capex_cad']=n*unit
            r['grant_eligible_net_cad']+=n*unit+funded_sale
            r['vehicle_production_t']=n*manufacture(cls,True)
            stock=[dict(age=0,life=evlife,value=unit,electric=True,purchased_in_horizon=True) for _ in range(n)]
        else:
            need=p['baseline_fleet']-len(stock) if y==2024 else 0
            expired=[a for a in stock if a['age']>=a['life']]
            stock=[a for a in stock if a['age']<a['life']]
            r['retired']=len(expired)
            n=len(expired)+max(0,need)
            # No new electric cohort reaches life expiry by 2033 in this model.
            if n and conversion and y>conversion:
                raise ValueError('unexpected post-conversion expiry')
            r['acquired_conventional']=n
            r['vehicle_capex_cad']=n*conv
            r['grant_eligible_net_cad']+=n*conv
            r['vehicle_production_t']=n*manufacture(cls,False)
            stock += [dict(age=0,life=life,value=conv,electric=False,purchased_in_horizon=True) for _ in range(n)]
        if conversion and conversion-6<=y<conversion:
            r['infrastructure_capex_cad']=site_cost/6
            r['grant_eligible_net_cad']+=site_cost/6
            r['infrastructure_t']=infra_t/6
        converted=conversion is not None and y>=conversion
        if converted:
            # Maintenance excludes electricity; no addition of the all-in BEB O&M.
            r['maintenance_energy_cad']=ev_km*maintenance+electricity
            r['charger_maintenance_cad']=ev['annual_revenue_km']*to_2023(.04,2019)
            r['driver_cad']=ev['annual_driver_h']*driver_rate
            r['operating_t']=annual_energy*grid/1000+ev_km*.0675/1000
            r['electric_service_km']=ev['annual_revenue_km']
            r['required_power_kw']=ev['required_power_kw']
        else:
            share=p['existing_beb']/p['baseline_fleet']
            r['maintenance_energy_cad']=base_km*((1-share)*om+share*price('om_beb'))
            r['charger_maintenance_cad']=0.
            r['driver_cad']=base['annual_driver_h']*driver_rate
            r['operating_t']=base_km*((1-share)*fuel+share*.019+.0524)/1000
            r['electric_service_km']=base['annual_revenue_km']*share
            r['required_power_kw']=0.
        # Ages are completed years at the start of the year. Retire first,
        # serve the full year, then age. A five-year shuttle is not replaced
        # after only four service years.
        for a in stock:
            a['age']+=1
        if y==2033:
            residual=sum(a['value']*max(0,1-a['age']/a['life']) for a in stock)
            funded_residual=sum(a['value']*max(0,1-a['age']/a['life']) for a in stock if a['purchased_in_horizon'])
            infra_residual=site_cost*max(0,1-(2034-conversion)/30) if conversion else 0.
            r['terminal_credit_cad']=-residual-infra_residual
            r['grant_eligible_net_cad']-=funded_residual+infra_residual
        r['electric_stock']=sum(a['electric'] for a in stock)
        r['conventional_stock']=len(stock)-r['electric_stock']
        r['cost_cad']=sum(r[k] for k in ('vehicle_capex_cad','infrastructure_capex_cad','sale_credit_cad',
                                         'terminal_credit_cad','maintenance_energy_cad','charger_maintenance_cad','driver_cad'))
        r['ghg_t']=r['vehicle_production_t']+r['infrastructure_t']+r['operating_t']
        rows.append(r)
    return rows


def solve_options(cost, emissions, package_ids, annual_purchases, limit, weight, emission_limit=None):
    n=len(cost);packages=sorted(set(package_ids))
    matrix=[];low=[];high=[]
    for pid in packages:
        matrix.append([float(p==pid) for p in package_ids]);low.append(1);high.append(1)
    for yi in range(4):
        matrix.append([p[yi] for p in annual_purchases]);low.append(0);high.append(limit)
    if emission_limit is not None:
        matrix.append(emissions);low.append(-np.inf);high.append(emission_limit)
    objective=(1-weight)*np.array(cost)/1e9+weight*np.array(emissions)/1e6
    res=milp(objective,integrality=np.ones(n),bounds=Bounds(0,1),
             constraints=LinearConstraint(np.array(matrix),np.array(low),np.array(high)),
             options={'mip_rel_gap':1e-8,'time_limit':120})
    if not res.success:
        return dict(status='INFEASIBLE' if res.status==2 else 'NOT_SOLVED',message=res.message)
    selected=np.flatnonzero(res.x>.5).tolist()
    if any(sum(package_ids[i]==p for i in selected)!=1 for p in packages):
        raise ValueError('invalid package allocation')
    totals=np.array(annual_purchases)[selected].sum(axis=0)
    if np.any(totals>limit+1e-6):
        raise ValueError('procurement capacity violated')
    return dict(status='OPTIMAL_RESTRICTED_MASTER',selected=selected,
                mip_gap=float(res.mip_gap),annual_electric_purchases=totals.tolist())


def run(scenario, cap=650, label=None, **parameters):
    # Approved canonical policy: retrofit the existing estate first and buy
    # additional capacity only where required. Full-new-build remains an
    # explicit override for sensitivity runs.
    defaults = dict(infra_multiplier=.5, infra_carbon_multiplier=.3,
                    annual_energy_multiplier=.8)
    defaults.update(parameters)
    parameters = defaults
    schedule=json.loads((OUT/f'{scenario}_schedule.json').read_text())
    packages=prepare(schedule)
    all_results=[]
    for fuel_name,fuel in FUEL.items():
        bases=[ledger(p,None,fuel,**parameters) for p in packages]
        base_cost=sum(pv(rows) for rows in bases)
        base_ghg=sum(r['ghg_t'] for rows in bases for r in rows)
        base_eligible=sum(r['grant_eligible_net_cad']/1.03**(r['year']-2023) for rows in bases for r in rows)
        options=[];pids=[];counts=[]
        for i,p in enumerate(packages):
            for year in range(2030,2034):
                rows=ledger(p,year,fuel,**parameters)
                life = 8 if p['cls']=='shuttle' else 17
                # Full-life annual burden of every vehicle acquired in the
                # transition, amortized over its own service life. This makes
                # early conversion replace fewer bridge vehicles and therefore
                # reduces the full-life inventory rather than merely moving it.
                conv_life = 5 if p['cls'] == 'shuttle' else 17
                vehicle_annual_t = (
                    sum(r['acquired_electric'] for r in rows) * manufacture(p['cls'], True) / life
                    + sum(r['acquired_conventional'] for r in rows) * manufacture(p['cls'], False) / conv_life
                )
                infrastructure_annual_t = sum(r['infrastructure_t'] for r in rows) / 30.
                year_2033 = next(r for r in rows if r['year']==2033)
                full_life_t = vehicle_annual_t + infrastructure_annual_t + year_2033['operating_t']
                options.append(dict(package=i,year=year,rows=rows,cost=pv(rows),
                                    ghg=sum(r['ghg_t'] for r in rows),full_life_t=full_life_t))
                pids.append(i)
                counts.append([p['ev']['fleet_with_spares'] if y==year else 0 for y in range(2030,2034)])
        costs=[o['cost'] for o in options];ghgs=[o['ghg'] for o in options]
        life_ghgs=[o['full_life_t'] for o in options]
        full_base_t = sum(
            p['baseline_fleet']*manufacture(p['cls'],False)/(5 if p['cls']=='shuttle' else 17)
            for p in packages
        ) + sum(next(r['operating_t'] for r in ledger(p,None,fuel,**parameters) if r['year']==2033)
                for p in packages)
        first = solve_options(costs, life_ghgs, pids, counts, cap, 1.0)
        if 'selected' not in first:
            raise ValueError(f'{scenario}: full-life primary solve failed: {first}')
        best_life = sum(life_ghgs[i] for i in first['selected'])
        recommended = solve_options(costs, life_ghgs, pids, counts, cap, 0.0,
                                     emission_limit=best_life+1e-6)
        if 'selected' not in recommended:
            raise ValueError(f'{scenario}: lexicographic minimum-cost solve failed: {recommended}')
        sols=[];seen=set()
        for weight in np.linspace(0,1,11):
            solved=solve_options(costs,ghgs,pids,counts,cap,float(weight))
            if 'selected' not in solved:
                sols.append(dict(weight=float(weight),**solved));continue
            key=tuple(solved['selected'])
            if key in seen:
                continue
            seen.add(key)
            rows=[r for i in key for r in options[i]['rows']]
            plan_cost=sum(options[i]['cost'] for i in key)
            plan_ghg=sum(options[i]['ghg'] for i in key)
            eligible=sum(r['grant_eligible_net_cad']/1.03**(r['year']-2023) for r in rows)
            grants=[]
            for g in (0,.25,.5):
                b,p=base_cost-g*base_eligible,plan_cost-g*eligible
                grants.append(dict(grant_fraction=g,baseline_agency_pv_cad=b,plan_agency_pv_cad=p,economic_score_pct=100*(b-p)/b))
            sol=dict(weight=float(weight),**solved,plan_pv_cad=plan_cost,baseline_pv_cad=base_cost,
                     economic_score_pct=100*(base_cost-plan_cost)/base_cost,
                     plan_ghg_t=plan_ghg,baseline_ghg_t=base_ghg,
                     environmental_score_pct=100*(base_ghg-plan_ghg)/base_ghg,
                     full_life_plan_t=sum(life_ghgs[i] for i in key),
                     full_life_baseline_t=full_base_t,
                     full_life_environment_score_pct=100*(full_base_t-sum(life_ghgs[i] for i in key))/full_base_t,
                     grants=grants,conversion_years=[dict(site=packages[options[i]['package']]['site'],
                     vehicle_class=packages[options[i]['package']]['cls'],year=options[i]['year']) for i in key])
            sol['ledger_file']=f'{label or scenario}_{fuel_name}_w{weight:.1f}_ledger.csv'
            if sum(r['conventional_stock'] for r in rows if r['year']==2033)!=0:
                raise ValueError('2033 conventional stock nonzero')
            sol['zero_conventional_2033_check']='PASS'
            for i in key:
                option=options[i]
                package=packages[option['package']]
                inventory=package['initial']
                for r in option['rows']:
                    inventory+=r['acquired_conventional']+r['acquired_electric']-r['retired']
                    if inventory!=r['electric_stock']+r['conventional_stock']:
                        raise ValueError('annual inventory does not balance')
                    needed=package['ev']['fleet_with_spares'] if r['year']>=option['year'] else package['base']['fleet_with_spares']
                    if inventory<needed:
                        raise ValueError('annual fleet below dispatch plus spare need')
            sol['annual_inventory_and_spares_check']='PASS'
            sols.append(sol)
            pd.DataFrame(rows).to_csv(OUT/f'{label or scenario}_{fuel_name}_w{weight:.1f}_ledger.csv',index=False)
        feasible=[s for s in sols if 'plan_pv_cad' in s]
        # Weighted sums sample supported Pareto points; do not claim all integer frontier points.
        nondom=[s for s in feasible if not any(
            t['plan_pv_cad']<=s['plan_pv_cad']+.001 and t['plan_ghg_t']<=s['plan_ghg_t']+1e-7
            and (t['plan_pv_cad']<s['plan_pv_cad']-.01 or t['plan_ghg_t']<s['plan_ghg_t']-1e-6)
            for t in feasible)]
        recommended_rows=[r for i in recommended['selected'] for r in options[i]['rows']]
        recommended_cost=sum(options[i]['cost'] for i in recommended['selected'])
        recommended_ghg=sum(options[i]['ghg'] for i in recommended['selected'])
        recommended_eligible=sum(r['grant_eligible_net_cad']/1.03**(r['year']-2023)
                                 for r in recommended_rows)
        recommended_grants=[]
        for g in (0,.25,.5):
            b,p=base_cost-g*base_eligible,recommended_cost-g*recommended_eligible
            recommended_grants.append(dict(grant_fraction=g,
                baseline_agency_pv_cad=b,plan_agency_pv_cad=p,
                economic_score_pct=100*(b-p)/b))
        recommended.update(
            full_life_plan_t=best_life,
            full_life_baseline_t=full_base_t,
            full_life_environment_score_pct=100*(full_base_t-best_life)/full_base_t,
            plan_pv_cad=recommended_cost,baseline_pv_cad=base_cost,
            economic_score_pct=100*(base_cost-recommended_cost)/base_cost,
            plan_ghg_t=recommended_ghg,baseline_ghg_t=base_ghg,
            environmental_score_pct=100*(base_ghg-recommended_ghg)/base_ghg,
            grants=recommended_grants,
            conversion_years=[dict(site=packages[options[i]['package']]['site'],
                vehicle_class=packages[options[i]['package']]['cls'],year=options[i]['year'])
                for i in recommended['selected']],
            annual_inventory_and_spares_check='PASS',
            zero_conventional_2033_check='PASS',
            ledger_file=f'{label or scenario}_{fuel_name}_recommended_ledger.csv')
        pd.DataFrame(recommended_rows).to_csv(OUT/recommended['ledger_file'],index=False)
        if sum(r['conventional_stock'] for r in recommended_rows if r['year']==2033)!=0:
            raise ValueError('recommended plan retains conventional stock in 2033')
        all_results.append(dict(fuel_case=fuel_name,baseline_intensity_kg_per_km=fuel,
                                solutions=sols,sampled_nondominated_weights=[s['weight'] for s in nondom],
                                recommended=recommended))
        pd.DataFrame([r for rows in bases for r in rows]).to_csv(OUT/f'{label or scenario}_{fuel_name}_baseline_ledger.csv',index=False)
        observed_reserve = (sum(p['ev']['fleet_with_spares'] for p in packages)
                            / sum(p['ev']['active_buses'] for p in packages) - 1)
        summary=dict(status='EXECUTED_CONDITIONAL_RESTRICTED_MASTER',scenario=scenario,
                 annual_delivery_cap_assumption=cap,packages=len(packages),parameter_overrides=parameters,
                 source_schedule=f'{scenario}_schedule.json',
                 scoring_boundary='Non-trolley fleet only; unchanged trolley costs/emissions excluded from both denominators.',
                 construction='Six annual equal payments before commissioning; all-in facility envelope, no extra charger capex.',
                 reserve=f'{100*observed_reserve:.1f}% approximately; all reserve vehicles purchased and housed.',
                 reserve_ratio=observed_reserve,
                 initial_age='Synthetic uniform completed-age cohorts at start 2024: heavy ages 1--17, shuttle ages 1--5, decks ages 1--5; five existing BEBs age one. Retire before service; age at year end.',
                 operating_boundary='Winter service design; annual energy multiplied by explicit scenario factor (default 1). Driver paid full duty span, including idle; charging unattended except 10 minutes per event.',
                 terminal='Straight-line 17-year heavy/8-year EV shuttle/30-year infrastructure; initial residuals included symmetrically; 25% book-value resale recovery.',
                 grants='Symmetric capex subsidy with proportional recapture for sale/terminal value of funded assets.',
                 incomplete_lca=['Local infrastructure EPD','route-specific glider masses','disposal of retired initial vehicles'],
                 results=all_results)
    (OUT/f'{label or scenario}_transition.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scenario':scenario,'results':[{'fuel':r['fuel_case'],'points':len(r['solutions']),
             'cost_min':min((s['plan_pv_cad'] for s in r['solutions'] if 'plan_pv_cad' in s),default=None),
             'scores':[(round(s['economic_score_pct'],2),round(s['environmental_score_pct'],2)) for s in r['solutions'] if 'plan_pv_cad' in s]} for r in all_results]},indent=2))
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',default='central')
    ap.add_argument('--cap',type=int,default=650)
    args=ap.parse_args();run(args.scenario,args.cap)
