"""English manuscript from executed results, with matching Markdown source."""
from pathlib import Path
import json, html, re, os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase.pdfmetrics import stringWidth
from PIL import Image as PILImage
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'results/claude_plan';OUT=ROOT/'paper/claude_plan'
OUT.mkdir(parents=True,exist_ok=True)
TEAM_CONTROL_NUMBER=os.environ.get('HIMCM_TEAM_NUMBER','__________').strip() or '__________'
CONTENT_WIDTH=475
def read(n):return json.loads((DATA/n).read_text(encoding='utf-8'))
def num(x,d=0):return f'{x:,.{d}f}'
def mil(x):return num(x/1e6,1)
def plain(s):return html.escape(str(s))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyX',fontName='Times-Roman',fontSize=12,leading=14.5,spaceAfter=7.5,alignment=TA_JUSTIFY))
styles.add(ParagraphStyle(name='HeadX',fontName='Times-Bold',fontSize=16,leading=19,textColor=colors.HexColor('#18384a'),spaceAfter=12))
styles.add(ParagraphStyle(name='CenterHeadX',parent=styles['HeadX'],alignment=TA_CENTER))
styles.add(ParagraphStyle(name='SummaryTitleX',fontName='Times-Bold',fontSize=14,leading=17,alignment=TA_CENTER,spaceAfter=5))
styles.add(ParagraphStyle(name='ControlX',fontName='Times-Roman',fontSize=9,leading=11,alignment=TA_CENTER,spaceAfter=1))
styles.add(ParagraphStyle(name='ControlNumberX',fontName='Times-Bold',fontSize=18,leading=21,alignment=TA_CENTER,textColor=colors.HexColor('#a51c30'),spaceAfter=3))
styles.add(ParagraphStyle(name='TabX',fontName='Helvetica',fontSize=9.5,leading=11.2))
styles.add(ParagraphStyle(name='THX',parent=styles['TabX'],fontName='Helvetica-Bold',textColor=colors.white))
styles.add(ParagraphStyle(name='CapX',fontName='Times-Italic',fontSize=10,leading=12,spaceAfter=8,alignment=TA_CENTER))
styles.add(ParagraphStyle(name='EqX',fontName='Courier',fontSize=9.5,leading=12.5,leftIndent=6,spaceAfter=10,backColor=colors.HexColor('#eef4f6'),borderPadding=6))
pages=[]
def page(title):
    style=styles['CenterHeadX'] if title=='Contents' else styles['HeadX']
    pages.append(dict(title=title,flow=[Paragraph(plain(title),style)],md=[]))


def summary_page():
    flow=[Paragraph('TEAM CONTROL NUMBER',styles['ControlX']),
          Paragraph(plain(TEAM_CONTROL_NUMBER),styles['ControlNumberX']),
          Paragraph('PROBLEM CHOSEN',styles['ControlX']),
          Paragraph('B',styles['ControlNumberX']),
          Paragraph('2023<br/>HiMCM',styles['ControlX']),
          Spacer(1,4),Paragraph('SUMMARY SHEET',styles['SummaryTitleX']),
          HRFlowable(width='100%',thickness=.8,color=colors.HexColor('#18384a'),spaceBefore=2,spaceAfter=8)]
    pages.append(dict(title='Summary Sheet',flow=flow,md=[]))
def text(s):
    pages[-1]['flow'].append(Paragraph(s,styles['BodyX']))
    md=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',r'[\2](\1)',s)
    pages[-1]['md'].append(re.sub('<[^>]+>','',md))
def eq(s):
    pages[-1]['flow'].append(Paragraph(plain(s).replace('\n','<br/>'),styles['EqX']))
    pages[-1]['md'].append('\n'.join('    '+x for x in s.splitlines()))
def table(headers,rows,widths):
    cells=[[Paragraph(plain(x),styles['THX'] if i==0 else styles['TabX']) for x in r] for i,r in enumerate([headers]+rows)]
    scale=CONTENT_WIDTH/sum(widths)
    t=Table(cells,colWidths=[w*scale for w in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#154c60')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white])]))
    pages[-1]['flow'] += [t,Spacer(1,10)]
    pages[-1]['md']+=['| '+' | '.join(map(str,headers))+' |','| '+' | '.join('---' for _ in headers)+' |']
    pages[-1]['md']+=['| '+' | '.join(map(str,r))+' |' for r in rows]
def figure(name,caption,width=CONTENT_WIDTH):
    path=DATA/name
    with PILImage.open(path) as im:w,h=im.size
    width=min(width,CONTENT_WIDTH)
    pages[-1]['flow'] += [Image(str(path),width=width,height=width*h/w),Paragraph(plain(caption),styles['CapX'])]
    pages[-1]['md'].append(f'![{caption}](../../results/claude_plan/{name})')


class TocLine(Flowable):
    def __init__(self,title,number,width):
        super().__init__();self.title=title;self.number=str(number);self.width=width
    def wrap(self,availWidth,availHeight):return (availWidth,15)
    def draw(self):
        c=self.canv;c.setFillColor(colors.HexColor('#18384a'));c.setFont('Times-Roman',10.5)
        title=self.title;number=self.number;y=2
        tw=stringWidth(title,'Times-Roman',10.5);nw=stringWidth(number,'Times-Roman',10.5)
        if tw>self.width-nw-20:
            while title and stringWidth(title+'...','Times-Roman',10.5)>self.width-nw-20:title=title[:-1]
            title=title+'...';tw=stringWidth(title,'Times-Roman',10.5)
        c.drawString(0,y,title);c.drawRightString(self.width,y,number)
        start=tw+5;end=self.width-nw-5;dot=stringWidth('.','Times-Roman',10.5)
        count=max(0,int((end-start)/dot))
        c.drawString(start,y,'.'*count)


def build():
    m=read('vancouver_main.json');pat=read('patterns.json');b=read('benchmark.json')['summary']
    impact=read('impacts.json');c=impact['central'];strict=impact['strict_zero_source_scenario'];g=c['grants']
    road=read('roadmap_budget.json')['annual'];schedule=read('roadmap_schedule.json')
    comparison=read('comparators.json');sensitivity=read('sensitivity.json');site_screen=read('site_cost_screen.json');S=m['stations']
    cta=comparison['chicago']['cohort']
    london=next(x for x in comparison['london']['cohort_scenarios'] if x['life_cap_years_scenario']==17)
    summary_page()
    text('<b>Charging Ahead: A Two-Constant, Timetable-Preserving Transition</b>')
    text('Modeling solution for 2023 HiMCM Problem B. Prepared 22 October 2026.')
    text('We model electric buses using usable range R and full-charge duration T. Every included timetable trip must be served exactly once at its published time. Exact diesel matching provides a lower bound; range blocks, resource-aware linking and station search construct feasible electric duties.')
    text(f'The existing fall-2023 TransLink data provide the primary case. The representative day has <b>{num(m["trips"])} trips</b>. At R = 270 km and T = 60 min, the exact diesel baseline is <b>{num(m["N_d"])} buses</b>; the electric heuristic uses <b>{num(m["vehicles"])} buses and {len(S)} daytime charging nodes</b>. Across all 25 service patterns, the largest tested electric requirement is <b>{num(c["Ne"])} active buses</b>. These are conditional model outputs, without spares or depot certification.')
    text(f'On 300 independent random instances, the improved heuristic equals the exact optimum in {b["p1_optimal_improved"]} cases; its maximum excess is {b["p1_max_gap"]} buses. All 200 infinite-range tests agree with exhaustive search. A three-block counterexample reveals why the reference algorithm must preserve incoming charging-detour mileage through the next block.')
    text(f'Against a homogeneous fossil-diesel counterfactual, the stated vehicle-production and operating boundary avoids {num(c["ten_year_avoided_t"]/1000,1)} kt CO2e over ten years. Net present savings are CAD {mil(g[0]["NPV"])}, {mil(g[1]["NPV"])} and {mil(g[2]["NPV"])} million under 0%, 25% and 50% support of the eligible capital increment. The zero-source electricity case is reported separately from the grid-average diagnostic.')
    cc=comparison['chicago'];lc=comparison['london']
    text(f'The same engine processed recovered 2023 CTA and London bus timetables: representative-day diesel/electric pairs are {num(cc["Nd"])}/{num(cc["Ne"])} in Chicago and {num(lc["Nd"])}/{num(lc["Ne"])} in London. Each nested-route illustration reaches zero modeled diesel trips by 2033. Comparator financial screens use common transferred parameters and are not local investment forecasts. Full AI transcripts are missing, so contest disclosure remains incomplete.')
    text('<b>Keywords:</b> electric bus scheduling; matching; charging sites; lifecycle boundary; external funding.')
    page('Contents');toc=pages[-1]
    page('I. Problem Statement, Evidence, and Scope')
    text('The problem asks for ecological and financial models, up to 50% external funding, a ten-year all-electric transition by 2033 in three metropolitan areas, and a one-page official letter [1]. We reconstruct a 2024-2033 scenario around 2023 service. Later publications are retrospective evidence, not information silently assumed available in 2023.')
    table(['Area','Eligibility and fleet evidence','Implemented boundary'],[
        ['Vancouver','2,642,825 CMA residents in 2021 [2]; mixed fleet in 2023 [3]','Timetable scheduling and scenario accounting'],
        ['Chicago','2,746,388 city residents in 2020 [4]; 1,875-bus year-end inventory [5]','2023 CTA bus timetable plus separate fleet cohorts'],
        ['London','Greater London census population exceeds 8 million [6]; 950 electric of 8,643 buses [7]','2023 bus trips touching Greater London; separate TfL cohorts']],[70,240,182])
    text('Service preservation means exact departure and arrival obligations. Capacity is assumed equal between modeled diesel and electric vehicles. Individual passenger observations are absent, so exact trip coverage does not prove that actual crowding limits are satisfied.')
    text('The problem defines an e-bus through zero-emissions electricity for propulsion and accessories. A low annual grid factor does not certify this. We show a zero-source case conditional on verified procurement and a nonzero grid-average diagnostic. The transferred electricity intensity includes electric cabin heat.')
    text('The architecture follows the user-supplied Claude specification and reference program [15], within the EVSP family studied by Wen et al. [20]. Codex assistant sessions (deepseek-flash, following earlier GPT-6 turns) assisted implementation, verification and drafting [16]. Contributions are disclosed in the appendix; missing transcript text is not invented.')
    page('II. Data, Assumptions, and Notation')
    text('The recovered TransLink feed is 23SEP_20231020, declared for 4 September-31 December 2023 [8]. The adapter uses the existing cleaned trip manifest, calendar and exceptions. Times beyond 24:00 remain on the service-day clock. Stop IDs are not merged by name.')
    table(['Input','Central treatment','Evidence status'],[
        ['Times / endpoints','Preserved trip obligations','Published schedule, not actual operations'],
        ['Trip distance','Audited upper interval endpoint','Derived bound; lower endpoint tested'],
        ['Travel matrix','1.35 x great-circle km; 30 km/h','Assumed road detour and speed'],
        ['Candidate sites',str(m.get('source_nodes',534))+' endpoint IDs','Coordinates observed; buildability unknown'],
        ['Trolley service','Retain cap47/cap70 proxy separately','Existing proxy, not propulsion roster'],
        ['Capacity / vehicle types','Homogeneous, equal capacity','No individual load or axle verification'],
        ['R / T','270 km / 60 min','Chosen usable range and charge duration'],
        ['Energy / efficiency','1.60 kWh/km / 90%','Historical all-electric transfer [9] / assumption'],
        ['Night / depot','Full at first trip; no pullout or pullin','Single-day boundary; cross-day closure absent'],
        ['Charging capacity','Unlimited in solver; count slots afterward','No utility or site certificate']],[115,178,199])
    text('The travel-time matrix is metric. This ensures a route via a charger is not faster than the direct transfer, which is necessary for the diesel lower-bound proof. A regression test shows that arbitrary nonmetric inputs can violate that bound.')
    text('All 25 distinct service patterns are evaluated separately. We use their maximum fleet requirement and retain their frequencies over 119 days. Annual activity is multiplied by 365/119. It is a seasonal extrapolation, not observed annual mileage.')
    eq('B_use = epsilon*R; B = B_use/u\nP_battery[kW] = 60*B_use/T_minutes\nP_grid = P_battery/eta')
    text('With u = 0.8, the central battery is 540 kWh and grid-side charging power is 480 kW. The factor 60 corrects the minute/hour mismatch. A partial battery still occupies the charger for T, but receives only the energy consumed since its last full charge.')
    page('III. Timetable-Preserving Scheduling Model')
    text('Trip i has origin o_i, destination d_i, departure s_i, arrival e_i and service length ell_i. A bus duty is a sequence of trip IDs and C(v) charge tokens. Each trip appears exactly once. Station set S has at most K nodes.')
    eq('Direct connection i -> j:\ne_i + tau(d_i,o_j) <= s_j\nu_i + w(d_i,o_j) + ell_j <= R\nu_j = u_i + w(d_i,o_j) + ell_j')
    eq('Connection through c in S:\nu_i + w(d_i,c) <= R\ne_i + tau(d_i,c) + T + tau(c,o_j) <= s_j\nw(c,o_j) + ell_j <= R\nu_j = w(c,o_j) + ell_j')
    text('The first trip begins fully charged at its origin and must itself fit within R. Both charging detour legs consume range. P1 minimizes duties for fixed S; P2 also chooses S. The heuristic solves these objectives approximately and returns feasible upper bounds.')
    text('The diesel compatibility graph includes i-to-j whenever its direct time condition holds. Positive trip durations make it acyclic. A matching of M arcs joins n trips into n-M paths; every path cover supplies such a matching. Thus maximum matching gives the exact minimum diesel fleet [17].')
    eq('N_d = n - maximum_matching_size\nPVR = max_t count{s_i <= t < e_i}\nN_e >= N_d >= PVR  (metric travel times)')
    text('We seed a matching using short connections, then search the complete compatibility graph until no augmenting path exists. Small cases use Hopcroft-Karp seeds; large cases use a greedy seed and disjoint-tree batched augmentations. Time indexing excludes only chronologically impossible edges. No final lower bound uses a truncated waiting horizon. Infinite range invokes this exact routine.')
    page('III.A. Correcting the Reference Algorithm')
    text('The reference links fixed blocks using their internal distance and a charging detour. However, incoming station-to-block mileage persists until the next charge. Pairwise feasibility alone does not account for that state.')
    text('Consider R = 10 km and T = 5 min, with a charger at A and node B 3 km away. Three well-separated blocks are A-to-A (10 km), B-to-B (7 km) and A-to-A (10 km). Both reference edges pass. But the middle block requires 3 + 7 + 3 = 13 km between charges. An independent validator rejects the one-bus chain; the repaired and exact solutions use two buses.')
    eq('Required condition for an interior block b:\nw(previous_charger,start_b) + dist_b\n+ w(end_b,next_charger) <= R')
    text('The corrected routine propagates actual incoming mileage, chooses a feasible charger, and prunes incompatible outgoing edges before rematching. Each repair removes an edge and therefore terminates. The pruning is conservative if a later matching changes the predecessor. Consequently fixed-block matching is a relaxation, and the repaired solution is not claimed exact.')
    text('Greedy blocks use range-first, time-first and balanced scores plus seeded restarts. Additional 55%- and 75%-range partitions expose intermediate charging opportunities while remaining feasible at the actual R. Small-instance experiments add bounded relocate and swap moves. A charging-aware pass reserves station-access mileage.')
    text('Site search ranks charge-compatible trip pairs, evaluates the top 12 of 534 candidates, greedily adds a site and performs exchanges. The ranking samples 50 successors per trip in the network experiment. It does not restrict the diesel graph. A cap of four daytime sites is supplied; no globally optimal site claim follows.')
    text('The independent validator reconstructs every trip, travel leg, charge interval and mileage state from output tokens. It also checks energy closure: daytime replenishment plus final overnight replenishment equals total vehicle travel. Malformed tokens, duplicate trips and missed departures are rejected.')
    page('III.B. Validation and Optimality Gaps')
    table(['Experiment','Executed result','Meaning'],[
        ['Six-trip specification sample','P1=1; K=1 picks node2; K=0 gives2','MILP cross-check passed'],
        ['Incoming-detour counterexample','Invalid reference chain rejected; optimum2','Regression test'],
        ['300 small P1 cases',str(b['p1_optimal_baseline'])+' base / '+str(b['p1_optimal_improved'])+' improved optimal','MILP and exhaustive agreement'],
        ['Largest improved excess',str(b['p1_max_gap'])+' buses','Not a worst-case guarantee'],
        ['60 P2 cases, four nodes, K=2',str(b['p2_optimal'])+' match the exact optimum','Heuristic site selection remains imperfect'],
        ['200 diesel-limit cases','200 match exhaustive search','Exact fallback verified']],[155,168,169])
    text('The independent random population uses eight trips, three nodes, symmetric integer travel times from 5 to 20 minutes and shortest-path closure. Distances are 0.7 times those metric times. Departures span 0-160 minutes. P2 uses four nodes. Seed streams and generators are recorded; these results do not claim to reproduce the unspecified original Claude random stream.')
    text('The small arc MILP has start/end arcs, direct arcs, charge arcs and per-trip used-range variables. Every trip has one incoming and one outgoing arc. Direct arcs propagate distance with arc-specific big-M constants. Charging arcs enforce reachability and reset distance. P2 adds binary station variables and a cardinality bound. A separate continuous relaxation gives an LP lower bound.')
    text('Only solver status optimal is reported as an exact optimum. Every extracted MILP duty is independently replayed. Regression tests also cover midnight, equal arrival/departure times, both charger detours, energy replenishment, grant limits, terminal values and negative environmental outcomes.')
    text('On the network, we report the difference from N_d and never infer optimality from successful validation. In sensitivity analysis, an incumbent from smaller R or larger T is reused only after revalidation. Raw search counts remain available, making heuristic instability visible.')
    page('IV. Vancouver Results Across Service Patterns')
    text(f'The reference day is {m["date"]}. Across all patterns, the largest tested electric fleet is {num(c["Ne"])}; the largest exact diesel baseline is {num(c["Nd"])}. Every pattern uses the same chosen daytime sites. Trolley-proxy service and reserve vehicles are outside these counts.')
    table(['Pattern','Date','Trips','N_d','PVR','N_e','Days'],[
        [r['pattern_id'],r['date'],num(r['trips']),r['N_d'],r['PVR'],r['vehicles'],r['occurrence_days']]
        for r in pat['patterns']],[47,85,70,60,60,60,50])
    text(f'The 25 checks represent {num(pat["trip_instances"])} non-trolley-proxy trip instances across {pat["days"]} days. Each isolated-day duty passes. This does not prove that the same physical buses can recharge and reposition between consecutive days; an overnight availability model is still required.')
    page('IV.A. Charging Sites and Recharge Requirements')
    table(['Node / stop ID','Stop name','Peak daytime charges'],[
        [str(x['node'])+' / '+x['stop_id'],x['name'],impact['peaks'].get(str(x['node']),0)]
        for x in m['selected_stops']],[100,307,85])
    text('Internal nodes are zero-based; the P1/P2 text interface prints one-based IDs. Output files retain original stop IDs, coordinates and names. These nodes are mathematical candidates, not surveyed construction sites.')
    text(f'<b>Physical interpretation:</b> one selected roadside node requires as many as {max(impact["peaks"].values())} simultaneous chargers. This is not a plausible claim of available curb space. The unlimited-capacity result is a scheduling benchmark; it requires a different site design or capacity-constrained re-optimization before deployment.')
    table(['Quantity','Executed value','Boundary'],[
        ['Reference service distance',num(m['service_km'],1)+' km','Upper trip-distance bounds'],
        ['Electric / diesel deadhead',num(m['deadhead_km'],1)+' / '+num(m['diesel_deadhead_km'],1)+' km','Different matching solutions'],
        ['Reference daytime charges',m['daytime_charge_count'],'Fixed-duration full resets'],
        ['Annual service mileage',num(impact['annual_service_km']/1e6,2)+' million km','Fall frequency extrapolation'],
        ['Annual grid energy',num(c['annual_grid_kwh']/1e6,2)+' GWh','Energy ledger closes'],
        ['Daytime / overnight energy',num(impact['daytime_grid_kwh']/1e6,2)+' / '+num(impact['overnight_grid_kwh']/1e6,2)+' GWh','Energy actually replenished'],
        ['Daytime charger positions',c['daytime_plugs'],'Sum of per-site daily maxima']],[170,155,167])
    text(f'With 480 kW per occupied daytime charger, summing site-specific maxima gives {num(c["daytime_plugs"]*c["charger_grid_kw"]/1000,1)} MW. This is an installed-power screen, not a coincident system peak. An assumed eight-hour nightly window implies an aggregate overnight lower bound of {num(impact["night_power_lower_bound_kw"]/1000,1)} MW; individual bus availability remains unverified.')
    text('The solver assumes unlimited plugs, but the validator counts how many the output would require. The financial model pays for those positions and an overnight allowance. Actual land, curb space, firm power, connection lead times and daily vehicle turnaround can still make the deployment infeasible.')
    text('Diesel matching minimizes fleet size only. Its deadhead is not a minimum-deadhead or least-cost baseline. The financial comparison therefore inherits this secondary-objective limitation.')
    page('IV.B. Fleet Sensitivity')
    figure('fleet_sensitivity.png','Figure 1. Validated fleet upper bounds at fixed selected sites, and the greedy station-addition trace.')
    text('The true optimum cannot increase when R increases or T decreases. The heuristic can miss that property because different block partitions hide different opportunities. We retain and validate earlier feasible incumbents under relaxed parameters. Both raw and retained counts are recorded.')
    text('The station curve shows the greedy addition path. Subsequent exchanges may change the final set. A plateau is specific to the tested candidates and partitions, not proof that further infrastructure is useless. A separate cost screen minimizes bus list price plus a fixed site allowance over the delivered trace; it excludes charger power, grid connection, land and maintenance, and does not solve the mixed-cost location model globally.')
    text(f'Its minimum-cost trace points have K = {site_screen["cases"]["vancouver"]["recommended"]["K"]} for Vancouver, {site_screen["cases"]["chicago"]["recommended"]["K"]} for Chicago and {site_screen["cases"]["london"]["recommended"]["K"]} for London. These are screening outcomes over the same candidate traces, not certified station counts.')
    table(['Additional check','Electric buses','Interpretation'],[
        [r['case'],r['vehicles'],'Independent assumption rerun'] for r in sensitivity['other']],[200,85,207])
    text('Infinite range is solved by exact diesel matching. A production fleet would also require reserve vehicles, reliability margin, compatible body types and cross-day closure. Neither the active fleet nor its ratio to N_d can be compared directly with inventory statistics containing maintenance and spare buses.')
    page('V. Ecological Model and Results')
    eq('Grid energy = (D_service + D_deadhead)*epsilon/eta\nDiesel operating CO2e = D_diesel*EF_diesel\nElectric operating CO2e = grid_energy*gamma_t\nBattery production CO2e = N_e*B*e_battery')
    text('The accounting uses the same annualized service on both sides and retains separate deadhead. Initial production is counted for every replacement vehicle, including any electric fleet expansion. Battery production recurs at replacement years. A common assumed body-production proxy of 70 t per vehicle does not cancel when fleet sizes differ.')
    text(f'The grid-average case avoids {num(c["ten_year_avoided_t"]/1000,1)} kt CO2e in ten years. The conditional zero-source case avoids {num(strict["ten_year_avoided_t"]/1000,1)} kt. Initial electric production is {num(c["initial_embodied_electric_t"]/1000,1)} kt, versus {num(c["initial_embodied_diesel_t"]/1000,1)} kt for the modeled diesel replacement fleet.')
    grid_rates=impact['grid_decline_cases']
    text(f'If the grid factor falls by 3% or 5% annually, the ten-year avoided total changes from {num(grid_rates[0]["result"]["ten_year_avoided_t"]/1000,1)} kt to {num(grid_rates[1]["result"]["ten_year_avoided_t"]/1000,1)} or {num(grid_rates[2]["result"]["ten_year_avoided_t"]/1000,1)} kt. This is a scenario path, not a local grid forecast.')
    text('The operating baseline is homogeneous fossil diesel, using a retrospective 2024 planning factor of 1.58 kgCO2e/km [18]. It is not the actual 2023 TransLink fuel mix. Sensitivities include lower-carbon fuel factors and more carbon-intensive electricity; negative results are not clipped.')
    table(['Tailpipe pollutant','Annual avoided tonnes','Scope'],[
        [r['pollutant'],num(r['annual_avoided_t_low'],2)+' to '+num(r['annual_avoided_t_high'],2),'Transferred factors [19], diesel travel only']
        for r in impact['pollution']],[110,150,232])
    text('Annual pollutant ranges repeat under the same activity assumption; the ten-year totals are ten times these values and are retained in JSON. They are screening ranges, not a forecast of local air-quality monitoring.')
    text('These pollutant ranges are scenario bounds, not statistical confidence intervals. Electric buses eliminate modeled exhaust emissions but not tyre, brake or road particles. Construction emissions, vehicle disposal and noise are excluded. The result is a vehicle-production and operating comparison, not a complete locally measured lifecycle assessment.')
    text('Battery carbon payback divides initial fleet battery emissions by annual operating savings when those savings are positive. It is a diagnostic, not a substitute for the full time ledger: extra bodies and future batteries can change the cumulative break-even point.')
    page('VI. Financial Model')
    text('The immediate-replacement experiment purchases the compared fleets at the start of 2024 and holds service for ten years. Money is constant 2023 CAD with a 3% real discount rate. Historical diesel prices are rebased using the project CPI table [13]. There is no initial old-bus resale credit because no disposition ledger exists.')
    eq('CAPEX_e = N_e*(body_price+B*battery_price)+infrastructure\nEligible = max(0,CAPEX_e-CAPEX_d)\nGrant = phi*Eligible; 0 <= phi <= 0.50\nNPV(phi) = PV_d-PV_e_gross+phi*Eligible')
    text('External support is a transfer. It improves agency affordability without changing gross resource cost. Eligible conversion cost is explicitly the positive initial capital increment over new diesel replacement, not a claim about a real grant program. No additional grant is assigned to replacement batteries in this comparison.')
    table(['Financial parameter','Central value','Status'],[
        ['Electric bus installed','CAD1.20 million','2023 screen [12]; initial battery included'],
        ['Battery price / decline','CAD180/kWh / 3% yearly','Assumed split and learning'],
        ['Diesel price','CAD1.66/L','2023 budget [14], not invoices'],
        ['Fuel use / electricity','0.60 L/km / CAD0.10/kWh','Historical transfer [9] / all-in assumption'],
        ['Diesel / electric maintenance','CAD0.60 / 0.40 per km','Assumption, excludes energy'],
        ['Battery / body life','8 / 12 years','Scenario with sensitivity'],
        ['Infrastructure life / upkeep','20 years / 2% yearly','Scenario'],
        ['Infrastructure costing','Site allowance + power-scaled plugs + overnight allowance','All components require local quotes']],[160,165,167])
    text('Both sides receive terminal asset values. Electric body, current battery and infrastructure use separate remaining lives. Diesel receives its remaining vehicle value. Replacement batteries are priced in their actual replacement year. This prevents asymmetric treatment of long-lived assets.')
    eq('phi_star = max(0,(PV_e_gross-PV_d)/Eligible)\nTCO = discounted net cost / discounted own vehicle-km')
    text('A required phi_star above 0.50 is infeasible under the cap, not silently clipped. Payback is the first nonnegative cumulative balance that stays nonnegative after later replacement costs. Final asset recovery is identified separately from operating savings.')
    page('VI.A. Financial and Carbon Results')
    table(['Grant share','Grant CAD m','Agency PV CAD bn','NPV savings CAD m','Payback year'],[
        [f'{100*x["phi"]:.0f}%',mil(x['grant']),num(x['agency_pv']/1e9,3),mil(x['NPV']),
         x['payback_year'] if x['payback_year'] is not None else '>10 / none'] for x in g],[80,95,115,115,87])
    text(f'Gross electric present cost is CAD {num(c["pv_electric_gross"]/1e9,3)} billion, versus CAD {num(c["pv_diesel"]/1e9,3)} billion for diesel. Break-even support is {num(c["phi_star"]*100,1)}% of the eligible initial increment. The 50% cap is sufficient in this scenario: {str(c["phi_star_within_cap"]).lower()}. These are conditional screens, not contract forecasts.')
    figure('environment_finance.png','Figure 2. Cumulative cash savings, with terminal credits in the final year, and emissions avoided within the stated boundary.')
    text(f'Gross discounted TCO is CAD {num(c["electric_tco_per_discounted_vehicle_km"],2)} per electric vehicle-km and CAD {num(c["diesel_tco_per_discounted_vehicle_km"],2)} per diesel vehicle-km. Own-mileage denominators differ because deadhead differs; the service obligations remain the same.')
    page('VI.B. Financial Sensitivity')
    figure('tornado.png','Figure 3. One-at-a-time 25%-grant NPV sensitivity; dashed line is the central scenario.',width=470)
    text('The parameter ledger distinguishes primary observations, historical transfers and explicit assumptions. Energy and diesel prices, battery cost and learning, discount rate, lives, infrastructure allowances and baseline fuels are varied. R/T cases also recompute the operating schedule, rather than imposing a new battery cost on a frozen fleet.')
    text('The all-in electricity price is a screening allowance, not an hourly tariff model. In particular, a historically temporary zero-demand tariff is not extended through 2033. Local interconnection quotes, construction schedules and body-specific costs are still missing.')
    text('A fossil-diesel counterfactual can overstate the benefit relative to continued low-carbon fuels. High grants can improve the agency balance while total resource cost remains higher. Those distinct questions should not be hidden in an unexplained weighted score.')
    conservative=impact['zero_diesel_deadhead_cost_lower_bound']
    text(f'A deliberately optimistic diesel cost bound removes all diesel deadhead while retaining the same fleet. The 25%-grant NPV then falls to CAD {mil(conservative["grants"][1]["NPV"])} million. The central financial result therefore depends materially on the diesel assignment, which minimizes fleet size rather than travel cost.')
    page('VII. Ten-Year Nested-Route Roadmap')
    text('Routes are ranked by service productivity per electric bus, penalized by the route electric/diesel fleet ratio. With common unit factors, this is a transparent benefit-per-capital proxy. It is not measured age priority: vehicle-to-route ages are absent.')
    eq('score_r = (daily_service_km_r/N_e_r)*(N_d_r/N_e_r)\nE_y = first ceil(number_of_routes*y/10) ranked routes\nstock_y = max(stock_(y-1),N_e(E_y))')
    text('Every year reruns electric scheduling on its nested subset and diesel matching on the complement. All selected daytime sites are available in stage one. High-water stock prevents negative purchases when trip regrouping reduces requirements. Final purchases include any additional buses needed by another tested pattern.')
    table(['Year','Routes','New BEBs','Electric stock','Diesel','Gross CAD m'],[
        [r['year'],r['route_count'],r['new_buses'],r['electric_stock'],r['diesel'],mil(r['gross_investment'])] for r in road],
        [57,60,80,100,80,115])
    text('This is a required-budget illustration, not an optimum under an externally supplied annual cap. Intermediate stages are checked on the representative day; all 25 patterns are checked at full conversion. Station commissioning, reserve buses, age-based retirements and seasonal intermediate schedules remain gates.')
    text('Complete annual route lists and trip duties are included in the result package. The endpoint contains no modeled diesel trips by 2033, but this does not certify a funded, buildable citywide program.')
    page('VII.A. Staged Investment and Implementation Gates')
    figure('roadmap.png','Figure 4. Purchased electric stock, representative-day residual diesel requirements, and annual required investment.')
    table(['Year','Grant25 CAD m','Grant50 CAD m','Agency50 CAD m','Battery replacement CAD m'],[
        [r['year'],mil(r['grant25']),mil(r['grant50']),mil(r['self_funded50']),mil(r['battery_replacement'])] for r in road],
        [55,102,102,110,123])
    text('The staged budget counts first-stage infrastructure, new vehicles and subsequent battery replacements. Its annual eligible increment deducts a counterfactual diesel replacement allowance. It is separate from the immediate-replacement NPV experiment.')
    text(f'The staged 50%-grant cash ledger ends at CAD {mil(road[-1]["cumulative_cash_grant50"])} million, including operating savings and avoided diesel purchases. The staged production-minus-operating estimate ends at {num(road[-1]["cumulative_partial_avoided_t"]/1000,1)} kt CO2e; this is a different boundary from the immediate-replacement ten-year total and must not be substituted for it.')
    text('Purchase releases should follow three gates: firm charging capacity commissioned; winter range and equal capacity validated on assigned routes; and actual vehicle ages and home depots reconciled with the route groups. These gates can change the illustrated order.')
    comparator_pages(m,c,cta,london)
    page('IX. Strengths, Limitations, and Completion Status')
    table(['Requirement','Status','Boundary'],[
        ['P1/P2 and specification sample','Implemented','Resource correction and independent replay'],
        ['Small exact comparisons','Implemented','MILP, LP and exhaustive tests'],
        ['Vancouver 25 patterns','Implemented conditionally','Approximate transfers; isolated-day duties'],
        ['Ecology and 0/25/50% grants','Implemented as scenarios','Transferred factors and explicit exclusions'],
        ['Ten-year Vancouver stages','Partial illustration','Representative day; required budgets, no hard cap'],
        ['Three cities at trip level','Implemented conditionally','Real 2023 timetables; assumed transfer travel'],
        ['Clean power and sites','Unverified','No hourly source match or utility capacity'],
        ['Full AI disclosure','Incomplete','Full Claude conversation and prior outputs missing']],[165,130,197])
    text('The strengths are exact trip obligations, explicit detour accounting, a valid diesel lower bound, replayable duties and unified service/energy/cost ledgers. The counterexample shows why successful example outputs are insufficient evidence of correctness.')
    text('The limitations are homogeneous capacity, assumed deadhead paths, unlimited charging capacity, no pullout/pullin, no repeated-day fleet closure and heuristic site selection. A worst isolated day does not guarantee that buses can reset between days. Seasonal annualization is not a full-year observation.')
    text('Financial inputs are not invoices, and transferring 40-ft energy and cost parameters to heterogeneous service is only a screening approximation. Diesel deadhead is a minimum-fleet assignment, not the cheapest diesel assignment. The current comparison is not an optimal economic baseline.')
    text('The additional Chicago and London trips close the timetable-input gap. Local investment forecasts, funded annual caps, route-specific retirement ages and complete contest disclosure remain unresolved. These require actual local inputs and original AI records.')
    page('X. Letter to Transportation Officials')
    text('To the Transportation Planning Team, Metro Vancouver')
    text('<b>Subject: A conditional, timetable-preserving electric-bus transition</b>')
    text('Dear Transportation Officials,')
    text(f'We recommend using an independently validated timetable model to begin planning a 2033 transition. Under a 270-km usable-range and 60-minute charge assumption, the recovered service patterns require up to {num(c["Ne"])} active battery buses alongside retained trolley-proxy service. The fleet-minimizing search retains {len(S)} daytime charging nodes; the transparent bus-plus-site screen suggests starting with {site_screen["cases"]["vancouver"]["recommended"]["K"]}. These are not construction-ready sites.')
    text(f'With the stated cost assumptions, the staged 50%-grant cash request totals CAD {mil(sum(r["grant50"] for r in road))} million; the immediate-replacement screen yields ten-year net present savings of CAD {mil(g[2]["NPV"])} million. The immediate production-plus-operating difference is approximately {num(c["ten_year_avoided_t"]/1000,1)} thousand tonnes CO2e, while the separately bounded staged ledger reaches {num(road[-1]["cumulative_partial_avoided_t"]/1000,1)} thousand tonnes. Actual fuel mix, local quotes and utility studies could materially change those figures.')
    text('The illustrative stages establish capacity and early route groups in 2024-2026, expand compatible groups in 2027-2030, and close remaining obligations in 2031-2033. The representative timetable is preserved at each step, but intermediate seasonal schedules, retirement ages and construction milestones still require review.')
    text('Before procurement, obtain the bus-to-depot roster and winter duty tests, survey candidate charging locations, and secure firm utility capacity. Verify zero-emissions electricity for both propulsion and cabin systems. A low average grid factor alone does not satisfy that condition.')
    text('Use the delivered duties and annual budgets as an auditable starting point. Make purchase releases contingent on operational and funding gates, with explicit provision for reserve vehicles, driver arrangements and installation delays.')
    text('Sincerely,<br/>The Modeling Team')
    references()
    page('Report on Use of AI')
    text('<b>Status: incomplete disclosure. This appendix is outside the solution page count.</b>')
    text('<b>1. Anthropic Claude</b>')
    text('Purpose: user-supplied modeling specification and reference Python program. The specification labels the model "Claude Sonnet 5.5." This is preserved as user-provided metadata; actual model identity and the original conversation are not independently verified. Both received files are archived byte-for-byte and hashed.')
    text('<b>Query record:</b> NOT SUPPLIED. <b>Output record:</b> only the archived specification and reference program are available; the complete original answers are absent.')
    text('<b>2. Codex assistant</b>')
    text('Purpose: evidence review, equation checking, corrected scheduling and accounting, experiment execution, source checks and drafting. The current session used deepseek-flash; earlier turns in the same thread were labeled GPT-6. The user requested implementation of Claude\'s plan with the existing data and later supplied the reference-program path.')
    text('<b>Query record:</b> the current task history exists in the application UI, but complete machine-readable user messages and outputs are not included in the submitted folder. They therefore are not represented as verbatim replacements here.')
    text('<b>Verification performed</b>')
    text('The reference was not assumed correct. A counterexample exposed missing incoming deadhead mileage, and the charging-power unit conversion was corrected. Independent simulations, exact small-instance solutions, source checks and visible limitation labels were used to verify generated work. No external 2023 HiMCM solution manuscript was used.')
    text('The official problem includes a disclosure example requiring exact queries and complete outputs [1]. The full Claude conversation is absent. Existing project request logs are artifact maps, not complete prior-output transcripts. This appendix therefore cannot honestly be labeled the complete required report.')
    text('<b>Pre-submission completion</b>')
    text('Append exact user-visible queries and complete outputs for the Claude design conversation and other relevant AI-assisted stages, confirm versions when available, and obtain human verification of references, calculations, team number and rules. Missing transcripts must not be replaced by invented dialogue or summaries called verbatim. The accompanying materials/research/claude_plan directory preserves the supplied files and hashes for inspection.')
    emit(toc)


def comparator_pages(v,vc,cta,cohort_london):
    cities=['chicago','london'];m={x:read(f'{x}/main.json') for x in cities}
    impacts={x:read(f'{x}/impacts.json')['standardized_transfer'] for x in cities}
    days={x:read(f'{x}/days.json')['days'] for x in cities}
    page('VIII. Three-City Comparison')
    text('CTA publishes a complete GTFS feed [21]. We recovered its 3 May 2023 snapshot [22]. For London, we extracted the 10 June 2023 BODS snapshot from the UBDC national archive [23] and retained scheduled bus trips touching a Greater London stop (ATCO prefix 490 [24]). Both comparator weeks are 12-18 June 2023; Vancouver remains a fall case.')
    table(['Representative-day field','Vancouver','Chicago','London'],[
        ['Date',v['date'],m['chicago']['date'],m['london']['date']],
        ['Trips',num(v['trips']),num(m['chicago']['trips']),num(m['london']['trips'])],
        ['Concurrency lower bound',v['PVR'],m['chicago']['PVR'],m['london']['PVR']],
        ['Exact diesel N_d',v['N_d'],m['chicago']['N_d'],m['london']['N_d']],
        ['Feasible electric N_e',v['vehicles'],m['chicago']['vehicles'],m['london']['vehicles']],
        ['N_e / N_d',num(v['vehicles']/v['N_d'],3),num(m['chicago']['vehicles']/m['chicago']['N_d'],3),num(m['london']['vehicles']/m['london']['N_d'],3)],
        ['Daytime nodes',len(v['stations']),len(m['chicago']['stations']),len(m['london']['stations'])],
        ['Service km',num(v['service_km']),num(m['chicago']['service_km']),num(m['london']['service_km'])],
        ['Electric deadhead km',num(v['deadhead_km']),num(m['chicago']['deadhead_km']),num(m['london']['deadhead_km'])],
        ['Daytime charges',v['daytime_charge_count'],m['chicago']['daytime_charge_count'],m['london']['daytime_charge_count']],
        ['Largest tested active EV fleet',vc['Ne'],impacts['chicago']['Ne'],impacts['london']['Ne']]
    ],[198,98,98,98])
    text('Each comparator retains every included fixed-time trip, including times beyond midnight [25]. All seven dates are independently replayed with one selected site set. The search uses eight screened candidates, up to five block partitions and K <= 4. Above 3,000 blocks, each block-station pair retains at most 256 timed successors. This limits memory and solution quality; feasible counts remain upper bounds. Diesel matching still checks its complete graph.')
    text('The four London candidate stop IDs lie within 169 m in the Trafalgar Square/Charing Cross interchange; they are one charging district for engineering purposes and four nodes in the optimization and cost ledger. Chicago has two endpoint nodes about 171 m apart. Neither set is a surveyed construction location.')
    for city in cities:
        audit=m[city]['source_manifest']
        text(f'{city.title()} data exclusions: {audit["rejected_nonpositive_duration"]} nonpositive-duration records; {audit.get("frequency_templates_excluded_in_scope",audit.get("frequency_templates_excluded_before_geographic_filter",0))} nonexact frequency templates. Exact-frequency records are expanded at their source headways ({audit.get("exact_frequency_trips_generated",0)} generated fixed-time trips). No unknown departure times are invented.')
    text('Comparator trip distances use 1.35 times the polyline through scheduled stops. This is a stated proxy, not measured road distance or a guaranteed upper bound. Different service seasons, distance evidence and homogeneous capacity assumptions prevent interpreting the ratios as an intrinsic ranking of cities.')
    page('VIII.A. Common-Parameter Transfer and Annual Stages')
    text('Comparators use common 2023-CAD cost and energy assumptions, annualizing one week by 365/7. The BC grid factor is a diagnostic transfer, not a local factor. These are method comparisons, not local tariffs, grants or investment forecasts.')
    table(['Scenario screen','Chicago','London'],[
        ['Annual grid energy (GWh)',num(impacts['chicago']['annual_grid_kwh']/1e6,1),num(impacts['london']['annual_grid_kwh']/1e6,1)],
        ['Daytime simultaneous plug sum',impacts['chicago']['daytime_plugs'],impacts['london']['daytime_plugs']],
        ['10-year avoided (kt CO2e)',num(impacts['chicago']['ten_year_avoided_t']/1000,1),num(impacts['london']['ten_year_avoided_t']/1000,1)],
        ['0% grant NPV (CAD m)',mil(impacts['chicago']['grants'][0]['NPV']),mil(impacts['london']['grants'][0]['NPV'])],
        ['25% grant NPV (CAD m)',mil(impacts['chicago']['grants'][1]['NPV']),mil(impacts['london']['grants'][1]['NPV'])],
        ['50% grant NPV (CAD m)',mil(impacts['chicago']['grants'][2]['NPV']),mil(impacts['london']['grants'][2]['NPV'])]
    ],[252,120,120])
    figure('threecity_comparison.png','Figure 5. Representative-day diesel/electric fleets and common-parameter 25% grant NPV.',width=360)
    a=read('chicago/roadmap_budget.json')['annual'];b=read('london/roadmap_budget.json')['annual']
    table(['Year','CTA new EV','CTA diesel','CTA gross m','London new EV','London diesel','London gross m'],[
        [x['year'],x['new_buses'],x['diesel'],mil(x['investment']),y['new_buses'],y['diesel'],mil(y['investment'])] for x,y in zip(a,b)
    ],[44,64,62,76,82,74,90])
    text('Stages rerun electric and residual-diesel scheduling, and stock never decreases. All grant and funding columns, route lists and duties are supplied separately. All modeled fixed-time obligations become electric by 2033.')
    text('These are required budgets, not solutions under known annual spending caps. Initial power and site capacity, vehicle ages, construction dates, zero-source electricity and local prices remain unverified.')
    page('VIII.B. Speed, Sensitivity, and Inventory Boundary')
    figure('comparator_sensitivity.png','Figure 6. Fixed-site feasible upper bounds by range and charge time (top), plus greedy station traces and charging-aware final solutions (bottom). Raw heuristic counts remain in JSON.')
    table(['Inventory-renewal comparison','Chicago','London'],[
        ['Inventory scope','1,875 at year end','8,643 at 31 March 2023'],
        ['Initial electric evidence','25, inferred June state','950 observed in audit'],
        ['Life cap tested here','17 years','17 years'],
        ['Minimum peak annual renewal',cta['minimum_peak_annual_purchases'],cohort_london['minimum_peak_annual_slot_renewal']],
        ['Total renewed positions',cta['minimum_total_purchases_with_known_beb_renewals'],cohort_london['total_slots_renewed']]
    ],[252,120,120])
    text('The original cohort optimizers are also re-executed; London includes 12- and 14-year life sensitivities. Fleet stock contains reserves and existing technologies, whereas timetable counts are active homogeneous vehicles. London geographic bus coverage also differs from its TfL contract inventory. The two outputs must not be merged into an unsupported purchase total.')
    text('Different route lengths, operating windows and endpoint geometry change the route scores and charging opportunities. Actual local costs and route-assigned ages could reverse the illustrated order. Four candidate nodes, or even a smaller selected set, do not establish physical charging sufficiency.')


def references():
    page('References: data and problem sources')
    refs=[
        ('1','COMAP. Problem B: Charging Ahead with E-buses, 2023 HiMCM problem statement and AI-use policy.','https://www.contest.comap.org/highschool/contests/himcm/2023_Problems/2023_HiMCM_Problem_B.pdf'),
        ('2','Statistics Canada. Population and growth rate of census metropolitan areas, 2011 to 2016 and 2016 to 2021, Table 2. Released 9 February 2022. Cached HTML used; live link unavailable 22 October 2026.','https://www150.statcan.gc.ca/n1/daily-quotidien/220209/t002a-eng.htm'),
        ('3','TransLink. Metro Vancouver diesel buses transitioning to cleaner renewable fuel. December 2023.','https://www.translink.ca/news/2023/december/metro%20vancouver%20diesel%20buses%20transitioning%20to%20cleaner%20renewable%20fuel'),
        ('4','U.S. Census Bureau. Chicago city, Illinois, 2020 census.','https://data.census.gov/profile/Chicago_city%3B_Illinois?g=160XX00US1714000'),
        ('5','U.S. DOT NTD. 2022-2025 NTD Annual Data - Vehicles (Age Distribution), CTA ID50066; 2023 report-year extract. Accessed 22 October 2026.','https://data.transportation.gov/d/6abt-uhgq'),
        ('6','Greater London Authority. 2021 Census resources for Greater London.','https://data.london.gov.uk/census'),
        ('7','TfL. Bus Fleet Audit, 31 March2023. Detailed body/cohort tables reconcile fleet totals.','https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf'),
        ('8','TransLink. GTFS23SEP_20231020, immutable mirror commit eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b. Publisher metadata and hashes retained.','https://github.com/JaydenCWong/JAAM-project/tree/eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b/backend/engine/translink_data'),
        ('9','TransLink. Low Carbon Fleet Transition Plan,2020. Appendix C-1 all-electric energy; Appendix D-1 historical costs.','https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf'),
        ('10','Reboucas and Cieplinski. Quantifying avoided greenhouse gas emissions by e-buses in Latin America. ICCT,2024. Transferred battery factor.','https://theicct.org/wp-content/uploads/2024/08/ID-118-%E2%80%93-E-bus-radar_final2.pdf')]
    for n,t,u in refs:text(f'[{n}] {plain(t)} <link href="{plain(u)}" color="#154c60">Source</link>.')
    page('References: accounting and methods')
    refs=[
        ('11','Government of British Columbia. Electricity emission intensity factors for grid-connected entities; 2023 integrated-grid value 11.3 tCO2e/GWh used. Page accessed 22 October 2026.','https://www2.gov.bc.ca/gov/content/environment/climate-change/data/electricity'),
        ('12','TransLink. Zero Emissions Bus Fleet Technology Update, 29 June 2023 Mayors Council agenda, PDF p.29. CAD1.2m per bus and CAD460-610k for one on-route charger.','https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf'),
        ('13','Bank of Canada. All-items Consumer Price Index, series V41690973 (2002=100), 2019-2025; accessed 22 October 2026.','https://www.bankofcanada.ca/valet/observations/V41690973/json?start_date=2019-01-01&end_date=2025-12-31'),
        ('14','TransLink. 2023 Business Plan, Operating and Capital Budget, Attachment 1; PDF p.17. Created 6 December 2022.','https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2023_business_plan_operating_and_capital_budget.pdf'),
        ('15','Anthropic Claude. User-supplied specification and reference code, received 22 October 2026; full transcript and model-version verification missing. The label "Claude Sonnet 5.5" is user metadata, not an independently verified version.',''),
        ('16','OpenAI Codex assistant sessions (deepseek-flash; earlier thread turns labeled GPT-6). Implementation, validation and writing assistance, 22 October 2026. See the AI appendix.',''),
        ('17','Bunte and Kliewer. An overview on vehicle scheduling models. Public Transport1,299-317 (2009). Metadata verified with author university.','https://www.wiwiss.fu-berlin.de/fachbereich/bwl/pwo/kliewer/forschung/testpub/article_-an-overview-on-vehicle-scheduling-models-in-public-transport/index.html'),
        ('18','TransLink. Zero-Emission Fleet Transition Playbook (ZEFTP), 28 November 2024 Mayors Council agenda package. Retrospective operating emissions.','https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf'),
        ('19','EMEP/EEA. Air pollutant emission inventory guidebook2023, road transport. Existing source-derived factor table.','https://www.eea.europa.eu/publications/emep-eea-guidebook-2023'),
        ('20','Wen, Linde, Ropke, Mirchandani and Larsen. An adaptive large neighborhood search heuristic for the Electric Vehicle Scheduling Problem. Computers & Operations Research76,73-83 (2016).','https://doi.org/10.1016/j.cor.2016.06.013')]
    for n,t,u in refs:
        link=f' <link href="{plain(u)}" color="#154c60">Source</link>.' if u else ''
        text(f'[{n}] {plain(t)}{link}')
    page('References: acquired comparator timetables')
    refs=[
        ('21','Chicago Transit Authority. GTFS scheduled-service documentation. The official source publishes only its current package.','https://www.transitchicago.com/developers/gtfs/'),
        ('22','CTA feed archived by OpenMobilityData, snapshot 3 May 2023, service through 31 July 2023. Downloaded bytes and SHA-256 retained.','https://openmobilitydata-data.s3.us-west-1.amazonaws.com/public/feeds/chicago-transit-authority/165/20230503/gtfs.zip'),
        ('23','Urban Big Data Centre. Bus Open Data Service GTFS archive, version 2023.1. The 10 June 2023 member was extracted with ZIP CRC verification.','https://zenodo.org/records/14779119'),
        ('24','Department for Transport. NaPTAN area code 490 identifies Greater London. Geographic filtering does not establish a TfL fleet assignment.','https://beta-naptan.dft.gov.uk/article/atco-codes-in-use'),
        ('25','GTFS Schedule Reference. Times beyond midnight and the distinction between exact schedules and frequency-based services.','https://gtfs.org/documentation/schedule/reference/')]
    for n,t,u in refs:text(f'[{n}] {plain(t)} <link href="{plain(u)}" color="#154c60">Source</link>.')
    text('Both archive acquisitions are retrospective research in October 2026. Their service dates, not download dates, define the modeled schedules. Current 2026 downloads were retained as fallback evidence but are not substituted for 2023 timetables.')
    text('The London archive is a national collection. Only scheduled bus trips touching at least one Greater London stop are included. Railway, metro, tram and coach categories are excluded by route type; frequency templates and any rejected malformed trips are separately recorded.')


def emit(toc):
    entries=[(i+1,p['title']) for i,p in enumerate(pages) if p is not toc and i>1]
    for number,title in entries:toc['flow'].append(TocLine(title,number,CONTENT_WIDTH))
    toc['md']=[f'{title} ...... {i}' for i,title in entries]
    story=[]
    for i,p in enumerate(pages):
        if i:story.append(PageBreak())
        story.extend(p['flow'])
    def header(canvas,doc):
        canvas.saveState();canvas.setFont('Times-Roman',9.5);canvas.setFillColor(colors.HexColor('#243746'))
        canvas.drawString(60,818,f'Team # {TEAM_CONTROL_NUMBER}')
        canvas.drawRightString(535,818,f'Page {doc.page} of {len(pages)}')
        canvas.setStrokeColor(colors.HexColor('#8fa3ad'));canvas.setLineWidth(.6);canvas.line(60,809,535,809)
        canvas.restoreState()
    doc=SimpleDocTemplate(str(OUT/'charging_ahead_claude_plan.pdf'),pagesize=A4,
        leftMargin=60,rightMargin=60,topMargin=78,bottomMargin=55,
        title='Charging Ahead: A Two-Constant, Timetable-Preserving Transition',author='Modeling Team')
    doc.build(story,onFirstPage=header,onLaterPages=header)
    md='\n\n'.join('# '+p['title']+'\n\n'+'\n\n'.join(p['md']) for p in pages)
    (OUT/'charging_ahead_claude_plan.md').write_text(md+'\n',encoding='utf-8')
    (DATA/'manuscript_page_plan.json').write_text(json.dumps([dict(page=i+1,title=p['title']) for i,p in enumerate(pages)],indent=2))
    print('Planned pages:',len(pages),'solution pages:',len(pages)-1)


if __name__=='__main__':build()
