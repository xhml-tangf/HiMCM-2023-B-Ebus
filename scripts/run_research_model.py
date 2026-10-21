"""One command to rebuild the canonical research model and its input ledger."""
from pathlib import Path
import sys
import subprocess
import json
import hashlib
import os
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from solve_research_schedule import TECH,SITES,SCENARIOS,OUT
from solve_research_transition import run, GLIDER,CONVENTIONAL_GLIDER,SCALE


def main(finance_only=False):
    OUT.mkdir(exist_ok=True,parents=True)
    parameters={
        'status':'SOURCE_VALUES_PLUS_EXPLICIT_RESEARCH_ASSUMPTIONS',
        'service':dict(value='All published fall-2023 GTFS trips execute at scheduled times',
                       source='User-authorized assumption, 2026-10-21',
                       annualization='Observed 119-day calendar repeated at 365/119 for annual costs and emissions'),
        'technology_tuple_fields':['required_available_capacity','battery_kwh','traction_kwh_per_km','active_heat_kw','grid_charge_kw'],
        'technology':TECH,
        'technology_evidence':{
            'standard':'Nova 2021 LFSe+ brochure: 564 kWh, 59 total passengers, 150 kW plug; energy/heat are design assumptions.',
            'articulated':'Winnipeg RFP 763-2023 appendix A table 1: 605 kWh and 90% manufacturer usable. Model 75 passengers is a procurement requirement, not a local certification.',
            'deck':'Foothill 2024 procurement >700 kWh, model uses 700; North America price. Capacity 85 including standees assumed. 150 kW is a conservative design setting.',
            'shuttle':'150 kWh/24 passengers is a REQUIRED future accessible configuration, assembled from evidence envelopes; not a proven single TransLink product. Compare 260-kWh later product in existing source table.'},
        'site_anchors':{'status':'ASSUMED_REGIONAL_SERVICE_HUBS_NOT_SURVEYED_DEPOTS','coordinates':SITES,
                        'parking':'Size facilities for every active and spare vehicle; no use of nominal old capacity as vacant spaces.',
                        'power':'Compute a sufficient firm-power requirement from concurrency, not a promised utility allocation.'},
        'operations':dict(spare_ratio=.15,charge_efficiency=.90,initial_soc_fraction=.90,
                          central_min_soc_fraction=.10,driver_relief=True,
                          vehicle_duty_span_cap='none; driver replacement allowed without plug-in dwell',
                          standby_heat='Off during waiting and parking; heat on during all movement and charging.',
                          charge_policy='Unattended immediate depot charge, five-minute release margin, 10 driver minutes per event.',
                          driver_shifts='Relief allowed without reducing service; driver paid full duty span incl waiting. Labour-law rostering outside scope.',
                          charger_ports='One per active scheduled bus, dedicated; spares assumed ready and interchangeable.'),
        'operational_scenarios':SCENARIOS,
        'finance':dict(currency='Constant 2023 CAD',discount_real=.03,delivery_cap_per_year=650,
                       heavy_life=17,conventional_shuttle_life=5,electric_shuttle_life=8,
                       building_life=30,construction_years=6,driver_cad_per_h=60,
                       standard_price='2023 TransLink hardware 1.2m incl installed battery',
                       articulated_price='1.5 x standard hardware, ASSUMPTION',
                       conventional_deck_price='1m CAD ASSUMPTION; no in-horizon natural deck expiry',
                       deck_and_shuttle_prices='Existing CPI/FX-converted class source table, external costs',
                       maintenance='0.80 CAD/km in 2019, TransLink appendix D-1, CPI to 2023; transferred across classes',
                       conventional_om='2024 CNG benchmark 2.77 CAD/km, CPI to 2023; excludes driver',
                       facilities='500m/340 slots in 2023, multiplied by required 40-foot equivalents; all-in construction/charging/utility planning envelope',
                       facility_scenarios='Primary: retrofit-first .5 cost/.3 building carbon plus required expansion; full new-build 1.0 is sensitivity',
                       annual_energy='Winter schedule x 0.8 seasonal-average factor in primary; factor 1.0 in winter sensitivity',
                       resale='25% remaining straight-line value at early conversion, zero-value sensitivity available',
                       taxes_financing='Real unlevered budget; no VAT/debt interest transfers',
                       grants='0/25/50%, same rules for both fleets with proportional funded-asset recapture'),
        'lca':dict(glider_kg_assumptions=GLIDER,conventional_glider_kg_assumptions=CONVENTIONAL_GLIDER,
                   glider_kgco2_per_kg=6.6,battery_kgco2_per_kwh=58,
                   building_kgco2_per_m2=650,building_m2_per_standard_slot=800000*.09290304/340,
                   charger_tco2_per_port=6.40395,grid_kgco2_per_kwh=.0113,
                   end_of_life='Initial-vehicle disposal unmeasured; excluded and retained as limitation. No credit for possible second-life displacement.',
                   source='ICCT 2024 transfer factors and existing infrastructure LCA ledger; no local EPD'),
        'body_footprint_factors':SCALE,
        'trolleys':'275 retained electrical positions; official existing service and power infrastructure assumed functional. Unchanged common trolley costs/emissions excluded from scoring denominators.',
        'real_world_status':'Not a delivered fleet, construction permit, utility agreement, or globally optimal city design.'}
    (OUT/'input_ledger.json').write_text(json.dumps(parameters,indent=2)+'\n',encoding='utf-8')
    for scenario in SCENARIOS:
        if not finance_only:
            subprocess.run([sys.executable,'src/solve_research_schedule.py','--scenario',scenario,
                            '--workers',str(min(12,os.cpu_count() or 1))],cwd=ROOT,check=True)
        run(scenario, annual_energy_multiplier=(1.0 if scenario == 'winter_stress' else .8))
    # Stable name for the manuscript consumer, independent of loop ordering.
    run('central',label='canonical')
    # Same dispatch schedule, but costs and annual exposure differ explicitly.
    run('central',label='full_new',infra_multiplier=1.,infra_carbon_multiplier=1.,
        annual_energy_multiplier=.8)
    run('central',label='fossil_sensitivity',infra_multiplier=.5,infra_carbon_multiplier=.3,
        annual_energy_multiplier=.8)
    run('central',label='central_high_cost',infra_multiplier=1.25,driver_rate=75.,
        electric_maintenance=1.4)
    # Every published numerical result can be traced to a script/input hash.
    files=[ROOT/'src/solve_research_schedule.py',ROOT/'src/solve_research_transition.py',
           ROOT/'data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv',
           ROOT/'data/processed/vancouver_gtfs_daily_service_2023.csv',OUT/'input_ledger.json']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT/'run_manifest.json').write_text(json.dumps({'input_sha256':hashes,
        'runtime':sys.version,'cpu_workers':min(12,os.cpu_count() or 1),
        'command':'python scripts/run_research_model.py'},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--finance-only',action='store_true')
    ap.add_argument('--canonical',action='store_true',help='Build the canonical aggregate after the simulation')
    args=ap.parse_args()
    main(args.finance_only)
    if args.canonical:
        from build_canonical_results import main as canonical_main
        canonical_main()
        subprocess.run([sys.executable, 'scripts/build_paper_tables.py'], cwd=ROOT, check=True)
