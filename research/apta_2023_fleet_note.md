# APTA 2023 and TransLink fleet evidence note

Checked 2026-10-18. Scope is TransLink/CMBC fixed-route buses. SeaBus,
HandyDART and rail are outside the 1,711--1,733 bridge. No 2023 HiMCM solution
or answer was consulted.

## Result

The APTA 2023 vehicle archive is listed on APTA's official page, but its bytes
were not obtained. The URL returns a Cloudflare browser challenge (HTTP 403),
and both curl and headless Edge stopped at that challenge. A second fetch path
confirmed that the URL serves an `application/zip` file, but could not return
the binary archive. Therefore no APTA 2023 model/age/length/fuel/count table
is generated, and the inclusion of TransLink or CMBC remains **MISSING**.

The TransLink 2023 FOI request log was obtained and hashed. It confirms the
scope and disposition of the six requested FOI numbers. It does **not** publish
their attachments: the 15-page log has no URI annotations or embedded links.

The currently published CMBC active/in-storage scan is FOI **2025/469**, not a
2023 release. It confirms the existing 2025 snapshot exactly: 1,733 active
buses and 63 buses in storage, effective 2025-11-18.

## APTA 2023

- Official page: <https://www.apta.com/news-research/public-transit-statistics/vehicle-database/>
- Archive URL: <https://www.apta.com/wp-content/uploads/2026/03/APTA-2023-Vehicle-Database.zip>
- Local bytes: not downloaded
- SHA-256: not available
- Access result: HTTP 403, `cf-mitigated: challenge`; no archive parse
- Project source ledger had already recorded `not_downloaded_due_network`

The APTA page says that the ZIP contains PDF and Excel files and that the
vehicle database reports manufacture date, manufacturer, model, length, fuel
type and number of vehicles. It also says that both U.S. and Canadian agencies
are included. That is a statement about possible coverage, not evidence that
TransLink or CMBC is a reporting agency.

The 2023 cutoff cannot be directly verified without the archive. The adjacent
APTA 2024 report describes a 2024-01-01 snapshot; the 2025 report uses the same
January 1 convention. This makes 2023-01-01 the expected cutoff, but that is a
series convention, not a direct 2023 source statement.

A search-index screen of the APTA 2024 PDF found the Toronto Transit Commission
(APTA ID 280) with detailed vehicle rows. Targeted searches of that same 2024
PDF found no TransLink, Coast Mountain Bus Company or Greater Vancouver agency
record. The APTA 2024 release announcement says it includes six Canadian
agencies. That adjacent screen shows why a national or Canadian title cannot
be used as proof of local coverage. It is not a complete workbook enumeration
and does not establish absence from the unavailable 2023 file.

## TransLink FOI 2023

Official log:
<https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/past-non-personal-access-requests/foi-requests-received-in-2023.pdf>

- SHA-256: `60c61527821fae42e456636777b4f9299a89cc72fabf74ce73fa0097d5fc1fba`
- Size: 123,449 bytes; 15 pages
- PDF annotations: 0
- Individual release URLs/attachments in the log: 0

| FOI | Closed | Scope | Logged disposition | Value for this audit |
|---|---|---|---|---|
| 2023-249 | 2023-06-13 | Every bus retired/decommissioned in the previous two years | Released in full | Retirement list only; attachment not public in the log |
| 2023-327 | 2023-07-20 | Number of spare buses, 2019--2023 | Released in full | Could establish spares if obtained; attachment is missing |
| 2023-375 | 2023-07-26 | Buses on road during peak service by category | Released in full | Peak deployment only; not total fleet or reserve ratio |
| 2023-409 | 2023-07-27 | Operator sign-up sheets for four transit centres | Released in full | Assignment sheets; no age/propulsion totals |
| 2023-411 | 2023-07-27 | Richmond Transit Centre operator sign-up sheet | Released in full | Assignment record; no fleet inventory |
| 2023-416 | 2023-07-27 | Blank September sign-up sheet for all depots | Released in full | Blank form; no fleet data |

`Released in full` is a disposition to the requester. It does not establish
web publication, attachment survival or permission for third-party download.
No 2023 FOI release page with an attachment was found on TransLink's public FOI
page or in the PDF's links.

## Current CMBC evidence and bridge comparison

The public recurring record is:
<https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/cmbc-fleet--active--instorage.pdf>

- SHA-256: `be0d3cd5f00b8217872705c5a46e290923debacfa6002c849041123630f839b2`
- Size: 373,331 bytes; 5 pages; image-only scan
- Memo date: 2025-11-20; effective timestamp: 2025-11-18 15:11:58
- FOI request shown on page 1: **2025/469**
- Active: 1,733; in storage: 63
- Active by class: 261 trolley, 22 battery, 535 hybrid, 365 CNG, 379 diesel,
  171 community-shuttle gasoline
- The rendered aggregate table, depot totals and storage total match
  `data/processed/cmbc_depot_snapshot_2025.csv` exactly.

| Fleet measure | Value | Status |
|---|---:|---|
| Detailed 2022 category snapshot | 1,711 | Observed 2022 total; reused as the bridge lower endpoint under a no-net-drop assumption |
| Existing 2023 bridge point | 1,725 | Derived from 1,711 plus 14 zero-emission-equivalent vehicles; not observed |
| Existing 2023 bridge interval | 1,711--1,733 | Derived interval; not an observed 31 December 2023 roster |
| CMBC active fleet on 2025-11-18 | 1,733 | Observed in FOI 2025/469 and the processed depot table |
| CMBC vehicles in storage on 2025-11-18 | 63 | Observed in the same scan; separate from the 1,733 active total |
| APTA 2023 aggregate for TransLink | MISSING | 2023 ZIP could not be downloaded or parsed |

The exact APTA difference is unavailable. Thus APTA neither confirms nor
rejects the 1,725 derived point or the 1,711--1,733 interval. The existing
bridge and 2025 snapshot remain the strongest reproducible evidence currently
available, with their original derivation limits unchanged.

## Still missing

- APTA 2023 ZIP bytes, SHA-256, workbook/PDF inventory and data-cutoff text.
- Whether APTA 2023 contains TransLink, CMBC or Greater Vancouver records.
- The requested 2023 APTA rows by model, manufacture year, age, length, power,
  active count and total count.
- Public attachments for FOI 2023-249, 2023-327 and 2023-375.
- A 31 December 2023 operator fleet register by vehicle, status, depot, age and
  propulsion.
- Verified 2023 spare policy/count, garage allocation and charging capacity.

If the official archive is later supplied locally, reproduce the extraction
with:

```powershell
python src/audit_apta_2023.py --archive path\to\APTA-2023-Vehicle-Database.zip
```

The script writes `apta_2023_translink_records.csv` and
`apta_2023_translink_models.csv` only when it finds parseable TransLink/CMBC
vehicle rows. With no archive it records the blocked status without inventing
records. The current run used the locally obtained official FOI log and CMBC
scan:

```powershell
python src/audit_apta_2023.py --foi-log tmp\foi-requests-2023.pdf --cmbc-pdf tmp\cmbc-fleet-active-instorage.pdf
```

Machine-readable results are in `results/apta_2023_fleet_audit.json`; the
source/status ledger is `data/processed/apta_2023_translink_evidence.csv`.
