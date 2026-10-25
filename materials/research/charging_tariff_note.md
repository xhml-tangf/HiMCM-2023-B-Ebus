# Charging tariff and site-power bounds

## What is newly sourced

BC Hydro's approved April 2023 tariff has distinct large-general-service,
fleet overnight and demand-transition schedules. The digitized parameters in
`data/processed/bchydro_2023_charging_tariffs.json` preserve printed and PDF
page numbers, eligibility, dates and exclusions. The official PDF was readable
through web text extraction; a direct local download returned HTTP 403, so no
download hash is asserted. A second official BC Hydro financial statement
confirms that the parenthesized 1% rate rider is a refund, not a surcharge.
Use 22:00--06:00 as the overnight nonbilled-demand window. Zero billing demand
does not remove physical interconnection power, charger ports or energy cost.
RS1650's zero demand fee expires on 31 March 2026 in the historical schedule;
it is not a valid unchanged 2033 price assumption.

TransLink's original 2023 Business Plan p. 17 gives a **budget assumption** of
CAD 1.66/L diesel and 32.17 million L operational use. The latter covers a
broader operational boundary, not actual fixed-route bus-only consumption.
`translink_2023_energy_budget.csv` keeps that distinction. None of the regional
taxable-fuel volume figures are used as transit-bus consumption.

## Executed mathematical experiment

`python src/analyze_charging_tariffs.py` solves 243 CPU LP cases, plus two
crossover verification LPs. This is a conditional **aggregate relaxation** of
charging, with declared common availability windows. It is not an observed
100-bus fleet, a one-for-one replacement claim, a full-city schedule or a
whole-project economic score. The normalization is 100 distance-equivalent
units at the historical 40-ft 68,000 km/year assumption. The 1.37--2.0 kWh/km
range comes from the 2020 plan's projected onboard propulsion plus cabin heat;
the central 1.6 is assumed battery-delivered energy. Charging efficiencies
85/90/95%, site limits 2.5/3.5/5 MW, and 20:00, 22:00 or midnight returns before
06:00 are explicit design sensitivities. Meter-measured intensities must not
be divided by efficiency again. Daily demand is flat, so seasonal winter peaks
and duty energy cannot be certified from these annual averages.

For required daily grid energy E, nonbilled and billed available durations
h0 and h1, and site limit P, the minimum billed peak is
max(0,(E-h0*P)/h1) when h1>0; it is zero for a feasible wholly nonbilled window.
Total feasibility additionally requires E <= (h0+h1)*P. The LP optimum matches
this independent cumulative-energy certificate in every feasible case. A
second stage minimizes physical peak without worsening billed peak.
All monthly invoices include daily basic charges and the 1% rider refund.
The prior-winter minimum is a **total-bill floor** using the preceding eleven
billing periods, not an invented replacement peak demand; history expires.
It is inactive in the central steady-use case. Calendar-month billing periods,
secondary-voltage utility transformation and separately metered loads are
assumed. All April-2023 rates are frozen for a 365-day comparison, not a claim
about actual 2023 invoices or 2024--2033 forecasts.

## Numerical results and meaning

At 1.6 battery-kWh/km and 90% efficiency, the daily grid requirement is
33,120.24 kWh for the 100 distance-equivalent units. An eight-hour window needs
at least 4.140 MW of firm charging power. With a declared 5-MW supply, annual
bills are CAD 1.350m under RS1600, 0.905m under RS1640 and 1.113m under the
pre-April-2026 RS1650 price snapshot. Overnight billing is 32.96% below general
service; physical peak remains 4.140 MW even though billed peak is zero.

At only 3.5 MW, eight-hour-only charging is energy-infeasible. Extending the
window to 20:00--06:00 permits charging but creates 2.560 MW of daytime billing
demand on RS1640. Its annual CAD 1.285m exceeds RS1600's CAD 1.227m on the same
window. The two steady annual bills cross at a site limit of 3.598 MW, confirmed
by separate LP solves to less than 1e-5 CAD. Between 3.312 and 4.140 MW, each
additional firm kW saves CAD 594/year under RS1640 in this fixed-price,
fixed-window relaxation, before upgrade capital. This is an explicit mechanism
for valuing electrical capacity through service feasibility and future bills;
construction spending is not counted a second time as an economic benefit.

At the budget diesel price, the same normalized annual distance and historical
0.60 L/km rate imply CAD 6.773m of diesel fuel. The central overnight bill is
86.64% lower **for energy alone**. Maintenance, extra vehicles/drivers,
connection and charger capital, batteries, grants and residual value remain
separate; 86.64% is not the paper's economic score.

## Reproduce and limitations

Run the analysis, then `python src/plot_charging_tariffs.py` to regenerate the
included figure and table. Source/assumption metadata and all cases remain in
`results/charging_tariff_bounds.json`. Three discriminating regression checks
cover physical versus billed peak, feasible daytime extension, and the
eleven-month expiry of a historical winter invoice floor.
Real per-bus windows, charger-port sharing, site contracts, all-electric winter
energy and dated later tariffs remain necessary for an operational fleet plan.
Charging-capacity LP infeasibility is a valid necessary-condition failure under
the specified window; a relaxation pass does not prove vehicle feasibility.
