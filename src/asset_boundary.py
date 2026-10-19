"""Vehicle terminal-value and early-retirement ledger for the class scenario.

The 2023 age profile is unavailable at vehicle level. The central asset memo
therefore uses the same explicit uniform-age scenario as the ordinary-renewal
model and a straight-line economic life. Values are replacement-cost proxies;
they are not bids or accounting-book values.
"""

from __future__ import annotations

from collections import defaultdict


def uniform_ages(count: int, max_age: int = 16) -> dict[int, int]:
    if count < 0:
        raise ValueError("negative vehicle count")
    quotient, remainder = divmod(count, max_age + 1)
    return {age: quotient + (age < remainder) for age in range(max_age + 1)}


def age_one_year(ages: dict[int, int]) -> dict[int, int]:
    return {age + 1: count for age, count in ages.items() if count}


def retire_oldest(ages: dict[int, int], count: int) -> tuple[dict[int, int], dict[int, int]]:
    if count < 0 or count > sum(ages.values()):
        raise ValueError("invalid retirement count")
    remaining, retired = dict(ages), defaultdict(int)
    for age in sorted(remaining, reverse=True):
        take = min(remaining[age], count)
        remaining[age] -= take
        retired[age] += take
        count -= take
        if not count:
            break
    return {a: n for a, n in remaining.items() if n}, dict(retired)


def residual_fraction(age: int, life: int = 17) -> float:
    return max(0.0, min(1.0, (life - age) / life))


def terminal_value(ages: dict[int, int], unit_cost: float, life: int = 17) -> float:
    return sum(count * unit_cost * residual_fraction(age, life)
               for age, count in ages.items())


def early_retirement_value(retired: dict[int, int], unit_cost: float,
                           recovery_fraction: float, life: int = 17) -> float:
    if not 0 <= recovery_fraction <= 1:
        raise ValueError("recovery fraction outside [0, 1]")
    return recovery_fraction * sum(
        count * unit_cost * residual_fraction(age, life)
        for age, count in retired.items()
    )


def simulate_class(initial_ages: dict[int, int], purchases: dict[int, int],
                   retirements: dict[int, int], years=range(2024, 2034)):
    ages = dict(initial_ages)
    retired_events = {}
    for year in years:
        ages = age_one_year(ages)
        ages, retired = retire_oldest(ages, int(retirements.get(year, 0)))
        if retired:
            retired_events[year] = retired
        bought = int(purchases.get(year, 0))
        if bought:
            ages[0] = ages.get(0, 0) + bought
    return ages, retired_events
