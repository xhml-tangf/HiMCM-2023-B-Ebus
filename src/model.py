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
    # Traction is in kwh_per_km_winter. This separate all-electric load runs
    # during trips, charging, deadhead and active layovers in the duty span.
    # None means the winter accessory demand has not been measured.
    accessory_kwh_per_hour_winter: float | None = None
    # Explicit supply type avoids imposing a fictitious battery on diesel or
    # grid-fed trolley vehicles. Defaults preserve the battery-bus interface.
    energy_source: str = "battery"
    fuel: FuelSystem | None = None
    overhead_peak_kw: float | None = None


@dataclass(frozen=True)
class FuelSystem:
    """All-in fuel use = distance term + time term; no en-route refuelling.

    Rates must be jointly calibrated, not two alternative all-in averages.
    The unit can be L or kg, but every quantity must use that same unit.
    """
    unit: str
    tank_capacity: float
    initial: float
    reserve: float
    units_per_km_winter: float
    units_per_hour_winter: float


@dataclass(frozen=True)
class OverheadFeeder:
    """Firm power available to the modeled fleet, after other loads/reserve."""
    name: str
    firm_power_kw: float
    commissioned_year: int


@dataclass(frozen=True)
class Assignment:
    trip_id: str
    vehicle_id: str


@dataclass(frozen=True)
class Charge:
    vehicle_id: str
    depot: str  # Site name; may be home depot or an in-route terminal.
    start_min: int
    end_min: int
    power_kw: float
    efficiency: float


@dataclass(frozen=True)
class Depot:
    """Charging site; terminal sites use physical_bus_spaces=0."""
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
    overhead_paths: dict[tuple[str, ...], tuple[str, ...]] | None = None,
    overhead_feeders: Iterable[OverheadFeeder] | None = None,
) -> Check:
    """Exact trip/SOC/site checks. Missing essential inputs yield UNVERIFIED.

    Trip continuity requires deadhead time and distance between locations.
    A zero value is permitted only when colocation is established. Charging
    sites may be terminals away from the home depot. Winter traction energy
    and all-electric accessory power are separate; accessory power is assumed
    on continuously from the first to last scheduled event. Fuel vehicles
    require a measured fuel budget. Trolleys require certified wired paths
    and concurrent feeder power; missing inputs never imply battery supply.
    Path keys are ('trip', trip_id), ('link', origin, destination), and
    ('location', name) for stationary accessories. A path lists every feeder
    traversed; reserving peak draw on each for the full segment is conservative.
    Deadheads depart as late as possible and return immediately after duty.
    Split duties or
    provide measured duty profiles if a bus shuts its accessories off.
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
    feeders = {x.name: x for x in (overhead_feeders or [])}
    overhead_loads: list[tuple[str, int, int, float]] = []
    busy: dict[str, list[tuple[int, int]]] = {key: [] for key in v}
    if not trips or not vehicles or not depots:
        return Check("UNVERIFIED", missing=["nonempty_trip_vehicle_depot_data"])
    if len(t) != len(trips) or len(v) != len(vehicles) or len(d) != len(depots):
        errors.append("duplicate trip, vehicle, or depot identifier")
    if year >= 2033:
        for bus in vehicles:
            if not (bus.electric_propulsion and bus.electric_accessories):
                errors.append(f"non-electric 2033 fleet vehicle {bus.vehicle_id}")
    for bus in vehicles:
        if bus.depot not in d:
            missing.append(f"home_depot:{bus.vehicle_id}:{bus.depot}")
        if bus.energy_source not in {"battery", "fuel", "overhead"}:
            errors.append(f"unknown energy source on {bus.vehicle_id}")
        elif (bus.energy_source == "fuel") == bus.electric_propulsion:
            errors.append(f"inconsistent propulsion/supply on {bus.vehicle_id}")
        if bus.energy_source in {"battery", "overhead"}:
            if bus.accessory_kwh_per_hour_winter is None:
                missing.append(f"winter_electric_accessory_demand:{bus.vehicle_id}")
            elif bus.accessory_kwh_per_hour_winter < 0:
                errors.append(f"negative winter accessory demand on {bus.vehicle_id}")
        if bus.energy_source == "battery" and not (
                bus.battery_kwh > 0 and 0 <= bus.minimum_soc_fraction < bus.usable_fraction <= 1
                and bus.battery_kwh * bus.minimum_soc_fraction <= bus.initial_kwh
                <= bus.battery_kwh * bus.usable_fraction
                and bus.kwh_per_km_winter >= 0):
            errors.append(f"invalid battery energy parameters on {bus.vehicle_id}")
        if bus.energy_source == "fuel":
            fuel = bus.fuel
            if fuel is None:
                missing.append(f"winter_fuel_budget:{bus.vehicle_id}")
            elif not (fuel.unit in {"L", "kg"} and fuel.tank_capacity > 0
                      and 0 <= fuel.reserve <= fuel.initial <= fuel.tank_capacity
                      and fuel.units_per_km_winter >= 0 and fuel.units_per_hour_winter >= 0):
                errors.append(f"invalid fuel parameters on {bus.vehicle_id}")
        if bus.energy_source == "overhead":
            if bus.overhead_peak_kw is None:
                missing.append(f"overhead_peak_demand:{bus.vehicle_id}")
            elif bus.overhead_peak_kw <= 0 or bus.overhead_peak_kw < (bus.accessory_kwh_per_hour_winter or 0):
                errors.append(f"invalid overhead peak demand on {bus.vehicle_id}")
    by_trip: dict[str, list[str]] = {k: [] for k in t}
    for trip in trips:
        if trip.distance_km < 0 or trip.end_min <= trip.start_min or trip.baseline_capacity <= 0:
            errors.append(f"invalid trip parameters on {trip.trip_id}")
    by_vehicle: dict[str, list[Trip]] = {k: [] for k in v}
    seen_assignments: set[tuple[str, str]] = set()
    for a in assignments:
        if a.trip_id not in t or a.vehicle_id not in v:
            errors.append(f"unknown assignment {a.trip_id}/{a.vehicle_id}")
            continue
        trip, bus = t[a.trip_id], v[a.vehicle_id]
        if (a.trip_id, a.vehicle_id) in seen_assignments:
            errors.append(f"duplicate assignment {a.trip_id}/{a.vehicle_id}")
            continue
        seen_assignments.add((a.trip_id, a.vehicle_id))
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
        if site.commissioned_year > year:
            errors.append(f"charger at {c.depot} not commissioned in {year}")
        if (c.power_kw > site.charger_power_kw or c.power_kw <= 0 or
                c.end_min <= c.start_min or not 0 < c.efficiency <= 1):
            errors.append(f"invalid charge power/time for {c.vehicle_id}")
        events[c.vehicle_id].append((c.start_min, c.end_min, "charge", c))
    def overhead_segment(bus: Vehicle, key: tuple[str, ...], start: int,
                         end: int, power: float) -> None:
        if end <= start or power <= 0:
            return
        path = (overhead_paths or {}).get(key)
        if not path:
            missing.append(f"wired_path:{':'.join(key)}")
            return
        for name in set(path):
            feeder = feeders.get(name)
            if feeder is None:
                missing.append(f"overhead_feeder:{name}")
            elif feeder.commissioned_year > year:
                errors.append(f"overhead feeder {name} not commissioned in {year}")
            else:
                overhead_loads.append((name, start, end, power))

    for vid, schedule in events.items():
        bus = v[vid]
        schedule.sort(key=lambda e: e[0])
        energy = bus.initial_kwh
        fuel_left = bus.fuel.initial if bus.fuel else 0.0
        auxiliary_kw = bus.accessory_kwh_per_hour_winter or 0.0

        def consume(start: int, end: int, distance: float,
                    path_key: tuple[str, ...], *, charge: Charge | None = None) -> None:
            nonlocal energy, fuel_left
            duration = max(0, end - start) / 60
            if bus.energy_source == "battery":
                energy -= distance * bus.kwh_per_km_winter
                if charge is not None:
                    energy = min(bus.battery_kwh * bus.usable_fraction,
                                 energy + (charge.power_kw * charge.efficiency
                                           - auxiliary_kw) * duration)
                else:
                    energy -= auxiliary_kw * duration
                if energy < bus.battery_kwh * bus.minimum_soc_fraction - 1e-9:
                    errors.append(f"minimum SOC violated on {vid} at minute {end}")
            elif bus.energy_source == "fuel" and bus.fuel is not None:
                fuel_left -= (distance * bus.fuel.units_per_km_winter
                              + duration * bus.fuel.units_per_hour_winter)
                if fuel_left < bus.fuel.reserve - 1e-9:
                    errors.append(f"fuel reserve violated on {vid} at minute {end}")
            elif bus.energy_source == "overhead":
                power = auxiliary_kw if path_key[0] == "location" else (bus.overhead_peak_kw or 0)
                overhead_segment(bus, path_key, start, end, power)

        prior_location = bus.depot
        prior_end = 0
        for i, (start, end, kind, obj) in enumerate(schedule):
            if end <= start:
                errors.append(f"invalid vehicle activity interval on {vid}")
            if i and start < prior_end:
                errors.append(f"overlapping vehicle activity on {vid}")
            current_location = obj.start_location if kind == "trip" else obj.depot
            link = (prior_location, current_location)
            movement_minutes = deadhead_minutes.get(link)
            movement_km = deadhead_km.get(link)
            if movement_minutes is None:
                missing.append(f"deadhead:{prior_location}->{current_location}")
            elif movement_minutes < 0 or start - prior_end < movement_minutes:
                errors.append(f"insufficient travel/turn time on {vid} at minute {start}")
            if movement_km is None:
                missing.append(f"deadhead_km:{prior_location}->{current_location}")
            elif movement_km < 0 or (movement_km > 0 and movement_minutes == 0):
                errors.append(f"invalid deadhead distance/time on {vid}")
            if movement_minutes is not None and movement_km is not None:
                departure = start - movement_minutes
                if i:
                    consume(prior_end, departure, 0, ("location", prior_location))
                if movement_minutes > 0:
                    busy[vid].append((departure, start))
                consume(departure, start, movement_km, ("link", *link))
            if kind == "charge" and bus.energy_source != "battery":
                errors.append(f"plug-in charge assigned to {bus.energy_source} vehicle {vid}")
            consume(start, end, obj.distance_km if kind == "trip" else 0,
                    ("trip", obj.trip_id) if kind == "trip" else ("location", obj.depot),
                    charge=obj if kind == "charge" else None)
            busy[vid].append((start, end))
            prior_location = obj.end_location if kind == "trip" else obj.depot
            prior_end = end
        if schedule:
            link = (prior_location, bus.depot)
            minutes, km = deadhead_minutes.get(link), deadhead_km.get(link)
            if minutes is None:
                missing.append(f"deadhead:{prior_location}->{bus.depot}")
            elif minutes < 0:
                errors.append(f"negative return travel time on {vid}")
            if km is None:
                missing.append(f"deadhead_km:{prior_location}->{bus.depot}")
            elif km < 0 or (km > 0 and minutes == 0):
                errors.append(f"invalid return distance/time on {vid}")
            if minutes is not None and km is not None:
                consume(prior_end, prior_end + minutes, km, ("link", *link))
                if minutes > 0:
                    busy[vid].append((prior_end, prior_end + minutes))

    for name, feeder in feeders.items():
        if feeder.firm_power_kw < 0:
            errors.append(f"negative overhead feeder power at {name}")
        boundaries = sorted({m for f, a, b, _ in overhead_loads if f == name for m in (a, b)})
        for a, b in zip(boundaries, boundaries[1:]):
            load = sum(power for f, start, end, power in overhead_loads
                       if f == name and start < b and end > a)
            if load > feeder.firm_power_kw + 1e-9:
                errors.append(f"overhead feeder power exceeded at {name}")
                break
    for depot in depots:
        times = sorted({z for c in charges if c.depot == depot.name for z in (c.start_min, c.end_min)})
        for a, b in zip(times, times[1:]):
            active = [c for c in charges if c.depot == depot.name and c.start_min < b and c.end_min > a]
            if len(active) > depot.charger_slots:
                errors.append(f"charger slots exceeded at {depot.name}")
            if sum(c.power_kw for c in active) > depot.grid_limit_kw:
                errors.append(f"grid power exceeded at {depot.name}")
        fleet_here = sum(bus.depot == depot.name for bus in vehicles)
        if fleet_here and depot.name not in spare_by_depot:
            missing.append(f"spare_policy:{depot.name}")
        if fleet_here > depot.physical_bus_spaces:
            errors.append(f"bus parking spaces exceeded at {depot.name}")
        # A spare must be physically at its depot and free of a trip or charge.
        # Counting only vehicles with no trips anywhere in the day undercounts
        # buses that return to the garage between peaks.
        boundaries = sorted({0} | {minute for bus in vehicles if bus.depot == depot.name
                                  for start, end in busy[bus.vehicle_id]
                                  for minute in (start, end)})
        for moment in boundaries:
            available = 0
            for bus in vehicles:
                if bus.depot != depot.name:
                    continue
                activity = events[bus.vehicle_id]
                if any(start <= moment < end for start, end in busy[bus.vehicle_id]):
                    continue
                prior = [event for event in activity if event[1] <= moment]
                last_location = (prior[-1][3].end_location if prior[-1][2] == "trip"
                                 else prior[-1][3].depot) if prior else bus.depot
                if prior and not any(e[0] >= prior[-1][1] for e in activity):
                    return_time = deadhead_minutes.get((last_location, depot.name))
                    if return_time is not None and moment >= prior[-1][1] + return_time:
                        last_location = depot.name
                if last_location == depot.name:
                    available += 1
            if available < spare_by_depot.get(depot.name, 0):
                errors.append(f"spare requirement not met at {depot.name} minute {moment}")
                break
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
