"""Produce a citation ledger for the 25 references used by the manuscript."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'materials/research/claude_plan/references_audit.json'

refs=[
 (1,'Problem B: Charging Ahead with E-buses, 2023 HiMCM problem statement and AI-use policy','https://www.contest.comap.org/highschool/contests/himcm/2023_Problems/2023_HiMCM_Problem_B.pdf','metadata_checked','Full title checked against problem source; access date recorded in paper',[]),
 (2,'Statistics Canada, Population and growth rate of census metropolitan areas, Table 2','https://www150.statcan.gc.ca/n1/daily-quotidien/220209/t002a-eng.htm','partial','Cached HTML available; live URL unavailable during 2026 check',['materials/sources/raw/statistics_canada_2021_cma_population.html']),
 (3,'TransLink, Metro Vancouver diesel buses transitioning to cleaner renewable fuel','https://www.translink.ca/news/2023/december/metro%20vancouver%20diesel%20buses%20transitioning%20to%20cleaner%20renewable%20fuel','metadata_checked','Public release title checked; no local copy',[]),
 (4,'U.S. Census Bureau, Chicago city 2020 census profile','https://data.census.gov/profile/Chicago_city%3B_Illinois?g=160XX00US1714000','metadata_checked','Public source checked; no local copy',[]),
 (5,'U.S. DOT NTD, 2022-2025 NTD Annual Data - Vehicles (Age Distribution), CTA ID50066','https://data.transportation.gov/d/6abt-uhgq','supported_local','2023 report-year extract retained; dataset title changes over time',['materials/sources/raw/cta_2023_age_distribution.json']),
 (6,'Greater London Authority, 2021 Census resources','https://data.london.gov.uk/census','metadata_checked','Public portal; no local copy',[]),
 (7,'TfL, Bus Fleet Audit, 31 March 2023','https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf','supported_local','Fleet total and 950 electric positions checked in cached PDF',['materials/sources/raw/tfl_2023_bus_fleet_audit.pdf']),
 (8,'TransLink GTFS feed 23SEP_20231020, mirror commit eb584b1','https://github.com/JaydenCWong/JAAM-project/tree/eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b/backend/engine/translink_data','supported_local','Publisher metadata and local feed retained; third-party mirror is not the operator download endpoint',['materials/sources/raw/vancouver_gtfs_2023/feed_info.txt']),
 (9,'TransLink, Low Carbon Fleet Transition Plan','https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf','supported_local','Retained PDF and extracted pages',['materials/sources/raw/translink_2020_fleet_plan.pdf']),
 (10,'ICCT, Quantifying avoided GHG emissions by e-buses in Latin America','https://theicct.org/wp-content/uploads/2024/08/ID-118-%E2%80%93-E-bus-radar_final2.pdf','supported_local','Retained PDF; direct fetch may be unavailable',['materials/sources/raw/icct_2024_ebus_lca_method.pdf']),
 (11,'Government of British Columbia, Electricity emission intensity factors for grid-connected entities','https://www2.gov.bc.ca/gov/content/environment/climate-change/data/electricity','partial','Current official page updated after 2023; the 2023 11.3 tCO2e/GWh value is retained from the project factor ledger',['data/processed/transit_air_quality_factors_2023.json']),
 (12,'TransLink, Zero Emissions Bus Fleet Technology Update, 29 June 2023 Mayors Council agenda','https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf','supported_local','PDF page 29 checked; parent agenda package dated June 29 2023',['materials/sources/raw/translink_2023_june_technology_update.pdf']),
 (13,'Bank of Canada, All-items Consumer Price Index V41690973, 2002=100','https://www.bankofcanada.ca/valet/observations/V41690973/json?start_date=2019-01-01&end_date=2025-12-31','supported_local','Monthly series cached and annual rebasing table retained',['materials/sources/raw/canada_cpi_monthly_2019_2025.json','data/processed/canada_cpi_annual_2019_2025.csv']),
 (14,'TransLink, 2023 Business Plan, Operating and Capital Budget, Attachment 1','https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2023_business_plan_operating_and_capital_budget.pdf','supported_local','Cached PDF and p.17 budget context retained',['materials/sources/raw/translink_2023_business_plan.pdf']),
 (15,'Anthropic Claude, user-supplied specification and reference Python program','','user_supplied','Archived byte-for-byte; full original conversation and exact model version not supplied',['materials/research/claude_plan/spec_original.md','materials/research/claude_plan/solver_reference_original.py']),
 (16,'Codex assistant sessions used for implementation, validation and drafting','','self_disclosure','Earlier turns labeled GPT-6; final continuation identified deepseek-flash; full transcripts are not available in the project',[]),
 (17,'Bunte and Kliewer, An overview on vehicle scheduling models, Public Transport 1, 299-317 (2009)','https://www.wiwiss.fu-berlin.de/fachbereich/bwl/pwo/kliewer/forschung/testpub/article_-an-overview-on-vehicle-scheduling-models-in-public-transport/index.html','metadata_checked','Bibliographic metadata checked; no local full text',[]),
 (18,'TransLink, Zero-Emission Fleet Transition Playbook, 28 November 2024 Mayors Council package','https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf','supported_local','Cached summary and agenda metadata retained',['materials/sources/raw/translink_2024_playbook_summary.pdf']),
 (19,'EEA, EMEP/EEA air pollutant emission inventory guidebook 2023, road transport','https://www.eea.europa.eu/publications/emep-eea-guidebook-2023','partial','Derived air-quality factor table is local; original guidebook is not retained in full',['data/processed/transit_air_quality_factors_2023.csv']),
 (20,'Wen, Linde, Ropke, Mirchandani and Larsen, Adaptive large neighborhood search for EVSP','https://doi.org/10.1016/j.cor.2016.06.013','metadata_checked','DOI and bibliographic record checked; no local full text',[]),
 (21,'CTA, GTFS/Scheduled Service Data documentation','https://www.transitchicago.com/developers/gtfs/','metadata_checked','Official current-feed documentation checked; historical archive is separate',[]),
 (22,'OpenMobilityData, CTA GTFS archive snapshot 3 May 2023','https://openmobilitydata-data.s3.us-west-1.amazonaws.com/public/feeds/chicago-transit-authority/165/20230503/gtfs.zip','supported_local','65,120,098-byte ZIP retained; all member CRCs passed',['materials/sources/raw/comparator_timetables/chicago_2023.zip']),
 (23,'Urban Big Data Centre, Bus Open Data Service GTFS archive, version 2023.1','https://zenodo.org/records/14779119','supported_local','19,549,809,163-byte archive catalogued; 10 June 2023 member extracted and inner ZIP CRCs passed',['materials/sources/raw/comparator_timetables/london_2023.zip','materials/sources/raw/comparator_timetables/zenodo_record.json']),
 (24,'UK Department for Transport, NaPTAN ATCO area codes in use','https://beta-naptan.dft.gov.uk/article/atco-codes-in-use','metadata_checked','Area code 490 = Greater London checked; geographic filter is not a fleet roster',[]),
 (25,'GTFS Schedule Reference, times beyond 24:00 and exact_times','https://gtfs.org/documentation/schedule/reference/','metadata_checked','Specification text checked; no local copy',[]),
]
if __name__=='__main__':
    entries=[]
    for rid,title,url,status,note,paths in refs:
        evidence=[]
        for rel in paths:
            p=ROOT/rel
            evidence.append(dict(path=rel,exists=p.exists(),sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None))
        entries.append(dict(id=rid,title=title,url=url or None,status=status,note=note,evidence=evidence))
    OUT.write_text(json.dumps(dict(checked_on='2026-10-22',entries=entries,
        boundary='A metadata check is not a claim that every web resource was available on every later date. Full Claude transcripts remain missing.'),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('wrote',OUT)
