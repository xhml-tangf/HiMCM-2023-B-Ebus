"""Transparent, conditional financial and ecological accounting, in 2023 CAD.

This is a homogeneous diesel-counterfactual screening model, not observed
TransLink technology mix or an awarded local price. Inputs are separately labeled.
"""
from dataclasses import dataclass,asdict,replace
import math
from .price_index import to_2023


@dataclass
class Parameters:
    epsilon:float=1.6
    efficiency:float=.9
    usable_depth:float=.8
    R:float=270.
    T:float=60.
    grid:float=.0113
    diesel_ghg:float=1.58
    battery_ghg:float=58.
    body_ghg_t:float=70.
    battery_life:int=8
    vehicle_life:int=12
    horizon:int=10
    discount:float=.03
    electricity:float=.10
    diesel_price:float=1.66
    litres_km:float=.60
    diesel_maintenance:float=.60
    electric_maintenance:float=.40
    battery_price:float=180.
    battery_decline:float=.03
    body_price:float=1102800. # 1.2m installed price minus 540kWh * 180
    diesel_bus_price:float=0.
    site_fixed:float=610000.
    charger_per_kw:float=533.3333333333
    overnight_per_bus:float=100000.
    infrastructure_life:int=20
    station_maintenance_fraction:float=.02

    def __post_init__(self):
        if not self.diesel_bus_price:self.diesel_bus_price=to_2023(630000,2019)
        if self.T<=0 or self.R<=0 or not 0<self.efficiency<=1 or not 0<self.usable_depth<=1:
            raise ValueError('invalid energy parameters')
        if self.battery_life<=0 or self.vehicle_life<=self.horizon:
            raise ValueError('this screening model requires vehicle life greater than horizon')

    @property
    def B(self):return self.epsilon*self.R/self.usable_depth
    @property
    def power_grid(self):return 60*self.epsilon*self.R/self.T/self.efficiency
    @property
    def bus_price(self):return self.body_price+self.B*self.battery_price


def parameter_ledger(p):
    evidence={
        'epsilon':('HISTORICAL_TRANSFER','TransLink 2020 Appendix C-1, annual all-electric 40-ft mean; 1.37-2.00 range'),
        'grid':('DATED_PRIMARY','BC 2023 integrated grid factor 11.3 tCO2e/GWh'),
        'diesel_ghg':('RETROSPECTIVE_TRANSFER','TransLink 2024 playbook fossil diesel operating 1580 gCO2e/km'),
        'diesel_price':('DATED_PLAN','2023 TransLink business-plan budget 1.66 CAD/L'),
        'litres_km':('HISTORICAL_TRANSFER','TransLink 2020 Appendix D-1, 0.60 L/km'),
        'battery_ghg':('LITERATURE_TRANSFER','ICCT 2024 battery production factor 58 kgCO2e/kWh'),
        'diesel_bus_price':('HISTORICAL_REBASED','2019 CAD630000, TransLink 2020 Appendix D-1; Bank of Canada CPI to2023'),
        'site_fixed':('ASSUMPTION_ANCHORED_TO_DIFFERENT_SCOPE','TransLink June2023 quotes CAD460-610k for ONE on-route CHARGER, not a station; CAD610k here is an independent fixed-site allowance. Added power-scaled plugs are separately assumed, not sourced itemization.'),
    }
    return {k:dict(value=v,status=evidence.get(k,('ASSUMPTION','Explicit screening choice; sensitivity required'))[0],
                   basis=evidence.get(k,('ASSUMPTION','Explicit screening choice; sensitivity required'))[1])
            for k,v in asdict(p).items()}


def evaluate_impacts(Nd,Ne,Dd,De,stations,plugs,p=None,grid_decline=0.0):
    p=p or Parameters()
    if min(Nd,Ne,Dd,De,stations,plugs)<0:raise ValueError('negative activity')
    B=p.B
    infrastructure=stations*p.site_fixed+plugs*p.power_grid*p.charger_per_kw+Ne*p.overnight_per_bus
    cap_d=Nd*p.diesel_bus_price
    cap_e=Ne*p.bus_price+infrastructure
    eligible=max(0.,cap_e-cap_d)
    annual_grid=De*p.epsilon/p.efficiency
    annual_diesel_op=Dd*(p.litres_km*p.diesel_price+p.diesel_maintenance)
    annual_electric_op=annual_grid*p.electricity+De*p.electric_maintenance+infrastructure*p.station_maintenance_fraction
    embodied_e=Ne*(p.body_ghg_t+B*p.battery_ghg/1000)
    embodied_d=Nd*p.body_ghg_t
    rows=[];cum_d=embodied_d;cum_e=embodied_e
    for t in range(1,p.horizon+1):
        replacement=Ne*B*p.battery_price*(1-p.battery_decline)**t if t%p.battery_life==0 else 0.
        ghg_replacement=Ne*B*p.battery_ghg/1000 if replacement else 0.
        grid=p.grid*(1-grid_decline)**(t-1)
        gd=Dd*p.diesel_ghg/1000
        ge=annual_grid*grid/1000
        cum_d+=gd;cum_e+=ge+ghg_replacement
        rows.append(dict(year=2023+t,t=t,baseline_cost=annual_diesel_op,
                         electric_cost=annual_electric_op+replacement,battery_replacement=replacement,
                         diesel_operating_t=gd,electric_operating_t=ge,battery_replacement_t=ghg_replacement,
                         cumulative_diesel_t=cum_d,cumulative_electric_t=cum_e,
                         cumulative_avoided_t=cum_d-cum_e,grid_factor=grid))
    # Symmetric terminal assets, with separate remaining body and battery lives.
    last_battery=(p.horizon//p.battery_life)*p.battery_life
    battery_fraction=max(0.,1-(p.horizon-last_battery)/p.battery_life)
    residual_d=cap_d*(1-p.horizon/p.vehicle_life)
    residual_e=Ne*p.body_price*(1-p.horizon/p.vehicle_life)+Ne*B*p.battery_price*(1-p.battery_decline)**last_battery*battery_fraction
    residual_e+=infrastructure*max(0.,1-p.horizon/p.infrastructure_life)
    pv_d=cap_d+sum(r['baseline_cost']/(1+p.discount)**r['t'] for r in rows)-residual_d/(1+p.discount)**p.horizon
    pv_e=cap_e+sum(r['electric_cost']/(1+p.discount)**r['t'] for r in rows)-residual_e/(1+p.discount)**p.horizon
    grants=[]
    for phi in (0.,.25,.5):
        cash=-cap_e+cap_d+phi*eligible
        cumulative=[dict(t=0,cash=cash,cumulative=cash)]
        discounted=cash
        for r in rows:
            delta=r['baseline_cost']-r['electric_cost']
            if r['t']==p.horizon:delta+=residual_e-residual_d
            discounted+=delta/(1+p.discount)**r['t']
            cash+=delta
            cumulative.append(dict(t=r['t'],year=r['year'],cash=delta,cumulative=cash))
        # Sustained payback: first nonnegative point after which it never falls below zero.
        payback=next((r['t'] for k,r in enumerate(cumulative) if min(x['cumulative'] for x in cumulative[k:])>=0),None)
        grants.append(dict(phi=phi,grant=phi*eligible,agency_pv=pv_e-phi*eligible,
                           NPV=pv_d-pv_e+phi*eligible,payback_year=payback,cashflow=cumulative))
        assert abs(discounted-grants[-1]['NPV'])<1e-5
    factor=sum(1/(1+p.discount)**t for t in range(1,p.horizon+1))
    phi_star=max(0.,(pv_e-pv_d)/eligible) if eligible>0 else (0. if pv_e<=pv_d else None)
    op_saving=(Dd*p.diesel_ghg-annual_grid*p.grid)/1000
    return dict(Nd=Nd,Ne=Ne,annual_diesel_km=Dd,annual_electric_km=De,annual_grid_kwh=annual_grid,
                B_kwh=B,charger_grid_kw=p.power_grid,stations=stations,daytime_plugs=plugs,
                infrastructure=infrastructure,capex_electric=cap_e,capex_diesel=cap_d,grant_eligible_increment=eligible,
                pv_diesel=pv_d,pv_electric_gross=pv_e,residual_diesel=residual_d,residual_electric=residual_e,
                phi_star=phi_star,phi_star_within_cap=phi_star is not None and phi_star<=.5,
                diesel_tco_per_discounted_vehicle_km=pv_d/(Dd*factor) if Dd else None,
                electric_tco_per_discounted_vehicle_km=pv_e/(De*factor) if De else None,
                battery_carbon_payback_years=(Ne*B*p.battery_ghg/1000)/op_saving if op_saving>0 else None,
                initial_embodied_diesel_t=embodied_d,initial_embodied_electric_t=embodied_e,
                ten_year_avoided_t=cum_d-cum_e,grants=grants,annual=rows,
                exclusions=['local construction embodied carbon','vehicle disposal','non-exhaust particles','new labour/driver arrangements'],
                boundary='Full replacement at start of 2024; no initial old-bus sale. Terminal assets symmetric. Grid average, not certified zero-carbon electricity.')
