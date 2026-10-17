"""Auditable fleet-transition primitives. No missing city inputs are imputed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Trip:
    trip_id: str
    route: str
    direction: str
    start_min: int
    end_min: int
    distance_km: float
    baseline_capacity: int
    start_location: str
    end_location: str
    accessible: bool
    allowed_vehicle_classes: tuple[str, ...]


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    depot: str
    vehicle_class: str
    capacity: int
    battery_kwh: float
    usable_fraction: float
    initial_kwh: float
    kwh_per_km_winter: float
    electric_propulsion: bool
    electric_accessories: bool
    accessible: bool
    minimum_soc_fraction: float


@dataclass(frozen=True)
class Assignment:
    trip_id: str
    vehicle_id: str


@dataclass(frozen=True)
class Charge:
    vehicle_id: str
    depot: str
    start_min: int
    end_min: int
    power_kw: float
    efficiency: float


@dataclass(frozen=True)
class Depot:
    name: str
    charger_slots: int
    charger_power_kw: float
    grid_limit_kw: float
    commissioned_year: int
    physical_bus_spaces: int


@dataclass
class Check:
    status: str
    errors: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


def check_schedule(
    trips: Iterable[Trip] | None,
    vehicles: Iterable[Vehicle] | None,
    assignments: Iterable[Assignment] | None,
    charges: Iterable[Charge] | None,
    depots: Iterable[Depot] | None,
    *,
    year: int,
    peak_capacity_by_route_direction: dict[tuple[str, str], int] | None = None,
    spare_by_depot: dict[str, int] | None = None,
    deadhead_minutes: dict[tuple[str, str], int] | None = None,
    deadhead_km: dict[tuple[str, str], float] | None = None,
) -> Check:
    """Exact trip/SOC/site checks. Missing essential inputs yield UNVERIFIED.

    Trip continuity requires a supplied deadhead-time matrix between locations.
    A zero value is permitted only if the data source establishes colocation.
    """
    required = {"trip_manifest": trips, "vehicle_register": vehicles,
                "assignments": assignments, "charges": charges, "depots": depots,
                "peak_capacity": peak_capacity_by_route_direction,
                "spare_policy": spare_by_depot, "deadhead_time_matrix": deadhead_minutes,
                "deadhead_distance_matrix": deadhead_km}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        return Check("UNVERIFIED", missing=missing)
    trips = list(trips)
    vehicles = list(vehicles)
    assignments = list(assignments)
    charges = list(charges)
    depots = list(depots)
    t = {x.trip_id: x for x in trips}
    v = {x.vehicle_id: x for x in vehicles}
    d = {x.name: x for x in depots}
    errors: list[str] = []
    if not trips or not vehicles or not depots:
        return Check("UNVERIFIED", missing=["nonempty_trip_vehicle_depot_data"])
    if len(t) != len(trips) or len(v) != len(vehicles) or len(d) != len(depots):
        errors.append("duplicate trip, vehicle, or depot identifier")
    if year >= 2033:
        for bus in vehicles:
            if not (bus.electric_propulsion and bus.electric_accessories):
                errors.append(f"non-electric 2033 fleet vehicle {bus.vehicle_id}")
    by_trip: dict[str, list[str]] = {k: [] for k in t}
    by_vehicle: dict[str, list[Trip]] = {k: [] for k in v}
    for a in assignments:
        if a.trip_id not in t or a.vehicle_id not in v:
            errors.append(f"unknown assignment {a.trip_id}/{a.vehicle_id}")
            continue
        trip, bus = t[a.trip_id], v[a.vehicle_id]
        by_trip[a.trip_id].append(a.vehicle_id)
        by_vehicle[a.vehicle_id].append(trip)
        if bus.vehicle_class not in trip.allowed_vehicle_classes:
            errors.append(f"incompatible vehicle class on {trip.trip_id}: {bus.vehicle_class}")
        if trip.accessible and not bus.accessible:
            errors.append(f"accessible vehicle missing on {trip.trip_id}")
        if year >= 2033 and not (bus.electric_propulsion and bus.electric_accessories):
            errors.append(f"non-electric vehicle or accessory on {trip.trip_id}")
    for trip_id, assigned in by_trip.items():
        if not assigned:
            errors.append(f"trip {trip_id} has no assigned vehicle")
        if sum(v[vid].capacity for vid in assigned) < t[trip_id].baseline_capacity:
            errors.append(f"capacity shortfall on {trip_id}")
    actual_peak: dict[tuple[str, str], int] = {}
    for key in peak_capacity_by_route_direction:
        endpoints = sorted({m for trip in trips if (trip.route, trip.direction) == key
                            for m in (trip.start_min, trip.end_min)})
        for a, b in zip(endpoints, endpoints[1:]):
            concurrent = [trip for trip in trips
                          if (trip.route, trip.direction) == key
                          and trip.start_min < b and trip.end_min > a
                          and by_trip[trip.trip_id]]
            actual_peak[key] = max(actual_peak.get(key, 0),
                                   sum(v[vid].capacity for trip in concurrent
                                       for vid in by_trip[trip.trip_id]))
    for key, baseline in peak_capacity_by_route_direction.items():
        if actual_peak.get(key, 0) < baseline:
            errors.append(f"route-direction {key} peak capacity {actual_peak.get(key,0)} < {baseline}")
    events: dict[str, list[tuple[int, int, str, object]]] = {k: [] for k in v}
    for vid, assigned in by_vehicle.items():
        assigned.sort(key=lambda x: x.start_min)
        for trip in assigned:
            events[vid].append((trip.start_min, trip.end_min, "trip", trip))
    for c in charges:
        if c.vehicle_id not in v or c.depot not in d:
            errors.append(f"unknown charging vehicle/site {c.vehicle_id}/{c.depot}")
            continue
        site = d[c.depot]
        if v[c.vehicle_id].depot != c.depot:
            errors.append(f"charge at wrong depot for {c.vehicle_id}")
        if site.commissioned_year > year:
            errors.append(f"charger at {c.depot} not commissioned in {year}")
        if (c.power_kw > site.charger_power_kw or c.power_kw <= 0 or
                c.end_min <= c.start_min or not 0 < c.efficiency <= 1):
            errors.append(f"invalid charge power/time for {c.vehicle_id}")
        events[c.vehicle_id].append((c.start_min, c.end_min, "charge", c))
    for vid, schedule in events.items():
        bus = v[vid]
        schedule.sort(key=lambda e: e[0])
        energy = bus.initial_kwh
        for i, (start, end, kind, obj) in enumerate(schedule):
            if i and start < schedule[i - 1][1]:
                errors.append(f"overlapping vehicle activity on {vid}")
            current_location = obj.start_location if kind == "trip" else obj.depot
            prior_location = (schedule[i - 1][3].end_location
                              if schedule[i - 1][2] == "trip" else schedule[i - 1][3].depot) if i else bus.depot
            prior_end = schedule[i - 1][1] if i else 0
            required_deadhead = deadhead_minutes.get((prior_location, current_location))
            if required_deadhead is None:
                missing.append(f"deadhead:{prior_location}->{current_location}")
            elif start - prior_end < required_deadhead:
                errors.append(f"insufficient travel/turn time on {vid} at minute {start}")
            movement_km = deadhead_km.get((prior_location, current_location))
            if movement_km is None:
                missing.append(f"deadhead_km:{prior_location}->{current_location}")
            else:
                energy -= movement_km * bus.kwh_per_km_winter
            if kind == "trip":
                energy -= obj.distance_km * bus.kwh_per_km_winter
            else:
                energy = min(bus.battery_kwh * bus.usable_fraction,
                             energy + obj.power_kw * (end - start) / 60 * obj.efficiency)
            if energy < bus.battery_kwh * bus.minimum_soc_fraction - 1e-9:
                errors.append(f"minimum SOC violated on {vid} at minute {end}")
        if bus.initial_kwh > bus.battery_kwh * bus.usable_fraction + 1e-9:
            errors.append(f"initial SOC exceeds usable energy on {vid}")
        if schedule:
            last_kind, last_obj = schedule[-1][2], schedule[-1][3]
            last_location = last_obj.end_location if last_kind == "trip" else last_obj.depot
            if (last_location, bus.depot) not in deadhead_minutes:
                missing.append(f"deadhead:{last_location}->{bus.depot}")
            if (last_location, bus.depot) not in deadhead_km:
                missing.append(f"deadhead_km:{last_location}->{bus.depot}")
            else:
                energy -= deadhead_km[last_location, bus.depot] * bus.kwh_per_km_winter
                if energy < bus.battery_kwh * bus.minimum_soc_fraction - 1e-9:
                    errors.append(f"minimum SOC violated on return to depot by {vid}")
    for depot in depots:
        if depot.name not in spare_by_depot:
            missing.append(f"spare_policy:{depot.name}")
        times = sorted({z for c in charges if c.depot == depot.name for z in (c.start_min, c.end_min)})
        for a, b in zip(times, times[1:]):
            active = [c for c in charges if c.depot == depot.name and c.start_min < b and c.end_min > a]
            if len(active) > depot.charger_slots:
                errors.append(f"charger slots exceeded at {depot.name}")
            if sum(c.power_kw for c in active) > depot.grid_limit_kw:
                errors.append(f"grid power exceeded at {depot.name}")
        fleet_here = sum(bus.depot == depot.name for bus in vehicles)
        if fleet_here > depot.physical_bus_spaces:
            errors.append(f"bus parking spaces exceeded at {depot.name}")
        active_here = sum(bool(by_vehicle[bus.vehicle_id]) for bus in vehicles if bus.depot == depot.name)
        if fleet_here - active_here < spare_by_depot.get(depot.name, 0):
            errors.append(f"spare requirement not met at {depot.name}")
    return Check("FAIL" if errors else "UNVERIFIED" if missing else "PASS",
                 errors, missing,
                 {"trips": len(trips), "vehicles": len(vehicles), "charges": len(charges)})


def discounted_cost(cashflows: dict[int, float], base_year: int, real_rate: float) -> float:
    if real_rate <= -1:
        raise ValueError("discount rate must exceed -100%")
    return sum(value / (1 + real_rate) ** (year - base_year)
               for year, value in cashflows.items())


def score(baseline: float, plan: float) -> float:
    if baseline <= 0:
        raise ValueError("positive baseline required")
    return 100 * (baseline - plan) / baseline


def cost_result(baseline_cashflow: dict[int, float], plan_cashflow: dict[int, float],
                eligible_grant_cost: dict[int, float], grant_fraction: float,
                real_rate: float = 0.03, base_year: int = 2023) -> dict[str, float]:
    if not 0 <= grant_fraction <= 0.5:
        raise ValueError("grant fraction outside problem range")
    baseline = discounted_cost(baseline_cashflow, base_year, real_rate)
    gross = discounted_cost(plan_cashflow, base_year, real_rate)
    grant = discounted_cost(eligible_grant_cost, base_year, real_rate) * grant_fraction
    return {"baseline_gross_pv": baseline, "plan_gross_pv": gross,
            "incremental_gross_pv": gross - baseline,
            "agency_plan_pv": gross - grant, "grant_transfer_pv": grant,
            "economic_score_gross_pct": score(baseline, gross)}


def environmental_result(baseline: dict[str, float] | None,
                         plan: dict[str, float] | None) -> dict:
    """Compare matched life-cycle boundaries, without discounting physical GHG.

    Required keys are tonnes of CO2e. NOx, PM and battery production are
    deliberately reported separately, rather than merged into one score.
    """
    required = ("vehicle_battery_manufacture_t", "infrastructure_t",
                "fuel_supply_combustion_t", "electricity_t", "maintenance_t",
                "end_of_life_credit_t", "tailpipe_nox_kg", "tailpipe_pm_kg",
                "electricity_kwh", "battery_manufacture_t")
    if baseline is None or plan is None:
        return {"status": "UNVERIFIED", "missing": list(required)}
    missing = [f"baseline:{k}" for k in required if k not in baseline]
    missing += [f"plan:{k}" for k in required if k not in plan]
    if missing:
        return {"status": "UNVERIFIED", "missing": missing}
    def total(case: dict[str, float]) -> float:
        return sum(case[k] for k in required[:5]) - case["end_of_life_credit_t"]
    b, p = total(baseline), total(plan)
    if b <= 0:
        raise ValueError("baseline life-cycle GHG must be positive")
    return {"status": "PASS", "baseline_lifecycle_t": b, "plan_lifecycle_t": p,
            "environment_score_pct": score(b, p),
            "baseline_tailpipe_nox_kg": baseline["tailpipe_nox_kg"],
            "plan_tailpipe_nox_kg": plan["tailpipe_nox_kg"],
            "baseline_tailpipe_pm_kg": baseline["tailpipe_pm_kg"],
            "plan_tailpipe_pm_kg": plan["tailpipe_pm_kg"],
            "baseline_electricity_kwh": baseline["electricity_kwh"],
            "plan_electricity_kwh": plan["electricity_kwh"],
            "baseline_battery_manufacture_t": baseline["battery_manufacture_t"],
            "plan_battery_manufacture_t": plan["battery_manufacture_t"]}


def pareto(points: list[dict], cost_key: str = "cost", emission_key: str = "ghg") -> list[dict]:
    return [p for p in points if not any(
        q is not p and q[cost_key] <= p[cost_key] and q[emission_key] <= p[emission_key]
        and (q[cost_key] < p[cost_key] or q[emission_key] < p[emission_key])
        for q in points)]
