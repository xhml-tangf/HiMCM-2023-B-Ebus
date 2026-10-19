"""One service-km ledger for conditional transition costs and emissions.

Shares are policy assumptions, not commissioning or dispatch certificates.
Annual kilometre values may be scalars or numpy arrays for the scenario grid.
"""

# Construction starts in 2024; the published six-to-eight-year delivery range
# first yields a conversion-ready wave in 2030. This is a planning gate, not a
# claim that every site or grid connection will be ready on that date.
READINESS_2024_33 = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.50, 0.85, 1.0)


def service_ledger(annual_km, shares=None):
    """Return annual service whose electric share is capped by readiness.

    The default list is deliberately not a linear financial ramp: services do
    not become electric before a site can deliver energy. The list is a shared
    scenario for O&M and emissions, and must be replaced by site commissioning
    records before it can be used as an operational certificate.
    """
    shares = list(shares if shares is not None else READINESS_2024_33)
    if len(shares) != 10 or any(not 0 <= a <= 1 for a in shares):
        raise ValueError("ten annual electric shares between zero and one required")
    return [dict(year=2024 + i, electric_share=a, baseline_km=annual_km,
                 conventional_km=annual_km * (1 - a), electric_km=annual_km * a)
            for i, a in enumerate(shares)]


def operating_costs(ledger, conventional_rate, electric_rate):
    return ({r['year']: r['baseline_km'] * conventional_rate for r in ledger},
            {r['year']: r['conventional_km'] * conventional_rate
             + r['electric_km'] * electric_rate for r in ledger})


def readiness_retirements(initial_count, shares=None):
    """Integer retirements whose cumulative capacity follows readiness."""
    shares = list(shares if shares is not None else READINESS_2024_33)
    prior = 0
    result = {}
    for year, share in zip(range(2024, 2034), shares):
        target = round(initial_count * share)
        result[year] = target - prior
        prior = target
    if prior != initial_count:
        raise ValueError("final readiness target must retire the full initial count")
    return result


def use_emissions(ledger, fuel_kg_per_km):
    """Undiscounted tonnes; include conventional service during the ramp."""
    return dict(
        baseline_operating_t=sum(r['baseline_km'] * fuel_kg_per_km / 1000 for r in ledger),
        plan_operating_t=sum((r['conventional_km'] * fuel_kg_per_km
                              + r['electric_km'] * .019) / 1000 for r in ledger),
        baseline_maintenance_t=sum(r['baseline_km'] * .0524 / 1000 for r in ledger),
        plan_maintenance_t=sum((r['conventional_km'] * .0524
                                + r['electric_km'] * .0675) / 1000 for r in ledger))
