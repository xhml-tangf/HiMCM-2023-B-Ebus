"""Construct and independently check a full-timetable electric planning case.

All source trips are obligations, not observed vehicle assignments. Approximate
regional depot anchors, road factors, payloads and winter loads are assumptions.
The duty heuristic returns a feasible upper bound, never a fleet optimum.
An exact cyclic resource allocation check includes the end/start calendar seam.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd
try:
    from .audit_gtfs_baseline import haversine_km
except ImportError:
    from audit_gtfs_baseline import haversine_km

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/research_model'
CAP = {'cap24': 24, 'cap47': 47, 'cap50': 50, 'cap70': 70,
       'cap75': 75, 'cap85': 85, 'unclassified': 50}
CLASS = {'cap24': 'shuttle', 'cap50': 'standard', 'cap75': 'articulated',
         'cap85': 'deck', 'unclassified': 'standard'}
# Planning anchors near the named regions, NOT surveyed depot coordinates.
# North Shore and Langley represent additional regional contracted-service hubs.
SITES = {'Vancouver': (49.211, -123.106), 'Burnaby': (49.252, -122.978),
         'Hamilton': (49.178, -122.955), 'Richmond': (49.174, -123.126),
         'Surrey': (49.164, -122.843), 'Port_Coquitlam': (49.258, -122.780),
         'North_Shore': (49.322, -123.094), 'Langley': (49.115, -122.659)}
TECH = {
    # capacity, battery kWh, traction kWh/km, active accessories kW, grid kW
    'standard': (59, 564., 1.79, 12., 150.),
    'articulated': (75, 605., 2.42, 18., 150.),
    'deck': (85, 700., 1.80, 15., 150.),
    'shuttle': (24, 150., .90, 6., 60.),
}
SCENARIOS = {
    'central': dict(road_factor=1.35, speed_kmh=30., heat_factor=1.,
                    traction_factor=1., charge_factor=1., usable=.80, turn_min=2.),
    'slow_charge': dict(road_factor=1.35, speed_kmh=30., heat_factor=1.,
                        traction_factor=1., charge_factor=.5, usable=.80, turn_min=2.),
    'winter_stress': dict(road_factor=1.50, speed_kmh=25., heat_factor=1.5,
                          traction_factor=1.20, charge_factor=1., usable=.70, turn_min=3.),
    'capacity_stress': dict(road_factor=1.35, speed_kmh=30., heat_factor=1.,
                            traction_factor=1., charge_factor=1., usable=.80, turn_min=2.,
                            unclassified_capacity=85),
    'spare10': dict(road_factor=1.35, speed_kmh=30., heat_factor=1.,
                    traction_factor=1., charge_factor=1., usable=.80, turn_min=2.,
                    spare_ratio=.10),
}


def road(a, b, factor):
    return float(haversine_km(a[0], a[1], b[0], b[1])) * factor


def periodic_color(starts, ends, period):
    """Feasible circular interval coloring, with explicit wrap deadlines.

    Resource IDs with a crossing interval can be reused inside its free gap.
    This is a constructive upper bound; optimal circular coloring is not claimed.
    """
    starts, ends = np.asarray(starts, float), np.asarray(ends, float)
    duration = ends - starts
    if np.any(duration <= 0) or np.any(duration >= period):
        raise ValueError('invalid interval duration')
    s = starts % period
    e = s + duration
    colors = np.full(len(s), -1, int)
    available, deadline = [], []
    for i in np.flatnonzero(e > period):
        colors[i] = len(available)
        available.append(e[i] - period)
        deadline.append(s[i])
    # Use numpy state for efficient scans of the small per-depot vehicle pool.
    limit = max(1, len(s))
    av = np.full(limit, np.inf)
    dl = np.full(limit, np.inf)
    n = len(available)
    av[:n], dl[:n] = available, deadline
    for i in np.argsort(s, kind='stable'):
        if colors[i] >= 0:
            continue
        possible = np.flatnonzero((av[:n] <= s[i] + 1e-7) & (dl[:n] >= e[i] - 1e-7))
        if len(possible):
            # Fill a wrap resource's finite gap before using unrestricted ones.
            j = int(possible[np.argmin(dl[possible])])
        else:
            j = n
            n += 1
        colors[i] = j
        av[j] = e[i]
    check_periodic_intervals(s, e, colors, period)
    return colors, n


def check_periodic_intervals(starts, ends, colors, period):
    """Independent sorted interval check, including each resource's wrap gap."""
    df = pd.DataFrame({'s': starts, 'e': ends, 'c': colors}).sort_values(['c', 's'])
    for _, g in df.groupby('c', sort=False):
        s, e = g.s.to_numpy(), g.e.to_numpy()
        if np.any(e[:-1] > s[1:] + 1e-6) or e[-1] > s[0] + period + 1e-6:
            raise ValueError('cyclic resource collision')


def construct_pattern(args):
    pid, rows, scenario, electric = args
    cfg = SCENARIOS[scenario]
    factor, speed = cfg['road_factor'], cfg['speed_kmh']
    duties, assigned = [], []
    pools = defaultdict(list)
    for r in sorted(rows, key=lambda x: (x['start_seconds'], x['trip_id'])):
        cls = CLASS[r['proxy_class']]
        capacity, battery, traction, heat, power = TECH[cls]
        traction *= cfg['traction_factor']
        heat *= cfg['heat_factor']
        power *= cfg['charge_factor']
        limit = battery * cfg['usable'] if electric else float('inf')
        first, last = (r['first_lat'], r['first_lon']), (r['last_lat'], r['last_lon'])
        # Same route always uses one anchor, allowing annual package migration.
        site = r['research_site']
        home = SITES[site]
        pullout = road(home, first, factor)
        pullin = road(last, home, factor)
        start, end = r['start_seconds']/3600, r['end_seconds']/3600
        km = float(r['distance_km_upper'])
        trip_energy = km * traction + (end-start) * heat
        back_energy = pullin * (traction + heat/speed)
        options = []
        for j in pools[(site, cls)]:
            d = duties[j]
            # Duty duration is a vehicle-chain property. Driver relief is
            # permitted, so no artificial 16-hour vehicle ceiling is imposed.
            gap = start - d['last_end_h']
            if gap < cfg['turn_min']/60:
                continue
            dh = road(d['last_location'], first, factor)
            if dh/speed + cfg['turn_min']/60 > gap + 1e-8:
                continue
            use = dh * (traction + heat/speed) + trip_energy
            if d['energy_kwh'] + use + back_energy <= limit + 1e-7:
                # Prefer little extra travel, then short idle time.
                options.append((dh + .2*gap, j, dh, use))
        if options:
            _, j, dh, use = min(options)
            d = duties[j]
            d['energy_kwh'] += use
            d['deadhead_km'] += dh
        else:
            use = pullout * (traction + heat/speed) + trip_energy
            if use + back_energy > limit + 1e-7:
                raise ValueError(f'{scenario}: trip {r["trip_id"]} alone needs {use+back_energy:.1f} > {limit:.1f} kWh')
            j = len(duties)
            d = dict(pattern_id=pid, duty_id=j, site=site, vehicle_class=cls,
                     depart_h=start-pullout/speed, energy_kwh=use,
                     deadhead_km=pullout, revenue_km=0., revenue_h=0.,
                     trip_count=0, battery_kwh=battery, usable_kwh=battery*cfg['usable'],
                     charge_kw=power, heat_kw=heat, capacity=capacity)
            duties.append(d)
            pools[(site, cls)].append(j)
        d['revenue_km'] += km
        d['revenue_h'] += end-start
        d['trip_count'] += 1
        d['last_end_h'], d['last_location'] = end, last
        d['pullin_km'], d['back_energy'] = pullin, back_energy
        assigned.append(dict(pattern_id=pid, trip_id=r['trip_id'], duty_id=j))
    for d in duties:
        d['energy_kwh'] += d.pop('back_energy')
        d['deadhead_km'] += d['pullin_km']
        d['return_h'] = d.pop('last_end_h') + d.pop('pullin_km')/speed
        d.pop('last_location')
        # Charging auxiliaries are conservatively held on at winter heat load.
        net_power = .9*d['charge_kw'] - d['heat_kw']
        if net_power <= 0:
            raise ValueError('nonpositive net charge power')
        d['ready_h'] = (d['return_h'] + d['energy_kwh']/net_power + 5/60
                        if electric else d['return_h'] + 15/60)
        d['charge_end_h'] = d['ready_h'] - 5/60 if electric else d['return_h']
        d['grid_kwh'] = (d['charge_end_h']-d['return_h'])*d['charge_kw'] if electric else 0.
    return duties, assigned


def validate_duties(duties, assignments, manifest, cfg, electric):
    """Rebuild each chain from source trips; do not trust constructor totals."""
    source = manifest.set_index('trip_id').to_dict('index')
    by_duty = defaultdict(list)
    for a in assignments:
        by_duty[(a['pattern_id'], a['duty_id'])].append(source[a['trip_id']])
    max_error = 0.
    for d in duties:
        chain = sorted(by_duty[(d['pattern_id'], d['duty_id'])], key=lambda r:r['start_seconds'])
        cls = d['vehicle_class']
        loc, t = SITES[d['site']], d['depart_h']
        traction, heat = TECH[cls][2]*cfg['traction_factor'], TECH[cls][3]*cfg['heat_factor']
        energy, dh_sum, revenue, hours = 0., 0., 0., 0.
        for k,r in enumerate(chain):
            first = (r['first_lat'],r['first_lon'])
            dh = road(loc, first, cfg['road_factor'])
            s,e = r['start_seconds']/3600, r['end_seconds']/3600
            turn = cfg['turn_min']/60 if k else 0
            if t+dh/cfg['speed_kmh']+turn > s+1e-7 or d['capacity'] < CAP[r['proxy_class']]:
                raise ValueError('time/location/capacity violation')
            km = r['distance_km_upper']
            energy += (dh+km)*traction+(dh/cfg['speed_kmh']+e-s)*heat
            dh_sum += dh
            revenue += km
            hours += e-s
            loc,t = (r['last_lat'],r['last_lon']),e
        dh = road(loc,SITES[d['site']],cfg['road_factor'])
        dh_sum += dh
        energy += dh*(traction+heat/cfg['speed_kmh'])
        ret = t+dh/cfg['speed_kmh']
        max_error = max(max_error,abs(energy-d['energy_kwh']),abs(ret-d['return_h']),
                        abs(dh_sum-d['deadhead_km']),abs(revenue-d['revenue_km']),abs(hours-d['revenue_h']))
        if electric:
            replenished = (d['charge_end_h']-ret)*(.9*d['charge_kw']-heat)
            max_error = max(max_error,abs(replenished-energy))
            if energy > d['usable_kwh']+1e-6:
                raise ValueError('SOC below reserve')
    if max_error > 1e-5:
        raise ValueError(f'independent energy/time ledger mismatch {max_error}')
    return max_error


def run(scenario, workers):
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT/'data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv'
    mf = pd.read_csv(manifest_path, dtype={'trip_id':str,'route_id':str,'service_id':str}, low_memory=False)
    if SCENARIOS[scenario].get('unclassified_capacity')==85:
        mf.loc[mf.proxy_class.eq('unclassified'),'proxy_class']='cap85'
    daily = pd.read_csv(ROOT/'data/processed/vancouver_gtfs_daily_service_2023.csv')
    patterns = json.loads((ROOT/'results/vancouver_gtfs_baseline_audit.json').read_text())['unique_service_patterns']
    battery = mf[mf.proxy_class.isin(CLASS)].copy()
    # Geographic route anchor is determined once across all service patterns.
    route_site = {}
    for route,g in battery.groupby('route_id'):
        centroid = ((g.first_lat.mean()+g.last_lat.mean())/2,
                    (g.first_lon.mean()+g.last_lon.mean())/2)
        route_site[route] = min(SITES,key=lambda site:road(centroid,SITES[site],1))
    battery['research_site'] = battery.route_id.map(route_site)
    expected = {}
    jobs = []
    for p in patterns:
        rows = battery[battery.service_id.isin(p['active_service_ids'])].to_dict('records')
        expected[p['pattern_id']] = {r['trip_id'] for r in rows}
        jobs.append((p['pattern_id'],rows,scenario,True))
    outputs = {}
    for electric in (True,False):
        mode = 'electric' if electric else 'baseline'
        duties, assignments = [], []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for ds,aa in pool.map(construct_pattern,[(a,b,c,electric) for a,b,c,_ in jobs]):
                duties.extend(ds)
                assignments.extend(aa)
        for pid, ids in expected.items():
            actual = [a['trip_id'] for a in assignments if a['pattern_id']==pid]
            if set(actual)!=ids or len(actual)!=len(ids):
                raise ValueError('omitted or duplicated source trip')
        error = validate_duties(duties, assignments, battery, SCENARIOS[scenario],electric)
        df = pd.DataFrame(duties)
        events = []
        for day, row in enumerate(daily.itertuples()):
            g = df[df.pattern_id.eq(row.pattern_id)].copy()
            g['date'] = row.date
            for col in ('depart_h','return_h','charge_end_h','ready_h'):
                g[col] += 24*day
            events.append(g)
        ev = pd.concat(events, ignore_index=True)
        period = len(daily)*24
        packages = []
        for (site,cls),g in ev.groupby(['site','vehicle_class']):
            colors,n = periodic_color(g.depart_h,g.ready_h,period)
            ev.loc[g.index,'vehicle'] = [f'{site}_{cls}_{i}' for i in colors]
            # One dedicated port per bus guarantees port assignment across classes.
            # Exact charge concurrence still supplies the required firm-power bound.
            try:
                from .build_full_city_schedule_v3 import peak_concurrency
            except ImportError:
                from build_full_city_schedule_v3 import peak_concurrency
            charge_intervals = []
            for s,e in zip(g.return_h,g.charge_end_h):
                if e <= s:
                    continue
                s,e = s%period,s%period+e-s
                charge_intervals.append((s,min(e,period)))
                if e>period:
                    charge_intervals.append((0,e-period))
            peak = peak_concurrency(charge_intervals) if charge_intervals else 0
            spare_fleet=math.ceil(n*(1+SCENARIOS[scenario].get('spare_ratio',.15)))
            packages.append(dict(site=site,vehicle_class=cls,active_buses=n,
                                 fleet_with_spares=spare_fleet,
                                 fleet_with_15pct_spare=spare_fleet,
                                 dedicated_ports=n if electric else 0,
                                 simultaneous_charge_peak=peak,
                                 required_power_kw=peak*float(g.charge_kw.iloc[0]),
                                 annual_revenue_km=float(g.revenue_km.sum()*365/len(daily)),
                                 annual_deadhead_km=float(g.deadhead_km.sum()*365/len(daily)),
                                 annual_driver_h=float(((g.return_h-g.depart_h).sum()+len(g)*(10/60 if electric else 0))*365/len(daily)),
                                 annual_grid_kwh=float(g.grid_kwh.sum()*365/len(daily)),
                                 min_soc_fraction=float(.9-g.energy_kwh.max()/g.battery_kwh.iloc[0]) if electric else None))
        df.to_csv(OUT/f'{scenario}_{mode}_duties.csv',index=False)
        pd.DataFrame(assignments).to_csv(OUT/f'{scenario}_{mode}_assignments.csv',index=False)
        ev[['date','pattern_id','duty_id','site','vehicle_class','vehicle','depart_h','return_h','charge_end_h','ready_h']].to_csv(
            OUT/f'{scenario}_{mode}_calendar.csv.gz',index=False,compression={'method':'gzip','mtime':0})
        outputs[mode] = dict(packages=packages,pattern_trips=len(assignments),
                             calendar_trip_instances=int(ev.trip_count.sum()),
                             active_buses=sum(p['active_buses'] for p in packages),
                             fleet_with_spares=sum(p['fleet_with_spares'] for p in packages),
                             independent_ledger_max_error=error,
                             calendar_cycle_hours=period,
                             cyclic_vehicle_collision_check='PASS',
                             port_check='PASS_DEDICATED_PORT_PER_ACTIVE_BUS',
                             schedule_optimality='HEURISTIC_FEASIBLE_UPPER_BOUND')
        print(f'{scenario} {mode}: fleet={outputs[mode]["fleet_with_spares"]}, trips={outputs[mode]["pattern_trips"]}',flush=True)
    result = dict(status='CONDITIONALLY_FEASIBLE_RESEARCH_SCHEDULE',scenario=scenario,
                  assumptions=SCENARIOS[scenario],technology=TECH,site_anchors=SITES,
                  route_site=route_site,source_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                  service_patterns=len(patterns),calendar_days=len(daily),
                  retained_trolley_pattern_trips=sum(p['bus_trips'] for p in patterns)-outputs['electric']['pattern_trips'],
                  unchanged_trolley_assumption='Official existing trolley duties and overhead supply execute normally; no added trolley demand.',
                  annualization='Repeat recovered 119-day service distribution over 365 days; no claim to recover missing January-August timetable.',
                  scope='Every non-trolley trip; per-trip capacity is the existing route proxy, not observed passenger count.',
                  unresolved_real_world=['surveyed road paths','actual depot occupancy and land permits','firm power agreements',
                                         'route payload approval','winter telemetry','exact 2023 vehicle ages'],
                  outputs=outputs,wall_seconds=time.perf_counter()-started)
    (OUT/f'{scenario}_schedule.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',choices=list(SCENARIOS),default='central')
    ap.add_argument('--workers',type=int,default=min(12,os.cpu_count() or 1))
    args=ap.parse_args()
    run(args.scenario,args.workers)
