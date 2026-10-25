"""Freeze a lightweight delivery manifest and explicit requirement status."""
from pathlib import Path
import hashlib,json,sys,platform
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    out=ROOT/'results/claude_plan'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    checks=read(out/'verification.json')
    cities={c:read(out/c/'verification.json') for c in ['chicago','london']}
    paths=list((ROOT/'src').glob('claude_*.py'))
    paths += [ROOT/'scripts'/n for n in ['benchmark_claude_plan.py','run_claude_plan.py','analyze_claude_plan.py',
              'prepare_comparator_gtfs.py','run_comparator_plan.py','verify_claude_plan.py','verify_comparator_plan.py','build_claude_paper.py']]
    paths += list(out.rglob('*.json'))+[p for p in (ROOT/'paper/claude_plan').glob('*') if '_before_reformat' not in p.name]
    for name in ['references_audit.json','timetable_acquisition.md','AI_DISCLOSURE_CHECKLIST.md','README.md']:
        p=ROOT/'materials/research/claude_plan'/name
        if p.exists():paths.append(p)
    p=ROOT/'materials/research/himcm_exemplars/format_notes.md'
    if p.exists():paths.append(p)
    for city in ['chicago','london']:paths+=list((ROOT/'data/processed'/f'{city}_claude_gtfs').glob('*'))
    paths=[p for p in paths if p.is_file() and p.name!='delivery_manifest.json']
    result=dict(status='IMPLEMENTED_AND_VERIFIED_UNDER_STATED_ASSUMPTIONS',python=platform.python_version(),
        assistant_models=['deepseek-flash (final continuation)','GPT-6 (earlier turns in this thread)'],
        verification=checks,comparator_verification=cities,
        requirements={
          'P1_P2_solver':'implemented; heuristic feasible upper bounds, no global-optimum claim',
          'MILP_LP_exhaustive':'executed; benchmark.json',
          'three_real_timetables':'2023 Vancouver, CTA and London geographic bus scope',
          'service_validation':'25 Vancouver patterns plus 7 dates per comparator; all included fixed-time trips',
          'ecology_finance_grant_0_25_50':'computed; comparator values are standardized transfers',
          'ten_year_route_transition':'10 independently checked representative-day stages per city; no hard annual budget supplied',
          'population_and_mixed_fleet':'dated sources retained; inventories differ from active timetable boundaries',
          'PDF_pages':'inspect pdf_quality.json for actual page and layout validation',
          'full_AI_disclosure':'INCOMPLETE: exact original Claude and earlier AI dialogues not supplied',
          'buildable_deployment':'NOT_CLAIMED: depot, driver, capacity, utility, site, local price and funding inputs remain absent'},
        sha256={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (out/'delivery_manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Manifest:',len(paths),'files; verified',list(cities))
